import os
import re
import shutil
import zipfile
import tempfile
import subprocess
import urllib.request
import urllib.parse
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
from services.analyzer.archive_validator import archive_validator, ArchiveSecurityError
from services.analyzer.detector import project_detector, AnalysisResult

logger = logging.getLogger("ziref.git_importer")

class GitSecurityError(Exception):
    pass

class GitImporter:
    """
    Securely clones or downloads a remote Git repository into a sanitized ZIP archive,
    extracts it safely, and detects project configuration.
    Supports GitHub, GitLab, Bitbucket, and arbitrary public Git repos.
    """

    SAFE_URL_REGEX = re.compile(r"^https?://[a-zA-Z0-9_\-\.]+(?::[0-9]+)?(?:/[a-zA-Z0-9_\-\./]+)?(?:\.git)?/?$")

    def validate_url(self, repo_url: str) -> str:
        cleaned = repo_url.strip()
        if not cleaned:
            raise GitSecurityError("Repository URL cannot be empty.")
        if cleaned.startswith("-"):
            raise GitSecurityError("Invalid repository URL: cannot start with hyphens.")

        # Auto-prepend https:// if user omitted scheme (e.g. github.com/owner/repo)
        if not (cleaned.startswith("https://") or cleaned.startswith("http://")):
            if cleaned.startswith("ssh://") or cleaned.startswith("file://") or cleaned.startswith("git://") or "@" in cleaned:
                raise GitSecurityError("Only HTTP and HTTPS repository URLs are supported.")
            cleaned = f"https://{cleaned}"

        # Strip fragment and query parameters
        parsed = urllib.parse.urlsplit(cleaned)
        if parsed.scheme not in ["http", "https"]:
            raise GitSecurityError("Only HTTP and HTTPS repository URLs are supported.")

        # Prevent shell injection characters
        forbidden_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r", "\t", '"', "'", "\\"]
        for ch in forbidden_chars:
            if ch in cleaned:
                raise GitSecurityError("Malformed or unsafe repository URL format: contains disallowed characters.")

        # Clean path: strip trailing slashes but preserve essential path
        clean_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))

        if not self.SAFE_URL_REGEX.match(clean_url):
            raise GitSecurityError("Malformed or unsafe repository URL format.")

        return clean_url

    def parse_repo_details(self, repo_url: str) -> Dict[str, Any]:
        """
        Parses repository URL into components.
        Extracts owner, repo, branch, subpath from URLs like:
        https://github.com/owner/repo/tree/main/packages/frontend
        """
        valid_url = self.validate_url(repo_url)
        parsed = urllib.parse.urlsplit(valid_url)
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]

        owner = parts[0] if len(parts) >= 1 else ""
        repo_raw = parts[1] if len(parts) >= 2 else ""
        repo = repo_raw.removesuffix(".git")

        branch = None
        subpath = None

        # Check for /tree/<branch>/<subpath> or /blob/<branch>/<subpath>
        if len(parts) >= 4 and parts[2] in ["tree", "blob"]:
            branch = parts[3]
            if len(parts) > 4:
                subpath = "/".join(parts[4:])
            clean_url = f"{parsed.scheme}://{parsed.netloc}/{owner}/{repo}.git"
        else:
            clean_url = valid_url

        return {
            "valid_url": valid_url,
            "clean_url": clean_url,
            "host": parsed.netloc.lower(),
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "subpath": subpath
        }

    def _clean_dir(self, directory: str) -> None:
        """Empties a directory without removing the directory itself."""
        for item in os.listdir(directory):
            p = os.path.join(directory, item)
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    os.remove(p)
            except Exception:
                pass

    def clone_or_download_repo(self, repo_url: str, branch: Optional[str] = None, target_workspace: Optional[str] = None) -> Tuple[str, str, int, str]:
        """
        Clones or downloads repository into a workspace.
        Returns: (workspace_dir, zip_path, file_size, checksum)
        """
        details = self.parse_repo_details(repo_url)
        clean_url = details["clean_url"]
        target_branch = branch.strip() if branch and branch.strip() else details["branch"]

        temp_dir = tempfile.mkdtemp(prefix="ziref_git_")

        try:
            cloned = False
            git_bin = shutil.which("git")

            # 1. Try git CLI if available
            if git_bin:
                # Attempt A: clone specified branch if requested
                if target_branch and re.match(r"^[a-zA-Z0-9_\-\./]+$", target_branch):
                    cmd = [git_bin, "clone", "--depth", "1", "--branch", target_branch, clean_url, temp_dir]
                    try:
                        subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=120,
                            check=True
                        )
                        cloned = True
                        logger.info(f"Successfully cloned {clean_url} on branch '{target_branch}'")
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                        logger.warning(f"Git clone with branch '{target_branch}' failed ({e}). Retrying default branch...")
                        self._clean_dir(temp_dir)

                # Attempt B: clone default branch if no branch specified or branch clone failed
                if not cloned:
                    cmd = [git_bin, "clone", "--depth", "1", clean_url, temp_dir]
                    try:
                        subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=120,
                            check=True
                        )
                        cloned = True
                        logger.info(f"Successfully cloned default branch of {clean_url}")
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                        logger.warning(f"Git clone default branch failed ({e}). Attempting archive download...")
                        self._clean_dir(temp_dir)

            # 2. Fallback to GitHub archive download if git CLI failed or not present
            if not cloned and "github.com" in details["host"] and details["owner"] and details["repo"]:
                owner = details["owner"]
                repo = details["repo"]

                candidate_urls = []
                if target_branch:
                    candidate_urls.append(f"https://github.com/{owner}/{repo}/archive/refs/heads/{target_branch}.zip")
                # Universal default branch HEAD.zip
                candidate_urls.append(f"https://github.com/{owner}/{repo}/archive/HEAD.zip")
                candidate_urls.append(f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip")
                candidate_urls.append(f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip")

                for zip_url in candidate_urls:
                    try:
                        req = urllib.request.Request(
                            zip_url,
                            headers={"User-Agent": "Ziref-Deployer/1.0"}
                        )
                        with urllib.request.urlopen(req, timeout=60) as resp:
                            zip_bytes = resp.read()

                        temp_zip = os.path.join(temp_dir, "archive.zip")
                        with open(temp_zip, "wb") as f:
                            f.write(zip_bytes)
                        with zipfile.ZipFile(temp_zip, "r") as zf:
                            zf.extractall(temp_dir)
                        os.remove(temp_zip)
                        cloned = True
                        logger.info(f"Successfully downloaded repository archive from {zip_url}")
                        break
                    except Exception as ex:
                        logger.debug(f"Archive download failed for {zip_url}: {ex}")
                        self._clean_dir(temp_dir)

            if not cloned:
                raise GitSecurityError(f"Could not clone or download repository from '{repo_url}'. Verify URL, branch name, and public accessibility.")

            # Remove .git directory if present to avoid storing large git history
            dot_git = os.path.join(temp_dir, ".git")
            if os.path.exists(dot_git):
                def _handle_readonly(func, path, _):
                    import stat
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass
                shutil.rmtree(dot_git, onerror=_handle_readonly)

            # If GitHub extracted a single root folder (e.g. repo-main/ or repo-HEAD/), resolve it
            subdirs = [os.path.join(temp_dir, d) for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d)) and d != ".git"]
            effective_dir = temp_dir
            if len(subdirs) == 1 and len([e for e in os.listdir(temp_dir) if e != ".git"]) == 1:
                effective_dir = subdirs[0]

            # If a subpath was requested in the URL (e.g. tree/main/client), target it
            if details["subpath"]:
                sub_target = os.path.join(effective_dir, details["subpath"])
                if os.path.isdir(sub_target):
                    logger.info(f"Targeting requested subfolder: {details['subpath']}")
                    effective_dir = sub_target

            # 3. Create a clean ZIP archive of this project directory (exclude .git entirely)
            target_zip = os.path.join(tempfile.gettempdir(), f"git_export_{os.path.basename(temp_dir)}.zip")
            with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(effective_dir):
                    if ".git" in dirs:
                        dirs.remove(".git")
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, effective_dir)
                        zf.write(full_path, rel_path)

            with open(target_zip, "rb") as f:
                content = f.read()
            file_size = len(content)
            checksum = hashlib.sha256(content).hexdigest()

            return effective_dir, target_zip, file_size, checksum

        except Exception:
            if os.path.exists(temp_dir):
                def _handle_readonly(func, path, _):
                    import stat
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass
                shutil.rmtree(temp_dir, onerror=_handle_readonly)
            raise

git_importer = GitImporter()

