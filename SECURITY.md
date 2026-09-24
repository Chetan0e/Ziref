# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.x     | ✅ Yes     |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub Issues.**

If you discover a security vulnerability in Ziref, please report it responsibly:

1. **Email**: Open a private GitHub Security Advisory via the **Security** tab → **Report a vulnerability**.
2. **Response Time**: We aim to acknowledge reports within **48 hours** and provide a resolution timeline within **7 days**.
3. **Disclosure**: We follow coordinated disclosure — please allow us time to patch before public disclosure.

## What to Include

A good vulnerability report includes:

- A clear description of the vulnerability and its potential impact.
- Step-by-step reproduction instructions.
- Affected version(s) and environment details.
- Proof-of-concept code or screenshots (where applicable).

## Security Architecture Overview

Ziref enforces defense-in-depth at every stage:

- **Archive Ingestion**: Zip Slip prevention, decompression bomb limits (100:1 ratio, 250 MB max), symlink sanitization.
- **Build Sandbox**: Ephemeral non-root Docker containers (`UID 1001`), no Docker socket exposure, strict cgroup resource caps.
- **Secret Storage**: Fernet (AES-128-CBC + HMAC-SHA256) encryption at rest; secrets are masked in all API responses and logs.
- **Multi-Tenant Isolation**: Per-request `user_id` authorization validation on every project, build, and deployment operation.
- **Security Headers**: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy` applied to all routed sites.

For the full threat model, see [`docs/SECURITY.md`](docs/SECURITY.md).
