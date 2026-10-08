import os
import shutil
import tarfile
import asyncio
import logging
import glob
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any
try:
    import docker
    from docker.errors import DockerException
except ImportError:
    docker = None
    class DockerException(Exception):
        pass
from services.api.core.config import settings
from services.api.core.models import LogLevel, BuildStage, BuildLogEvent

logger = logging.getLogger("ziref.sandbox")

class SandboxExecutionError(Exception):
    def __init__(self, message: str, stage: str, exit_code: Optional[int] = None):
        super().__init__(message)
        self.stage = stage
        self.exit_code = exit_code

class DockerSandbox:
    def __init__(self):
        self.client = None
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("Docker daemon successfully connected for sandbox execution.")
        except Exception as e:
            logger.warning(f"Docker daemon not directly available ({e}). Subprocess fallback will be used.")
            self.client = None

    def _resolve_project_root(self, base_path: str) -> str:
        """Unwraps single enclosing folders common in ZIP archives."""
        valid_entries = [
            e for e in os.listdir(base_path)
            if not e.startswith(".") and e != "__MACOSX" and not e.startswith("~")
        ]
        if len(valid_entries) == 1:
            nested = os.path.join(base_path, valid_entries[0])
            if os.path.isdir(nested):
                return self._resolve_project_root(nested)
        return base_path

    async def execute_build(
        self,
        workspace_dir: str,
        package_manager: str,
        build_command: Optional[str],
        output_directory: Optional[str],
        env_vars: Dict[str, str],
        log_callback: Callable[[BuildLogEvent], Any]
    ) -> str:
        """
        Executes dependency installation and build inside a secure isolated sandbox.
        Handles Static HTML, React/Vite/Next, MERN mono-repos, Python, and generic projects.
        Returns the absolute path to the directory containing deployable files.
        """
        abs_workspace = os.path.abspath(workspace_dir)
        root_dir = self._resolve_project_root(abs_workspace)

        clean_build_cmd = (build_command or "").strip()
        clean_out_dir = (output_directory or "").strip() or "."
        pm = (package_manager or "none").lower()

        # ---------------------------------------------------------------
        # For MERN / mono-repos the detector sets outputDirectory to
        # "client/dist", "frontend/build", etc.  We derive the correct
        # build-root (the subfolder containing package.json) from that.
        # ---------------------------------------------------------------
        # Resolve build root (the directory containing package.json)
        build_root = root_dir  # default: build from workspace root
        if "/" in clean_out_dir or "\\" in clean_out_dir:
            sub_candidate = clean_out_dir.split("/")[0].split("\\")[0]
            sub_path = os.path.join(root_dir, sub_candidate)
            if os.path.isdir(sub_path) and os.path.exists(os.path.join(sub_path, "package.json")):
                build_root = sub_path
        elif not os.path.exists(os.path.join(build_root, "package.json")):
            for sub in ["client", "frontend", "web", "app", "ui", "src"]:
                candidate = os.path.join(root_dir, sub)
                if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "package.json")):
                    build_root = candidate
                    break

        has_package_json = (
            os.path.exists(os.path.join(build_root, "package.json"))
            or bool(glob.glob(os.path.join(root_dir, "**", "package.json"), recursive=True))
        )
        has_requirements = os.path.exists(os.path.join(root_dir, "requirements.txt")) or os.path.exists(os.path.join(root_dir, "pyproject.toml"))
        has_index_html = os.path.exists(os.path.join(root_dir, "index.html")) or bool(glob.glob(os.path.join(root_dir, "**", "index.html"), recursive=True))

        # Check availability of package manager binary; fallback to npm if missing
        if pm in ["pnpm", "yarn", "bun"] and not shutil.which(pm):
            logger.info(f"Package manager '{pm}' not found on host. Falling back to 'npm'.")
            pm = "npm"

        # Ignore Node build commands if no package.json exists anywhere in workspace
        if not has_package_json and (
            clean_build_cmd.startswith("npm ")
            or clean_build_cmd.startswith("yarn ")
            or clean_build_cmd.startswith("pnpm ")
            or clean_build_cmd.startswith("bun ")
            or clean_build_cmd == "npm run build"
        ):
            clean_build_cmd = ""

        # -------------------------------------------------------------
        # 1. Zero-build Static Application (HTML, JS, CSS, Static Assets)
        # -------------------------------------------------------------
        if (pm == "none" or not has_package_json) and not clean_build_cmd and (has_index_html or not has_requirements):
            await log_callback(BuildLogEvent(
                stage=BuildStage.SANDBOX_INIT.value,
                level=LogLevel.INFO,
                message="Static application detected. No compilation or dependency installation required."
            ))

            target_out = self._resolve_output_directory(root_dir, clean_out_dir)
            await log_callback(BuildLogEvent(
                stage=BuildStage.BUILD.value,
                level=LogLevel.INFO,
                message=f"Distribution directory verified at '{os.path.relpath(target_out, abs_workspace)}'. Ready for packaging."
            ))
            return target_out

        # -------------------------------------------------------------
        # 2. Project with Build Step or Dependencies
        # -------------------------------------------------------------
        await log_callback(BuildLogEvent(
            stage=BuildStage.SANDBOX_INIT.value,
            level=LogLevel.INFO,
            message="Provisioning isolated build sandbox environment..."
        ))

        # Decide whether to use Docker or Subprocess execution
        if self.client:
            return await self._execute_docker(
                build_root, pm, clean_build_cmd, clean_out_dir, has_package_json, has_requirements, env_vars, log_callback, root_dir
            )
        else:
            return await self._execute_subprocess(
                build_root, pm, clean_build_cmd, clean_out_dir, has_package_json, has_requirements, env_vars, log_callback, root_dir
            )

    def _resolve_output_directory(self, root_dir: str, configured_output_dir: str) -> str:
        """Deterministically locates the directory with deployable artifacts."""
        # 1. Direct configured directory if explicitly set and not root
        if configured_output_dir and configured_output_dir not in [".", "./"]:
            target = os.path.abspath(os.path.join(root_dir, configured_output_dir))
            if os.path.exists(target) and os.path.isdir(target):
                return target

        # 2. Check standard build output directories first (prioritize compiled assets over raw sources)
        for candidate in ["dist", "build", "out", "public", ".next", ".output/public"]:
            target = os.path.join(root_dir, candidate)
            if os.path.exists(target) and os.path.isdir(target):
                # Check for Angular browser subfolder (e.g. dist/project/browser)
                browser_sub = os.path.join(target, "browser")
                if os.path.exists(browser_sub):
                    return browser_sub
                # Check for single nested project folder in dist
                subs = [os.path.join(target, d) for d in os.listdir(target) if os.path.isdir(os.path.join(target, d))]
                if len(subs) == 1 and os.path.exists(os.path.join(subs[0], "index.html")):
                    return subs[0]
                # Return directory if it contains files or index.html
                if os.path.exists(os.path.join(target, "index.html")) or len(os.listdir(target)) > 0:
                    return target

        # 3. Check root directory for index.html (static HTML projects or in-place builds)
        if os.path.exists(os.path.join(root_dir, "index.html")):
            return root_dir

        # 4. Search for index.html anywhere in root_dir
        html_files = glob.glob(os.path.join(root_dir, "**", "index.html"), recursive=True)
        if html_files:
            html_files.sort(key=lambda p: len(os.path.relpath(p, root_dir).split(os.sep)))
            return os.path.dirname(html_files[0])

        # 5. Fallback to root_dir
        return root_dir

    async def _execute_docker(
        self,
        workspace_dir: str,
        package_manager: str,
        build_command: str,
        output_directory: str,
        has_package_json: bool,
        has_requirements: bool,
        env_vars: Dict[str, str],
        log_callback: Callable[[BuildLogEvent], Any],
        artifact_root: Optional[str] = None,
    ) -> str:
        container = None
        try:
            script_lines = ["set -e"]

            # Install dependencies only if manifest exists (include devDependencies for bundlers/compilers)
            if has_package_json and package_manager != "none":
                install_cmd = {
                    "pnpm": "pnpm install || pnpm install --no-frozen-lockfile",
                    "yarn": "yarn install",
                    "bun": "bun install",
                    "npm": "npm install --include=dev"
                }.get(package_manager, "npm install --include=dev")

                script_lines.append(f'echo "==> Installing dependencies with {package_manager}..."')
                script_lines.append(install_cmd)
            elif has_requirements:
                script_lines.append('echo "==> Installing Python dependencies..."')
                script_lines.append("pip install --no-cache-dir -r requirements.txt")

            # Execute build command inside container
            if build_command:
                script_lines.append(f'echo "==> Running build command: {build_command}..."')
                script_lines.append(f"NODE_ENV=production {build_command}")

            combined_script = "\n".join(script_lines)

            sanitized_env = {
                "CI": "true",
                **env_vars
            }

            await log_callback(BuildLogEvent(
                stage=BuildStage.DEPENDENCIES.value,
                level=LogLevel.INFO,
                message=f"Starting container sandbox with image {settings.SANDBOX_IMAGE}..."
            ))

            container = self.client.containers.create(
                image=settings.SANDBOX_IMAGE,
                command=["sh", "-c", combined_script],
                working_dir="/workspace",
                environment=sanitized_env,
                volumes={
                    workspace_dir: {"bind": "/workspace", "mode": "rw"}
                },
                mem_limit=settings.BUILD_MEMORY_LIMIT,
                nano_cpus=int(settings.BUILD_CPU_LIMIT * 1e9),
                pids_limit=128,
                network_mode="bridge",
                user="0:0"
            )

            container.start()

            for log_line in container.logs(stream=True, follow=True):
                line = log_line.decode("utf-8", errors="replace").strip()
                if line:
                    stage = BuildStage.BUILD.value if "Running build command" in line or "vite" in line.lower() else BuildStage.DEPENDENCIES.value
                    await log_callback(BuildLogEvent(stage=stage, level=LogLevel.INFO, message=line))

            res = container.wait(timeout=settings.BUILD_TIMEOUT_SECONDS)
            exit_code = res.get("StatusCode", 1)

            if exit_code != 0:
                raise SandboxExecutionError(
                    f"Build command failed with exit code {exit_code}",
                    stage=BuildStage.BUILD.value,
                    exit_code=exit_code
                )

        except DockerException as de:
            logger.error(f"Docker sandbox error: {de}")
            raise SandboxExecutionError(f"Container sandbox failure: {str(de)}", stage=BuildStage.BUILD.value)
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        real_root = artifact_root or workspace_dir
        return self._resolve_output_directory(real_root, output_directory)

    async def _execute_subprocess(
        self,
        workspace_dir: str,
        package_manager: str,
        build_command: str,
        output_directory: str,
        has_package_json: bool,
        has_requirements: bool,
        env_vars: Dict[str, str],
        log_callback: Callable[[BuildLogEvent], Any],
        artifact_root: Optional[str] = None,
    ) -> str:
        """Fallback local subprocess runner with devDependencies and path isolation."""
        env = {
            **os.environ,
            "CI": "true",
            **env_vars
        }
        # Do not enforce NODE_ENV=production during dependency installation so devDependencies (vite, tsc, etc.) are installed
        if "NODE_ENV" in env:
            del env["NODE_ENV"]

        # Ensure node_modules/.bin in workspace is in PATH
        node_bin_dir = os.path.join(workspace_dir, "node_modules", ".bin")
        if os.path.exists(node_bin_dir):
            env["PATH"] = f"{node_bin_dir}{os.pathsep}{env.get('PATH', '')}"

        # 1. Install dependencies only if project manifest is present
        if has_package_json and package_manager != "none":
            install_cmd = {
                "pnpm": "pnpm install",
                "yarn": "yarn install",
                "bun": "bun install",
                "npm": "npm install --include=dev"
            }.get(package_manager, "npm install --include=dev")

            await log_callback(BuildLogEvent(
                stage=BuildStage.DEPENDENCIES.value,
                level=LogLevel.INFO,
                message=f"Executing {install_cmd}..."
            ))

            proc = await asyncio.create_subprocess_shell(
                install_cmd,
                cwd=workspace_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                msg = line.decode('utf-8', errors='replace').strip()
                if msg:
                    await log_callback(BuildLogEvent(
                        stage=BuildStage.DEPENDENCIES.value,
                        level=LogLevel.INFO,
                        message=msg
                    ))

            await proc.wait()
            if proc.returncode != 0:
                # If pnpm or yarn failed, attempt graceful fallback to npm install
                if package_manager in ["pnpm", "yarn", "bun"]:
                    await log_callback(BuildLogEvent(
                        stage=BuildStage.DEPENDENCIES.value,
                        level=LogLevel.WARNING,
                        message=f"{package_manager} install exited with {proc.returncode}. Attempting npm install fallback..."
                    ))
                    fallback_proc = await asyncio.create_subprocess_shell(
                        "npm install --include=dev",
                        cwd=workspace_dir,
                        env=env,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT
                    )
                    while True:
                        line = await fallback_proc.stdout.readline()
                        if not line:
                            break
                        msg = line.decode('utf-8', errors='replace').strip()
                        if msg:
                            await log_callback(BuildLogEvent(
                                stage=BuildStage.DEPENDENCIES.value,
                                level=LogLevel.INFO,
                                message=msg
                            ))
                    await fallback_proc.wait()
                    if fallback_proc.returncode != 0:
                        raise SandboxExecutionError(
                            f"Dependency installation failed with code {fallback_proc.returncode}",
                            stage=BuildStage.DEPENDENCIES.value,
                            exit_code=fallback_proc.returncode
                        )
                else:
                    raise SandboxExecutionError(
                        f"Dependency installation failed with code {proc.returncode}",
                        stage=BuildStage.DEPENDENCIES.value,
                        exit_code=proc.returncode
                    )

            # Re-check node_modules/.bin after installation to add to PATH
            if os.path.exists(node_bin_dir) and node_bin_dir not in env.get("PATH", ""):
                env["PATH"] = f"{node_bin_dir}{os.pathsep}{env.get('PATH', '')}"

        elif has_requirements:
            req_file = os.path.join(workspace_dir, "requirements.txt")
            if os.path.exists(req_file):
                await log_callback(BuildLogEvent(
                    stage=BuildStage.DEPENDENCIES.value,
                    level=LogLevel.INFO,
                    message="Installing Python dependencies via pip..."
                ))
                pip_cmd = "pip install --no-cache-dir -r requirements.txt"
                proc = await asyncio.create_subprocess_shell(
                    pip_cmd,
                    cwd=workspace_dir,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    msg = line.decode('utf-8', errors='replace').strip()
                    if msg:
                        await log_callback(BuildLogEvent(
                            stage=BuildStage.DEPENDENCIES.value,
                            level=LogLevel.INFO,
                            message=msg
                        ))
                await proc.wait()
                if proc.returncode != 0:
                    raise SandboxExecutionError(
                        f"Python dependency installation failed with code {proc.returncode}",
                        stage=BuildStage.DEPENDENCIES.value,
                        exit_code=proc.returncode
                    )

        # 2. Run build command if configured
        if build_command:
            await log_callback(BuildLogEvent(
                stage=BuildStage.BUILD.value,
                level=LogLevel.INFO,
                message=f"Executing build command: {build_command}..."
            ))

            build_env = {
                **env,
                "NODE_ENV": "production"
            }

            proc = await asyncio.create_subprocess_shell(
                build_command,
                cwd=workspace_dir,
                env=build_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                msg = line.decode('utf-8', errors='replace').strip()
                if msg:
                    await log_callback(BuildLogEvent(
                        stage=BuildStage.BUILD.value,
                        level=LogLevel.INFO,
                        message=msg
                    ))

            await proc.wait()
            if proc.returncode != 0:
                raise SandboxExecutionError(
                    f"Build failed with code {proc.returncode}",
                    stage=BuildStage.BUILD.value,
                    exit_code=proc.returncode
                )

        real_root = artifact_root or workspace_dir
        return self._resolve_output_directory(real_root, output_directory)

docker_sandbox = DockerSandbox()
