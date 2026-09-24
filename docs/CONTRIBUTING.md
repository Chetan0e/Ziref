# Contributing Guide — Ziref

Welcome to the Ziref codebase! We follow high engineering standards, strict type checking, and modular architecture.

---

## 1. Monorepo Organization

- `apps/dashboard`: Next.js frontend (React 19, Tailwind CSS, TypeScript).
- `services/api`: FastAPI backend service.
- `services/analyzer`: Framework and build configuration detection engine.
- `services/builder`: Docker sandbox runner and build orchestrator.
- `services/deployer`: Static site serving and dynamic routing.
- `services/app-builder`: Android project generation and Gradle compilation.
- `services/worker`: Asynchronous job consumer for Redis queues.
- `packages/types`: Shared TypeScript definitions.
- `tests/`: Automated test suite (unit, integration, e2e).

---

## 2. Code Quality Guidelines

1. **TypeScript Strict Mode**: No `any` types unless strictly necessary and documented.
2. **Python Type Hints**: Use full typing (`typing` / `pydantic` models) for all functions and endpoints.
3. **No Dead Code**: Remove unused imports, dead functions, and unlinked files.
4. **No Fake Functionality**: Every UI action must connect to a real backend workflow.
5. **Security First**: Always validate incoming files, sanitize archive paths, and encrypt secrets.

---

## 3. Running Tests

```bash
# Python unit & integration tests
pytest

# Frontend typechecking & linting
pnpm --filter dashboard typecheck
pnpm --filter dashboard lint
```
