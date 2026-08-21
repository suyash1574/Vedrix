# Autergo Deployment Guide

## Quick Start

### Local Development
```bash
cd Vedrix
python run_dev.py
```
Access: http://localhost:5173

### Docker Compose (All Services)
```bash
cd Vedrix
make docker-up
```

---

## Environments

| Environment | URL | Docker Compose |
|-------------|-----|----------------|
| Development | http://localhost:5173 | `docker-compose.yml` |
| Staging | https://staging.vedrix.com | `docker-compose.staging.yml` |
| Production | https://vedrix.com | `docker-compose.prod.yml` |

---

## Prerequisites

1. **Docker & Docker Compose** installed
2. **PostgreSQL 15+** (or use Docker)
3. **Redis 7+** (or use Docker)
4. **Node.js 20** (for frontend build)
5. **Python 3.12** (for backend)

---

## Manual Deployment Steps

### 1. Prepare Environment Variables
```bash
# Copy production env template
cp backend/.env.production backend/.env

# Edit with your values
nano backend/.env
```

Required variables:
- `SECRET_KEY` - Generate with: `openssl rand -base64 32`
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `GROQ_API_KEY` - Your API key
- `OPENROUTER_API_KEY` - Your API key

### 2. Build Images
```bash
# Backend
cd backend
docker build -t vedrix/backend:latest .

# Frontend
cd ../frontend
docker build -t vedrix/frontend:latest .
```

### 3. Start Services
```bash
# Production
cd Vedrix
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verify Deployment
```bash
# Check health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

---

## Using Makefile

```bash
# Start all services
make docker-up

# View logs
make logs

# Stop services
make docker-down

# Backup database
make db-backup

# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-prod
```

---

## GitHub Actions Deployment

### CI Pipeline (Automatic on PR)
- Runs tests
- Builds frontend
- Lints code
- Security scans

### CD Pipeline (Automatic on Main)
1. Builds Docker images
2. Pushes to registry
3. Deploys to staging (manual trigger)
4. Deploys to production (automatic on main)

### Required Secrets
Add these in GitHub repository settings:
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password
- `STAGING_HOST` - Staging server IP
- `STAGING_USER` - SSH user for staging
- `STAGING_SSH_KEY` - Private SSH key
- `PRODUCTION_HOST` - Production server IP
- `PRODUCTION_USER` - SSH user for production
- `PRODUCTION_SSH_KEY` - Private SSH key

---

## Kubernetes Deployment

For large-scale production deployments:

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
```

---

## Monitoring

### Metrics Endpoint
```
http://localhost:8000/metrics
```

Key metrics:
- `http_requests_total` - Total HTTP requests
- `interviews_started_total` - Interviews started
- `interviews_completed_total` - Interviews completed
- `active_interviews` - Current active interviews

### Health Checks
```
/health         - Basic health check
/health/ready   - Readiness check (includes DB)
/metrics        - Prometheus metrics
```

---

## Backup & Restore

### Backup
```bash
# Manual backup
./scripts/backup.sh production

# Or use Makefile
make db-backup
```

### Restore
```bash
# List backups
ls -la backups/

# Restore (replace FILENAME with actual file)
FILE=vedrix_production_20260101_120000.sql
make db-restore FILE=$FILE
```

---

## Troubleshooting

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Restart service
```bash
docker-compose restart backend
```

### Check health
```bash
curl http://localhost:8000/health/ready
```

### Database connection issues
```bash
# Check if database is running
docker ps | grep postgres

# Connect to database
docker exec -it vedrix-db-prod psql -U postgres -d vedrix_prod
```

---

## Security Checklist

- [ ] Change default `SECRET_KEY`
- [ ] Use strong PostgreSQL password
- [ ] Enable SSL for production
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Regular backups
- [ ] Update dependencies regularly

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-repo/issues
- Email: support@vedrix.com