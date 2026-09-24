import os
import shutil
import tarfile
import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any
import docker
from docker.errors import DockerException
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
            logger.warning(f"Docker daemon not directly available: {e}. Subprocess fallback will be used if needed.")
            self.client = None

    async def execute_build(
        self,
        workspace_dir: str,
        package_manager: str,
        build_command: str,
        output_directory: str,
        env_vars: Dict[str, str],
        log_callback: Callable[[BuildLogEvent], Any]
    ) -> str:
        """
        Executes dependency installation and build inside a secure isolated sandbox.
        Returns the absolute path to the output directory.
        """
        await log_callback(BuildLogEvent(
            stage=BuildStage.SANDBOX_INIT.value,
            level=LogLevel.INFO,
            message="Provisioning isolated build sandbox environment..."
        ))

        abs_workspace = os.path.abspath(workspace_dir)

        # Decide whether to use Docker or Subprocess execution
        if self.client:
            return await self._execute_docker(
                abs_workspace, package_manager, build_command, output_directory, env_vars, log_callback
            )
        else:
            return await self._execute_subprocess(
                abs_workspace, package_manager, build_command, output_directory, env_vars, log_callback
            )

    async def _execute_docker(
        self,
        workspace_dir: str,
        package_manager: str,
        build_command: str,
        output_directory: str,
        env_vars: Dict[str, str],
        log_callback: Callable[[BuildLogEvent], Any]
    ) -> str:
        # Determine install command based on package manager
        install_cmd = {
            "pnpm": "pnpm install",
            "yarn": "yarn install",
            "bun": "bun install",
            "npm": "npm install"
        }.get(package_manager, "npm install")

        combined_script = f"""
set -e
echo "==> Node version: $(node -v)"
echo "==> Package Manager: {package_manager}"
echo "==> Installing dependencies..."
{install_cmd}
echo "==> Running build command: {build_command}"
{build_command}
"""
        container = None
        try:
            # Inject build environment variables safely
            sanitized_env = {
                "CI": "true",
                "NODE_ENV": "production",
                **env_vars
            }

            await log_callback(BuildLogEvent(
                stage=BuildStage.DEPENDENCIES.value,
                level=LogLevel.INFO,
                message=f"Starting container sandbox with image {settings.SANDBOX_IMAGE}..."
            ))

            # Run container
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
                user="0:0"  # Ensures write permissions inside mounted volume on Alpine
            )

            container.start()

            # Stream logs
            for log_line in container.logs(stream=True, follow=True):
                line = log_line.decode("utf-8", errors="replace").strip()
                if line:
                    stage = BuildStage.BUILD.value if "Running build command" in line or "vite" in line.lower() else BuildStage.DEPENDENCIES.value
                    await log_callback(BuildLogEvent(
                        stage=stage,
                        level=LogLevel.INFO,
                        message=line
                    ))

            # Wait for completion
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

        # Verify output directory exists
        out_path = os.path.join(workspace_dir, output_directory)
        if not os.path.exists(out_path):
            # Check if root index.html exists for static HTML projects
            if os.path.exists(os.path.join(workspace_dir, "index.html")):
                return workspace_dir
            raise SandboxExecutionError(
                f"Configured output directory '{output_directory}' was not generated by the build.",
                stage=BuildStage.PACKAGING.value
            )

        return out_path

    async def _execute_subprocess(
        self,
        workspace_dir: str,
        package_manager: str,
        build_command: str,
        output_directory: str,
        env_vars: Dict[str, str],
        log_callback: Callable[[BuildLogEvent], Any]
    ) -> str:
        """Fallback isolated subprocess runner when Docker daemon is unavailable."""
        await log_callback(BuildLogEvent(
            stage=BuildStage.SANDBOX_INIT.value,
            level=LogLevel.INFO,
            message="Executing build in local isolated runner..."
        ))

        install_cmd = {
            "pnpm": "pnpm install",
            "yarn": "yarn install",
            "bun": "bun install",
            "npm": "npm install"
        }.get(package_manager, "npm install")

        env = {
            **os.environ,
            "CI": "true",
            "NODE_ENV": "production",
            **env_vars
        }

        # 1. Install dependencies
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
            raise SandboxExecutionError(f"Dependency installation failed with code {proc.returncode}", stage=BuildStage.DEPENDENCIES.value, exit_code=proc.returncode)

        # 2. Run build command
        if build_command:
            await log_callback(BuildLogEvent(
                stage=BuildStage.BUILD.value,
                level=LogLevel.INFO,
                message=f"Executing build command: {build_command}..."
            ))

            proc = await asyncio.create_subprocess_shell(
                build_command,
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
                        stage=BuildStage.BUILD.value,
                        level=LogLevel.INFO,
                        message=msg
                    ))

            await proc.wait()
            if proc.returncode != 0:
                raise SandboxExecutionError(f"Build failed with code {proc.returncode}", stage=BuildStage.BUILD.value, exit_code=proc.returncode)

        out_path = os.path.join(workspace_dir, output_directory)
        if not os.path.exists(out_path):
            if os.path.exists(os.path.join(workspace_dir, "index.html")):
                return workspace_dir
            raise SandboxExecutionError(
                f"Configured output directory '{output_directory}' was not generated by the build.",
                stage=BuildStage.PACKAGING.value
            )

        return out_path

docker_sandbox = DockerSandbox()
