# Autergo API Reference

**Base URL:** `/api/v1`  
**Protocol:** HTTP/HTTPS  
**Format:** JSON  

---

## Authentication

Autergo uses **cookie-based authentication** with httpOnly cookies and CSRF double-submit pattern. Tokens are never stored in JavaScript/localStorage.

### Auth Headers

For state-changing requests (POST, PUT, DELETE, PATCH), include a `X-CSRF-Token` header:
```
X-CSRF-Token: <csrf_token_from_cookie>
```

Alternatively, use Bearer token auth for API clients:
```
Authorization: Bearer <jwt_access_token>
```

### Cookie Types

| Cookie | Type | Accessible | Expiry | Purpose |
|--------|------|------------|--------|---------|
| `access_token` | httpOnly | Server only | 30 minutes | Authenticates requests |
| `refresh_token` | httpOnly | Server only | 7 days | Obtains new access tokens |
| `csrf_token` | Standard | JavaScript | Session | CSRF protection |

### Authentication Flow

```
1. POST /auth/login          → Receive cookies
2. GET  /users/me            → Validate session, get user profile
3. POST /auth/refresh        → Refresh expired access token
4. POST /auth/logout         → Clear session
```

### SSO Providers

- Google: `GET /auth/google/login`
- GitHub: `GET /auth/github/login`
- LinkedIn: `GET /auth/linkedin/login`

All SSO flows redirect to the provider's authorization page, then back to the frontend upon success.

---

## Common Patterns

### Pagination

List endpoints support cursor or offset-based pagination:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of records to skip |
| `limit` | integer | 50 | Max records to return (max 100) |

### Error Format

```json
{
  "detail": "Human-readable error message"
}
```

### Standard Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes | `application/json` (unless file upload) |
| `X-CSRF-Token` | State-changing | CSRF token from cookie |
| `Authorization` | Optional | `Bearer <token>` for API clients |

---

## Endpoints

---

### Authentication

#### `POST /auth/login`

Authenticate user and establish session.

**Request:**
```
Content-Type: application/x-www-form-urlencoded
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Email or username |
| `password` | string | Yes | User password |

**Response:** `200 OK`
```
Set-Cookie: access_token=<jwt>; HttpOnly; Path=/; SameSite=Lax
Set-Cookie: refresh_token=<jwt>; HttpOnly; Path=/; SameSite=Lax
Set-Cookie: csrf_token=<token>; Path=/; SameSite=Lax
```
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

**Errors:** `401 Unauthorized` — Invalid credentials or account locked

---

#### `POST /auth/register`

Create a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecureP@ss1",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "user_type": "student"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `email` | string | Yes | — | Valid email address |
| `password` | string | Yes | — | Min 8 chars, 1 uppercase, 1 number |
| `username` | string | Yes | — | 3-50 chars, alphanumeric + underscore |
| `first_name` | string | Yes | — | 1-50 chars |
| `last_name` | string | Yes | — | 1-50 chars |
| `user_type` | string | No | `student` | `student`, `hr`, or `admin` |

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "user_type": "student",
  "is_active": true,
  "created_at": "2026-05-23T10:00:00Z"
}
```

**Errors:** `409 Conflict` — Email or username already exists

---

#### `POST /auth/refresh`

Refresh the access token using the refresh cookie.

**Request:** (no body — refresh token sent via cookie)

**Response:** `200 OK`
```
Set-Cookie: access_token=<new_jwt>; HttpOnly; ...
```

**Errors:** `401 Unauthorized` — Expired or invalid refresh token

---

#### `POST /auth/logout`

Clear the session and invalidate cookies.

**Response:** `200 OK`
```
Set-Cookie: access_token=; Max-Age=0; ...
Set-Cookie: refresh_token=; Max-Age=0; ...
Set-Cookie: csrf_token=; Max-Age=0; ...
```

---

#### `POST /auth/forgot-password`

Send a password reset email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK` (always returns success to prevent email enumeration)

---

#### `POST /auth/reset-password`

Reset password using token from email.

**Request:**
```json
{
  "token": "reset-token-from-email",
  "password": "NewSecureP@ss1"
}
```

**Errors:** `400 Bad Request` — Invalid or expired token

---

### User Management

All endpoints require authentication unless noted.

#### `GET /users/me`

Get the current authenticated user's profile.

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "user_type": "student",
  "role": "student",
  "is_active": true,
  "profile_photo": "https://...",
  "created_at": "2026-05-23T10:00:00Z"
}
```

---

#### `PUT /users/username`

Update display username.

**Request:**
```json
{
  "username": "newusername"
}
```

**Response:** `200 OK`
```json
{
  "username": "newusername"
}
```

---

#### `POST /users/change-password`

Change current password.

**Request:**
```json
{
  "current_password": "oldpassword",
  "new_password": "newpassword"
}
```

**Errors:** `400 Bad Request` — Incorrect current password

---

#### `GET /users/sessions/{id}/report`

Get detailed interview report.

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "candidate_name": "John Doe",
  "job_role": "Software Engineer",
  "date": "2026-05-23T10:00:00Z",
  "duration_minutes": 35,
  "overall_score": 7.8,
  "strengths": ["Strong problem-solving", "Clear communication"],
  "weaknesses": ["System design needs improvement"],
  "skill_matrix": { "python": 8, "algorithms": 7, "system_design": 5 },
  "hire_recommendation": "yes",
  "transcript": [...]
}
```

---

#### `GET /users/sessions/{id}/certificate`

Get interview certificate as PDF download.

**Response:** `200 OK` (PDF binary, `Content-Type: application/pdf`)

---

#### `GET /users/sessions/{id}/certificate/png`

Get interview certificate as PNG image.

**Response:** `200 OK` (PNG binary, `Content-Type: image/png`)

---

#### `GET /users/export-data`

GDPR data export — returns all user data as JSON.

---

#### `POST /users/delete-account`

Request account deletion (30-day grace period).

**Response:** `200 OK`
```json
{
  "message": "Account deletion scheduled. You have 30 days to cancel.",
  "scheduled_deletion_at": "2026-06-22T10:00:00Z"
}
```

---

#### `POST /users/cancel-deletion`

Cancel pending account deletion request.

---

#### `GET /users/consent`

Get current GDPR consent preferences.

**Response:** `200 OK`
```json
{
  "consents": {
    "interview": true,
    "analytics": true,
    "marketing": false,
    "cookies": true
  }
}
```

---

#### `POST /users/consent`

Update GDPR consent preferences.

**Request:**
```json
{
  "purpose": "marketing",
  "granted": false
}
```

---

### Profiles

#### `POST /profiles/student`

Create or update student profile.

**Request:**
```json
{
  "university": "MIT",
  "degree": "B.S. Computer Science",
  "graduation_year": 2027,
  "gpa": 3.8,
  "skills": ["Python", "JavaScript", "React", "AWS"],
  "experience_level": "junior",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "portfolio_url": "https://johndoe.dev"
}
```

**Response:** `201 Created`

---

#### `GET /profiles/student`

Get current student profile.

---

#### `POST /profiles/student/resume`

Upload and parse resume (PDF).

**Request:** `multipart/form-data`
| Field | Type | Description |
|-------|------|-------------|
| `file` | File | PDF file, max 10MB |

**Response:** `200 OK`
```json
{
  "resume_text": "Parsed text content...",
  "skills_summary": ["Python", "React", "AWS"]
}
```

---

#### `POST /profiles/hr`

Create or update HR profile.

**Request:**
```json
{
  "company_name": "Tech Corp",
  "company_website": "https://techcorp.com",
  "company_industry": "Technology",
  "department": "Engineering",
  "position": "Technical Recruiter",
  "hiring_volume": 50,
  "common_roles": ["Software Engineer", "Data Scientist"]
}
```

---

### Interview Engine

#### `WS /interview/ws/{session_id}`

Real-time interview WebSocket connection.

**Authentication:**
- **Authenticated users:** Pass `auth_token` as query parameter (JWT)
- **Guest/Invite users:** Pass `drive_id` and `token` as query parameters

**Message Types (Server → Client):**

```json
// Question
{
  "type": "question",
  "data": {
    "question": "Explain the difference between REST and GraphQL...",
    "question_index": 3,
    "phase": "technical",
    "difficulty": "medium",
    "audio": "base64-encoded-audio",
    "is_coding": false
  }
}

// Status Update
{
  "type": "status",
  "data": {
    "status": "evaluating",
    "message": "Analyzing your response..."
  }
}

// Metrics Update
{
  "type": "metrics_update",
  "data": {
    "avg_score": 7.5,
    "skill_coverage": 65,
    "current_phase": "technical",
    "questions_remaining": 8
  }
}

// Execution Result (coding)
{
  "type": "execution_result",
  "data": {
    "stdout": "Hello World!",
    "stderr": "",
    "passed": true
  }
}

// Advisor Suggestion
{
  "type": "advisor_suggestion",
  "data": {
    "ready_to_close": false,
    "confidence": 0.85,
    "reason": "Candidate has demonstrated strong knowledge across all required skills"
  }
}

// Interview Complete
{
  "type": "complete",
  "data": {
    "session_id": "uuid",
    "overall_score": 7.8,
    "hire_recommendation": "yes",
    "redirect_url": "/report/uuid"
  }
}

// Error
{
  "type": "error",
  "data": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "AI service temporarily unavailable"
  }
}
```

**Message Types (Client → Server):**

```json
// Answer (verbal)
{
  "type": "answer",
  "data": {
    "text": "REST is a stateless architectural style...",
    "audio": "base64-encoded-audio"  // optional
  }
}

// Code submission
{
  "type": "code",
  "data": {
    "code": "def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)",
    "language": "python"
  }
}
```

---

#### `POST /interview/sessions/{id}/hr-instruction`

Inject HR instructions into an active interview session.

**Authentication:** HR/Admin required  
**Rate Limit:** 20/minute

**Request:**
```json
{
  "instruction": "Focus more on system design topics"
}
```

---

#### `WS /interview/video/{room_id}`

WebRTC signaling relay for video interviews.

**Message Types (bidirectional):**
```
offer, answer, ice_candidate, toggle_video, toggle_audio
```

---

### Student Endpoints

#### `GET /student/stats`

Get student dashboard statistics.

**Response:** `200 OK`
```json
{
  "total_interviews": 15,
  "completed_interviews": 12,
  "average_score": 7.3,
  "top_skills": ["Python", "Algorithms"],
  "recent_sessions": [...]
}
```

---

#### `GET /student/interviews`

Get paginated list of student's interviews.

**Query Parameters:** `skip`, `limit`, `status`

---

#### `GET /student/sessions/{id}/skill-gap`

Get skill gap analysis comparing candidate skills to role requirements.

**Response:** `200 OK`
```json
{
  "candidate_skills": { "python": 8, "react": 7, "aws": 4 },
  "required_skills": { "python": 7, "react": 6, "aws": 7, "docker": 5 },
  "gaps": ["aws", "docker"],
  "recommendations": ["Learn Docker fundamentals", "AWS certification prep"]
}
```

---

#### `GET /student/sessions/{id}/replay`

Get step-by-step interview replay data.

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "steps": [
    {
      "index": 1,
      "phase": "warmup",
      "question": "Tell me about yourself",
      "answer": "I'm a CS graduate with...",
      "score": 7.5,
      "feedback": "Good structure, could add more specific examples"
    }
  ]
}
```

---

### HR Endpoints

Authentication: HR or Admin role required.

#### `POST /hr/drives`

Create a new interview drive.

**Request:**
```json
{
  "title": "Backend Engineer 2026",
  "description": "Hiring for our backend team",
  "job_role": "Backend Engineer",
  "experience_required": "2-5 years",
  "skills_required": ["Python", "FastAPI", "PostgreSQL", "Docker"]
}
```

**Response:** `201 Created`

---

#### `GET /hr/drives`

Get paginated list of HR's drives.

**Query Parameters:** `skip`, `limit`, `is_active`

---

#### `PUT /hr/drives/{id}`

Update drive details.

---

#### `DELETE /hr/drives/{id}`

Soft-delete a drive.

---

#### `POST /hr/drives/{id}/magic-link`

Generate a magic invite link for candidates.

**Response:** `200 OK`
```json
{
  "magic_link": "https://app.vedrix.com/interview?drive_id=uuid&token=secret"
}
```

---

#### `POST /hr/drives/{id}/bulk-invite`

Send bulk email invites to candidates.

**Request:**
```json
{
  "emails": ["candidate1@example.com", "candidate2@example.com"]
}
```

---

#### `GET /hr/drives/{id}/candidates`

Get candidate list for a drive with scores.

---

#### `GET /hr/interviews`

Get all interviews for HR's drives.

**Query Parameters:** `drive_id`, `status`, `skip`, `limit`

---

#### `GET /hr/interviews/{id}`

Get detailed interview information.

---

#### `GET /hr/interviews/{id}/pdf`

Download interview report as PDF.

---

#### `GET /hr/interviews/{id}/skill-gap`

Get skill gap analysis for a specific interview.

---

#### `GET /hr/interviews/{id}/replay`

Get interview replay data.

---

#### `POST /hr/interviews/schedule`

Schedule a new interview.

**Request:**
```json
{
  "candidate_email": "candidate@example.com",
  "drive_id": "uuid",
  "scheduled_time": "2026-05-25T14:00:00Z",
  "duration_minutes": 60
}
```

---

#### `POST /hr/feedback/candidate`

Submit candidate feedback survey response.

---

#### `POST /hr/feedback/hr`

Submit HR evaluation for a candidate.

**Request:**
```json
{
  "session_id": "uuid",
  "strengths": ["Communication", "Technical depth"],
  "weaknesses": ["System design"],
  "hire_recommendation": "yes",
  "notes": "Great candidate, recommend moving to final round"
}
```

---

#### `POST /hr/import/validate`

Validate CSV candidate import file.

---

#### `POST /hr/import/execute`

Execute validated CSV import.

---

#### `GET /hr/analytics/export/csv`

Export HR analytics as CSV.

---

### Admin Endpoints

Authentication: Admin role required.

#### `GET /admin/stats`

Get global platform statistics.

**Response:** `200 OK`
```json
{
  "total_users": 1500,
  "active_users_today": 120,
  "total_interviews": 3200,
  "completed_today": 45,
  "average_score": 7.2,
  "active_sessions": 8
}
```

---

#### `GET /admin/users`

Get paginated user list.

**Query Parameters:** `skip`, `limit`, `user_type`, `search`, `is_active`

---

#### `PATCH /admin/users/{id}`

Update user details (including role changes).

---

#### `DELETE /admin/users/{id}`

Soft-delete a user.

---

#### `POST /admin/users/{id}/reset-password`

Force-reset a user's password.

---

#### `GET /admin/ai-health`

Check health status of all AI providers.

**Response:** `200 OK`
```json
{
  "groq": "available",
  "nvidia": "available",
  "openrouter": "degraded",
  "openai": "available",
  "apifree": "circuit_open"
}
```

---

#### `GET /admin/drives`

Get all drives across all HR users.

---

#### `POST /admin/drives/{id}/magic-link`

Generate magic link for any drive.

---

#### `GET /admin/interviews`

Get all interviews across the platform.

---

#### `GET /admin/interviews/{id}/pdf`

Download any interview report PDF.

---

#### `CRUD /admin/templates`

Manage interview scenario templates.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/templates` | List all templates |
| POST | `/admin/templates` | Create template |
| PATCH | `/admin/templates/{id}` | Update template |
| DELETE | `/admin/templates/{id}` | Delete template |

---

#### `GET /admin/audit-logs`

Get paginated audit logs.

**Query Parameters:** `user_id`, `action`, `start_date`, `end_date`, `skip`, `limit`

---

#### `GET /admin/analytics/team`

Get team-wide analytics data.

**Response:** `200 OK`
```json
{
  "total_interviews": 3200,
  "avg_score": 7.2,
  "hire_rate": 0.45,
  "score_distribution": { "0-4": 5, "4-6": 20, "6-8": 45, "8-10": 30 },
  "daily_trends": [...],
  "role_breakdown": { "backend": 1200, "frontend": 800, "fullstack": 600 }
}
```

---

#### `GET /admin/analytics/export/csv`

Export analytics as CSV.

---

### Health & Monitoring

#### `GET /health`

Basic liveness check.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

#### `GET /health/ready`

Readiness check including database connectivity.

**Response:** `200 OK`
```json
{
  "status": "ready",
  "database": "connected",
  "redis": "connected",
  "uptime_seconds": 3600
}
```

---

#### `GET /metrics`

Prometheus metrics endpoint (text format).

---

### Developer Tools

| Tool | URL | Description |
|------|-----|-------------|
| Swagger UI | `/docs` | Interactive API documentation |
| ReDoc | `/redoc` | Alternative API documentation viewer |
| Prometheus | `/metrics` | Application metrics |
| Health Check | `/health` | Basic liveness |
| Readiness | `/health/ready` | Full readiness |

---

## Error Codes

| Status | Code | Description |
|--------|------|-------------|
| `400` | Bad Request | Invalid input data |
| `401` | Unauthorized | Missing or invalid authentication |
| `403` | Forbidden | Insufficient permissions or CSRF failure |
| `404` | Not Found | Resource does not exist |
| `409` | Conflict | Duplicate resource (email, username) |
| `422` | Unprocessable | Validation error in request body |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Error | Server-side failure |
| `503` | Service Unavailable | Backend or database is down |

### WebSocket Error Codes

| Code | Description |
|------|-------------|
| `AUTH_FAILED` | Invalid or expired authentication |
| `SESSION_NOT_FOUND` | Interview session does not exist |
| `SESSION_COMPLETED` | Interview already finished |
| `PROVIDER_UNAVAILABLE` | AI provider circuit is open |
| `INVALID_MESSAGE` | Malformed WebSocket message |
| `RATE_LIMITED` | Too many messages in short period |

---

## Rate Limits

| Endpoint Group | Limit | Scope |
|----------------|-------|-------|
| Auth (login, register) | 10/minute | IP address |
| Interview WebSocket | 100/minute | Session |
| HR Instruction | 20/minute | Session |
| OAuth | 5/minute | IP address |
| General API | 100/minute | User |
| Admin endpoints | 200/minute | User |

---

## Data Types

### User Types

| Value | Description |
|-------|-------------|
| `student` | Candidate taking interviews |
| `hr` | Recruiter or HR personnel |
| `admin` | Platform administrator |

### Interview Phases

| Phase | Description |
|-------|-------------|
| `greeting` | Introduction and system check |
| `welcome` | Overview and expectations |
| `warmup` | Easy icebreaker questions |
| `technical` | Core technical assessment |
| `stress` | Challenging problem-solving |
| `behavioral` | Soft skills and experience |
| `closing` | Summary and next steps |

### Interview Status

| Status | Description |
|--------|-------------|
| `scheduled` | Interview booked but not started |
| `in_progress` | Interview is active |
| `completed` | Candidate finished |
| `hr_closed` | HR terminated the session |

---

## SDK Examples

### cURL

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=SecureP@ss1" \
  -c cookies.txt

# Get user profile
curl http://localhost:8000/api/v1/users/me \
  -b cookies.txt

# Create HR drive (with CSRF token)
CSRF=$(grep csrf_token cookies.txt | awk '{print $7}')
curl -X POST http://localhost:8000/api/v1/hr/drives \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -b cookies.txt \
  -d '{"title":"Backend Engineer","job_role":"Backend Engineer","skills_required":["Python","FastAPI"]}'

# Health check
curl http://localhost:8000/health
```

### Python

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000/api/v1")

# Login
response = client.post(
    "/auth/login",
    data={"username": "johndoe", "password": "SecureP@ss1"},
)
cookies = response.cookies

# Get user profile
response = client.get("/users/me", cookies=cookies)
user = response.json()

# With Bearer token
token = response.json()["access_token"]
response = client.get(
    "/users/me",
    headers={"Authorization": f"Bearer {token}"}
)
```

### JavaScript (Axios)

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' }
});

// CSRF token interceptor
api.interceptors.request.use((config) => {
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1];
  
  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

// Login
await api.post('/auth/login', 
  `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
  { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
);

// Get profile
const { data: user } = await api.get('/users/me');

// Create drive
const { data: drive } = await api.post('/hr/drives', {
  title: 'Backend Engineer',
  job_role: 'Backend Engineer',
  skills_required: ['Python', 'FastAPI']
});
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | May 2026 | Initial API release |

---

*For interactive exploration, visit `/docs` (Swagger UI) when running in development mode.*
