# 🏗️ Software Architecture Document (SWADS)

**Project:** Autergo AI Interview System
**Version:** 1.0.0

## 1. System Context Diagram
The following diagram illustrates how Autergo interacts with external entities and users.

```mermaid
graph TD
    User((Candidate)) <--> Web[React Frontend]
    HR((Recruiter)) <--> Web
    Admin((System Admin)) <--> Web
    Web <--> API[FastAPI Backend]
    API <--> DB[(PostgreSQL)]
    API <--> AI[AI Service Providers: Groq, NVIDIA, OpenAI]
    API <--> Cache[Redis Cache]
```

## 2. Layered Architecture
Autergo follows a clean, decoupled architecture:

### 2.1 Presentation Layer (Frontend)
- **Framework:** React 19 (Vite) + TypeScript.
- **State Management:** Zustand (Global) + React Query (Server Sync).
- **Communication:** Axios (REST) + WebSockets (Live Interview).

### 2.2 Application Layer (Backend API)
- **Framework:** FastAPI (Asynchronous).
- **Security:** JWT Auth (HTTP-only cookies) + CSRF Protection.
- **Task Routing:** Specialized Model Router for cost/performance optimization.

### 2.3 Logic Layer (Services)
- **Orchestration:** LangGraph (Stateful multi-agent workflows).
- **AI Services:** 
    - **STT:** Groq (Whisper Large V3).
    - **TTS:** OpenAI (TTS-1).
    - **Reasoning:** NVIDIA (Llama 3.1 70B).
    - **Evaluation:** Groq (Llama 3.3 70B).

### 2.4 Data Persistence Layer
- **ORM:** SQLModel (SQLAlchemy).
- **Primary DB:** PostgreSQL (Production) / SQLite (Development).
- **Migrations:** Alembic.

## 3. High-Level Logic Flow (SOCME)
This sequence diagram shows the interaction during a typical interview turn.

```mermaid
sequenceDiagram
    participant C as Candidate (Browser)
    participant WS as WebSocket Handler
    participant G as LangGraph Engine
    participant LLM as AI Models (Groq/OpenRouter)
    participant DB as Database

    C->>WS: Sends Audio / Text Answer
    WS->>WS: STT (if audio)
    WS->>G: Invoke Graph with Answer
    G->>LLM: evaluate_answer_node
    LLM-->>G: Returns Scores & Feedback
    G->>LLM: generate_question_node
    LLM-->>G: Returns Next Question
    G->>DB: update_memory_node (Persist State)
    G-->>WS: Final Turn State
    WS->>WS: TTS (Generate Audio)
    WS-->>C: Sends Question + Audio + Metrics
```

## 4. Deployment Architecture
The system is containerized and ready for cloud orchestration.

```mermaid
graph LR
    subgraph Cloud
        NG[Nginx Ingress] --> FE[Frontend Container]
        NG --> BE[Backend Container]
        BE --> PG[(Managed PostgreSQL)]
        BE --> RD[(Managed Redis)]
    end
    Internet((Internet)) --> NG
```

## 5. Security Architecture
- **Stateless Authentication:** JWT issued via cookies with `httponly`, `secure`, and `samesite` flags.
- **Encryption:** Transcripts and PII are encrypted at rest using Fernet (AES-128).
- **Rate Limiting:** Implemented via `SlowAPI` on sensitive endpoints (Auth, AI).
