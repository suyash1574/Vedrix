# Autergo Operations Runbook

**Audience:** On-call engineers, DevOps, and platform maintainers.  
**Purpose:** Standard operating procedures for common operational scenarios.

---

## Table of Contents

1. [Service Health Check](#1-service-health-check)
2. [Application Restart](#2-application-restart)
3. [AI Provider Failure](#3-ai-provider-failure)
4. [Database Recovery](#4-database-recovery)
5. [High Latency / Performance Degradation](#5-high-latency--performance-degradation)
6. [WebSocket Connection Issues](#6-websocket-connection-issues)
7. [Rate Limiting Issues](#7-rate-limiting-issues)
8. [Certificate Generation Failure](#8-certificate-generation-failure)
9. [Account Lockout Issues](#9-account-lockout-issues)
10. [Session Cleanup Problems](#10-session-cleanup-problems)
11. [Audit Log Investigation](#11-audit-log-investigation)
12. [Emergency Escalation](#12-emergency-escalation)

---

## 1. Service Health Check

### When to Use
- On-call handoff
- User reports "the app is down"
- Monitoring alert fires

### Prerequisites
- Access to the server (SSH or Kubernetes)
- Access to Docker logs

### Step-by-Step

**Step 1: Check basic health**

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{"status": "healthy", "version": "1.0.0"}
```

**Step 2: Check readiness** (includes database)

```bash
curl http://localhost:8000/health/ready
```

**Expected response:**
```json
{"status": "ready", "database": "connected", "redis": "connected", "uptime_seconds": 3600}
```

**Step 3: Check all services are running**

```bash
docker ps
```

**Expected output:**
```
CONTAINER ID   IMAGE                STATUS         PORTS                    NAMES
abc12345       vedrix-backend:latest  Up 2 hours   0.0.0.0:8000->8000/tcp   vedrix-backend
def67890       vedrix-frontend:latest Up 2 hours   0.0.0.0:5173->80/tcp     vedrix-frontend
ghi11121       postgres:15           Up 2 hours   0.0.0.0:5432->5432/tcp   vedrix-postgres
jkl22232       redis:7-alpine        Up 2 hours   0.0.0.0:6379->6379/tcp   vedrix-redis
```

**Step 4: Check AI provider health**

```bash
curl http://localhost:8000/api/v1/admin/ai-health
```

**Step 5: Check Prometheus metrics**

```bash
curl http://localhost:8000/metrics | grep -E "(http_requests_total|active_interviews|ai_api_calls_total)"
```

### Expected State

All health endpoints return 200, all containers are `Up`, AI providers are `available` or `degraded` (not `circuit_open`).

### Rollback

If services are unhealthy, proceed to [Application Restart](#2-application-restart).

---

## 2. Application Restart

### When to Use
- After configuration changes
- After deployment
- Unhealthy service from health check
- Memory leak suspected

### Step-by-Step

**Option A: Full Stack Restart (Docker)**

```bash
# Graceful restart
docker-compose -f Autergo/docker-compose.prod.yml down
docker-compose -f Autergo/docker-compose.prod.yml up -d

# Verify
docker-compose -f Autergo/docker-compose.prod.yml ps
```

**Option B: Single Service Restart**

```bash
# Restart backend only (zero-downtime for frontend)
docker-compose restart backend

# Restart frontend only
docker-compose restart frontend
```

**Option C: Backend with Clear Cache**

```bash
docker-compose restart backend
docker exec vedrix-redis redis-cli FLUSHALL
```

### Verification

```bash
sleep 5  # Wait for services to initialize
curl http://localhost:8000/health/ready
```

### Rollback

```bash
# Rollback to previous version
docker-compose -f Autergo/docker-compose.prod.yml down
docker pull vedrix/backend:previous-tag
docker pull vedrix/frontend:previous-tag
docker-compose -f Autergo/docker-compose.prod.yml up -d
```

---

## 3. AI Provider Failure

### When to Use
- Interview questions are not being generated
- Users report "AI service unavailable" errors
- Circuit breaker alert fires
- `GET /admin/ai-health` shows `circuit_open` or `unavailable`

### Symptoms

- WebSocket messages showing `{"type": "error", "data": {"code": "PROVIDER_UNAVAILABLE"}}`
- Fallback questions being used exclusively
- Increased latency on interview endpoints

### Step-by-Step

**Step 1: Check provider status**

```bash
curl http://localhost:8000/api/v1/admin/ai-health
```

**Step 2: Check circuit breaker logs**

```bash
docker logs vedrix-backend --since 5m | grep "circuit_breaker"
```

**Step 3: Check API key validity**

```bash
# Test Groq
curl -X POST "https://api.groq.com/openai/v1/chat/completions" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"test"}]}'

# Test OpenRouter
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen/qwen-2.5-coder-32b-instruct","messages":[{"role":"user","content":"test"}]}'
```

**Step 4: Clear circuit breaker cache** (if provider recovered)

```bash
# Restart backend to reset circuit breakers
docker-compose restart backend
```

**Step 5: Review provider dashboard**

| Provider | Dashboard |
|----------|-----------|
| Groq | https://console.groq.com |
| OpenRouter | https://openrouter.ai/activity |
| NVIDIA | https://build.nvidia.com |

### Resolution

- **Rate limited:** Wait for rate limit window to reset (usually 1 minute)
- **Quota exhausted:** Upgrade API plan or switch providers
- **Provider outage:** The system automatically falls back through the provider chain
- **Invalid key:** Update the key in environment variables and restart

### Escalation

If all providers are down simultaneously:
1. The system falls back to static questions from `fallback_questions.py`
2. Escalate to platform team for emergency provider configuration changes
3. Consider enabling `apifree` provider as temporary fallback

---

## 4. Database Recovery

### When to Use
- Database connection errors in logs
- `GET /health/ready` shows `database: "disconnected"`
- Data corruption suspected
- Accidental data deletion

### Step-by-Step

**Step 1: Verify database connection**

```bash
# From host
docker exec vedrix-postgres pg_isready -U postgres

# Check connection from backend
docker logs vedrix-backend --since 5m | grep "database"
```

**Step 2: Check disk space**

```bash
docker exec vedrix-postgres df -h /var/lib/postgresql/data
```

**Step 3: Restore from backup**

```bash
# List available backups
ls -la backups/

# Restore
gunzip -c backups/vedrix_production_20260501.sql.gz | docker exec -i vedrix-postgres psql -U postgres -d vedrix_prod
```

**Step 4: Verify data integrity**

```bash
# Check user count
docker exec -i vedrix-postgres psql -U postgres -d vedrix_prod -c "SELECT COUNT(*) FROM \"user\";"

# Check active sessions
docker exec -i vedrix-postgres psql -U postgres -d vedrix_prod -c "SELECT COUNT(*) FROM interviewsession WHERE status = 'in_progress';"
```

### SQLite (Development)

For local SQLite development:

```bash
# Backup
cp backend/vedrix.db backend/vedrix.db.backup

# Restore
cp backend/vedrix.db.backup backend/vedrix.db

# Or delete and restart (auto-creates fresh)
rm backend/vedrix.db
# Restart backend
```

### Rollback

If the restore causes issues, restore a different backup point or re-run database migrations:

```bash
cd backend
alembic upgrade head    # Run pending migrations
```

---

## 5. High Latency / Performance Degradation

### When to Use
- API response times > 2 seconds (p95)
- Users report slow interview responses
- Monitoring alert for slow requests
- `ai_api_duration` metrics show high values

### Step-by-Step

**Step 1: Check current latency**

```bash
curl http://localhost:8000/metrics | grep "http_request_duration"
```

**Step 2: Check slow AI provider calls**

```bash
docker logs vedrix-backend --since 30m | grep "slow_request\|>2s"
```

**Step 3: Check database query performance**

```bash
docker logs vedrix-backend --since 30m | grep "slow_query\|>500ms"
```

**Step 4: Check connection pool usage**

```bash
docker logs vedrix-backend --since 5m | grep "pool"
```

### Common Causes & Solutions

| Cause | Symptom | Solution |
|-------|---------|----------|
| AI provider latency | High `ai_api_duration` | Switch to faster provider or upgrade plan |
| Database connection pool exhausted | Pool timeout errors | Increase `pool_size` in `db/session.py` |
| Slow queries | `slow_query` log entries | Add database indexes or optimize queries |
| Redis not responding | Cache miss storm | Restart Redis or check connection |
| Memory pressure | Container OOM kills | Increase container memory limits |
| Too many active interviews | High `active_interviews` | Scale backend horizontally |

### Resolution

```bash
# Option 1: Increase connection pool (requires restart)
# Edit backend/app/db/session.py
# pool_size=20, max_overflow=40
docker-compose restart backend

# Option 2: Scale horizontally (Kubernetes)
kubectl scale deployment vedrix-backend --replicas=3

# Option 3: Clear Redis cache
docker exec vedrix-redis redis-cli FLUSHALL
```

---

## 6. WebSocket Connection Issues

### When to Use
- Users cannot start or continue interviews
- WebSocket disconnects during interview
- "WebSocket is closed before the connection is established" errors

### Step-by-Step

**Step 1: Verify WebSocket endpoint is accessible**

```bash
# Test WebSocket connection
curl -i -N -H "Upgrade: websocket" -H "Connection: Upgrade" \
  http://localhost:8000/api/v1/interview/ws/test-session \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=="
```

**Step 2: Check active connections**

```bash
docker logs vedrix-backend --since 10m | grep "WebSocket\|ConnectionManager"
```

**Step 3: Check for reverse proxy timeout**

```bash
# Check nginx/traefik logs if using a reverse proxy
docker logs vedrix-proxy --since 10m | grep "upstream"
```

**Step 4: Check WebSocket timeout settings**

```bash
# Verify env variables
docker exec vedrix-backend env | grep WS
```

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| 426 Upgrade Required | Missing `Upgrade: websocket` header | Check proxy configuration |
| Connection closed after 60s | Proxy timeout too low | Increase proxy timeout to > 30 min |
| 401 on WS connect | Expired or invalid auth token | Regenerate token before connecting |
| Max connections reached | Server limit hit | Increase `max_connections` or scale out |

### Resolution

```bash
# Increase WebSocket timeout in backend config
# Edit backend/app/services/session_cleanup.py
# Check SESSION_TIMEOUT value
docker-compose restart backend
```

---

## 7. Rate Limiting Issues

### When to Use
- Users getting 429 Too Many Requests errors
- Legitimate traffic being blocked
- HR instruction injection failing

### Step-by-Step

**Step 1: Check rate limit configuration**

```bash
docker logs vedrix-backend --since 5m | grep "rate_limit\|429"
```

**Step 2: Check current rate limit settings**

```bash
# View rate limit config in backend/app/core/rate_limit.py
grep -r "limiter.limit" Vedrix/backend/app/
```

**Step 3: Identify the affected endpoint**

The error response includes details:
```json
{"detail": "Rate limit exceeded: 10 per 1 minute"}
```

### Rate Limit Table

| Endpoint | Limit | Window | Scope |
|----------|-------|--------|-------|
| Auth login/register | 10 | 1 minute | IP |
| General API | 100 | 1 minute | User |
| HR instruction | 20 | 1 minute | Session |
| Admin API | 200 | 1 minute | User |
| OAuth | 5 | 1 minute | IP |

### Resolution

**Temporary — increase limit in code:**

```python
# In backend/app/api/v1/endpoints/auth.py
@router.post("/login")
@limiter.limit("20/minute")  # Increased from 10
async def login(...):
```

**Permanent — adjust in configuration:**

```python
# backend/app/core/rate_limit.py
# Consider making limits configurable via environment variables
```

---

## 8. Certificate Generation Failure

### When to Use
- Certificate download returns 500
- PDF generation fails
- PNG generation fails

### Step-by-Step

**Step 1: Check PDF service logs**

```bash
docker logs vedrix-backend --since 10m | grep "pdf\|certificate\|fpdf"
```

**Step 2: Check for missing fonts**

```bash
# Verify fonts directory exists
docker exec vedrix-backend ls -la /app/fonts/
```

**Step 3: Test PDF generation**

```bash
# Generate test PDF
curl http://localhost:8000/api/v1/users/sessions/test-uuid/certificate
```

### Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `FPDF error: Unsupported font` | Missing font file | Add font to deployment |
| `Session not found` | Session ID doesn't exist | Verify session UUID |
| `Score not available` | Session not completed | Wait for completion |
| `Memory error` | Large certificate generation | Increase container memory |

---

## 9. Account Lockout Issues

### When to Use
- User reports "account locked" despite correct password
- Lockout persists beyond 15 minutes
- Multiple failed login attempts from legitimate user

### Step-by-Step

**Step 1: Check user account status**

```bash
# Connect to DB and check
docker exec -i vedrix-postgres psql -U postgres -d vedrix_prod -c \
  "SELECT email, failed_login_attempts, locked_until, is_active FROM \"user\" WHERE email = 'user@example.com';"
```

**Step 2: Manually unlock account**

```bash
docker exec -i vedrix-postgres psql -U postgres -d vedrix_prod -c \
  "UPDATE \"user\" SET failed_login_attempts = 0, locked_until = NULL WHERE email = 'user@example.com';"
```

**Step 3: Notify user**

Inform the user they can try again immediately.

### Resolution

- The lockout automatically expires after 15 minutes
- Admins can force-unlock via the database
- Consider increasing the `failed_login_attempts` threshold if this is a recurring issue

---

## 10. Session Cleanup Problems

### When to Use
- Abandoned interviews not being cleaned up
- Active interviews count incorrect
- "Session already completed" errors for new attempts

### Step-by-Step

**Step 1: Check cleanup process is running**

```bash
docker logs vedrix-backend --since 30m | grep "cleanup\|session_cleanup"
```

**Step 2: Manually check for stuck sessions**

```bash
docker exec -i vedrix-postgres psql -U postgres -d vedrix_prod -c \
  "SELECT id, status, start_time, (strftime('%s','now') - strftime('%s', start_time)) / 60 as minutes_elapsed \
   FROM interviewsession WHERE status = 'in_progress' AND start_time < datetime('now', '-2 hours');"
```

**Step 3: Manually close stuck sessions**

```bash
docker exec -i vedrix-postgres psql -U postgres -d vedrix_prod -c \
  "UPDATE interviewsession SET status = 'hr_closed' \
   WHERE status = 'in_progress' AND start_time < datetime('now', '-2 hours');"
```

### Configuration

```python
# In backend/app/services/session_cleanup.py
INACTIVE_TIMEOUT = 30  # minutes
ABANDONED_TIMEOUT = 24 * 60  # minutes (24 hours)
CLEANUP_INTERVAL = 5  # minutes
```

---

## 11. Audit Log Investigation

### When to Use
- Suspicious activity reported
- Compliance investigation
- Debugging unauthorized access
- GDPR request for data processing records

### Step-by-Step

**Step 1: Query audit logs via API**

```bash
curl -H "Authorization: Bearer <admin-token>" \
  "http://localhost:8000/api/v1/admin/audit-logs?action=failed_login&start_date=2026-05-01"
```

**Step 2: Query directly from database**

```bash
docker exec -i vedrix-postgres psql -U postgres -d vedrix_prod -c \
  "SELECT * FROM auditlog WHERE action = 'failed_login' AND timestamp > now() - interval '24 hours' ORDER BY timestamp DESC;"
```

**Step 3: Export for compliance**

```bash
curl -H "Authorization: Bearer <admin-token>" \
  "http://localhost:8000/api/v1/admin/analytics/export/csv?start_date=2026-01-01&end_date=2026-05-23" \
  -o audit_export.csv
```

### Audit Log Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `user_id` | User who performed the action |
| `action` | Action type (login, create_drive, delete_user, etc.) |
| `target` | Affected resource |
| `timestamp` | When the action occurred |
| `ip_address` | Originating IP |
| `details` | Additional context (JSON) |
| `status_code` | HTTP response status |

---

## 12. Emergency Escalation

### Escalation Path

```
Level 0: On-call Engineer
  ├── Handles: Health checks, restarts, AI provider failures
  └── Time to resolve: < 30 minutes

Level 1: Platform Team
  ├── Handles: Database issues, deployment failures, scaling
  └── Time to resolve: < 2 hours

Level 2: Engineering Lead
  ├── Handles: Code bugs, architectural issues
  └── Time to resolve: < 8 hours

Level 3: CTO / Architect
  ├── Handles: Critical incidents, data loss, security breaches
  └── Time to resolve: Immediate
```

### Incident Severity Levels

| Severity | Definition | Response Time | Example |
|----------|------------|---------------|---------|
| **P1** | Complete service outage | < 15 minutes | All services down, database inaccessible |
| **P2** | Major feature broken | < 1 hour | AI providers all down, interview engine broken |
| **P3** | Partial feature broken | < 4 hours | Certificate generation fails, skill-gap missing |
| **P4** | Minor issue / cosmetic | < 1 week | UI alignment, typo in copy |

### Incident Response Procedure

1. **Identify** — Confirm the issue and its severity
2. **Contain** — Prevent further damage (restart, rollback, disable feature)
3. **Communicate** — Post incident status in team channel
4. **Investigate** — Use this runbook to diagnose
5. **Resolve** — Apply the fix
6. **Verify** — Confirm service is healthy
7. **Document** — Write a post-mortem within 24 hours

### Emergency Contact

| Role | Contact Method | Expected Response |
|------|---------------|-------------------|
| On-call engineer | Pager/slack @oncall | < 15 min |
| Platform team | Slack #platform | < 30 min |
| Engineering lead | Phone/Slack DM | < 1 hour |
| CTO | Phone (for P0/P1) | Immediate |

---

## Appendix: Useful Log Queries

```bash
# Recent errors
docker logs vedrix-backend --since 1h | grep -i "error\|exception\|traceback"

# Slow requests (>2s)
docker logs vedrix-backend --since 1h | grep "slow_request"

# AI provider calls
docker logs vedrix-backend --since 1h | grep "ai_api\|groq\|nvidia\|openrouter"

# Authentication failures
docker logs vedrix-backend --since 24h | grep "failed_login\|401\|Unauthorized"

# WebSocket connections
docker logs vedrix-backend --since 1h | grep "WebSocket\|ws_connect\|ws_disconnect"

# Rate limit hits
docker logs vedrix-backend --since 1h | grep "429\|rate_limit"

# Database queries
docker logs vedrix-backend --since 1h | grep "slow_query\|db_query"

# Follow logs in real-time
docker logs -f vedrix-backend --tail 100
```

---

## Appendix: Diagnostic Commands

```bash
# System resource usage
docker stats --no-stream

# Container logs (last 50 lines)
docker logs --tail 50 vedrix-backend

# Check disk usage
df -h

# Check memory
free -m

# Check CPU
top -bn1 | head -20

# Network connectivity test
docker exec vedrix-backend curl -s -o /dev/null -w "%{http_code}" http://vedrix-postgres:5432

# DNS resolution test
docker exec vedrix-backend nslookup api.groq.com

# TLS test
docker exec vedrix-backend openssl s_client -connect api.groq.com:443 -servername api.groq.com
```

---

*Last updated: May 2026*  
*On-call rotation: See team calendar for current on-call engineer*
