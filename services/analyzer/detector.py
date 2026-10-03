import os
import json
import glob
from typing import Optional, Dict, Any, List
from services.api.core.models import AnalysisResult

class ProjectDetector:
    """
    Deterministic analyzer that inspects a project workspace directory
    and infers framework, language, package manager, build command, and output directory.
    Supports: Static HTML/JS/CSS, React, Vite, Next.js, Vue, Angular, Svelte, Astro, Python, and Generic.
    """

    def analyze(self, workspace_path: str) -> AnalysisResult:
        workspace = os.path.abspath(workspace_path)
        warnings: List[str] = []

        # Find project root (handle single folder enclosing the zip content or macosx artifacts)
        root_dir = self._find_project_root(workspace)

        package_json_path = os.path.join(root_dir, "package.json")
        has_package_json = os.path.exists(package_json_path)

        if has_package_json:
            return self._analyze_node_project(root_dir, package_json_path, warnings)

        # Check Python projects
        if os.path.exists(os.path.join(root_dir, "requirements.txt")) or os.path.exists(os.path.join(root_dir, "pyproject.toml")) or os.path.exists(os.path.join(root_dir, "Pipfile")):
            return AnalysisResult(
                projectType="web",
                framework="python",
                language="python",
                packageManager="pip",
                runtime="python",
                buildCommand=None,
                startCommand="python main.py" if os.path.exists(os.path.join(root_dir, "main.py")) else ("python app.py" if os.path.exists(os.path.join(root_dir, "app.py")) else None),
                outputDirectory=".",
                port=8000,
                confidence=0.90,
                warnings=warnings
            )

        # Check Static HTML/CSS/JS (direct in root)
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
                confidence=0.98,
                warnings=warnings
            )

        # Check if index.html exists in a subfolder (e.g. public/index.html, src/index.html, dist/index.html, or nested site folder)
        html_matches = glob.glob(os.path.join(root_dir, "**", "index.html"), recursive=True)
        if html_matches:
            # Sort by shortest relative path to get closest to root
            html_matches.sort(key=lambda p: len(os.path.relpath(p, root_dir).split(os.sep)))
            target_html = html_matches[0]
            rel_folder = os.path.relpath(os.path.dirname(target_html), root_dir).replace("\\", "/")
            out_dir = "." if rel_folder in [".", ""] else rel_folder
            return AnalysisResult(
                projectType="web",
                framework="html",
                language="html",
                packageManager="none",
                runtime="static",
                buildCommand=None,
                startCommand=None,
                outputDirectory=out_dir,
                port=80,
                confidence=0.95,
                warnings=warnings
            )

        # Check if any .html file exists in the directory
        any_html = glob.glob(os.path.join(root_dir, "*.html"))
        if any_html:
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
                confidence=0.90,
                warnings=warnings
            )

        # Default fallback: Static project (no compilation, none package manager)
        warnings.append("No standard project manifest (package.json, index.html) found. Treating as static assets.")
        return AnalysisResult(
            projectType="generic",
            framework="static",
            language="javascript",
            packageManager="none",
            runtime="static",
            buildCommand=None,
            startCommand=None,
            outputDirectory=".",
            confidence=0.50,
            warnings=warnings
        )

    def _find_project_root(self, base_path: str) -> str:
        # If directory contains only 1 folder (ignoring __MACOSX, hidden files), drill down
        valid_entries = [
            e for e in os.listdir(base_path)
            if not e.startswith(".") and e != "__MACOSX" and not e.startswith("~")
        ]
        if len(valid_entries) == 1:
            nested = os.path.join(base_path, valid_entries[0])
            if os.path.isdir(nested):
                return self._find_project_root(nested)
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
            # Check if it's configured for static export
            has_static_export = False
            if has_next_config:
                try:
                    config_file = glob.glob(os.path.join(root_dir, "next.config.*"))[0]
                    with open(config_file, "r", encoding="utf-8") as f:
                        config_content = f.read()
                        if "output: 'export'" in config_content or "output: 'standalone'" in config_content:
                            has_static_export = True
                except Exception:
                    pass
            
            if not has_static_export:
                warnings.append("Next.js detected but not configured for static export. Add 'output: \"export\"' to next.config.js for static deployment.")
            
            # Default to static export mode for deployment
            output_dir = "out"
            runtime = "static"
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
