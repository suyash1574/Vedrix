# 🤖 Autergo: System Prompt & Blueprint

**Project Name:** Autergo
**Core Tech:** FastAPI, React, PostgreSQL, OpenRouter.

## 🏗️ Architectural Mandates
1.  **Asynchronous First:** All backend I/O (Database, AI API calls) must be `async`.
2.  **Type Safety:** Use Pydantic for request/response validation and SQLAlchemy for ORM.
3.  **Clean Separation:** Keep business logic in `services/`, API routes in `api/`, and data models in `models/`.
4.  **Real-time Interaction:** Use optimized adaptive loops for interviews (Groq for low-latency follow-ups).

## 📁 Backend Structure
- `app/api/`: Versioned API endpoints.
- `app/core/`: Settings (Pydantic-settings) and Security (JWT).
- `app/models/`: SQLAlchemy models.
- `app/schemas/`: Pydantic schemas.
- `app/services/`: AI logic and business workflows.
- `app/db/`: Session management and migrations.

## 📁 Frontend Structure
- `src/components/`: Atomic UI components.
- `src/pages/`: Main views.
- `src/hooks/`: Custom React hooks (MediaRecorder, Auth).
- `src/services/`: API client.

## 🧠 AI Strategy
- **Low Latency (Interview Loop):** Groq (LPU).
- **Deep Analysis (Feedback):** DeepSeek Chat.
- **Technical/Code:** NVIDIA Nemotron or GPT-4 class models via OpenRouter.
