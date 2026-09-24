import os
import re
import shutil
import zipfile
import tempfile
import subprocess
import urllib.request
import urllib.parse
import hashlib
from typing import Dict, Any, Optional, Tuple
from services.analyzer.archive_validator import archive_validator, ArchiveSecurityError
from services.analyzer.detector import project_detector, AnalysisResult

class GitSecurityError(Exception):
    pass

class GitImporter:
    """
    Securely clones or downloads a remote Git repository into a sanitized ZIP archive,
    extracts it safely, and detects project configuration.
    """

    SAFE_URL_REGEX = re.compile(r"^https?://[a-zA-Z0-9_\-\.]+(?::[0-9]+)?/[a-zA-Z0-9_\-\./]+(?:\.git)?/?$")

    def validate_url(self, repo_url: str) -> str:
        cleaned = repo_url.strip()
        if cleaned.startswith("-"):
            raise GitSecurityError("Invalid repository URL: cannot start with hyphens.")
        if not (cleaned.startswith("https://") or cleaned.startswith("http://")):
            raise GitSecurityError("Only HTTP and HTTPS repository URLs are supported.")
        if not self.SAFE_URL_REGEX.match(cleaned):
            raise GitSecurityError("Malformed or unsafe repository URL format.")
        return cleaned

    def clone_or_download_repo(self, repo_url: str, branch: Optional[str] = None, target_workspace: Optional[str] = None) -> Tuple[str, str, int, str]:
        """
        Clones or downloads repository into a workspace.
        Returns: (workspace_dir, zip_path, file_size, checksum)
        """
        valid_url = self.validate_url(repo_url)
        temp_dir = tempfile.mkdtemp(prefix="ziref_git_")

        try:
            cloned = False
            # 1. Try git CLI if available
            git_bin = shutil.which("git")
            if git_bin:
                cmd = [git_bin, "clone", "--depth", "1"]
                if branch and re.match(r"^[a-zA-Z0-9_\-\./]+$", branch):
                    cmd.extend(["--branch", branch])
                cmd.extend([valid_url, temp_dir])

                try:
                    res = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=120,
                        check=True
                    )
                    cloned = True
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    # Fallback to direct archive download if GitHub
                    pass

            # 2. Fallback to GitHub archive download if git CLI failed or not present
            if not cloned:
                if "github.com" in valid_url:
                    parsed = urllib.parse.urlparse(valid_url)
                    path_parts = parsed.path.strip("/").removesuffix(".git").split("/")
                    if len(path_parts) >= 2:
                        owner, repo = path_parts[0], path_parts[1]
                        ref = branch or "main"
                        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{ref}.zip"
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
                        except Exception:
                            # Try master branch if main failed
                            if ref == "main":
                                zip_url_master = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
                                try:
                                    req = urllib.request.Request(zip_url_master, headers={"User-Agent": "Ziref-Deployer/1.0"})
                                    with urllib.request.urlopen(req, timeout=60) as resp:
                                        zip_bytes = resp.read()
                                    temp_zip = os.path.join(temp_dir, "archive.zip")
                                    with open(temp_zip, "wb") as f:
                                        f.write(zip_bytes)
                                    with zipfile.ZipFile(temp_zip, "r") as zf:
                                        zf.extractall(temp_dir)
                                    os.remove(temp_zip)
                                    cloned = True
                                except Exception:
                                    pass

            if not cloned:
                raise GitSecurityError(f"Could not clone or download repository from '{valid_url}'. Verify URL and permissions.")

            # Remove .git directory if present to avoid storing large git history
            dot_git = os.path.join(temp_dir, ".git")
            if os.path.exists(dot_git):
                shutil.rmtree(dot_git, ignore_errors=True)

            # If GitHub extracted a single root folder (e.g. repo-main/), resolve it
            subdirs = [os.path.join(temp_dir, d) for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
            effective_dir = temp_dir
            if len(subdirs) == 1 and len(os.listdir(temp_dir)) == 1:
                effective_dir = subdirs[0]

            # 3. Create a clean ZIP archive of this project directory
            target_zip = os.path.join(tempfile.gettempdir(), f"git_export_{os.path.basename(temp_dir)}.zip")
            with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(effective_dir):
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
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise

git_importer = GitImporter()
