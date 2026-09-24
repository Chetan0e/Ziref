# Security Architecture & Threat Model — Ziref

## 1. Security Principles

1. **Untrusted Code Execution**: Every uploaded project archive and build command is treated as untrusted and potentially hostile.
2. **Defense in Depth**: Security controls are enforced at archive ingestion, container isolation, process privileges, and network boundaries.
3. **Least Privilege**: Containers and application processes run with minimal permissions and cannot access the host machine or Docker socket.
4. **Secret Zero**: Secrets are encrypted at rest, masked in UI and API output, and injected strictly into the sandbox environment.

---

## 2. Threat Model

| Threat | Impact | Mitigation Strategy | Residual Risk |
|---|---|---|---|
| **Malicious Archive / Zip Slip** | Path traversal, overwriting host files | Archive validator verifies every path. Rejects any entry with `..`, leading `/`, or absolute paths. Rejects symlinks pointing outside target directory. | Negligible |
| **Zip Bomb / Decompression Bomb** | Denial of service, disk exhaustion | Enforce maximum uncompressed size (250MB limit) and compression ratio checks during streaming extraction. Max 10,000 files. | Low |
| **Container Breakout** | Host takeover | Build runs inside unprivileged container (`--security-opt=no-new-privileges:true`), non-root user (`UID 1001`), Docker socket is never mounted. | Low |
| **Host Resource Exhaustion** | Worker slowdown or crash | Hard cgroup limits enforced per build: `1024MB RAM`, `1.0 CPU`, `128 PIDs`, and a `300s` execution timeout. | Low |
| **Secret Exfiltration** | Leakage of API keys and credentials | Sensitive environment variables are stored using Fernet symmetric encryption. Environment values are never logged in build events or returned raw to frontend without masking. | Low |
| **Cross-Tenant Access** | Access to another user's projects/builds | Backend authorization middleware explicitly validates `user_id == project.user_id` on every operation. | Low |

---

## 3. Archive Validation Engine

Before any ZIP file is unpacked onto disk or sent to the build runner, it is passed through `ArchiveValidator`:

```python
class ArchiveValidator:
    MAX_FILE_SIZE = 50 * 1024 * 1024       # 50 MB compressed
    MAX_EXTRACTED_SIZE = 250 * 1024 * 1024 # 250 MB uncompressed
    MAX_FILE_COUNT = 10000                 # Max 10,000 files
    MAX_COMPRESSION_RATIO = 100            # Ratio limit
```

Checks performed:
1. Valid ZIP structure (magic bytes & valid central directory).
2. Path traversal check: Normalizing file paths and ensuring they remain strictly within the target extract root.
3. Symlink safety: Symlinks pointing outside extraction boundary are rejected or sanitized.
4. Hidden malicious executables: Dangerous binaries or `.exe`/`.bat`/`.sh` root autoruns are flagged.

---

## 4. Docker Sandbox Isolation

Build containers are launched with the following configuration:

```bash
docker run \
  --name "ziref-build-${BUILD_ID}" \
  --memory="1024m" \
  --cpus="1.0" \
  --pids-limit=128 \
  --security-opt="no-new-privileges:true" \
  --user="1001:1001" \
  --network="bridge" \
  --rm \
  ziref-sandbox-node:latest
```

Containers are strictly ephemeral and automatically destroyed on build completion, cancellation, or timeout.
