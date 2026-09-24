# System Architecture — Ziref

## 1. Architectural Blueprint

```text
                             ┌───────────────────────┐
                             │       User Browser    │
                             └───────────┬───────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │ (Port 3000)                             │ (Port 8080)
                    ▼                                         ▼
         ┌─────────────────────┐                   ┌─────────────────────┐
         │   Dashboard (Web)   │                   │  Deployer / Router  │
         │   Next.js 15 App    │                   │ Reverse Proxy / SPA │
         └──────────┬──────────┘                   └──────────┬──────────┘
                    │ REST / SSE                              │ Static / Proxy
                    ▼                                         ▼
         ┌─────────────────────┐                   ┌─────────────────────┐
         │      Ziref API      │                   │ Deployed Artifacts  │
         │   FastAPI Service   │                   │ /storage/deployments│
         └──────────┬──────────┘                   └─────────────────────┘
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
  ┌─────────┐  ┌─────────┐  ┌─────────┐
  │ MongoDB │  │  Redis  │  │ Storage │
  └─────────┘  └────┬────┘  └─────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│  Build Worker   │   │  Appify Worker  │
└────────┬────────┘   └────────┬────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│ Docker Sandbox  │   │ Android Builder │
│  (Isolated Env) │   │ (Gradle / APK)  │
└─────────────────┘   └─────────────────┘
```

---

## 2. Core Subsystems

### 2.1 API Service (`services/api`)
- **Framework**: FastAPI (Python 3.12+ async).
- **Responsibilities**:
  - Request authentication & RBAC.
  - Project CRUD and metadata lifecycle.
  - Upload reception & archive security validation.
  - Build & Appify job submission to Redis queues.
  - Real-time log streaming over Server-Sent Events (SSE).
  - Health & readiness probes (`/health`, `/ready`).

### 2.2 Storage Engine Abstraction (`packages/storage` / `services/api/core/storage.py`)
- Provides a unified storage interface:
  - `save_file(stream, path)`
  - `get_file(path)`
  - `delete_file(path)`
  - `exists(path)`
- Backends supported:
  - Local Disk / Volume storage (`LocalStorageDriver`)
  - S3 / MinIO compatible storage (`S3StorageDriver`)

### 2.3 Analyzer Engine (`services/analyzer`)
- Deterministic heuristic engine that inspects extracted project trees:
  - Detects `package.json`, lockfiles (`pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`, `bun.lockb`).
  - Detects config files: `vite.config.*`, `next.config.*`, `astro.config.*`, `svelte.config.*`, `angular.json`, `vue.config.*`.
  - Determines build command, dev/start command, and target output directory (`dist`, `build`, `.next`, `out`).

### 2.4 Build Worker & Docker Sandbox (`services/builder` & `services/worker`)
- Background daemon consuming from the Redis `build_queue`.
- Spins up an ephemeral container with strict resource constraints:
  - Image: `ziref-sandbox-node:latest`
  - RAM limit: `1024MB`
  - CPU quota: `1.0 vCPU`
  - PID limit: `128`
  - Network: Enabled during dependency resolution, optionally sandboxed during build.
  - Non-root user (`builduser`).
- Captures stdout/stderr into structured events (`timestamp`, `stage`, `level`, `message`).
- Publishes events to Redis Pub/Sub channel `build:{build_id}:logs` for real-time streaming and saves to MongoDB.
- Compresses output directory into an immutable tarball artifact.

### 2.5 Deployer & Site Router (`services/deployer`)
- Manages deployment directory: `/storage/deployments/{deployment_id}`.
- Resolves requests via:
  - Hostname: `http://<slug>.localhost:8080` or `http://<slug>.localtest.me:8080`
  - Path: `http://localhost:8080/sites/<slug>/`
- Serves static assets with appropriate MIME types and caching headers.
- Implements SPA fallback (serves `index.html` on 404 for client-side routing).
- Atomic rollback: Updating project's active deployment pointer changes the served site instantly with zero rebuild or restart.

### 2.6 Appify Engine (`services/app-builder`)
- Transforms any deployed web application into an installable Android APK.
- Generates a complete Android Studio / Gradle project structure:
  - `app/src/main/AndroidManifest.xml` (with network permissions and intent filters)
  - `MainActivity.kt` (configured WebView with DOM storage, file upload, error handling)
  - Resources: App icons, splash screens, theme colors, manifest strings.
- Executes Gradle compilation inside an Android build container or Gradle script to produce an installable debug APK.
- Archives the complete Android project source code into `.zip` for developers wanting native customization.

---

## 3. Data Store Schema (MongoDB)

| Collection | Key Fields | Purpose |
|------------|------------|---------|
| `users` | `_id`, `email`, `password_hash`, `name`, `created_at` | User identities |
| `sessions` | `_id`, `user_id`, `token_hash`, `expires_at` | Active user sessions |
| `projects` | `_id`, `user_id`, `name`, `slug`, `framework`, `active_deployment_id`, `status` | Project definitions |
| `uploads` | `_id`, `project_id`, `file_size`, `checksum`, `storage_path`, `analysis` | Uploaded ZIP records |
| `builds` | `_id`, `project_id`, `upload_id`, `status`, `exit_code`, `duration_seconds` | Build execution records |
| `build_events` | `_id`, `build_id`, `timestamp`, `stage`, `level`, `message` | Structured build logs |
| `deployments` | `_id`, `project_id`, `build_id`, `status`, `url`, `artifact_path` | Immutable deployments |
| `environment_variables` | `_id`, `project_id`, `key`, `encrypted_value`, `is_secret` | Project secrets |
| `mobile_apps` | `_id`, `project_id`, `app_name`, `package_id`, `version`, `theme` | Mobile app configurations |
| `mobile_builds` | `_id`, `mobile_app_id`, `status`, `apk_artifact_id`, `source_artifact_id` | Android build records |
