from typing import List, Dict, Optional, TypedDict, Annotated, Literal, Any
import operator

class InterviewState(TypedDict):
    # Chat history
    messages: Annotated[List[Dict[str, str]], operator.add]

    # Context
    resume_text: str
    job_role: str
    candidate_first_name: Optional[str]

    # Interview Tracking
    current_question_index: int
    max_questions: int
    interview_complete: bool
    completion_reason: Optional[str]  # Why interview ended

    # Phase Management - Natural Flow
    # Phases: "greeting" -> "welcome" -> "warmup" -> "technical" -> "stress" -> "behavioral" -> "closing"
    current_phase: Literal["greeting", "welcome", "warmup", "technical", "stress", "behavioral", "closing"]
    phase_transition: bool  # Flag when transitioning to new phase
    previous_phase: Optional[str]

    # Performance & Memory
    difficulty: Literal["easy", "medium", "hard"]

    # Granular Scoring (0-10 scale)
    latest_score: float
    metrics: Dict[str, float]  # accuracy, clarity, depth, communication
    avg_score: float  # Running average

    # Skill Coverage Tracking - Ensure all skills are covered
    covered_skills: List[str]  # Skills covered in interview
    skills_to_cover: List[str]  # Required skills from job role
    pending_skills: List[str]  # Skills not yet covered
    skill_coverage_percentage: float

    topic_scores: Dict[str, float]
    topic_strengths: Dict[str, str]  # "weak", "strong", "improving"

    # Response Quality Tracking
    total_responses: int
    low_quality_count: int  # Count of low effort answers
    high_quality_count: int  # Count of good answers

    # HR Intervention & Mode
    interviewer_mode: Literal["ai", "human", "suggestion"]
    hr_instructions: Optional[str]

    # Latest evaluation
    last_evaluation: Optional[Dict]

    # Per-answer typed evaluations used by the NOOA report/coaching agents
    evaluation_history: List[Dict[str, Any]]

    # ── Multi-agent Coordination Protocol ───────────────────────────────────
    # Stable identity for the candidate response currently being processed.
    turn_id: Optional[str]
    coordination_round_id: Optional[str]
    # Reducer-backed append-only trace; parallel agents must never overwrite it.
    coordination_trace: Annotated[List[Dict[str, Any]], operator.add]

    # Latest candidate payload for coordinated interviewer/evaluator handoff.
    last_candidate_answer: Optional[str]

    # Next question to be asked
    next_question: Optional[Dict]

    # Technical Coding Sandbox
    code_snippet: Optional[str]
    code_language: Optional[str]
    is_coding_mode: Optional[bool]

    # Natural follow-up tracking
    follow_up_requested: bool  # When candidate asks for clarification
    previous_topic: Optional[str]  # Track for natural continuation

    # ── AI Advisor Tracking (Phase 1A) ─────────────────────────────────────
    # Advisor monitors interview and suggests to HR when ready to close.
    # HR always retains control — AI never forces termination.
    advisor_ready_to_close: bool  # AI suggests ready to close
    advisor_confidence: Optional[float]  # Confidence in suggestion
    advisor_reason: Optional[str]  # Human-readable reason
    advisor_reason_category: Optional[str]  # Categorized reason
    advisor_notified: bool  # Has interviewer been notified?
    advisor_action_taken: bool  # Has interviewer acted on suggestion?

    # ── AI Supervisor (Phase 1B) ────────────────────────────────────────────
    # The AI Supervisor monitors duration, difficulty, and controls interview flow.
    # Three control modes determine its authority level.
    supervisor_session_id: str  # internal session reference for supervisor registry
    supervisor_mode: Literal["monitor", "suggest", "auto"]  # control authority
    supervisor_observations: List[Dict]  # chronological observation log
    supervisor_last_action: Optional[Dict]  # most recent action taken/suggested
    supervisor_paused: bool  # supervisor paused by admin
    session_start_epoch: float  # unix timestamp of session start
    question_start_epoch: Optional[float]  # unix timestamp of current question
    per_question_times: List[float]  # duration per question in seconds
    score_history: List[float]  # full score history for trend analysis
    difficulty_history: List[str]  # full difficulty change history

    # ── Next-Gen Agentic Fields ───────────────────────────────────────────
    copilot_suggestions: List[Dict[str, Any]]  # code co-pilot recommendations
    copilot_request_pending: bool  # did the candidate ask for help?
    hr_whisper_instructions: Optional[str]  # recruiter live whispers
    empathy_metrics: Dict[str, Any]  # stress_level, hesitation_rating, typing_speed
    stress_history: List[float]  # stress_level values per response for alert tracking
    empathy_timeline: List[Dict[str, Any]]  # time-series of empathy_metrics snapshots
    rag_context: Optional[str]  # context fetched from ChromaDB resume/GitHub
    debate_rounds: Optional[Dict[str, Any]]  # critiques of skeptic, pragmatist, bias auditor
    skeptic_critique: Optional[str]
    pragmatist_critique: Optional[str]
    bias_auditor_critique: Optional[str]
    interview_plan: Optional[Dict[str, Any]]
    plan_phase_index: int
    consecutive_low_quality: int

    # ── QA Agent Fields ───────────────────────────────────────────────────
    qa_regeneration_count: int  # How many times current question was regenerated
    qa_session_quality_score: float  # Ratio of approved to total questions
    qa_flags: List[Dict[str, Any]]  # All flags for this session
    qa_total_questions: int  # Total generated questions evaluated by QA
    qa_flagged_questions: int  # Generated questions flagged by QA
    qa_paused: bool  # Whether question generation is paused for QA review


