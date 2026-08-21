# Vedrix Interview Timing and Precision Improvements

## Scope

The live interview critical path now prioritizes fast, deterministic user feedback while keeping AI output structured, evidence-based, and observable. The changes apply to NOOA production routing, the ReAct fallback route, LangGraph execution, RAG retrieval, TTS, sentiment persistence, and recruiter observability.

## Timing contract

| Stage | Default budget | Behavior when exceeded |
|---|---:|---|
| Response validation | 50 ms | Deterministic validation rejects malformed or stale payloads immediately. |
| RAG context | 0.8 s | The turn continues with the seed context or no retrieved context. |
| Question generation | 10 s | NOOA falls back to the deterministic question planner. |
| Answer evaluation | 12 s | NOOA falls back to validated deterministic scoring. |
| Code execution | 15 s | Existing Judge0 execution result or error is passed to the evaluator. |
| TTS attachment | 3 s | Text question remains delivered; audio is omitted if it is late or unavailable. |
| Complete candidate turn | 20 s | The graph stream is cancelled and the existing error/fallback path reports the degraded turn. |

The budgets are configurable through `INTERVIEW_TURN_TIMEOUT_SECONDS`, `INTERVIEW_QUESTION_TIMEOUT_SECONDS`, `INTERVIEW_EVALUATION_TIMEOUT_SECONDS`, `INTERVIEW_TTS_TIMEOUT_SECONDS`, `INTERVIEW_RAG_TIMEOUT_SECONDS`, `INTERVIEW_MAX_CONTEXT_MESSAGES`, and `INTERVIEW_MAX_CONTEXT_CHARS`.

## Critical-path improvements

The WebSocket now sends each question as text immediately. TTS runs as an asynchronous optional task and is delivered as a separate `question_audio` event associated with the question ID. Slow audio cannot delay the candidate’s next response.

The response path uses one graph state snapshot instead of repeatedly reading the checkpointer for typing timing, RAG context, turn identity, and code language. RAG retrieval is bounded by a short timeout and is treated as enrichment rather than a prerequisite for evaluation. Sentiment snapshots are persisted asynchronously after the state update instead of forcing a database commit on every response before the next question can proceed.

A bounded graph-stream collector applies a hard per-turn timeout. The runtime emits a `turn_timing` event containing stage durations and total duration, while recruiter state synchronization includes `turn_timing`, `precision_flags`, and `response_degraded`.

NOOA question and evaluation requests now use separate operation budgets and cache typed agent instances per process. Model-router routes use shorter request timeouts and bounded output tokens for question and answer-critical tasks. The ReAct fallback has `VEDRIX_REACT_FAST_PATH=true` by default, selecting the single structured deterministic node instead of the slower tool-planning plus second-model-call route. Set it to `false` only when multi-step ReAct reasoning is explicitly preferred over response speed.

## Precision safeguards

NOOA context is capped to recent questions and answers. This reduces stale-context interference and keeps the model focused on the current question. Structured NOOA outputs remain validated by typed Pydantic contracts and continue to use deterministic fallbacks when a provider times out or emits malformed content.

Evaluation metrics now include relevance in the clarity dimension rather than counting communication twice. The live state records low-confidence evaluations and evaluations without evidence in `precision_flags`. These flags are visible to recruiter clients and should be used to trigger human review rather than silent score inflation.

Thinking pauses and clarification requests remain non-scoring control turns. Duplicate and stale submissions continue to be rejected before the graph is invoked, preserving precise one-response-per-question semantics.

## Client events

| Event | Meaning |
|---|---|
| `question` | The question text and structured question metadata are ready immediately. |
| `question_audio` | Optional TTS for the same question arrived after text delivery. |
| `turn_timing` | Timing breakdown and precision flags for the processed turn. |
| `state_sync` | Recruiter state including empathy, coordination, timing, and precision metadata. |
| `response_ack` / `response_rejected` | Candidate submission lifecycle result. |

## Validation evidence

The timing and precision changes pass the focused timing/NOOA/WebSocket suite and the complete backend regression suite. The final backend run reports **461 passed tests** with no test failures. Production file validation and Python compilation also pass.
