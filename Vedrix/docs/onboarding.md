# Autergo Developer Onboarding Guide

**Audience:** New developers joining the Autergo team.
**Goal:** Get productive within your first week.

---

## Week 1 Checklist

- [ ] **Day 1:** Environment setup, repo access, introduction to architecture
- [ ] **Day 2:** Run the full stack locally, complete first API call
- [ ] **Day 3:** Understand the interview engine, complete a test interview
- [ ] **Day 4:** Pick up a small bug fix or feature task
- [ ] **Day 5:** Submit your first PR with a passing CI pipeline

---

## Prerequisites

### Software

| Requirement | Version | Why |
|-------------|---------|-----|
| **Git** | Latest | Version control |
| **Python** | 3.12+ | Backend runtime |
| **Node.js** | 20+ | Frontend runtime |
| **Docker Desktop** | Latest | PostgreSQL, Redis, Judge0 |
| **Visual Studio Code** | Latest | Recommended editor |

### Access

| Resource | How to Get It | Purpose |
|----------|--------------|---------|
| GitHub repo | Ask your team lead | Code access |
| API keys | Copy from `.env.example` or ask team lead | AI service access |
| Docker registry | Optional, for production images | Deployment |
| Staging environment | Ask DevOps team | Testing |

---

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Vedrix
```

### 2. Verify Dependencies

```bash
# Python
python --version      # Should be 3.12+
pip --version

# Node.js
node --version        # Should be 20+
npm --version

# Docker
docker --version
docker-compose --version
```

### 3. Start Database Services

```bash
# Start PostgreSQL + Redis
docker-compose -f Autergo/docker-compose.yml up -d

# Verify they're running
docker ps

# Expected output:
# CONTAINER ID   IMAGE          ...  vedrix-postgres
# CONTAINER ID   IMAGE          ...  vedrix-redis
```

### 4. Configure Backend

```bash
# Navigate to backend directory
cd Vedrix/backend

# Create Python virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env   # If available, or create manually
```

**Required environment variables** in `Vedrix/backend/.env`:

```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite+aiosqlite:///./vedrix.db
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=gsk_your_key_here
OPENROUTER_API_KEY=sk-or-your-key-here
DEEPSEEK_API_KEY=your-key-here
OPENAI_API_KEY=sk-your-key-here
NVIDIA_API_KEY=nvapi-your-key-here
FRONTEND_URL=http://localhost:5173
```

> **Note:** For local development, SQLite is the default. PostgreSQL is only needed when testing production-like behavior. The `DATABASE_URL` in `config.py` auto-fixes to `sqlite+aiosqlite://` if you forget.

### 5. Start the Application

```bash
# From the Autergo root directory
python run_dev.py
```

This script:
1. Checks that all dependencies are available
2. Finds free ports (backend on 8000+, frontend on 5173+)
3. Starts both services concurrently
4. Generates `Vedrix/frontend/.env.development.local` with the correct API URL
5. Prints the URLs to the console

### 6. Verify Everything Works

```bash
# Check backend health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs

# Check frontend
open http://localhost:5173
```

---

## Key Systems and How They Connect

### Project Structure

```
Autergo/
├── backend/                    # FastAPI Python backend
│   ├── main.py                 # App entry point
│   ├── app/
│   │   ├── api/                # API routes and dependencies
│   │   ├── core/               # Config, security, metrics
│   │   ├── db/                 # Database session and migrations
│   │   ├── middleware/         # Audit, performance monitoring
│   │   ├── models/             # SQLModel database models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/
│   │       ├── interview_engine/  # LangGraph interview engine
│   │       ├── voice_service.py   # STT/TTS
│   │       ├── evaluation_service.py
│   │       ├── email_service.py
│   │       ├── cache_service.py
│   │       ├── code_execution_service.py
│   │       └── pdf_service.py
│   └── tests/
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── pages/              # Page components
│   │   ├── components/         # Shared components
│   │   ├── services/           # API client (Axios)
│   │   └── store/              # Zustand auth store
│   └── package.json
├── run_dev.py                  # Development runner
├── docker-compose.yml          # Database services
└── DEPLOYMENT.md               # Production deployment
```

### Data Flow Overview

```
Frontend (React) ──HTTP/WS──▶ Backend (FastAPI) ──▶ Database (SQLite/PG)
                                  │
                                  ├──▶ Redis (Cache)
                                  ├──▶ Groq (Fast LLM)
                                  ├──▶ NVIDIA (Deep LLM)
                                  ├──▶ OpenRouter (Code LLM)
                                  └──▶ Judge0 (Code Execution)
```

### Configuration Flow

```
run_dev.py                    # Generates frontend .env
    │
    ├── backend/.env          # Read by pydantic-settings
    │   └── app/core/config.py # Settings class
    │
    └── frontend/.env.development.local  # Read by Vite
        └── VITE_API_URL      # Used by Axios client
```

---

## Common Developer Tasks

### Task 1: Add a New API Endpoint

1. **Define any new schema** in `backend/app/schemas/`
2. **Add the endpoint** in the appropriate file in `backend/app/api/v1/endpoints/`
3. **Implement business logic** in `backend/app/services/`
4. **Add dependency injection** via `backend/app/api/deps.py`
5. **Register the router** in `backend/app/api/v1/__init__.py`
6. **Test it** via pytest and Swagger UI

**Example** — Adding a simple health endpoint:

```python
# In backend/app/api/v1/endpoints/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"pong": True}
```

### Task 2: Modify a Database Model

1. Edit the model in `backend/app/models/`
2. If using Alembic, generate a migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "describe change"
   alembic upgrade head
   ```
3. If using SQLite (dev), just restart the server — tables are created on startup via `init_db()`

### Task 3: Add a New Frontend Page

1. Create the page component in `frontend/src/pages/`
2. Add the route in `frontend/src/App.jsx`
3. Add the API call in the page (or create a new service file)
4. If the page needs authentication, wrap it in `<ProtectedRoute>`
5. If the page needs a specific role, pass `allowedRoles` prop

### Task 4: Run Tests

```bash
# Backend tests
cd Vedrix/backend
python -m pytest                           # All tests
python -m pytest tests/test_auth.py        # Specific file
python -m pytest -k "interview"            # By keyword
python -m pytest -v --cov                  # With coverage

# Frontend tests
cd Vedrix/frontend
npm test                                    # All tests
npm run lint                                # ESLint check
```

### Task 5: Debug an Interview Session

1. **Check the WebSocket connection** — Open browser DevTools → Network → WS
2. **View the LangGraph state** — Add logging in `nodes.py` at key points
3. **Check the database** — Look at the `interviewsession` table
4. **Monitor AI provider health** — Check `GET /admin/ai-health`
5. **Review logs** — Backend logs show each graph node execution

---

## Who to Ask for What

| Topic | Contact | Resources |
|-------|---------|-----------|
| **Architecture questions** | Senior backend dev | `docs/architecture.md` |
| **Interview engine internals** | AI team lead | `backend/app/services/interview_engine/ARCHITECTURE.md` |
| **Frontend components** | Frontend lead | `frontend/src/components/` |
| **Database schema** | Backend lead | `backend/app/models/` |
| **Deployment/DevOps** | DevOps engineer | `DEPLOYMENT.md` |
| **AI provider config** | Platform team | `backend/app/core/config.py` |
| **OAuth/SSO issues** | Backend lead | `backend/app/api/v1/endpoints/oauth.py` |
| **Security concerns** | Security lead | `backend/app/core/security.py` |
| **Bug reports** | Team (GitHub Issues) | Create a new issue |

---

## Code Style & Standards

### Backend

- **Python 3.12+** — Use modern features (type hints, async/await)
- **Async-first** — All I/O operations must be async
- **Type hints** — Required for all function signatures
- **Docstrings** — Required for all public functions and classes
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Testing**: pytest with async support

### Frontend

- **JavaScript (JSX)** — All source files are `.jsx`
- **Zustand** — For global state (auth only); use local state for everything else
- **Axios** — For API calls (with CSRF interceptor)
- **Tailwind CSS v4** — For styling (use `@apply` sparingly, prefer utility classes)
- **Components** — One component per file, named exports
- **React 19** — Use hooks, avoid class components

### Git

```bash
# Branch naming conventions
feature/description     # New features
fix/description         # Bug fixes
refactor/description    # Code refactoring
docs/description        # Documentation changes

# Commit message format
type(scope): description

# Examples
feat(interview): add video recording support
fix(auth): handle token refresh race condition
docs(api): update rate limit documentation
```

### PR Checklist

- [ ] Code compiles and passes lint
- [ ] Tests pass (new tests for new functionality)
- [ ] No hardcoded secrets or API keys
- [ ] Updated relevant documentation
- [ ] Added appropriate error handling
- [ ] Considered edge cases and failure modes
- [ ] Self-reviewed the diff before requesting review

---

## Development Tips

### Hot Reload

Both backend and frontend have hot reload enabled in development:
- **Backend:** Uvicorn with `--reload` detects Python file changes
- **Frontend:** Vite HMR updates the browser instantly

### Database

- SQLite DB file: `Vedrix/backend/vedrix.db` (check .gitignore — it should be excluded)
- For clean slate: Delete the file and restart the backend
- For PostgreSQL: Use `docker-compose -f Autergo/docker-compose.yml up`

### AI Provider Keys

If you don't have production API keys:
- **Groq:** Free tier available at https://console.groq.com
- **OpenRouter:** Free tier for evaluation
- The system degrades gracefully — falls back to static questions if all providers fail

### Common Pitfalls

1. **Frontend won't connect to API** — Ensure `.env.development.local` exists with correct `VITE_API_URL`. Always use `run_dev.py` or create this file manually.
2. **SQLite file not found** — The `init_db()` function creates it on startup. Check write permissions in `backend/` directory.
3. **Docker containers not starting** — Ensure Docker Desktop is running and ports 5432/6379 are not in use.
4. **WebSocket disconnects** — Check for reverse proxy timeout settings in development.

---

## Useful Commands Reference

```bash
# Development
python run_dev.py                                       # Start full stack
cd backend && python -m uvicorn main:app --reload       # Start backend only
cd frontend && npm run dev                              # Start frontend only

# Testing
cd backend && python -m pytest                          # Backend tests
cd frontend && npm test                                  # Frontend tests
cd frontend && npm run lint                              # ESLint

# Database
docker-compose -f Autergo/docker-compose.yml up -d       # Start PG + Redis
docker-compose -f Autergo/docker-compose.yml down        # Stop services

# Building
cd frontend && npm run build                             # Production build
cd backend && docker build -t vedrix/backend:latest .   # Docker build

# Git
git log --oneline -10                                    # Recent commits
git status                                                # Current changes
git diff                                                  # Unstaged changes
```

---

## Resources

### Documentation Index

| Document | Location | Purpose |
|----------|----------|---------|
| Architecture Guide | `docs/architecture.md` | System design overview |
| API Reference | `docs/api-reference.md` | Complete endpoint docs |
| Getting Started | `docs/getting-started.md` | Quick setup guide |
| Deployment Guide | `DEPLOYMENT.md` | Production deployment |
| Runbook | `docs/runbook.md` | Operational procedures |
| Interview Engine Docs | `backend/app/services/interview_engine/ARCHITECTURE.md` | LangGraph flow |

### Code References

| File | What to Learn |
|------|---------------|
| `backend/main.py` | App initialization and middleware setup |
| `backend/app/api/deps.py` | Authentication and authorization dependencies |
| `backend/app/services/interview_engine/graph.py` | LangGraph state machine |
| `backend/app/services/interview_engine/nodes.py` | Graph node implementations |
| `backend/app/core/config.py` | All environment variables and settings |
| `frontend/src/store/useAuthStore.js` | Authentication state management |
| `frontend/src/services/api.js` | API client configuration |

---

*Last updated: May 2026*
