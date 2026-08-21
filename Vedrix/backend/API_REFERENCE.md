# 📖 Autergo API Reference

This document provides a high-level overview of the Autergo API endpoints. The API follows RESTful principles (where applicable) and uses `/api/v1` as the base prefix.

## 🔐 Authentication & Users

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | `POST` | Exchange credentials for session cookies. |
| `/auth/refresh` | `POST` | Refresh session cookies using a refresh token. |
| `/auth/register` | `POST` | Create a new user account. |
| `/users/me` | `GET` | Get current authenticated user profile. |

*Autergo uses HTTP-only cookies and CSRF tokens for secure session management.*

## 🎙️ Interview Engine

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/interview/sessions` | `POST` | Start a new interview session. |
| `/interview/ws/{session_id}`| `WS` | Real-time interview communication (LangGraph). |
| `/interview/{session_id}` | `GET` | Retrieve session status and history. |

## 💼 Recruiter (HR) Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hr/drives` | `GET/POST` | Manage interview drives for specific roles. |
| `/hr/candidates` | `GET` | List candidates and their interview scores. |
| `/hr/reports/{id}` | `GET` | Get detailed AI evaluation reports. |

## 🛡️ Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/stats` | `GET` | Global platform performance and usage metrics. |
| `/admin/users` | `GET` | User management and moderation. |

## 🛠️ Developer Tools

- **Swagger UI**: Available at `/docs` when running in development mode.
- **ReDoc**: Available at `/redoc`.
- **Prometheus Metrics**: Available at `/metrics`.
- **Health Checks**:
  - `/health`: Basic service status.
  - `/health/ready`: Detailed check including database connectivity.

## ⚠️ Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| `401` | Unauthorized | Missing or invalid authentication. |
| `403` | Forbidden | Insufficient permissions or CSRF failure. |
| `429` | Too Many Requests | Rate limit exceeded (SlowAPI). |
| `503` | Service Unavailable | Backend or database is down. |
