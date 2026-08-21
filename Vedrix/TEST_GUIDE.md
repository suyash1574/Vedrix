# Autergo E2E Test Suite

## Backend Tests (pytest)

### Run all backend tests
```bash
cd Vedrix/backend
python -m pytest tests/ -v
```

### Run specific test files
```bash
python -m pytest tests/test_interview_engine.py -v        # Interview engine node logic
python -m pytest tests/test_interview_websocket.py -v      # WebSocket handling
python -m pytest tests/test_report_authenticity.py -v     # Report & email tests
python -m pytest tests/test_auth.py -v                    # Auth endpoints
python -m pytest tests/test_interview.py -v                # Interview API endpoints
```

### What the tests cover

| File | Coverage |
|------|----------|
| `test_interview_engine.py` | Question generation, adaptive difficulty, skill tracking, low-effort detection, phase transitions, code evaluation, skill initialization |
| `test_interview_websocket.py` | WebSocket lifecycle, JWT validation, message parsing, session disconnect, WebRTC signaling, video room management |
| `test_report_authenticity.py` | Report schema, score consistency, email templates, email delivery, code execution free-mode, session persistence |
| `test_auth.py` | Login, registration, token validation |
| `test_interview.py` | Student stats, session history, report retrieval |

### Test fixtures (conftest.py)
- `event_loop` — async event loop for pytest-asyncio
- `mock_groq_stt` — mock Groq Whisper transcription
- `mock_groq_llm` — mock LLM for question generation
- `mock_strong_llm` — mock LLM for evaluation
- `sample_interview_state` — initial state for interview engine
- `sample_answer_state` — state after candidate answers
- `sample_report` — sample evaluation report

---

## Frontend Tests (Vitest)

### Run all frontend tests
```bash
cd Vedrix/frontend
npm test
```

### Run specific test file
```bash
npm test -- InterviewRoom.test.jsx
```

### What the tests cover

| File | Coverage |
|------|----------|
| `InterviewRoom.test.jsx` | ReadyCheckWizard, WebSocket message handling, recording flow, browser TTS, coding mode, timer logic, auto-submit timeout |

---

## Edge Cases Covered

### Interview Flow
- ✅ Full interview runs to completion (max questions or all skills covered)
- ✅ Interview ends early (too many low-quality responses, max reached)
- ✅ Minimum 6 questions enforced — never ends too early
- ✅ Disconnect mid-interview — partial transcript saved
- ✅ Empty/very short answers detected as low-effort
- ✅ Null last_evaluation at interview start
- ✅ Empty pending_skills list handled
- ✅ Multi-word skill identification

### Report Authenticity
- ✅ Overall score consistent with individual metrics (within 2 points)
- ✅ Strengths and weaknesses are different lists
- ✅ Hire recommendation matches score thresholds
- ✅ Summary is substantive (≥30 chars)
- ✅ Report + transcript stored separately (transcript not modified by AI)
- ✅ Fallback report (score 5.0) if LLM fails

### WebSocket
- ✅ Valid JWT token returns user ID
- ✅ Invalid/expired tokens return None
- ✅ Invalid JSON handled gracefully
- ✅ Binary audio triggers STT
- ✅ Session finalized on disconnect
- ✅ WebRTC broadcast excludes sender

### Voice & TTS
- ✅ Browser Web Speech API used when backend TTS returns empty
- ✅ MediaRecorder captures audio chunks
- ✅ Auto-submit after 1.5s silence
- ✅ Auto-submit on question timer expiry

### Code Execution
- ✅ Free mode (no API key) uses public Judge0 instance
- ✅ All common languages have language IDs
- ✅ Unknown language defaults to Python
- ✅ Error response has consistent format