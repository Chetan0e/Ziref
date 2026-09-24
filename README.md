<div align="center">

<img src="docs/assets/ziref-logo.svg" alt="Ziref Brandmark" width="96" height="96" />

# ZIREF

### *Developer Infrastructure, Continuous Deployment & Web-to-Mobile Platform*

**"One project in, multiple production targets out."**

[![License](https://img.shields.io/badge/license-MIT-18181b?style=flat-square)](LICENSE)
[![Architecture](https://img.shields.io/badge/architecture-modular%20monorepo-0284c7?style=flat-square)](docs/architecture/ARCHITECTURE.md)
[![Status](https://img.shields.io/badge/status-production--ready-10b981?style=flat-square)](tests)
[![Tests](https://img.shields.io/badge/tests-35%20passing-38bdf8?style=flat-square)](tests)
[![CLI](https://img.shields.io/badge/cli-ziref--v1.0.0-6366f1?style=flat-square)](packages/cli)

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-core-capabilities">Capabilities</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-monorepo-layout">Monorepo</a> •
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-developer-cli">CLI</a> •
  <a href="#-documentation-sitemap">Documentation</a>
</p>

</div>

---

## 🌟 Overview

**Ziref** is a modern, modular, production-oriented developer platform designed to bridge the gap between web deployment and mobile application distribution.

Developers submit a raw project archive (ZIP) or connect a public Git repository. Ziref automatically analyzes the dependencies and build pipeline, provisions an isolated ephemeral Docker execution sandbox with enforced resource quotas, compiles the distribution bundle, serves the resulting immutable deployment behind a high-performance reverse router, and provides **1-click native mobile packaging into an installable Android APK** with zero manual Gradle configuration.

---

## 🚀 Core Capabilities

### 1. 🔍 Zero-Configuration Deterministic Analyzer
- **Polyglot & Framework Detection**: Automatic inspection of `package.json`, dependency trees, configuration manifests, and directory layouts.
- **Out-of-the-Box Framework Support**: Vite, React, Next.js, Vue, Angular, Node.js, and static HTML/CSS/JS.
- **Automated Parameter Inference**: Predicts package managers (`npm`, `pnpm`, `yarn`, `bun`), compilation scripts (`build`), output distribution directories (`dist`, `out`, `build`), and runtime execution modes.

### 2. 🛡️ Untrusted Code Isolation & Sandboxed Builds
- **Hardened Ephemeral Containers**: Build tasks execute inside isolated Docker containers with non-root user privileges, read-only root filesystems where appropriate, and strictly isolated bridge networking.
- **Resource Constraints (cgroups)**: Enforced limits per build task (1.0 CPU core, 1024 MB RAM, 128 max PIDs, and 300-second execution timeouts).
- **Archive Security Validation**: Defense against Zip Slip directory traversal, decompression bombs (100x uncompressed ratio limits), symlink escapes, and path manipulation attacks.
- **Zero-Prerequisite Subprocess Fallback**: Automatically falls back to an isolated process runner on local machines when Docker Desktop is inactive.

### 3. 📦 Atomic, Immutable Deployments & Rollbacks
- **Zero-Downtime Cutover**: Each build produces an immutable, SHA-256 verified `.tar.gz` distribution artifact extracted to an isolated directory path.
- **Traffic Pointer Switching**: Active traffic switches instantly via in-memory Redis routing caches and MongoDB pointers.
- **1-Click Instant Rollback**: Revert production traffic to any prior successful deployment in milliseconds.

### 4. 📱 Appify Engine (Native Android Compilation)
- **One-Click Native Transformation**: Transforms any deployed web application into a complete, modern Android Studio Kotlin project.
- **Production Android Architecture**: Modern `WebViewClient` shell, pull-to-refresh (`SwipeRefreshLayout`), offline fallback screens, and responsive lifecycle bindings.
- **Adaptive App Icons & Permissions**: Auto-generates Android adaptive vector drawables (`mipmap-anydpi-v26`) and wires selectable hardware permissions (`CAMERA`, `ACCESS_FINE_LOCATION`, `POST_NOTIFICATIONS`, `RECORD_AUDIO`).
- **Downloadable Artifacts**: Directly compiles and serves downloadable debug `.apk` files and full Gradle source `.zip` archives.

### 5. 🧠 AI Build Failure Diagnostics
- **Intelligent Error Pattern Matching**: Inspects terminal error streams to classify failure categories (`MISSING_DEPENDENCY`, `MISSING_BUILD_SCRIPT`, `COMMAND_NOT_FOUND`, `OUTPUT_DIRECTORY_MISSING`, `OUT_OF_MEMORY`, `TYPESCRIPT_ERROR`, `SYNTAX_ERROR`, `ENV_VAR_MISSING`).
- **Actionable Fix Guidance**: Generates root-cause summaries and copy-pasteable resolution commands right inside the dashboard and CLI.

### 6. 🌐 Hardened Production Site Router
- **Dynamic Multi-Tenant Routing**: Directs traffic based on subdomains (`<slug>.localhost:8080`), path prefixes (`/sites/<slug>/`), or custom verified CNAME hostnames (`app.mycompany.com`).
- **Production Security Headers**: Automatically applies `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection`, `Referrer-Policy`, and `Permissions-Policy`.
- **Intelligent Caching**: Injects `Cache-Control: public, max-age=31536000, immutable` on hashed assets (`.js`, `.css`, `/assets/`) and `no-cache` on `index.html`.
- **In-Flight Compression**: Native Gzip streaming compression middleware for sub-millisecond asset transfers.

### 7. 📊 Traffic Analytics & Observability
- **Real-Time Request Metrics**: Aggregates HTTP access traffic into total request counts, unique visitors, response status codes (`2xx`, `3xx`, `4xx`, `5xx`), and latency percentiles (`avg`, `p95`).
- **Endpoint Performance**: Tracks top visited paths and device distribution (Desktop, Mobile, Tablet).
- **Live Terminal Log Streaming**: Server-Sent Events (SSE) stream build logs and HTTP access logs live into the dashboard with sub-50ms latency.

### 8. 💻 Ziref Developer CLI (`packages/cli`)
- Zero-dependency, ANSI-colored command-line interface.
- Deploy local directories directly to production (`ziref deploy`), inspect logs (`ziref logs`), and download mobile APKs (`ziref appify`) without leaving the terminal.

### 9. 🔔 Outbound HMAC Webhooks
- Delivers real-time notifications for `build.completed`, `build.failed`, and `deployment.ready` to Slack, Discord, or custom backend services.
- Authenticated with cryptographic `X-Ziref-Signature` HMAC-SHA256 headers.

---

## 🏗️ System Architecture

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                           INGESTION CHANNELS                           │
 │   • Dashboard Web UI (Next.js 15)                                      │
 │   • Ziref Developer CLI (`ziref deploy`)                               │
 │   • Git Remote Clone (`POST /projects/import-git`)                     │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Multipart Archive / Git URL
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                           ZIREF API BACKEND                            │
 │   • FastAPI Async Gateway (Port 8000)                                  │
 │   • JWT + bcrypt Authentication & Multi-Tenant Authorization           │
 │   • Fernet Symmetric Secret Encryption at Rest                         │
 │   • Project Analyzer (Zip Slip, Bomb Defense, AST Framework Detection) │
 └───────────────────┬───────────────────────────────┬────────────────────┘
                     │ Push Job                      │ Persist
                     ▼                               ▼
       ┌───────────────────────────┐   ┌───────────────────────────┐
       │   REDIS JOB BROKER        │   │    MONGODB DATASTORE      │
       │   • `build` Queue         │   │   • Users & Projects      │
       │   • `deploy` Queue        │   │   • Builds & Deployments  │
       │   • `app_build` Queue     │   │   • Runtime Logs & Events │
       │   • Pub/Sub Event Channels│   │   • Encrypted Env Vars    │
       └─────────────┬─────────────┘   └───────────────────────────┘
                     │ Consume Job
                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      ISOLATED WORKER DAEMON                            │
 │   • Ephemeral Docker Sandbox Runner (CPU/RAM/PID Limits)               │
 │   • Subprocess Sandbox Fallback                                        │
 │   • Real-Time SSE Log Streaming via Redis Pub/Sub                      │
 │   • AI Build Failure Diagnostics Engine                                │
 │   • Android Kotlin Studio Project & APK Compiler                       │
 └───────────────────┬────────────────────────────────────────────────────┘
                     │ Store Artifact
                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                     STORAGE & ATOMIC ROUTING                           │
 │   • Artifact Repository (`./storage/artifacts/*.tar.gz`)               │
 │   • Immutable Deployments (`./storage/deployments/<id>/`)              │
 │   • Dynamic Reverse Site Router (FastAPI, Port 8080)                   │
 │   • Custom Domain Resolution & Security Header Injection               │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Monorepo Layout

```text
zipref/
├── apps/
│   └── dashboard/                  # Next.js 15 Dark-Themed Developer Dashboard
│       ├── app/                    # App Router (Pages: Overview, Projects, Logs, Analytics, Appify)
│       ├── components/             # Reusable UI components, TerminalViewer, StatusBadge
│       ├── lib/api.ts              # Type-safe API client for backend communication
│       └── public/                 # Static assets and demo fixtures
├── packages/
│   ├── cli/                        # Ziref Developer CLI (zero external dependencies)
│   │   ├── main.py                 # CLI entry point, argument parsing, ANSI formatting
│   │   ├── client.py               # HTTP client with multipart upload support
│   │   └── config.py               # Local token storage (~/.ziref/config.json)
│   └── types/                      # Shared TypeScript definitions (@ziref/types)
├── services/
│   ├── analyzer/                   # Framework detection & archive security
│   │   ├── archive_validator.py    # Path traversal, Zip Slip, bomb mitigation
│   │   ├── detector.py             # Deterministic AST & manifest framework analyzer
│   │   └── git_importer.py         # Shallow git clone & URL security sanitization
│   ├── api/                        # Central REST API Service (FastAPI)
│   │   ├── core/                   # Database (Mongo + Embedded), Redis (Live + In-Memory), Security
│   │   ├── routers/                # Auth, Projects, Uploads, Builds, Deployments, Domains, Analytics
│   │   └── schemas/                # Pydantic v2 validation contracts
│   ├── builder/                    # Sandbox execution engine
│   │   ├── docker_sandbox.py       # Hardened Docker container & fallback subprocess runner
│   │   ├── build_executor.py       # Pipeline coordinator, packaging, live log emitter
│   │   └── diagnostics.py          # AI build failure diagnostic classifier
│   ├── deployer/                   # Atomic deployment service & HTTP site router
│   │   ├── deployer_service.py     # Tarball unpacking, zero-downtime cutover, rollback
│   │   └── site_router.py          # Dynamic reverse proxy, custom domains, security headers
│   ├── app_builder/                # Web-to-mobile packaging engine
│   │   ├── android_generator.py    # Kotlin project generator, adaptive icons, permissions
│   │   └── apk_builder.py          # Installable debug APK compiler
│   └── worker/                     # Asynchronous background job daemon
├── infrastructure/
│   └── docker/                     # Dockerfiles for API, Worker, Router, Dashboard, Sandbox
├── scripts/
│   ├── dev.ps1                     # ⚡ ONE-COMMAND: Start all 4 services in parallel
│   ├── start-all.ps1               # Unified platform launch helper
│   ├── start-local.ps1             # Local development boot script
│   ├── test.ps1                    # Full automated test & build verification script
│   └── ziref.ps1                   # Developer CLI executable wrapper
├── storage/                        # Persistent volume (uploads, workspaces, artifacts, mobile)
├── tests/                          # 35 Automated Unit & Integration Tests (100% passing)
├── docker-compose.yml              # Production container orchestration
└── requirements.txt                # Python backend dependencies
```

---

## ⚡ Quickstart

### Prerequisites

| Requirement | Minimum Version | Notes |
| :--- | :--- | :--- |
| **Python** | 3.11+ (Tested on 3.14) | Core backend services and CLI |
| **Node.js** | 20+ (Tested on 22) | Next.js 15 dashboard |
| **pnpm** | 9+ (Tested on 11) | Monorepo package manager |
| **Docker Desktop** | Optional for Dev | Automatically activates embedded datastores if inactive |

---

### 1. Environment Setup

Clone the repository and initialize the environment file:

```bash
cp .env.example .env
```

---

### 2. Run Verification Test Suite

Verify all 35 Python unit and integration tests, as well as the Next.js production build:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
```

```text
==> Running Python Unit & Integration Tests...
============================= 35 passed in 8.87s ==============================
==> Verifying Dashboard Build & Types...
 ✓ Compiled successfully in 1.9s
 ✓ Generating static pages (9/9)
==> All Tests and Builds Passed Successfully!
```

---

### 3. Launch Development Services

#### ⚡ Option A: One-Command Launch (Recommended)

Starts **all 4 services in parallel** in a single terminal window with live color-coded log output. Press `Ctrl+C` to stop everything cleanly.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

> **What this does:**
> - Attempts to start Docker datastores (MongoDB & Redis) — falls back to embedded in-memory datastores automatically if Docker is unavailable.
> - Spawns the API Gateway, Worker Daemon, Site Router, and Next.js Dashboard as parallel background jobs.
> - Streams all service logs into one terminal with color-coded prefixes (`[API]`, `[Worker]`, `[SiteRouter]`, `[Dashboard]`).
> - Cleans up all processes on `Ctrl+C`.

#### Option B: Individual Service Commands

Run each service independently in its own terminal. All services can run in any order — they connect to each other automatically.

---

##### 🔷 Service 1 — API Gateway

The core FastAPI backend. Handles auth, project management, builds, deployments, analytics, and webhooks. Starts with hot-reload enabled.

```powershell
.\.venv\Scripts\uvicorn services.api.main:app --port 8000 --reload
```

| | |
|---|---|
| **Base URL** | `http://localhost:8000` |
| **Swagger Docs** | `http://localhost:8000/docs` |
| **ReDoc** | `http://localhost:8000/redoc` |

---

##### 🟣 Service 2 — Background Worker Daemon

Consumes build jobs from the Redis queue (or embedded memory queue), runs sandboxed builds, streams live logs, compiles Android APKs, and dispatches webhooks.

```powershell
.\.venv\Scripts\python -m services.worker.main
```

> Runs silently in the background. View its activity in the Dashboard → Builds log stream.

---

##### 🟡 Service 3 — Dynamic Site Router

FastAPI-based reverse proxy that serves deployed web apps. Routes traffic by subdomain (`<slug>.localhost:8080`), path prefix, or custom CNAME domain. Injects security headers and caching.

```powershell
.\.venv\Scripts\python -m services.deployer.main
```

| | |
|---|---|
| **Base URL** | `http://localhost:8080` |
| **Deployed Sites** | `http://<project-slug>.localhost:8080` |

---

##### 🔵 Service 4 — Next.js Dashboard

The developer-facing web UI. Built with Next.js 15 App Router. Provides project management, real-time build log streaming, analytics, and one-click Appify (Android APK generation).

```powershell
pnpm --filter dashboard dev
```

| | |
|---|---|
| **Dashboard URL** | `http://localhost:3000` |
| **Hot Reload** | Enabled (HMR via Next.js) |

#### Option C: Production Docker Compose

Runs the full stack (including MongoDB & Redis) inside Docker containers:

```bash
docker compose up -d
```

To view container logs:

```bash
docker compose logs -f
```

To stop all containers:

```bash
docker compose down
```

---

### 4. Service Endpoints & Ports

| Component | URL | Description |
| :--- | :--- | :--- |
| **Dashboard UI** | `http://localhost:3000` | Web application management console |
| **API Gateway** | `http://localhost:8000` | Core platform REST API |
| **Interactive Docs** | `http://localhost:8000/docs` | Swagger / OpenAPI interactive explorer |
| **Site Router** | `http://localhost:8080` | Live web preview & custom domain router |
| **MongoDB** | `localhost:27017` | Document database (embedded fallback available) |
| **Redis** | `localhost:6379` | Event broker & job queue (embedded fallback available) |

---

## 💻 Developer CLI Usage

The Ziref Developer CLI allows end-to-end deployments without ever leaving the terminal.

```bash
# 1. Authenticate with your Ziref account
python -m packages.cli.main login
# Or on Windows:
.\scripts\ziref.ps1 login

# 2. Verify authenticated user identity
.\scripts\ziref.ps1 whoami

# 3. List all deployed projects & live URLs
.\scripts\ziref.ps1 list

# 4. Deploy the current local directory
.\scripts\ziref.ps1 deploy

# 5. Transform project into a native Android APK and download directly
.\scripts\ziref.ps1 appify my-awesome-app
```

---

## 🔒 Security Architecture

Ziref enforces defense-in-depth across every stage of the lifecycle:

1. **Archive Ingestion Defense**:
   - **Zip Slip Traversal**: Explicit canonicalization of target paths ensures files cannot write outside destination boundaries.
   - **Decompression Bombs**: Verifies compressed vs. uncompressed byte ratios (max 100:1) and caps maximum archive extract size at 250 MB.
   - **Dangerous Elements**: Blocks Unix socket files, named pipes, and dangerous symbolic links that point outside the sandbox boundary.

2. **Sandbox Hardening**:
   - Non-root execution (`UID 10001`).
   - Host filesystem isolation (no Docker socket `/var/run/docker.sock` exposure).
   - Strict cgroups resource capping (CPU, memory, maximum PID count).

3. **Multi-Tenant Data Isolation**:
   - Every project, build, deployment, secret, and mobile artifact is tagged with tenant ownership identifiers.
   - API middleware strictly verifies tenant authorization headers on every request.

4. **Secret Storage**:
   - Environment variables are encrypted at rest using symmetric **Fernet (AES-128-CBC + HMAC-SHA256)** keys.
   - Secrets are masked in UI and API responses and injected into sandboxes only during build execution.

---

## 📚 Documentation Sitemap

Comprehensive specifications and operational guides are maintained in the [`docs/`](docs/) directory:

- 📋 [**Product Requirements Document (`docs/PRD.md`)**](docs/PRD.md): Vision, user personas, MVP scope, and product principles.
- 🏛️ [**Architecture Specification (`docs/ARCHITECTURE.md`)**](docs/ARCHITECTURE.md): Microservices topology, data models, and queue flows.
- 🛡️ [**Security Specification (`docs/SECURITY.md`)**](docs/SECURITY.md): Threat modeling, cgroups, sandbox constraints, and mitigation strategies.
- 🔌 [**REST & SSE API Reference (`docs/API.md`)**](docs/API.md): Full documentation of all HTTP endpoints, schemas, and live streams.
- 🚀 [**Production Deployment Guide (`docs/DEPLOYMENT.md`)**](docs/DEPLOYMENT.md): Production scaling, SSL termination, and orchestration instructions.
- 🤝 [**Contributing Guide (`docs/CONTRIBUTING.md`)**](docs/CONTRIBUTING.md): Monorepo setup, branch standards, and code hygiene rules.
- 🗺️ [**Product Roadmap (`docs/ROADMAP.md`)**](docs/ROADMAP.md): Detailed phase breakdown from core MVP to commercial SaaS scaling.

---

## 🧪 Testing

Execute the comprehensive automated test suite:

```bash
# Run all unit and integration tests
.\.venv\Scripts\python -m pytest tests/ -v

# Run targeted test suites
.\.venv\Scripts\python -m pytest tests/unit/test_diagnostics.py
.\.venv\Scripts\python -m pytest tests/unit/test_analytics.py
.\.venv\Scripts\python -m pytest tests/integration/test_git_import.py
.\.venv\Scripts\python -m pytest tests/integration/test_router_security.py
```

---

## 📄 License

This project is licensed under the terms of the **MIT License**. See [`LICENSE`](LICENSE) for details.

Developed with precision for modern software engineering teams.
