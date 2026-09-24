# Changelog

All notable changes to Ziref are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-09-24

### Added
- **Zero-Configuration Analyzer**: Automatic polyglot framework detection (Vite, React, Next.js, Vue, Angular, Node.js, static HTML/CSS).
- **Sandboxed Build Engine**: Ephemeral Docker container execution with enforced CPU, RAM, PID, and timeout constraints (cgroups).
- **Archive Security Validator**: Defense against Zip Slip traversal, decompression bombs, symlink escapes, and path manipulation.
- **Subprocess Fallback Runner**: Automatic isolated process runner when Docker Desktop is unavailable.
- **Atomic Immutable Deployments**: SHA-256 verified tarball artifacts with zero-downtime traffic switching.
- **1-Click Rollback**: Instant revert to any prior successful deployment via Redis routing cache pointer update.
- **Appify Engine**: One-click web-to-native Android APK transformation with Kotlin `WebViewClient`, adaptive icons, and selectable permissions.
- **AI Build Failure Diagnostics**: Pattern-matching classifier for 8+ failure categories with root-cause summaries and fix commands.
- **Dynamic Multi-Tenant Site Router**: Subdomain, path prefix, and custom CNAME routing with full security header injection.
- **Real-Time Log Streaming**: Server-Sent Events (SSE) build log and access log streams with sub-50ms latency.
- **Traffic Analytics**: Request aggregation, unique visitors, status codes, latency percentiles, and device distribution.
- **HMAC Webhooks**: Cryptographic `X-Ziref-Signature` authenticated outbound notifications for `build.*` and `deployment.*` events.
- **Ziref Developer CLI**: Zero-dependency ANSI-colored terminal CLI (`deploy`, `logs`, `appify`, `list`, `whoami`).
- **JWT + bcrypt Authentication**: Secure multi-tenant authentication with Fernet-encrypted secret storage at rest.
- **Docker Compose Orchestration**: Production-grade `docker-compose.yml` for full-stack local and cloud deployment.
- **35 Automated Tests**: Full unit and integration test suite (100% passing).
- **Next.js 15 Dashboard**: App Router dashboard with dark theme, real-time streams, analytics, and Appify UI.
