# 📋 Software Requirements Specification (SWRTS)

**Project:** Autergo AI Interview System
**Version:** 1.0.0  
**Status:** Approved / Implemented

## 1. Introduction
Autergo is an agentic AI platform designed to automate and enhance the interview process. It provides a realistic, multi-phase interview experience for candidates and a data-driven recruitment tool for HR professionals.

## 2. System Overview
The system consists of three main interfaces:
- **Candidate Portal:** For taking interviews, practice sessions, and viewing reports.
- **HR Dashboard:** For managing job drives, candidate pipelines, and analytics.
- **Admin Command Center:** For platform monitoring, user management, and audit logs.

## 3. Functional Requirements

### 3.1 Interview Engine (Core)
- **FR-1.1:** The system shall conduct interviews using a multi-agent LangGraph orchestration.
- **FR-1.2:** The system shall support adaptive questioning based on candidate responses.
- **FR-1.3:** The system shall support both text-based and voice-based (STT/TTS) communication.
- **FR-1.4:** The system shall provide real-time evaluation of technical skills, communication, and depth of knowledge.
- **FR-1.5:** The system shall include an "AI Advisor" that suggests when an interview is ready to close based on confidence metrics.

### 3.2 Candidate Management
- **FR-2.1:** Candidates shall be able to register, login, and manage their professional profiles.
- **FR-2.2:** Candidates shall be able to upload resumes (PDF) for AI-driven skill extraction.
- **FR-2.3:** Candidates shall be able to join interviews via "Magic Links" without mandatory registration.
- **FR-2.4:** Candidates shall receive a detailed performance report with radar charts after completion.

### 3.3 Recruiter (HR) Tools
- **FR-3.1:** HR shall be able to create "Job Drives" with specific roles and required skills.
- **FR-3.2:** HR shall be able to monitor live interviews in real-time via WebSockets.
- **FR-3.3:** HR shall be able to bulk-invite candidates via CSV import.
- **FR-3.4:** HR shall be able to manually close interviews or override AI suggestions.

### 3.4 Administrative Governance
- **FR-4.1:** Admins shall have a global view of all system activities and metrics.
- **FR-4.2:** Admins shall be able to view detailed audit logs for all state-changing actions.
- **FR-4.3:** The system shall support soft-deletion of all major entities for data recovery.

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-1.1 (Latency):** Voice transcription (STT) shall complete in under 500ms.
- **NFR-1.2 (Concurrency):** The system shall support at least 100 concurrent interview sessions.

### 4.2 Security
- **NFR-2.1 (Auth):** The system shall use JWT with httpOnly cookies for session management.
- **NFR-2.2 (CSRF):** All state-changing requests shall be protected by CSRF tokens.
- **NFR-2.3 (Privacy):** Sensitive data (responses, transcripts) shall be encrypted at rest.

### 4.3 Availability
- **NFR-3.1:** The system shall target 99.9% uptime.
- **NFR-3.2:** The system shall implement circuit breakers for all external AI API calls.

## 5. Compliance
- **Requirement:** The system shall be WCAG 2.1 AA compliant for accessibility.
- **Requirement:** The system shall support GDPR "Right to be Forgotten" via account deletion with a 30-day grace period.
