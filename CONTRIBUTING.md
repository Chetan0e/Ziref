# Contributing to Ziref

Thank you for your interest in contributing to Ziref! This guide will help you get set up quickly and ensure your contributions align with the project's standards.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Running Tests](#running-tests)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Code Style Guidelines](#code-style-guidelines)

---

## Code of Conduct

This project is governed by the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this standard.

---

## Getting Started

1. **Fork** the repository.
2. **Clone** your fork: `git clone https://github.com/<your-username>/Ziref.git`
3. **Create a branch**: `git checkout -b feat/my-feature` or `fix/my-bug-fix`

---

## Development Setup

### Requirements

| Tool | Minimum Version |
|------|-----------------|
| Python | 3.11+ |
| Node.js | 20+ |
| pnpm | 9+ |
| Docker Desktop | Optional |

### 1. Python Environment

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Node / Dashboard Environment

```bash
pnpm install
```

### 3. Environment Variables

```bash
cp .env.example .env
# Edit .env as needed
```

### 4. Start All Services

```powershell
# Windows — starts API, Worker, Router, and Dashboard in parallel
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

---

## Project Structure

| Path | Description |
|------|-------------|
| `apps/dashboard/` | Next.js 15 developer dashboard |
| `services/api/` | FastAPI REST gateway |
| `services/analyzer/` | Framework detection & archive security |
| `services/builder/` | Docker sandbox build executor |
| `services/deployer/` | Atomic deployment & site router |
| `services/app_builder/` | Android APK generator |
| `services/worker/` | Async Redis job consumer |
| `packages/cli/` | Developer CLI |
| `packages/types/` | Shared TypeScript definitions |
| `tests/` | Unit & integration tests |
| `infrastructure/docker/` | Dockerfiles |

---

## Making Changes

- **Feature branches**: `feat/<description>` (e.g., `feat/s3-storage-driver`)
- **Bug fix branches**: `fix/<description>` (e.g., `fix/zip-slip-edge-case`)
- **Docs branches**: `docs/<description>`
- Keep commits atomic and descriptive. Follow [Conventional Commits](https://www.conventionalcommits.org/).

---

## Running Tests

```bash
# All Python unit & integration tests
pytest tests/ -v

# Specific suites
pytest tests/unit/
pytest tests/integration/

# Dashboard typecheck & lint
pnpm --filter dashboard typecheck
pnpm --filter dashboard lint

# Full verification (Python tests + Next.js build)
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
```

All tests must pass before submitting a PR.

---

## Submitting a Pull Request

1. Push your branch: `git push origin feat/my-feature`
2. Open a Pull Request against `main`.
3. Fill in the [PR template](.github/pull_request_template.md) completely.
4. Ensure all CI checks pass.
5. Request a review.

---

## Code Style Guidelines

### Python
- **Type hints**: Full typing on all function signatures and Pydantic models.
- **Formatting**: `black` compatible (88-character line length).
- **No dead code**: Remove unused imports and functions.
- **Security first**: Always validate archive paths, sanitize inputs, encrypt secrets.

### TypeScript (Dashboard)
- **Strict mode**: No `any` types without explicit justification.
- **Component style**: Functional components with React hooks.
- **API calls**: Use the typed API client in `apps/dashboard/lib/api.ts`.

---

Thank you for helping make Ziref better! 
