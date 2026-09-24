# API Reference Specification — Ziref

All REST endpoints are versioned under `/api/v1`.

---

## 1. Authentication (`/api/v1/auth`)

### `POST /auth/register`
Create a new developer account.
- **Request Body**:
  ```json
  {
    "email": "dev@example.com",
    "password": "SecurePassword123!",
    "name": "Jane Developer"
  }
  ```
- **Response**: `201 Created`

### `POST /auth/login`
Authenticate with email and password.
- **Response**: `200 OK` (returns JWT token and sets secure session cookie).

### `GET /auth/me`
Fetch current user profile and workspace information.

---

## 2. Projects (`/api/v1/projects`)

### `GET /projects`
List all projects belonging to the authenticated user.

### `POST /projects`
Create a new empty project.

### `POST /projects/import-git`
Import and deploy directly from a public Git repository (GitHub/GitLab).
- **Request Body**:
  ```json
  {
    "name": "vite-starter",
    "repo_url": "https://github.com/vitejs/vite",
    "branch": "main",
    "slug": "my-vite"
  }
  ```
- **Response**: `201 Created` (returns `project_id`, `slug`, `build_id`, and detected `analysis`).

### `POST /projects/create-demo`
One-click deployment of the bundled React 18 + Vite sample fixture.

### `GET /projects/{id_or_slug}`
Get project details, latest deployment, and framework info.

### `POST /projects/{id}/redeploy`
Trigger an immediate rebuild and redeployment using the project's most recent source archive.

### `DELETE /projects/{id}`
Delete project and all associated builds, deployments, and artifacts.

---

## 3. Uploads & Analyzer (`/api/v1/projects/{id}/uploads`)

### `POST /projects/{id}/uploads`
Upload a project ZIP file.
- **Form Data**: `file: [project.zip]`
- **Response**: `201 Created`

---

## 4. Builds (`/api/v1/builds`)

### `POST /projects/{id}/builds`
Trigger an isolated Docker sandbox build from an upload.

### `GET /builds/{id}`
Get build status (`QUEUED`, `BUILDING`, `BUILT`, `FAILED`, `CANCELLED`), duration, exit code, and diagnosis.

### `GET /builds/{id}/diagnosis`
Fetch AI root-cause analysis for failed builds:
```json
{
  "build_id": "bld_...",
  "category": "MISSING_DEPENDENCY",
  "summary": "Missing dependency: 'axios'",
  "root_cause": "The package 'axios' is imported but not declared in dependencies.",
  "confidence": 0.95,
  "actionable_fix": "Add the package: run 'npm install axios', then re-deploy."
}
```

### `POST /builds/{id}/cancel`
Cancel an active build job.

### `POST /builds/{id}/retry`
Re-enqueue a build job with the same configuration.

### `GET /builds/{id}/artifact`
Download the compiled distribution `.tar.gz` artifact.

### `GET /builds/{id}/logs`
Get structured log events array.

### `GET /builds/{id}/logs/stream`
Server-Sent Events (SSE) live log streaming endpoint.

---

## 5. Traffic & Performance Analytics (`/api/v1/projects/{id}/analytics`)

### `GET /projects/{id}/analytics`
Aggregates live HTTP traffic from deployed endpoints:
```json
{
  "total_requests": 1420,
  "unique_visitors": 312,
  "avg_latency_ms": 14.2,
  "p95_latency_ms": 28.5,
  "status_codes": {
    "status_2xx": 1390,
    "status_3xx": 12,
    "status_4xx": 16,
    "status_5xx": 2
  },
  "device_breakdown": {
    "desktop": 1100,
    "mobile": 300,
    "bot_or_other": 20
  },
  "top_paths": [
    { "path": "/", "count": 820, "avg_latency_ms": 12.1 },
    { "path": "/assets/index.js", "count": 410, "avg_latency_ms": 5.4 }
  ]
}
```

---

## 6. Deployments (`/api/v1/deployments`)

### `GET /projects/{id}/deployments`
List deployment history for a project.

### `POST /projects/{id}/rollback`
Instantly roll back project routing to a previous successful deployment.

---

## 7. Outbound Webhooks (`/api/v1/projects/{id}/webhooks`)

- `GET /projects/{id}/webhooks`: List registered webhook subscriptions.
- `POST /projects/{id}/webhooks`: Register endpoint for `build.completed`, `build.failed`, `deployment.ready`.
- `DELETE /projects/{id}/webhooks/{webhook_id}`: Remove webhook.
- `POST /projects/{id}/webhooks/{webhook_id}/test`: Dispatch test ping.

All outgoing webhooks include the HMAC-SHA256 signature header:
`X-Ziref-Signature: <hex_digest>`

---

## 8. Appify Engine (`/api/v1/apps`)

### `POST /projects/{id}/apps`
Create mobile app configuration with native permissions (`camera`, `location`, `notifications`, `audio`).

### `POST /apps/{id}/build`
Start compilation of Android APK and Gradle project.

### `GET /mobile-builds/{id}/logs/stream`
SSE live log stream of the Android build process.

### `GET /mobile-builds/{id}/download/{type}`
Download build artifact (`type=apk` or `type=source`).

---

## 9. Health Probes

- `GET /health`: Liveness probe (API operational)
- `GET /ready`: Readiness probe (MongoDB and Redis connections verified)
