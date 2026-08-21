# 🔄 System Workflows & Logic

**Project:** Autergo AI Interview System
**Version:** 1.0.0

## 1. Interview Engine Workflow
The interview logic is managed by a stateful graph (LangGraph). The workflow is non-linear and adapts to candidate performance.

```mermaid
graph TD
    Entry((Start)) --> QGen[Generate Question]
    QGen --> Route{Mode Check}
    Route -->|Text| EvalA[Evaluate Answer]
    Route -->|Coding| EvalC[Evaluate Code]
    EvalA --> Mem[Update Memory]
    EvalC --> Mem
    Mem --> Adv[Advisor Monitor]
    Adv -->|Continue| QGen
    Adv -->|Saturated| End((Completion))
```

### 1.1 Decision Logic (generate_question)
The engine decides the next question using the following priority:
1. **HR Override:** If the recruiter has sent an instruction, follow it immediately.
2. **Phase Completion:** Ensure warmup is done before technical questions.
3. **Skill Gaps:** Prioritize skills listed in the Job Drive that haven't been evidenced yet.
4. **Adaptive Difficulty:** If the previous score was > 8, increase difficulty; if < 4, decrease it.

## 2. Magic Link Authentication Workflow
Candidates can join interviews without an account using secure, one-time tokens.

```mermaid
sequenceDiagram
    participant HR as Recruiter
    participant API as Autergo API
    participant Email as SMTP Server
    participant C as Candidate

    HR->>API: Create Job Drive & Invite Candidate
    API->>API: Generate UUID Token
    API->>Email: Send Invite with /interview/ws?token=XYZ
    Email-->>C: Delivers Email
    C->>API: Click Link (Token Handshake)
    API->>API: Validate Token & Drive ID
    API->>API: Create/Identify Shadow User
    API-->>C: Established WebSocket Session
```

## 3. Account Deletion Workflow (GDPR)
Ensures compliance while preventing accidental data loss.

```mermaid
graph LR
    User[User] --> Request[Request Deletion]
    Request --> Flag[Mark as 'deletion_pending']
    Flag --> Grace[30-Day Grace Period]
    Grace -->|Cancel| Active[Restored to Active]
    Grace -->|Timeout| Permanent[Permanent Scrub]
    Permanent --> Clean[Data Anonymized/Deleted]
```

## 4. Voice Intelligence Pipeline
Standardizes browser-specific audio for consistent AI transcription.

1. **Capture:** Frontend records raw audio (typically `audio/webm` or `audio/ogg`).
2. **Buffer:** Raw bytes sent over WebSocket.
3. **Normalize:** `VoiceService` uses `pydub` to convert to `MP3 (64k)`.
4. **Transcribe:** `Groq Whisper V3` converts audio to text.
5. **Enrich:** Transcribed text is injected into the LangGraph state for evaluation.
