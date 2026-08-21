# Autergo Architecture Overview

**Audience:** Senior engineers, architects, and technical leads evaluating or contributing to the Autergo AI Interview System.

---

## System Context

Autergo is a dual-sided AI interview platform serving **candidates (B2C)** and **recruiters (B2B)**. It provides realistic, AI-driven interview experiences with automated evaluation, skill gap analysis, and detailed reporting.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| AI-Powered Interviews | LangGraph-orchestrated conversational interviews with dynamic question generation |
| Multi-Phase Interview | Greeting, warmup, technical, stress, behavioral, and closing phases |
| Real-Time Communication | WebSocket-based interview flow with optional WebRTC video |
| AI Evaluation | Multi-dimensional scoring (accuracy, clarity, depth, communication) with bias detection |
| Code Assessment | Live coding with Monaco editor, Judge0 execution sandbox, and AI code evaluation |
| HR Dashboard | Job drive management, candidate pipeline, skill matrices, AI advisor suggestions |
| Admin Panel | User management, system health monitoring, audit logs, platform analytics |
| Voice & Audio | Speech-to-text (Groq Whisper) and text-to-speech (OpenAI TTS) |
| SSO Integration | Google, GitHub, and LinkedIn OAuth login |
| GDPR Compliance | Consent tracking, data export, account deletion with grace period |

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser (React SPA)                        │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────┐  │
│  │ Landing  │  │ Student      │  │ HR         │  │ Admin     │  │
│  │ Page     │  │ Dashboard    │  │ Dashboard  │  │ Dashboard │  │
│  └──────────┘  └──────────────┘  └────────────┘  └───────────┘  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Interview Room (WS + WebRTC)             │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────┬───────────────────────────┘
                                       │ HTTP + WS
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend Server                        │
│                                                                   │
│  ┌────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │ Middleware  │  │   API Routers    │  │   WebSocket        │   │
│  │ Pipeline    │  │   (/api/v1/*)   │  │   Handlers         │   │
│  │  ┌──────┐   │  │  ┌────┐┌─────┐  │  │  ┌──────────────┐ │   │
│  │  │Rate  │   │  │  │Auth ││User │  │  │  │Interview     │ │   │
│  │  │Limit │   │  │  └────┘└─────┘  │  │  │Engine (WS)   │ │   │
│  │  │CSRF  │   │  │  ┌────┐┌─────┐  │  │  └──────────────┘ │   │
│  │  │Audit │   │  │  │ HR  ││Admin│  │  │  ┌──────────────┐ │   │
│  │  │Perf  │   │  │  └────┘└─────┘  │  │  │Video (WS)    │ │   │
│  │  │CORS  │   │  │  ┌────┐┌─────┐  │  │  └──────────────┘ │   │
│  │  └──────┘   │  │  │Student│Prof│  │  └────────────────────┘   │
│  └────────────┘  │  └────┘└─────┘  │                            │
│                  └──────────────────┘                            │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      Services Layer                         │  │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐ │  │
│  │  │ Interview Engine │ │ Evaluation      │ │ Voice        │ │  │
│  │  │ (LangGraph)      │ │ Service         │ │ Service      │ │  │
│  │  └─────────────────┘ └─────────────────┘ └──────────────┘ │  │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐ │  │
│  │  │ Cache Service   │ │ PDF/Cert        │ │ Export       │ │  │
│  │  │ (Redis)         │ │ Service         │ │ Service      │ │  │
│  │  └─────────────────┘ └─────────────────┘ └──────────────┘ │  │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐ │  │
│  │  │ Session Cleanup │ │ Code Execution  │ │ Bulk Import  │ │  │
│  │  │ (Background)    │ │ (Judge0)        │ │ Service      │ │  │
│  │  └─────────────────┘ └─────────────────┘ └──────────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     Core Infrastructure                     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Config   │  │ Security │  │ Metrics  │  │ Alerting │  │  │
│  │  │ (Env)    │  │ (JWT)    │  │(Prometh.)│  │(Slack)   │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Tracing  │  │Encryption│  │ Logging  │  │ Rate     │  │  │
│  │  │(OTel)    │  │(Fernet)  │  │ (JSON)   │  │ Limit    │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Database   │     │     Redis        │     │  External AI    │
│  SQLite/     │     │   Cache +        │     │  Providers      │
│  PostgreSQL  │     │   Session Store  │     │  Groq / NVIDIA  │
│              │     │                  │     │  / OpenRouter   │
│  - Users     │     │                  │     │  / OpenAI       │
│  - Profiles  │     │                  │     │  / ApiFree      │
│  - Sessions  │     │                  │     │                 │
│  - Drives    │     │                  │     │  Judge0 (Code   │
│  - Audit     │     │                  │     │  Execution)     │
└──────────────┘     └──────────────────┘     └─────────────────┘
```

---

## Backend Architecture

### Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python 3.12+) |
| ORM | SQLModel (SQLAlchemy + Pydantic) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Cache | Redis (with graceful degradation) |
| Auth | httpOnly cookies + JWT + CSRF double-submit |
| AI Orchestration | LangGraph (StateGraph with MemorySaver) |
| Real-Time | WebSockets (interview loop, video signaling) |
| Rate Limiting | slowapi |
| Monitoring | Prometheus metrics + OpenTelemetry tracing |
| Encryption | Fernet symmetric (field-level for PII) |

### Middleware Pipeline

Middleware executes in this order on every request:

```
┌─────────────┐    ┌──────────┐    ┌───────────┐
│ 1. Rate     │───▶│ 2. CSRF  │───▶│ 3. Audit  │
│    Limit    │    │          │    │    Log    │
└─────────────┘    └──────────┘    └───────────┘
                                              │
              ┌─────────────┐    ┌───────────┐
              │ 5. Request  │◀───│ 4. Perf   │
              │    ID       │    │ Monitor   │
              └─────────────┘    └───────────┘
```

1. **Rate Limiting** (slowapi) — Per-endpoint request throttling
2. **CSRF Protection** — Double-submit cookie pattern, exempts auth/health/WS/Bearer
3. **Audit Logging** — Records all state-changing actions with user context
4. **Performance Monitoring** — Tracks latency, feeds Prometheus metrics
5. **CORS** — Allows configured frontend origins
6. **Request ID** — Adds `X-Request-ID` header for tracing

### API Route Structure

All endpoints are mounted under `/api/v1`:

| Router | Prefix | Auth | Key Endpoints |
|--------|--------|------|---------------|
| Auth | `/auth` | Public | `POST /login`, `/register`, `/refresh`, `/logout`, password reset |
| OAuth | `/auth` | Public | `GET /google/login`, `/github/login`, `/linkedin/login` + callbacks |
| Users | `/users` | Authenticated | `GET /me`, session management, certificates, GDPR, consent |
| Profiles | `/profiles` | Authenticated | Student & HR profile CRUD |
| Resume | `/profiles` | Authenticated | Resume upload + AI parsing |
| Interview | `/interview` | Mixed | WebSocket loop, video signaling, HR instruction injection |
| Admin | `/admin` | Admin only | User CRUD, stats, AI health, drives, templates, audit logs |
| HR | `/hr` | HR/Admin | Drive CRUD, candidates, interviews, feedback, import, analytics |
| Student | `/student` | Student | Stats, interviews, skill-gap, replay |
| Voice | `/voice` | Public | Voice capabilities check |

### Authentication Flow

```
Client                      Server
  │                           │
  │  POST /auth/login         │
  │  (username + password)    │
  │                           ├── Verify credentials
  │                           ├── Check lockout status
  │                           ├── Create JWT access (30m)
  │                           ├── Create JWT refresh (7d)
  │                           ├── Set httpOnly cookies
  │                           └── Set csrf_token cookie (JS-readable)
  │◀────── 200 OK + cookies───│
  │                           │
  │  GET /users/me            │
  │  (httpOnly cookie sent    │
  │   automatically)          ├── Validate access token
  │◀────── User profile───────│
```

### Database Model Relationships

```
User
├── 1:1 ── StudentProfile
│           └── skills, resume, university, experience
├── 1:1 ── HRProfile
│           └── company, department, hiring_volume
│           └── 1:N ── JobDrive
│                       ├── title, role, skills
│                       ├── 1:N ── InterviewSession
│                       │           └── questions, responses, scores, feedback
│                       └── 1:N ── DriveInviteToken
│                                   └── token, email, status
└── 1:N ── InterviewSession (as candidate)
```

Additional standalone models:
- `ScenarioTemplate` — Reusable interview scenarios
- `AuditLog` — All state-changing actions
- `CandidateFeedback` / `HRFeedback` — Post-interview evaluations
- `UserConsent` — GDPR consent records

---

## LangGraph Interview Engine

The interview engine is the core AI component, built as a `StateGraph` with `MemorySaver` checkpointer.

### State

```python
class InterviewState(TypedDict):
    messages: Annotated[List[Dict], operator.add]
    resume_text: str
    job_role: str
    current_question_index: int      # max 15
    max_questions: int
    interview_complete: bool
    current_phase: str               # greeting → closing
    difficulty: str                  # easy / medium / hard
    latest_score: float
    avg_score: float
    covered_skills: List[str]
    skill_coverage_percentage: float
    interviewer_mode: str            # ai / human / suggestion
    is_coding_mode: bool
    # ... plus advisor, metrics, and evaluation fields
```

### Graph Flow

```
                     ┌──────────────────────────────────┐
                     │         START                     │
                     └───────────────────┬──────────────┘
                                         ▼
                     ┌──────────────────────────────────┐
                     │    generate_question_node         │
                     │  ─ Creates natural question      │
                     │  ─ Routes to coding or verbal    │
                     └──────────┬───────────────────────┘
                                │
                    ┌───────────┤ (is_coding_mode?)
                    ▼           ▼
          ┌─────────────────┐  ┌───────────────────┐
          │ evaluate_code   │  │ evaluate_answer    │
          │ node            │  │ node               │
          │ (Qwen 32B /     │  │ (Llama 3.3 70B /  │
          │  Judge0 exec)   │  │  Groq)             │
          └────────┬────────┘  └─────────┬──────────┘
                   │                     │
                   └──────────┬──────────┘
                              ▼
                    ┌──────────────────────┐
                    │  update_memory_node   │
                    │  ─ Update difficulty  │
                    │  ─ Track skill coverage│
                    │  ─ Calculate avg score │
                    │  ─ Check completion    │
                    └──────────┬────────────┘
                               ▼
                    ┌──────────────────────┐
                    │  advisor_monitor_node │
                    │  ─ Assess if enough   │
                    │    data to close      │
                    │  ─ Set ready_to_close │
                    └──────────┬────────────┘
                               │
                    ┌──────────┤ (should_continue?)
                    ▼          ▼
              ┌─────────┐  ┌────────┐
              │ LOOP    │  │  END   │
              │ (QGen)  │  │        │
              └─────────┘  └────────┘
```

### Completion Conditions (at least 6 questions required)

| Condition | Trigger |
|-----------|---------|
| Max questions reached | `current_question_index >= max_questions` |
| High skill coverage | `skill_coverage >= 85% AND avg_score >= 6.0` |
| Low quality streak | `>= 3 low-quality responses after question 5` |
| Strong performance | `>= 5 high-quality responses after question 10 AND avg >= 8.0` |
| Closing phase | Phase reaches `closing` after question 12 |

### Model Routing

| Task | Primary Model | Provider | Fallback Chain |
|------|---------------|----------|----------------|
| Question Generation | Llama 3.1 8B | Groq | NVIDIA 8B → ApiFree |
| Deep Follow-ups | Llama 3.1 70B | NVIDIA | Groq 70B |
| Answer Evaluation | Llama 3.3 70B | Groq | NVIDIA 70B |
| Code Evaluation | Qwen 2.5 Coder 32B | OpenRouter | Groq 70B → Groq 8B |
| Report Generation | Llama 3.1 70B | NVIDIA | Groq 70B |
| Resume Parsing | Llama 3.1 8B | Groq | NVIDIA 8B |

### Circuit Breaker

Per-provider circuit breaker with state machine:
- **CLOSED** → **OPEN**: 3 consecutive failures
- **OPEN** → **HALF_OPEN**: 60s recovery timeout
- **HALF_OPEN** → **CLOSED**: 1 successful request
- **HALF_OPEN** → **OPEN**: 1 failed request

---

## Frontend Architecture

### Stack

| Component | Technology |
|-----------|-----------|
| Framework | React 19 |
| Routing | react-router-dom v7 |
| State Management | Zustand v5 (auth only) |
| HTTP Client | Axios (with CSRF interceptor) |
| Styling | Tailwind CSS v4 (`@tailwindcss/vite`) |
| Charts | Recharts (radar, bar, pie, line charts) |
| Animations | framer-motion |
| Icons | lucide-react |
| Code Editor | Monaco (`@monaco-editor/react`) |
| Build | Vite 8 |

### Page Structure

```
Public Routes:
  /home           ─ Landing page (hero, features, CTA)
  /login          ─ Login (password + OAuth buttons)
  /register       ─ Registration (role selection)
  /interview      ─ Live interview room (WS + WebRTC)
  /verify/:token  ─ Certificate verification
  /feedback/survey ─ Post-interview feedback

Protected (Student):
  /dashboard           ─ Student dashboard + stats
  /report/:sessionId   ─ Interview report with radar chart
  /replay/:sessionId   ─ Step-by-step interview replay
  /skill-gap/:sessionId ─ Skill gap analysis
  /settings            ─ Profile, GDPR consent, data export

Protected (HR/Admin):
  /hr              ─ HR dashboard (drives, candidates)
  /hr/pipeline     ─ Candidate pipeline (Kanban view)
  /hr/schedule     ─ Calendar + scheduling modal
  /hr/feedback/:sessionId ─ HR evaluation form
  /report/:sessionId ─ Interview report

Protected (Admin):
  /admin           ─ Admin dashboard (CRUD)
  /admin/health    ─ System health monitoring
  /admin/audit-logs ─ Audit log viewer
  /admin/config    ─ System configuration
  /analytics/team  ─ Platform-wide analytics
```

### Data Flow

```
User Action
    │
    ▼
React Component ──→ Zustand Auth Store
    │                     │
    ▼                     ▼
Axios Client ──────→ FastAPI Backend
(withCredentials)       │
    │                   ▼
    │             API Router
    │                   │
    │             Service Layer
    │                   │
    │             Database / Redis / AI
    │                   │
    ◀───────────────────┘
    │
    ▼
Component Re-render
```

---

## Key Design Decisions

### 1. Cookie-Based Auth over JWT in localStorage
- **Decision:** Use httpOnly cookies for session tokens
- **Rationale:** Mitigates XSS token theft; csrf_token cookie (JS-readable) used for CSRF protection
- **Trade-off:** Requires same-site backend or proxy; more complex SSO redirect handling

### 2. LangGraph over Custom State Machine
- **Decision:** Use LangGraph StateGraph for interview orchestration
- **Rationale:** Built-in state persistence, checkpointing, streaming; clean node-based architecture
- **Trade-off:** Adds dependency footprint; debugging requires understanding of LangGraph internals

### 3. SQLite for Dev, PostgreSQL for Prod
- **Decision:** Support both via configurable DATABASE_URL
- **Rationale:** Zero-config dev setup; production-grade performance when needed
- **Trade-off:** Need to test against both; some SQL features differ between dialects

### 4. Task-Aware Model Routing
- **Decision:** Route each AI task to its optimal model with fallback chains
- **Rationale:** Cost optimization (small models for simple tasks); reliability via fallbacks
- **Trade-off:** Complexity in provider configuration; circuit breaker state management

### 5. Field-Level Encryption
- **Decision:** Encrypt PII fields (resume_text, skills, evaluations) at rest
- **Rationale:** Defense in depth; compliance with data protection requirements
- **Trade-off:** Cannot search encrypted fields; key management overhead

### 6. WebSocket for Interview, HTTP for Everything Else
- **Decision:** Use WebSocket only for the live interview loop; all other communication via REST
- **Rationale:** Interview requires bidirectional low-latency streaming; standard CRUD doesn't
- **Trade-off:** Dual protocol complexity; WebSocket scaling considerations

---

## Integration Points

### External AI Providers

```
                    ┌─────────────────────────────────────┐
                    │         FastAPI Backend              │
                    │                                     │
                    │  ┌───────────────────────────────┐  │
                    │  │  Model Router                  │  │
                    │  │  ┌──────────┐ ┌────────────┐  │  │
                    │  │  │ Task     │ │ Circuit    │  │  │
                    │  │  │ Router   │ │ Breaker    │  │  │
                    │  │  └──────────┘ └────────────┘  │  │
                    │  └──────────────┬────────────────┘  │
                    └─────────────────┼───────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │          ┌────────────────┤────────────────┐          │
          ▼          ▼                ▼                ▼          ▼
    ┌─────────┐ ┌─────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐
    │  Groq   │ │ NVIDIA  │ │  OpenRouter  │ │   OpenAI     │ │ ApiFree│
    │         │ │         │ │              │ │              │ │        │
    │ Llama   │ │ Llama   │ │ Qwen Coder   │ │  tts-1       │ │ Llama  │
    │ 3.1-8B  │ │ 3.1-70B │ │ 32B          │ │  (TTS)       │ │ 3.1-8B │
    │ 3.3-70B │ │ 3.1-8B  │ │              │ │              │ │        │
    │ Whisper │ │         │ │              │ │              │ │        │
    └─────────┘ └─────────┘ └──────────────┘ └──────────────┘ └────────┘
```

### Code Execution (Judge0)

```
Interview Room (Monaco Editor)
        │ Submit code
        ▼
FastAPI Backend
        │ POST /submissions
        ▼
Judge0 CE API ──→ Docker sandbox
        │           │
        ◀───────────┘
        ▼
Code Evaluation (Qwen Coder 32B)
        │
        ▼
Interview Feedback
```

### SSO Providers

```
Login Page ──→ /auth/{provider}/login ──→ Provider OAuth
                                                │
                                                ▼
                                    Provider Authorization Page
                                                │
                                    User approves
                                                │
                                                ▼
                                    /auth/{provider}/callback
                                                │
                                                ▼
                                    Create/Find User
                                                │
                                    Set httpOnly cookies
                                                │
                                    Redirect to Frontend
```

---

## Monitoring & Observability

### Metrics (Prometheus at `/metrics`)

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by path/method/status |
| `http_request_duration` | Histogram | Request latency distribution |
| `interviews_started_total` | Counter | Total interviews started |
| `interviews_completed_total` | Counter | Total interviews completed |
| `active_interviews` | Gauge | Currently active interviews |
| `ai_api_calls_total` | Counter | AI provider calls by provider |
| `ai_api_duration` | Histogram | AI API call latency |
| `db_query_duration` | Histogram | Database query latency |

### Health Checks

| Endpoint | Checks |
|----------|--------|
| `/health` | Basic liveness |
| `/health/ready` | Readiness (DB connectivity) |

### Alerting

The `AlertManager` monitors:
- Error rates exceeding thresholds
- Slow API requests (>2s p95)
- AI provider failures (3+ in 5 minutes)
- Slow database queries (>500ms)

Alerts are sent via email and/or Slack with configurable cooldown periods.

---

## Security Architecture

```
                     ┌─────────────────────────────┐
                     │      Internet / Client       │
                     │  https://app.vedrix.com      │
                     └─────────────┬───────────────┘
                                   │ HTTPS
                                   ▼
                     ┌─────────────────────────────┐
                     │         FastAPI              │
                     │                             │
                     │  ┌───────────────────────┐  │
                     │  │  Rate Limiting        │  │
                     │  │  (slowapi)            │  │
                     │  ├───────────────────────┤  │
                     │  │  CSRF Protection      │  │
                     │  │  (double-submit)      │  │
                     │  ├───────────────────────┤  │
                     │  │  JWT Validation       │  │
                     │  │  (httpOnly cookies)   │  │
                     │  ├───────────────────────┤  │
                     │  │  SQL Injection Guard  │  │
                     │  ├───────────────────────┤  │
                     │  │  Field Encryption     │  │
                     │  │  (Fernet for PII)     │  │
                     │  └───────────────────────┘  │
                     └─────────────────────────────┘
                                   │
                                   ▼
                     ┌─────────────────────────────┐
                     │        Database              │
                     │  Encrypted at rest          │
                     │  Encrypted fields (PII)     │
                     └─────────────────────────────┘
```

### Security Layers

| Layer | Mechanism |
|-------|-----------|
| Transport | HTTPS (production) |
| Authentication | JWT in httpOnly cookies |
| Authorization | Role-based (student/hr/admin) |
| CSRF | Double-submit cookie pattern |
| Rate Limiting | slowapi per-endpoint |
| Input Validation | Email/username/password validators |
| SQL Injection | Regex pattern detection |
| Password Storage | bcrypt via passlib |
| PII Encryption | Fernet symmetric encryption |
| Account Lockout | 5 failed attempts → 15-min lock |
| Session Management | Fixed + sliding expiry |

---

## Development Workflow

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Code       │────▶│  run_dev.py  │────▶│  Local Dev   │
│  Changes    │     │  Starts both  │     │  Environment  │
└─────────────┘     │  services     │     └──────────────┘
                    └──────────────┘            │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Deploy     │◀────│  CI/CD       │◀────│  Tests /     │
│  (Docker)   │     │  (GH Actions)│     │  Lint / Build│
└─────────────┘     └──────────────┘     └──────────────┘
```

---

## Glossary

| Term | Definition |
|------|------------|
| **Job Drive** | A recruitment campaign for a specific role, created by HR |
| **Interview Session** | A single candidate's interview instance, linked to a drive |
| **LangGraph** | LangChain's graph-based framework for building stateful, multi-actor AI applications |
| **MemorySaver** | LangGraph checkpointer that persists graph state in memory |
| **Phase** | A stage in the interview (greeting, warmup, technical, stress, behavioral, closing) |
| **Skill Matrix** | Aggregate view of candidate skills vs role requirements |
| **Circuit Breaker** | Failure detection pattern that prevents cascading failures to AI providers |
| **Fernet** | Symmetric encryption scheme used for field-level data protection |
| **Hire Recommendation** | AI-generated assessment suggesting hire/no-hire with supporting evidence |
| **SSO** | Single Sign-On via Google, GitHub, or LinkedIn OAuth |

---

## Related Documents

- [Getting Started Guide](./getting-started.md) — Quick start and setup
- [API Reference](./api-reference.md) — Complete endpoint documentation
- [Deployment Guide](../DEPLOYMENT.md) — Production deployment instructions
- [Onboarding Guide](./onboarding.md) — New developer onboarding
- [Runbook](./runbook.md) — Operational procedures and troubleshooting

*Last updated: May 2026*
