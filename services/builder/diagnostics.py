import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class BuildDiagnosis(BaseModel):
    category: str
    summary: str
    root_cause: str
    confidence: float
    actionable_fix: str
    detected_snippet: Optional[str] = None

class BuildDiagnosticEngine:
    """
    Intelligent build log analyzer that diagnoses common compiler, bundler,
    and runtime errors and provides exact actionable fixes.
    """

    PATTERNS = [
        {
            "category": "MISSING_DEPENDENCY",
            "regex": r"(?:Cannot find module ['\"]([^'\"]+)['\"]|Module not found: Error: Can't resolve ['\"]([^'\"]+)['\"]|No module named ['\"]([^'\"]+)['\"])",
            "handler": lambda m: {
                "summary": f"Missing dependency: '{m.group(1) or m.group(2) or m.group(3)}'",
                "root_cause": f"The package '{m.group(1) or m.group(2) or m.group(3)}' is referenced in your code but is not listed in your package.json dependencies or installed in the sandbox.",
                "fix": f"Add the package to your dependencies: run 'npm install {m.group(1) or m.group(2) or m.group(3)}' (or pnpm/yarn add), then re-upload your project.",
                "confidence": 0.95
            }
        },
        {
            "category": "MISSING_BUILD_SCRIPT",
            "regex": r"(?:Missing script: ['\"]?([^'\"\n]+)['\"]?|ERR_PNPM_NO_SCRIPT.*Missing script: ([^\n]+)|npm error Missing script: \"([^\"]+)\")",
            "handler": lambda m: {
                "summary": f"Build script '{m.group(1) or m.group(2) or m.group(3)}' not defined",
                "root_cause": "The configured build command attempts to run an npm/pnpm script that is not present in package.json 'scripts'.",
                "fix": "Check your package.json scripts section. Add a \"build\" script (e.g. \"build\": \"vite build\" or \"next build\") or change the Build Command in Project Settings.",
                "confidence": 0.98
            }
        },
        {
            "category": "COMMAND_NOT_FOUND",
            "regex": r"(?:(?:sh|bash): line \d+: ([a-zA-Z0-9_-]+): command not found|'([a-zA-Z0-9_-]+)' is not recognized as an internal or external command)",
            "handler": lambda m: {
                "summary": f"Command '{m.group(1) or m.group(2)}' not found in build sandbox",
                "root_cause": f"The build command requires '{m.group(1) or m.group(2)}', which is not installed in the standard build environment.",
                "fix": f"Ensure your build scripts rely on packages installed via npm/pnpm (e.g. 'npx {m.group(1) or m.group(2)}') rather than global system binaries.",
                "confidence": 0.92
            }
        },
        {
            "category": "OUTPUT_DIRECTORY_MISSING",
            "regex": r"(?:Output directory ['\"]([^'\"]+)['\"] does not exist|Target build directory ['\"]([^'\"]+)['\"] was not created)",
            "handler": lambda m: {
                "summary": f"Output directory '{m.group(1) or m.group(2)}' missing",
                "root_cause": f"The build finished with exit code 0, but the configured output directory '{m.group(1) or m.group(2)}' was not produced by your build tool.",
                "fix": "Check your build tool's output folder (e.g. Vite outputs to 'dist', Next.js static exports to 'out', CRA to 'build'). Update the 'Output Directory' in Project Settings.",
                "confidence": 0.99
            }
        },
        {
            "category": "OUT_OF_MEMORY",
            "regex": r"(?:JavaScript heap out of memory|fatal error: runtime: out of memory|Killed.*signal 9)",
            "handler": lambda m: {
                "summary": "Build exceeded container memory limit (1024 MB)",
                "root_cause": "The build process consumed more RAM than the sandbox cgroup threshold.",
                "fix": "Optimize your bundling process, disable source maps in production ('sourcemap: false'), or set NODE_OPTIONS=\"--max-old-space-size=800\" in Environment Variables.",
                "confidence": 0.90
            }
        },
        {
            "category": "TYPESCRIPT_ERROR",
            "regex": r"TS\d+:\s*(?:Cannot find name|Type '[^']+' is not assignable|Property '[^']+' does not exist)(?:[^\n]*)",
            "handler": lambda m: {
                "summary": "TypeScript compilation error",
                "root_cause": f"TypeScript type check failed: {m.group(0)[:120]}",
                "fix": "Fix the TypeScript type error locally by running 'tsc --noEmit', or configure 'tsc --noEmit || true' if you want to bypass strict type checking for initial preview deployments.",
                "confidence": 0.93
            }
        },
        {
            "category": "SYNTAX_ERROR",
            "regex": r"SyntaxError:\s*([^\n]+)",
            "handler": lambda m: {
                "summary": "Source code syntax error",
                "root_cause": f"Syntax error encountered during parsing: {m.group(1)[:120]}",
                "fix": "Check the indicated file and line number for syntax mistakes or unclosed tags/brackets.",
                "confidence": 0.90
            }
        },
        {
            "category": "ENV_VAR_MISSING",
            "regex": r"(?:([A-Z0-9_]+) is not defined|Missing required environment variable ['\"]?([A-Z0-9_]+)['\"]?)",
            "handler": lambda m: {
                "summary": f"Missing environment variable: '{m.group(1) or m.group(2)}'",
                "root_cause": f"The application code or build script expects '{m.group(1) or m.group(2)}' to be set.",
                "fix": f"Navigate to the 'Environment' tab in the Ziref Dashboard and add key '{m.group(1) or m.group(2)}' with your desired value.",
                "confidence": 0.88
            }
        }
    ]

    def diagnose(self, log_messages: List[str], exit_code: Optional[int] = None, error_message: Optional[str] = None) -> BuildDiagnosis:
        combined_text = "\n".join(log_messages)
        if error_message:
            combined_text += f"\n{error_message}"

        # Match against known failure patterns
        for rule in self.PATTERNS:
            match = re.search(rule["regex"], combined_text, re.IGNORECASE)
            if match:
                res = rule["handler"](match)
                # Find matching line for snippet context
                snippet = match.group(0).strip()
                return BuildDiagnosis(
                    category=rule["category"],
                    summary=res["summary"],
                    root_cause=res["root_cause"],
                    confidence=res["confidence"],
                    actionable_fix=res["fix"],
                    detected_snippet=snippet
                )

        # Fallback generic diagnosis
        if exit_code and exit_code != 0:
            return BuildDiagnosis(
                category="BUILD_PROCESS_FAILED",
                summary=f"Build command failed with exit code {exit_code}",
                root_cause=error_message or f"The command terminated with non-zero exit code {exit_code}. Inspect terminal logs above for compiler output.",
                confidence=0.70,
                actionable_fix="Review the latest error logs in the Build Terminal. Verify your package.json scripts and ensure the project builds locally using 'npm run build'.",
                detected_snippet=error_message
            )

        return BuildDiagnosis(
            category="UNKNOWN",
            summary="No specific build failure pattern detected",
            root_cause="The build failed without matching a known signature.",
            confidence=0.50,
            actionable_fix="Review the full build terminal logs to identify the error.",
            detected_snippet=None
        )

build_diagnostic_engine = BuildDiagnosticEngine()
