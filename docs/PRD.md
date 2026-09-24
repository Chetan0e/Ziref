# Product Requirements Document (PRD) — Ziref

## 1. Executive Summary

**Ziref** is a modern developer platform that simplifies application deployment and mobile packaging. By taking raw project source code in the form of a ZIP file, Ziref analyzes the framework, provisions an ephemeral and secure container sandbox, compiles the project, serves the resulting immutable deployment via high-performance reverse routing, and enables 1-click mobile application generation (Android APK).

---

## 2. Product Principles

1. **Developer-First**: Technical, clean, keyboard-friendly, and transparent.
2. **Zero Unnecessary Configuration**: Automatic detection of frameworks, package managers, build commands, output paths, and ports.
3. **Secure by Default**: Uploaded code is strictly untrusted. Builds execute in non-privileged, isolated Docker sandboxes.
4. **Modular Architecture**: Clean micro-service boundaries allowing single-node bootstrap or distributed cloud scaling.
5. **Full Observability**: Structured event logs for uploads, analysis, builds, deployments, and app packaging.
6. **Immutable Deployments**: Every deployment is atomic and immutable, enabling instant rollbacks.
7. **No Mock/Fake Functionality**: Every UI control connects to real backend workflows.

---

## 3. MVP Scope & Acceptance Criteria

### 3.1 Authentication & Multi-Tenancy
- Email + password registration and login with bcrypt hashing.
- Cryptographically secure JWT tokens and session tracking.
- Per-user ownership and resource isolation (Users cannot access other users' projects, builds, or secrets).

### 3.2 Project Management & Uploads
- Create, list, inspect, and delete projects.
- Drag-and-drop ZIP upload with client-side and server-side validation.
- Secure archive extraction (zip bomb protection, path traversal mitigation, symlink safety).

### 3.3 Project Analyzer
Deterministic detection of:
- **Languages**: JavaScript, TypeScript, HTML/CSS, Python.
- **Frameworks**: React, Vite, Next.js, Vue, Angular, Node.js static/server.
- **Package Managers**: npm, pnpm, yarn, bun.
- Outputs normalized configuration: framework, package manager, build command, output directory.

### 3.4 Build Engine
- Redis-backed job queue for asynchronous build execution.
- Docker sandbox execution with cgroup limits (1.0 CPU, 1024MB RAM, process limits, 300s timeout).
- Non-root user execution, read-only rootfs where appropriate, no Docker socket access.
- Real-time structured log streaming via SSE / Redis Pub/Sub.
- Packaged immutable build artifacts stored in object storage.

### 3.5 Deployment & Routing
- Immutable deployment lifecycle (`QUEUED` → `BUILDING` → `BUILT` → `DEPLOYING` → `READY` / `FAILED`).
- Public URL assignment via subdomain (`http://<slug>.localhost:8080`) or path routing (`/sites/<slug>/`).
- SPA fallback support (serving `index.html` on client-side routes).
- Rollback and redeploy support.

### 3.6 Environment Variables
- Encrypted storage at rest.
- UI masking and secret toggle.
- Secure injection into sandbox build environments.

### 3.7 Appify Engine (Android)
- One-click transformation of deployed web applications into Android APKs.
- Customization: App name, package ID (e.g. `com.example.app`), icon, splash screen, theme.
- Generates clean Android Studio / Gradle project.
- Compiles debug APK and provides downloadable `.apk` and `.zip` source artifacts.

---

## 4. User Journey

```text
1. Sign Up / Sign In
       ↓
2. Create New Project
       ↓
3. Upload Project ZIP (e.g. React + Vite)
       ↓
4. Analyzer detects Framework (React), Tool (Vite), PM (pnpm), Output (dist/)
       ↓
5. Trigger Sandboxed Build
       ↓
6. View Live Terminal Build Logs
       ↓
7. Deployment reaches READY status
       ↓
8. Open Live Public URL (Website renders cleanly)
       ↓
9. Click "Create Mobile App" (Appify)
       ↓
10. Download Android APK & Source Package
```
