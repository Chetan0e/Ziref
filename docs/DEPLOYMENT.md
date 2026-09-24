# Deployment Guide — Ziref Platform

This guide describes how to run Ziref in local development and production environments.

---

## 1. System Requirements

- **Linux / macOS / Windows** (with WSL2 for Docker)
- **Docker & Docker Compose** (Docker Engine 24+)
- **Node.js 20+** (v20.x or v22.x LTS) & **pnpm 9+**
- **Python 3.11+**

---

## 2. Docker Compose Deployment (Single Node / On-Prem)

The easiest way to bootstrap the entire Ziref infrastructure is via `docker-compose.yml`.

### Architecture of the Compose Stack:
- `mongodb`: Primary document database (Port 27017)
- `redis`: In-memory broker for job queues and Pub/Sub (Port 6379)
- `api`: FastAPI application service (Port 8000)
- `worker`: Python background processor executing builds & Appify pipelines
- `deployer`: Static site router and reverse proxy (Port 8080)
- `dashboard`: Next.js web application (Port 3000)

### Quick Boot:

```bash
# 1. Setup environment file
cp .env.example .env

# 2. Build and start containers
docker compose up -d --build

# 3. Check container status
docker compose ps

# 4. View unified logs
docker compose logs -f
```

---

## 3. Distributed Cloud Deployment

In a cloud production environment (e.g. AWS, GCP, Azure, or Kubernetes):
1. **Database**: Managed MongoDB (Atlas or DocumentDB) + Managed Redis (ElastiCache or Redis Enterprise).
2. **Object Storage**: S3-compatible bucket (AWS S3, Cloudflare R2, or Google Cloud Storage) configured via `STORAGE_PROVIDER=s3`.
3. **API & Dashboard**: Deployed as scalable container services (e.g. AWS ECS, Google Cloud Run, or Kubernetes Deployments).
4. **Workers**: Deployed as autoscaling container instances with access to Docker-in-Docker (or Kubernetes Job controller) with resource quotas.
5. **Reverse Proxy**: Cloudflare / AWS ALB terminating SSL with wildcard certificate (`*.ziref.app`) pointing to the Deployer service.

---

## 4. Environment Variables Reference

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | Environment mode (`development`, `staging`, `production`) |
| `BASE_DOMAIN` | `localhost:8080` | Root domain for generated project URLs |
| `MONGODB_URI` | `mongodb://localhost:27017/ziref` | MongoDB connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `JWT_SECRET` | `secret_key_change_me` | Secret for signing JWT authentication tokens |
| `STORAGE_PROVIDER` | `local` | Storage provider (`local` or `s3`) |
| `STORAGE_PATH` | `/var/ziref/storage` | Local directory for storing archives & artifacts |
| `BUILD_CPU_LIMIT` | `1.0` | CPU limit for build sandbox container |
| `BUILD_MEMORY_LIMIT` | `1024m` | Memory limit for build sandbox container |
| `BUILD_TIMEOUT_SECONDS` | `300` | Max duration for a build job in seconds |
| `WORKER_CONCURRENCY` | `4` | Number of concurrent jobs per worker instance |
