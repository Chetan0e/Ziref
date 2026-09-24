import pytest
from services.builder.diagnostics import build_diagnostic_engine

def test_missing_dependency_diagnosis():
    logs = [
        "> vite build",
        "Error: Cannot find module 'axios'",
        "at Function.Module._resolveFilename (node:internal/modules/cjs/loader:1145:15)"
    ]
    diag = build_diagnostic_engine.diagnose(logs, exit_code=1)
    assert diag.category == "MISSING_DEPENDENCY"
    assert "axios" in diag.summary
    assert "npm install axios" in diag.actionable_fix

def test_missing_build_script_diagnosis():
    logs = [
        "npm error Missing script: \"build\"",
        "npm error To see a list of scripts, run: npm run"
    ]
    diag = build_diagnostic_engine.diagnose(logs, exit_code=1)
    assert diag.category == "MISSING_BUILD_SCRIPT"
    assert "build" in diag.summary

def test_output_dir_missing_diagnosis():
    logs = [
        "Build finished cleanly.",
        "Output directory 'dist' does not exist"
    ]
    diag = build_diagnostic_engine.diagnose(logs, exit_code=0)
    assert diag.category == "OUTPUT_DIRECTORY_MISSING"
    assert "dist" in diag.summary

def test_out_of_memory_diagnosis():
    logs = [
        "<--- Last few GCs --->",
        "FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory"
    ]
    diag = build_diagnostic_engine.diagnose(logs, exit_code=137)
    assert diag.category == "OUT_OF_MEMORY"
    assert "memory" in diag.summary.lower()

def test_typescript_error_diagnosis():
    logs = [
        "src/App.tsx(14,9): error TS2322: Type 'string' is not assignable to type 'number'."
    ]
    diag = build_diagnostic_engine.diagnose(logs, exit_code=2)
    assert diag.category == "TYPESCRIPT_ERROR"
    assert "TypeScript" in diag.summary

def test_generic_fallback_diagnosis():
    logs = [
        "Something went unexpectedly wrong with custom compiler.",
        "Exiting with status 42"
    ]
    diag = build_diagnostic_engine.diagnose(logs, exit_code=42, error_message="Process exited with code 42")
    assert diag.category == "BUILD_PROCESS_FAILED"
    assert "42" in diag.summary
