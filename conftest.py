"""
Root-level conftest.py — ensures the repo root is on sys.path so that
`import services.*` and `import packages.*` resolve correctly when pytest
is invoked from any working directory (locally or in CI).
"""
import sys
import os

# Insert the repository root at the front of sys.path.
# __file__ is <repo_root>/conftest.py, so its parent is the repo root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
