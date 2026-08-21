# 🗄️ Database Design & Entity Relationship

**Project:** Autergo AI Interview System
**Version:** 1.0.0

## 1. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USER ||--o| STUDENT_PROFILE : "has"
    USER ||--o| HR_PROFILE : "has"
    USER ||--o{ INTERVIEW_SESSION : "takes"
    HR_PROFILE ||--o{ JOB_DRIVE : "creates"
    JOB_DRIVE ||--o{ DRIVE_INVITE_TOKEN : "generates"
    JOB_DRIVE ||--o{ INTERVIEW_SESSION : "contains"
    USER ||--o{ AUDIT_LOG : "triggers"

    USER {
        int id PK
        string email
        string username
        string password_hash
        string user_type "student|hr|admin"
        datetime created_at
    }

    STUDENT_PROFILE {
        int id PK
        int user_id FK
        string university
        string degree
        string skills "Encrypted"
        string resume_text "Encrypted"
    }

    HR_PROFILE {
        int id PK
        int user_id FK
        string company_name
        string position
        string hr_code
    }

    JOB_DRIVE {
        int id PK
        int hr_id FK
        string title
        string job_role
        string skills_required
        boolean is_active
    }

    INTERVIEW_SESSION {
        int id PK
        int candidate_id FK
        int job_drive_id FK
        string status "scheduled|completed"
        float overall_score
        json responses "Encrypted"
        json ai_feedback "Encrypted"
        json skill_matrix "Encrypted"
    }

    DRIVE_INVITE_TOKEN {
        int id PK
        int drive_id FK
        string token "Unique UUID"
        string candidate_email
        boolean is_used
        datetime expires_at
    }
```

## 2. Security & Encryption Policy
Autergo implements a tiered data protection strategy:

- **PII Protection:** Student names, emails, and phone numbers are stored in plain text for fast lookup but are guarded by strict RBAC.
- **Sensitive Content:** `responses`, `resume_text`, and `ai_feedback` are stored as `EncryptedString` or `EncryptedJSON` using AES-128 (Fernet).
- **Password Safety:** Hashed using `bcrypt` with a minimum work factor of 12.

## 3. Indexing Strategy
To ensure performance under load (100+ concurrent sessions), the following indexes are maintained:

| Table | Index Columns | Purpose |
|-------|---------------|---------|
| `user` | `email`, `username` | Fast login/lookup. |
| `interview_session` | `candidate_id`, `job_drive_id`, `status` | Dashboard filtering. |
| `drive_invite_token` | `token`, `drive_id` | Fast magic link validation. |
| `audit_log` | `user_id`, `created_at` | Rapid forensic analysis. |

## 4. Scalability Note
While the system supports **SQLite** for zero-config local development, it is architected for **PostgreSQL**. All relationships use standard foreign key constraints, and the schema is optimized for asynchronous concurrent access via `asyncpg`.
