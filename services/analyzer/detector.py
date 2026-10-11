import os
import json
import glob
from typing import Optional, Dict, Any, List
from services.api.core.models import AnalysisResult

class ProjectDetector:
    """
    Deterministic analyzer that inspects a project workspace directory
    and infers framework, language, package manager, build command, and output directory.
    Supports: Static HTML/JS/CSS, React (CRA/Vite), Vite, Next.js, Vue, Angular, Svelte, Astro,
              MERN/MEAN mono-repos (client/frontend subfolder detection), Python, and Generic Node.
    """

    def analyze(self, workspace_path: str) -> AnalysisResult:
        workspace = os.path.abspath(workspace_path)
        warnings: List[str] = []

        # Find project root (handle single folder enclosing the zip content or macosx artifacts)
        root_dir = self._find_project_root(workspace)

        package_json_path = os.path.join(root_dir, "package.json")
        has_package_json = os.path.exists(package_json_path)

        if has_package_json:
            result = self._analyze_node_project(root_dir, package_json_path, warnings)
            # If root package.json is a mono-repo / generic (Express, Fastify, MERN backend),
            # or specifies npm/yarn workspaces, always prioritize frontend subfolder if present
            try:
                with open(package_json_path, "r", encoding="utf-8") as f:
                    root_pkg = json.load(f)
            except Exception:
                root_pkg = {}

            has_workspaces = "workspaces" in root_pkg
            is_generic_or_backend = result.framework == "nodejs" or any(
                b_dep in {**root_pkg.get("dependencies", {}), **root_pkg.get("devDependencies", {})}
                for b_dep in ["express", "fastify", "koa", "mongoose", "mongodb", "cors"]
            )

            if is_generic_or_backend or has_workspaces:
                frontend_result = self._detect_frontend_subfolder(root_dir, warnings, workspaces=root_pkg.get("workspaces"))
                if frontend_result:
                    return frontend_result

            return result

        # No root package.json — check common frontend subfolder names
        # (e.g. MERN with client/package.json or frontend/package.json)
        frontend_result = self._detect_frontend_subfolder(root_dir, warnings)
        if frontend_result:
            return frontend_result

        # Check Python projects
        if (
            os.path.exists(os.path.join(root_dir, "requirements.txt"))
            or os.path.exists(os.path.join(root_dir, "pyproject.toml"))
            or os.path.exists(os.path.join(root_dir, "Pipfile"))
        ):
            return AnalysisResult(
                projectType="web",
                framework="python",
                language="python",
                packageManager="pip",
                runtime="python",
                buildCommand=None,
                startCommand=(
                    "python main.py"
                    if os.path.exists(os.path.join(root_dir, "main.py"))
                    else (
                        "python app.py"
                        if os.path.exists(os.path.join(root_dir, "app.py"))
                        else None
                    )
                ),
                outputDirectory=".",
                port=8000,
                confidence=0.90,
                warnings=warnings,
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
                warnings=warnings,
            )

        # Check if index.html exists in a subfolder (e.g. public/index.html, dist/index.html)
        html_matches = glob.glob(os.path.join(root_dir, "**", "index.html"), recursive=True)
        if html_matches:
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
                warnings=warnings,
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
                warnings=warnings,
            )

        # Default fallback: Static project
        warnings.append(
            "No standard project manifest (package.json, index.html) found. Treating as static assets."
        )
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
            warnings=warnings,
        )

    # -----------------------------------------------------------------------
    # Mono-repo / MERN frontend subfolder detection
    # -----------------------------------------------------------------------
    FRONTEND_SUBFOLDERS = [
        "client",
        "frontend",
        "web",
        "app",
        "ui",
        "dashboard",
        "src",
        "public",
    ]

    def _detect_frontend_subfolder(
        self, root_dir: str, warnings: List[str], workspaces: Optional[Any] = None
    ) -> Optional[AnalysisResult]:
        """
        Scans known frontend subfolder names, workspaces, or subdirectories for a frontend app
        (React, Vite, Next, Vue, HTML, etc.). Returns an AnalysisResult with the subfolder as the build root.
        """
        candidate_dirs: List[str] = []

        # 1. Check workspace directories if configured
        if workspaces:
            workspace_list = workspaces if isinstance(workspaces, list) else workspaces.get("packages", []) if isinstance(workspaces, dict) else []
            for ws in workspace_list:
                ws_clean = ws.strip("/\\")
                if "*" in ws_clean:
                    for matched in glob.glob(os.path.join(root_dir, ws_clean)):
                        if os.path.isdir(matched) and matched not in candidate_dirs:
                            candidate_dirs.append(matched)
                else:
                    ws_dir = os.path.join(root_dir, ws_clean)
                    if os.path.isdir(ws_dir) and ws_dir not in candidate_dirs:
                        candidate_dirs.append(ws_dir)

        # 2. Check explicit known frontend names
        for name in self.FRONTEND_SUBFOLDERS:
            sub = os.path.join(root_dir, name)
            if os.path.isdir(sub) and sub not in candidate_dirs:
                candidate_dirs.append(sub)

        # 3. Also scan all other immediate subdirectories
        for entry in os.listdir(root_dir):
            full = os.path.join(root_dir, entry)
            if (
                os.path.isdir(full)
                and not entry.startswith(".")
                and entry not in ["node_modules", "backend", "server", "api", "dist", "build", "coverage", "__pycache__"]
                and full not in candidate_dirs
            ):
                candidate_dirs.append(full)

        FRONTEND_INDICATOR_DEPS = [
            "react",
            "react-dom",
            "react-scripts",
            "@vitejs/plugin-react",
            "@vitejs/plugin-vue",
            "vue",
            "svelte",
            "vite",
            "@angular/core",
            "next",
            "astro",
            "solid-js",
            "preact",
            "lit",
            "nuxt",
            "gatsby",
            "webpack",
            "parcel",
            "esbuild",
            "tailwindcss",
            "@remix-run/react",
        ]

        for sub_dir in candidate_dirs:
            pkg_path = os.path.join(sub_dir, "package.json")
            has_sub_pkg = os.path.exists(pkg_path)

            if has_sub_pkg:
                try:
                    with open(pkg_path, "r", encoding="utf-8") as f:
                        pkg = json.load(f)
                except Exception:
                    continue

                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                scripts = pkg.get("scripts", {})

                has_frontend_dep = any(dep in deps for dep in FRONTEND_INDICATOR_DEPS)
                has_frontend_scripts = any(
                    any(tool in script.lower() for tool in ["vite", "react-scripts", "webpack", "next", "astro", "build"])
                    for script in scripts.values()
                )
                has_html_or_src = (
                    os.path.exists(os.path.join(sub_dir, "index.html"))
                    or os.path.exists(os.path.join(sub_dir, "public", "index.html"))
                    or os.path.isdir(os.path.join(sub_dir, "src"))
                )

                if not (has_frontend_dep or has_frontend_scripts or has_html_or_src):
                    continue

                warnings.append(
                    f"Mono-repo/MERN detected: using frontend subfolder '{os.path.basename(sub_dir)}' as build root."
                )
                result = self._analyze_node_project(sub_dir, pkg_path, warnings)

                # Re-root the output directory relative to root_dir
                rel_sub = os.path.relpath(sub_dir, root_dir).replace("\\", "/")

                # If framework returned generic nodejs but frontend indicators present, refine to react/vite
                framework = result.framework
                if framework == "nodejs":
                    if "vite" in deps:
                        framework = "vite"
                    elif "react" in deps or "react-dom" in deps or "react-scripts" in deps:
                        framework = "react"

                out_dir = result.outputDirectory
                if out_dir in [".", "./", None, ""]:
                    # Default output folder based on framework
                    if "react-scripts" in deps or os.path.exists(os.path.join(sub_dir, "public")):
                        out_dir = "build"
                    else:
                        out_dir = "dist"

                final_out = f"{rel_sub}/{out_dir}" if out_dir not in [".", "./"] else rel_sub

                return AnalysisResult(
                    projectType="web",
                    framework=framework,
                    frameworkVersion=result.frameworkVersion,
                    language=result.language,
                    packageManager=result.packageManager,
                    runtime="static",  # Always deploy static website for frontend
                    buildCommand=result.buildCommand or (f"{result.packageManager} run build" if "build" in scripts else None),
                    startCommand=result.startCommand,
                    outputDirectory=final_out,
                    port=80,
                    confidence=0.96,
                    warnings=result.warnings,
                )

            # Check if subfolder has index.html without package.json (static frontend)
            elif os.path.exists(os.path.join(sub_dir, "index.html")):
                rel_sub = os.path.relpath(sub_dir, root_dir).replace("\\", "/")
                warnings.append(
                    f"Mono-repo/MERN detected: using static frontend subfolder '{os.path.basename(sub_dir)}'."
                )
                return AnalysisResult(
                    projectType="web",
                    framework="html",
                    language="html",
                    packageManager="none",
                    runtime="static",
                    buildCommand=None,
                    startCommand=None,
                    outputDirectory=rel_sub,
                    port=80,
                    confidence=0.95,
                    warnings=warnings,
                )
        return None

    # -----------------------------------------------------------------------
    # Project root unwrapping
    # -----------------------------------------------------------------------

    def _find_project_root(self, base_path: str) -> str:
        """
        If directory contains only 1 folder (ignoring __MACOSX, hidden files, and known
        backend-only dirs), drill down to unwrap ZIP single-root enclosures.
        """
        entries = [
            e
            for e in os.listdir(base_path)
            if not e.startswith(".")
            and e != "__MACOSX"
            and not e.startswith("~")
        ]
        if len(entries) == 1:
            nested = os.path.join(base_path, entries[0])
            if os.path.isdir(nested):
                return self._find_project_root(nested)
        return base_path

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _detect_package_manager(self, root_dir: str) -> str:
        if os.path.exists(os.path.join(root_dir, "pnpm-lock.yaml")):
            return "pnpm"
        if os.path.exists(os.path.join(root_dir, "yarn.lock")):
            return "yarn"
        if os.path.exists(os.path.join(root_dir, "bun.lockb")) or os.path.exists(
            os.path.join(root_dir, "bun.lock")
        ):
            return "bun"
        if os.path.exists(os.path.join(root_dir, "package-lock.json")):
            return "npm"
        return "npm"

    def _detect_language(self, root_dir: str, pkg: Dict[str, Any]) -> str:
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "typescript" in deps or os.path.exists(os.path.join(root_dir, "tsconfig.json")):
            return "typescript"
        return "javascript"

    def _analyze_node_project(
        self, root_dir: str, pkg_path: str, warnings: List[str]
    ) -> AnalysisResult:
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
        has_gatsby_config = bool(glob.glob(os.path.join(root_dir, "gatsby-config.*")))

        framework = "nodejs"
        runtime = "static"
        output_dir = "dist"
        build_command = None
        start_command = None
        confidence = 0.90
        version = None

        # ---- Next.js ----
        if "next" in deps or has_next_config:
            framework = "nextjs"
            version = deps.get("next")
            has_static_export = False
            if has_next_config:
                try:
                    config_file = glob.glob(os.path.join(root_dir, "next.config.*"))[0]
                    with open(config_file, "r", encoding="utf-8") as f:
                        config_content = f.read()
                        if "output: 'export'" in config_content or 'output: "export"' in config_content:
                            has_static_export = True
                except Exception:
                    pass
            if not has_static_export:
                warnings.append(
                    "Next.js detected but not configured for static export. "
                    "Add output: 'export' to next.config.js for static deployment."
                )
            output_dir = "out"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            start_command = f"{pm} start"
            confidence = 0.98

        # ---- Gatsby ----
        elif "gatsby" in deps or has_gatsby_config:
            framework = "gatsby"
            output_dir = "public"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else f"{pm} exec gatsby build"
            confidence = 0.97

        # ---- Vite / React+Vite / Vue+Vite / Svelte+Vite ----
        elif "vite" in deps or has_vite_config:
            if "react" in deps or "react-dom" in deps:
                framework = "react"
            elif "vue" in deps:
                framework = "vue"
            elif "svelte" in deps:
                framework = "svelte"
            elif "solid-js" in deps:
                framework = "solid"
            elif "preact" in deps:
                framework = "preact"
            else:
                framework = "vite"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else f"{pm} exec vite build"
            confidence = 0.98

        # ---- React (CRA or other) ----
        elif "react" in deps or "react-dom" in deps:
            framework = "react"
            output_dir = "build" if os.path.exists(os.path.join(root_dir, "public")) else "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        # ---- Vue CLI ----
        elif "vue" in deps or has_vue_config:
            framework = "vue"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        # ---- Angular ----
        elif "@angular/core" in deps or has_angular_json:
            framework = "angular"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        # ---- Astro ----
        elif "astro" in deps or has_astro_config:
            framework = "astro"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        # ---- Svelte (non-Vite) ----
        elif "svelte" in deps or has_svelte_config:
            framework = "svelte"
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.95

        # ---- Nuxt ----
        elif "nuxt" in deps:
            framework = "nuxt"
            output_dir = ".output/public"
            runtime = "static"
            build_command = f"{pm} run generate" if "generate" in scripts else (f"{pm} run build" if "build" in scripts else None)
            confidence = 0.95

        # ---- Solid.js / Preact / Lit ----
        elif "solid-js" in deps or "preact" in deps or "lit" in deps:
            framework = "solid" if "solid-js" in deps else ("preact" if "preact" in deps else "lit")
            output_dir = "dist"
            runtime = "static"
            build_command = f"{pm} run build" if "build" in scripts else None
            confidence = 0.90

        # ---- Generic Node.js (Express, Fastify, MERN backend, etc.) ----
        else:
            framework = "nodejs"
            output_dir = "dist" if "build" in scripts else "."
            build_command = f"{pm} run build" if "build" in scripts else None
            start_command = (
                f"{pm} start"
                if "start" in scripts
                else (
                    "node server.js"
                    if os.path.exists(os.path.join(root_dir, "server.js"))
                    else "node index.js"
                )
            )
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
            warnings=warnings,
        )


project_detector = ProjectDetector()
