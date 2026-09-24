import os
import json
import glob
from typing import Optional, Dict, Any, List
from services.api.core.models import AnalysisResult

class ProjectDetector:
    """
    Deterministic analyzer that inspects a project workspace directory
    and infers framework, language, package manager, build command, and output directory.
    """

    def analyze(self, workspace_path: str) -> AnalysisResult:
        workspace = os.path.abspath(workspace_path)
        warnings: List[str] = []

        # Find project root (handle single folder enclosing the zip content)
        root_dir = self._find_project_root(workspace)

        package_json_path = os.path.join(root_dir, "package.json")
        has_package_json = os.path.exists(package_json_path)

        if has_package_json:
            return self._analyze_node_project(root_dir, package_json_path, warnings)

        # Check Python
        if os.path.exists(os.path.join(root_dir, "requirements.txt")) or os.path.exists(os.path.join(root_dir, "pyproject.toml")):
            return AnalysisResult(
                projectType="web",
                framework="python",
                language="python",
                packageManager="pip",
                runtime="python",
                buildCommand=None,
                startCommand="python main.py",
                outputDirectory=".",
                port=8000,
                confidence=0.90,
                warnings=warnings
            )

        # Check Static HTML/JS
        if os.path.exists(os.path.join(root_dir, "index.html")):
            return AnalysisResult(
                projectType="web",
                framework="html",
                language="html",
                packageManager="none",
                runtime="static",
                buildCommand=None,
                startCommand=None,
                outputDirectory=".",
                port=80,
                confidence=0.95,
                warnings=warnings
            )

        # Default fallback
        warnings.append("No standard project manifest (package.json, index.html) found.")
        return AnalysisResult(
            projectType="generic",
            framework="static",
            language="javascript",
            packageManager="npm",
            runtime="static",
            buildCommand=None,
            startCommand=None,
            outputDirectory=".",
            confidence=0.40,
            warnings=warnings
        )

    def _find_project_root(self, base_path: str) -> str:
        # If directory contains only 1 folder, drill down (common with GitHub zip releases)
        entries = [e for e in os.listdir(base_path) if not e.startswith(".")]
        if len(entries) == 1:
            nested = os.path.join(base_path, entries[0])
            if os.path.isdir(nested) and (
                os.path.exists(os.path.join(nested, "package.json")) or
                os.path.exists(os.path.join(nested, "index.html")) or
                os.path.exists(os.path.join(nested, "requirements.txt"))
            ):
                return nested
        return base_path

    def _detect_package_manager(self, root_dir: str) -> str:
        if os.path.exists(os.path.join(root_dir, "pnpm-lock.yaml")):
            return "pnpm"
        if os.path.exists(os.path.join(root_dir, "yarn.lock")):
            return "yarn"
        if os.path.exists(os.path.join(root_dir, "bun.lockb")) or os.path.exists(os.path.join(root_dir, "bun.lock")):
            return "bun"
        if os.path.exists(os.path.join(root_dir, "package-lock.json")):
            return "npm"
        return "npm"

    def _detect_language(self, root_dir: str, pkg: Dict[str, Any]) -> str:
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "typescript" in deps or os.path.exists(os.path.join(root_dir, "tsconfig.json")):
            return "typescript"
        return "javascript"

    def _analyze_node_project(self, root_dir: str, pkg_path: str, warnings: List[str]) -> AnalysisResult:
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                pkg = json.load(f)
        except Exception as e:
            warnings.append(f"Failed to parse package.json: {e}")
            pkg = {}

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        scripts = pkg.get("scripts", {})

        pm = self._detect_package_manager(root_dir)
        lang = self._detect_language(root_dir, pkg)

        # File checks
        has_vite_config = bool(glob.glob(os.path.join(root_dir, "vite.config.*")))
        has_next_config = bool(glob.glob(os.path.join(root_dir, "next.config.*")))
        has_astro_config = bool(glob.glob(os.path.join(root_dir, "astro.config.*")))
        has_svelte_config = bool(glob.glob(os.path.join(root_dir, "svelte.config.*")))
        has_angular_json = os.path.exists(os.path.join(root_dir, "angular.json"))
        has_vue_config = bool(glob.glob(os.path.join(root_dir, "vue.config.*")))

        framework = "nodejs"
        runtime = "static"
        output_dir = "dist"
        build_command = None
        start_command = None
        confidence = 0.90
        version = None

        if "next" in deps or has_next_config:
            framework = "nextjs"
            version = deps.get("next")
            output_dir = ".next"
            runtime = "node"  # Next.js can be static export or node runtime
            if "build" in scripts:
                build_command = f"{pm} run build"
            start_command = f"{pm} start"
            confidence = 0.98

        elif "vite" in deps or has_vite_config:
            if "react" in deps:
                framework = "react"
            elif "vue" in deps:
                framework = "vue"
            elif "svelte" in deps:
                framework = "svelte"
            else:
                framework = "vite"

            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else f"{pm} exec vite build"
            confidence = 0.98

        elif "react" in deps:
            framework = "react"
            output_dir = "build" if os.path.exists(os.path.join(root_dir, "public")) else "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        elif "vue" in deps or has_vue_config:
            framework = "vue"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        elif "@angular/core" in deps or has_angular_json:
            framework = "angular"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        elif "astro" in deps or has_astro_config:
            framework = "astro"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        elif "svelte" in deps or has_svelte_config:
            framework = "svelte"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        else:
            # Generic Node.js
            framework = "nodejs"
            output_dir = "dist" if "build" in scripts else "."
            build_command = f"{pm} run build" if "build" in scripts else None
            start_command = f"{pm} start" if "start" in scripts else "node index.js"
            runtime = "node" if start_command else "static"
            confidence = 0.85

        return AnalysisResult(
            projectType="web",
            framework=framework,
            frameworkVersion=version,
            language=lang,
            packageManager=pm,
            runtime=runtime,
            buildCommand=build_command,
            startCommand=start_command,
            outputDirectory=output_dir,
            port=3000 if runtime == "node" else None,
            confidence=confidence,
            warnings=warnings
        )

project_detector = ProjectDetector()
