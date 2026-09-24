# Product Roadmap — Ziref

This roadmap charts the evolution of Ziref into an enterprise-grade developer platform.

---

## Phase 1: MVP Core (Completed)
- [x] Secure ZIP upload & path traversal protection
- [x] Deterministic project analyzer (React, Vite, Next.js, Vue, Angular, HTML)
- [x] Docker sandbox build engine with resource limits & timeouts
- [x] Real-time SSE build log streaming
- [x] Immutable static deployment & zero-downtime cutover
- [x] Encrypted environment variables management
- [x] Appify engine: Android Studio project generator & APK compilation
- [x] Modern dark developer dashboard with Next.js & Tailwind CSS
- [x] Bundled 1-Click React 18 + Vite sample demo fixture

---

## Phase 2: Git-Based Workflows & Developer Tooling (Completed)
- [x] Ziref Developer CLI (`packages/cli`): `login`, `whoami`, `deploy`, `status`, `logs`, `appify`
- [x] Git repository URL cloning & shallow extraction (`POST /api/v1/projects/import-git`)
- [x] Dashboard Git import flow with branch selection
- [x] Outbound HMAC-SHA256 signed webhook notification system (Slack, Discord, API)
- [x] Instant project redeploy without re-uploading (`POST /projects/{id}/redeploy`)
- [ ] OAuth integration for automated GitHub / GitLab webhook syncing

---

## Phase 3: Runtime & Routing Hardening (Completed)
- [x] Dynamic custom domain mapping and CNAME resolution in Site Router
- [x] Production security headers (`X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `CSP`)
- [x] Intelligent Cache-Control headers for static hashed assets vs HTML
- [x] Gzip compression middleware on asset routing
- [x] Real-time traffic analytics API (`GET /api/v1/projects/{id}/analytics`)
- [x] Interactive in-dashboard traffic metrics & top paths breakdown
- [ ] Node.js server-rendered application compute (SSR runners)
- [ ] Python web application runtime (FastAPI, Flask)

---

## Phase 4: Extended Mobile & Native Capabilities (Enhanced)
- [x] Adaptive Android app icons (`mipmap-anydpi-v26` vector drawables)
- [x] Configurable native permissions (Camera, GPS Location, Notifications, Audio)
- [x] Modern `WebView` optimizations (SwipeRefreshLayout, offline fallback screen, safe mixed content)
- [x] Interactive native phone simulator with bezel in Dashboard
- [ ] iOS build pipeline (macOS build runners)
- [ ] App Store & Google Play automated release publishing

---

## Phase 5: Intelligence, Governance & Commercial SaaS
- [x] AI build failure diagnosis engine with category classification and actionable fixes
- [x] Interactive in-dashboard diagnosis banner on failed builds
- [ ] Multi-member organizations & Role-Based Access Control (RBAC)
- [ ] Usage metering (build minutes, bandwidth, active deployments)
- [ ] Stripe billing integration with Free, Pro, and Team tiers
