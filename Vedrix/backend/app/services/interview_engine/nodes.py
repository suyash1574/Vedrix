import asyncio
import logging
import re
import random
from typing import Dict, Any, List
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from .state import InterviewState
from .providers import get_fast_llm, get_strong_llm, get_adaptive_llm, get_code_llm
from app.services.memory_service import memory_service

logger = logging.getLogger(__name__)


# ── SKILL DEFINITIONS ──────────────────────────────────────────────────────────

TECHNICAL_SKILLS = {
    "programming": ["coding", "programming", "code", "developer", "software"],
    "database": ["database", "sql", "mysql", "postgres", "mongodb", "data"],
    "frontend": ["react", "vue", "angular", "javascript", "html", "css", "frontend"],
    "backend": ["node", "python", "java", "django", "fastapi", "backend", "api"],
    "devops": ["docker", "kubernetes", "aws", "cloud", "ci/cd", "devops", "deployment"],
    "system_design": ["architecture", "system", "design", "scalability", "microservices"],
    "testing": ["test", "testing", "unit", "jest", "pytest", "quality"],
    "security": ["security", "auth", "oauth", "jwt", "encryption"],
}

SOFT_SKILLS = [
    "leadership", "teamwork", "communication", "problem_solving",
    "time_management", "adaptability", "conflict_resolution",
    "critical_thinking", "creativity", "decision_making"
]

BEHAVIORAL_AREAS = [
    "leadership", "teamwork", "conflict", "failure", "success",
    "challenge", "goal", "learning", "communication", "motivation"
]

# Phrases candidates use when they need a moment to think — never penalize these.
THINKING_INDICATORS = [
    "hmm",
    "let me think",
    "give me a moment",
    "thinking",
    "one second",
    "hold on",
    "let me think about that",
    "give me a second",
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class QuestionSchema(BaseModel):
    id: int = Field(description="Sequence number of the question")
    question: str = Field(description="The actual interview question text")
    category: str = Field(description="Category: technical, behavioral, resume-based, situational")
    difficulty: str = Field(description="The difficulty level targeted")
    time_limit: int = Field(description="Time limit for this question in seconds")
    skill_tested: str = Field(description="Primary skill being tested")
    follow_up_topic: str = Field(description="Topic for potential follow-up question")


class EvaluationSchema(BaseModel):
    score: float = Field(description="Overall score between 0.0 and 10.0")
    metrics: Dict[str, float] = Field(description="Scores for accuracy, clarity, depth, communication (0-10)")
    feedback: str = Field(description="Constructive feedback for the candidate")
    topic: str = Field(description="The specific skill or topic being evaluated")
    skill_category: str = Field(description="Category: technical, soft_skill, behavioral")
    should_deep_dive: bool = Field(description="Whether to ask a follow-up on this same topic")
    is_coding_challenge: bool = Field(default=False, description="Whether to trigger a coding sandbox")
    needs_easier: bool = Field(default=False, description="Whether the candidate needs an easier question")
    low_effort: bool = Field(default=False, description="Whether the answer is low effort")
    skill_identified: str = Field(description="The specific skill detected in the answer")


class CompletionSchema(BaseModel):
    should_complete: bool = Field(description="Whether interview should end")
    reason: str = Field(description="Reason for completion decision")
    skills_covered_count: int = Field(description="Number of unique skills covered")
    coverage_percentage: float = Field(description="Percentage of skills covered")
    average_score: float = Field(description="Average score across all questions")
    overall_quality: str = Field(description="Good, Average, or Poor")


# ── Helper Functions ───────────────────────────────────────────────────────────

# ── Human-like Response Templates ───────────────────────────────────────
CONVERSATIONAL_ACKNOWLEDGMENTS = [
    "Great, thanks for sharing that. ",
    "I appreciate you telling me about that. ",
    "That's helpful context. ",
    "Understood, let's build on that. ",
    "Got it, moving on. ",
    "Thanks for that perspective. ",
    "Good to know. ",
    "That's interesting — ",
    "Makes sense. ",
    "Interesting! Let me follow up on that. ",
]

PHASE_TRANSITIONS = {
    ("greeting", "welcome"): "Wonderful! It's great to have you here today. ",
    ("welcome", "warmup"): "I enjoy hearing about your journey. ",
    ("warmup", "technical"): "Now let's dig a bit deeper into your technical background. ",
    ("technical", "stress"): "Alright, let me challenge you a little. ",
    ("stress", "behavioral"): "That was a good exercise. Now let's talk about how you work with others. ",
    ("behavioral", "closing"): "We're almost done. I appreciate your patience. ",
}

GREETING_MESSAGES = [
    "Hey! I'm really glad you could make it today.",
    "Hi there! Welcome — thank you for joining.",
    "Hello! I'm excited to speak with you today.",
    "Good to see you! I appreciate you taking the time.",
]


def _get_conversational_ack(score: float, topic: str, should_deep_dive: bool = False) -> str:
    """Build a natural acknowledgment based on the previous answer quality."""
    if should_deep_dive:
        ack_options = [
            "That's a really strong answer. ",
            "Excellent response — you've clearly thought this through. ",
            "Impressive. You really know your stuff here. ",
            "Love that depth. You nailed it. ",
            "That's exactly the kind of insight I was looking for. ",
        ]
    elif score >= 6.0:
        ack_options = [
            "Good answer. ",
            "That's a solid response. ",
            "Right, that makes sense. ",
            "Good, I like where you're going with this. ",
            "Okay, that's a reasonable perspective. ",
        ]
    elif score >= 4.0:
        ack_options = [
            "I see what you mean. Let me ask about that differently. ",
            "Interesting approach. Let me dig a bit deeper. ",
            "That's one way to look at it — let's explore it further. ",
            "I hear you. Let me probe a bit more on this. ",
        ]
    else:
        ack_options = [
            "No worries, let me rephrase. ",
            "That's okay — let me try a simpler angle. ",
            "No problem at all. Let's approach this differently. ",
            "I understand. Let me help you with this one. ",
        ]
    return random.choice(ack_options)


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences from LLM output before JSON parsing."""
    text = text.strip()
    for fence in ["```json", "```json\n", "```"]:
        if text.startswith(fence):
            text = text[len(fence):]
            if text.endswith("```"):
                text = text[:-3]
            break
    return text.strip()


def _extract_skills_from_text(text: str) -> List[str]:
    """Extract skills mentioned in the text."""
    text_lower = text.lower()
    found_skills = []

    for category, keywords in TECHNICAL_SKILLS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_skills.append(category)
                break

    for skill in SOFT_SKILLS:
        if skill in text_lower:
            found_skills.append(f"soft_{skill}")

    return list(set(found_skills))


def _determine_phase_from_index(idx: int) -> str:
    """Natural phase flow based on question index."""
    if idx <= 1:
        return "greeting"
    elif idx <= 3:
        return "welcome"
    elif idx <= 6:
        return "warmup"
    elif idx <= 10:
        return "technical"
    elif idx <= 12:
        return "stress"
    elif idx <= 14:
        return "behavioral"
    else:
        return "closing"


def determine_phase_details_from_plan(state: InterviewState, idx: int) -> tuple[int, Dict[str, Any]]:
    """Determine phase index and details from plan if available, otherwise fallback."""
    plan = state.get("interview_plan")
    if not plan or not plan.get("phases"):
        return 0, {}
    phases = plan.get("phases", [])
    cumulative_questions = 0
    for phase_idx, phase_data in enumerate(phases):
        q_count = phase_data.get("question_count", 1)
        cumulative_questions += q_count
        if idx < cumulative_questions:
            return phase_idx, phase_data
    if phases:
        return len(phases) - 1, phases[-1]
    return 0, {}



def _initialize_skills_to_cover(resume_text: str, job_role: str) -> List[str]:
    """Initialize skills to cover based on resume and job role."""
    text = f"{resume_text} {job_role}".lower()
    skills = []

    for category, keywords in TECHNICAL_SKILLS.items():
        if any(kw in text for kw in keywords):
            skills.append(category)

    if not skills:
        skills = list(TECHNICAL_SKILLS.keys())[:5]

    skills.extend(["soft_communication", "soft_problem_solving", "soft_teamwork"])

    return list(set(skills))


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """Interviewer Agent — generates natural, adaptive, skill-based questions."""
    idx = state['current_question_index']
    if state.get("supervisor_mode") == "hr_takeover":
        return {
            "next_question": {
                "id": idx + 1,
                "question": "The recruiter has taken over the interview. Please speak with them directly.",
                "category": "situational",
                "difficulty": state.get("difficulty", "medium"),
                "time_limit": 600,
                "skill_tested": "Communication",
                "follow_up_topic": "None"
            }
        }

    if state.get("qa_paused", False):
        return {
            "next_question": {
                "id": idx + 1,
                "question": "The interview is temporarily paused for quality review. Please wait.",
                "category": "system",
                "difficulty": state.get("difficulty", "medium"),
                "time_limit": 600,
                "skill_tested": "general",
                "follow_up_topic": None
            },
            "qa_paused": True
        }

    last_eval = state.get('last_evaluation')
    plan_phase_idx, phase_details = determine_phase_details_from_plan(state, idx)
    current_phase = phase_details.get("phase", _determine_phase_from_index(idx))
    previous_phase = state.get('current_phase')

    # Check if transitioning to new phase
    phase_transition = previous_phase != current_phase if previous_phase else False

    difficulty = state.get("difficulty", "medium")
    if phase_transition and phase_details:
        plan_diff = phase_details.get("difficulty")
        if plan_diff:
            difficulty = plan_diff

    # Parse evaluation
    should_deep_dive = False
    needs_easier = False
    detected_skill = None

    if last_eval and isinstance(last_eval, dict):
        should_deep_dive = last_eval.get('should_deep_dive', False)
        needs_easier = last_eval.get('needs_easier', False)
        detected_skill = last_eval.get('skill_identified')
        low_effort = last_eval.get('low_effort', False)

        if low_effort or needs_easier:
            if difficulty == "hard":
                difficulty = "medium"
            elif difficulty == "medium":
                difficulty = "easy"
        elif should_deep_dive:
            if difficulty == "easy":
                difficulty = "medium"
            elif difficulty == "medium":
                difficulty = "hard"

    is_thinking_pause = last_eval.get("is_thinking_pause", False) if last_eval else False

    # Get LLM based on complexity
    llm = get_adaptive_llm() if should_deep_dive else get_fast_llm()
    parser = JsonOutputParser(pydantic_object=QuestionSchema)

    # Build conversation history with last few exchanges
    messages = state.get('messages', [])
    recent_history = messages[-6:] if len(messages) > 6 else messages

    history = "\n".join(
        f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content'][:400]}"
        for m in recent_history
    )

    # Get skills tracking
    covered_skills = state.get('covered_skills', [])
    pending_skills = state.get('pending_skills', [])

    # Build a natural conversational opening based on previous answer
    conversational_opening = ""
    if last_eval and messages:
        prev_score = last_eval.get('score', 5.0)
        prev_topic = last_eval.get('topic', 'topic')
        conversational_opening = _get_conversational_ack(prev_score, prev_topic, should_deep_dive)
        # Add specific acknowledgment that acknowledges what they actually said
        last_answer = messages[-1]['content'] if messages and messages[-1]['role'] == 'user' else ""
        if len(last_answer) < 100:
            conversational_opening += f"I hear you. "
        elif len(last_answer) < 300:
            conversational_opening += f"Got it. "

    # Phase guides with NATURAL flow — sound like a real human interviewer
    phase_guides = {
        "greeting": "Start with genuine warmth. Introduce yourself casually, like 'Hey, I'm Alex — thanks for making time for this.' Then casually ask something simple like 'How's your day going?' or 'How are you feeling about this?' Don't sound like a robot.",
        "welcome": "Express genuine interest in their story. Say something like 'I'd love to hear a bit about your background — what brought you here?' Make it feel like a conversation, not an interrogation. Use their name if you know it.",
        "warmup": "Ease into it naturally. Ask about their recent work in a way that lets them open up — 'What's been the most interesting thing you've worked on recently?' or 'Tell me about a project you're proud of.' Let them relax.",
        "technical": "Make the technical questions feel like a discussion, not a test. Say something like 'So I want to dig into some of the technical stuff you've worked on' or 'Let me ask you about some of the things you mentioned in your background.'",
        "stress": "Acknowledge the shift: 'Alright, things are about to get a bit more interesting' or 'Let me push you a little here.' Make it feel like a challenge between two professionals, not an interrogation.",
        "behavioral": "Transition naturally: 'Now let's talk about you as a person — how you work with teams, handle difficult situations, that kind of thing.' Sound like you genuinely want to understand who they are.",
        "closing": "Make it feel like the natural end of a good conversation. 'We're almost done here' or 'Almost through — I appreciate your patience.' Then give them space for any final thoughts. End warmly."
    }

    phase_guide = phase_guides.get(current_phase, "Ask a relevant question in a conversational way.")

    # Build context-aware instructions
    context_instructions = []

    # First question - natural greeting
    if idx == 0:
        greeting = random.choice(GREETING_MESSAGES)
        candidate_first_name = state.get("candidate_first_name")
        if candidate_first_name:
            context_instructions.append(
                f"FIRST IMPRESSION (CRITICAL): The candidate's name is {candidate_first_name}. "
                f"You MUST address them by their first name '{candidate_first_name}' in your very first sentence. "
                f"For example: 'Hey {candidate_first_name}, thanks for joining today!' or "
                f"'Hi {candidate_first_name} — great to have you here.' "
                f"Then invite them to share a bit about themselves. "
                f"Sound like a real person, not a script. Keep it warm and short."
            )
        else:
            context_instructions.append(f"FIRST IMPRESSION: Start with a warm, human greeting like '{greeting}' Then ask them to introduce themselves naturally. Use their name if known. Sound like a real person, not a script.")

    # Phase transition - natural bridge
    if phase_transition and previous_phase and current_phase:
        bridge = PHASE_TRANSITIONS.get((previous_phase, current_phase), "")
        if bridge:
            context_instructions.append(f"PHASE TRANSITION: Begin your response with something natural like '{bridge}' This should feel like a smooth, conversational shift.")

    # Candidate asked for a moment to think — be kind, re-state the question
    if is_thinking_pause:
        # Find the actual previous question text to repeat
        prev_q_text = ""
        for m in reversed(messages[:-1]):  # skip the user's "thinking" message
            if m.get("role") == "assistant":
                prev_q_text = m.get("content", "")
                break

        context_instructions.append(
            f"THINKING PAUSE (CRITICAL OVERRIDE): The candidate said they need a moment to think — "
            f"they did NOT answer yet. Do NOT ask a new question. "
            f"Instead, your output 'question' field MUST start with a kind, reassuring phrase like "
            f"'Take your time, no rush.' or 'Of course, no problem.' "
            f"Then re-state the previous question more simply. "
            f"The previous question was: \"{prev_q_text[:300]}\". "
            f"Rephrase it in simpler words after your reassurance. "
            f"Example: 'Take your time. To put it another way: <simpler version of the question>'"
        )

    # Skills coverage - naturally weave in
    if pending_skills and current_phase in ["technical", "stress"]:
        skill_context = f"IMPORTANT: These skills still need coverage: {', '.join(pending_skills[:3])}. Find natural ways to weave questions about these into the conversation."
        context_instructions.append(skill_context)

    # Adaptive based on last response - conversational adaptation
    if last_eval:
        score = last_eval.get('score', 5.0)
        topic = last_eval.get('topic', 'previous topic')
        skill_identified = last_eval.get('skill_identified', topic)

        if should_deep_dive:
            context_instructions.append(f"DEEP DIVE: They showed strength in '{skill_identified}'. Acknowledge their good answer naturally, then push them further with a more challenging angle.")
        elif needs_easier:
            context_instructions.append(f"SIMPLER PATH: They seemed to struggle a bit with '{skill_identified}'. Back off the complexity. Acknowledge their answer warmly, then ask an easier version that still lets them shine.")
        elif score >= 7.5:
            context_instructions.append(f"STRONG ANSWER: They did well on '{skill_identified}'. Acknowledge it naturally like 'Nice answer,' then either increase difficulty or explore a related angle.")

    # Natural follow-up instruction
    if state.get('follow_up_requested'):
        context_instructions.append("They asked a clarifying question. Answer it conversationally and briefly (1-2 sentences max), then smoothly return to the interview flow.")

    # Recruiter whispers - live instructions
    if state.get('hr_whisper_instructions'):
        context_instructions.append(f"RECRUITER LIVE WHISPER/OVERRIDE: {state['hr_whisper_instructions']}. Respect this instruction immediately and adapt your questioning accordingly.")

    # Episodic RAG Memory Context
    if state.get('rag_context'):
        context_instructions.append(f"CANDIDATE BACKGROUND CONTEXT (Indexed from Resume/GitHub):\n{state['rag_context']}\nUse this specific candidate project/experience context to ask highly tailored, contextualized, and personalized questions. Reference their real-world experience directly.")

    # Empathy adaptation
    empathy = state.get('empathy_metrics')
    if empathy and isinstance(empathy, dict):
        stress = empathy.get('stress_level', 0.0)
        if stress >= 7.0:
            context_instructions.append("EMPATHY ALERT: The candidate is showing high stress levels. Switch to an extremely warm, comforting, and supportive conversational tone. Simplify the phrasing of the question, and offer gentle encouragement.")

    # Build system prompt — sounds like a real, thoughtful human interviewer
    context_str = "\n".join(context_instructions)
    conversational_str = conversational_opening if conversational_opening else ""

    system_prompt = f"""You are a senior interviewer conducting a CONVERSATIONAL, NATURAL interview — not a rigid Q&A. You sound like an intelligent, empathetic human who is genuinely curious about the candidate. Think of yourself as a thoughtful senior engineer having a real conversation.

JOB ROLE: {state['job_role']}

CURRENT PHASE: {current_phase}
QUESTION NUMBER: {idx + 1}
CURRENT DIFFICULTY: {difficulty}

YOUR APPROACH: {phase_guide}

{context_str}

YOUR PREVIOUS RESPONSE ACKNOWLEDGMENT (include naturally at the start of your response):
{conversational_str}

SKILLS COVERED: {', '.join(covered_skills) if covered_skills else 'None yet'}
SKILLS STILL TO COVER: {', '.join(pending_skills) if pending_skills else 'All covered'}

RESUME CONTEXT (for relevant, personalized questions):
{state['resume_text'][:1500]}

RECENT CONVERSATION:
{history}

IMPORTANT RULES — READ CAREFULLY:
1. Your response should sound like a REAL HUMAN SPEAKING. Use casual but professional language.
2. Include a brief acknowledgment of their previous answer naturally (1-3 sentences).
3. Then ask ONE clear, conversational question at a time.
4. Never sound robotic. Avoid: "I would like to ask", "Moving on to", "Next question", etc.
5. Use phrases that sound human: "Tell me about...", "What are your thoughts on...", "How did you approach...", "Walk me through..."
6. If difficulty='easy', ask simple, concrete questions that let them shine.
7. If difficulty='hard', ask multi-part challenges that probe depth.
8. Never repeat questions already asked.
9. OUTPUT JSON ONLY with these fields: id, question, category, difficulty, time_limit, skill_tested, follow_up_topic
10. The 'question' field should be natural, human-sounding text only — no prefix like "Question:" or "My next question is:"

BIAS MITIGATION — CRITICAL:
- Evaluate candidates solely on their demonstrated skills and knowledge.
- Never make assumptions about a candidate's abilities based on their background, gender, age, or communication style.
- Ask the same core competency questions to all candidates for the same role.
- Focus on what the candidate CAN do, not what they haven't had the opportunity to learn.
- Avoid questions that assume specific cultural or socioeconomic experiences.
- If a candidate struggles with a question, offer an alternative approach rather than assuming lack of ability.

{parser.get_format_instructions()}"""

    # Set up QA agent evaluation loop
    from app.services.interview_engine.qa_node import qa_agent
    from app.models.trace_entry import TraceEntryCreate
    from app.services.observability_service import ObservabilityService
    from app.db.session import async_session
    from app.api.v1.endpoints.interview import manager

    attempts = 0
    max_attempts = 4  # 1 initial + 3 retries
    parsed_q = None
    is_coding = False

    skills_to_cover = state.get("skills_to_cover", [])
    session_id_str = state.get("supervisor_session_id")
    session_id = int(session_id_str) if session_id_str else None

    qa_total = state.get("qa_total_questions", 0)
    qa_flagged = state.get("qa_flagged_questions", 0)
    qa_paused_flag = False

    last_eval_res = None

    while attempts < max_attempts:
        try:
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Generate natural question {idx + 1} for {current_phase} phase."),
            ])
            clean_content = _strip_markdown(response.content)
            parsed_q = parser.parse(clean_content)
        except Exception as e:
            logger.error(f"LLM invoke failed in QA loop: {e}")
            break

        # Run QA check
        qa_res = await qa_agent.evaluate_question(parsed_q.get("question", ""), skills_to_cover, state)
        last_eval_res = qa_res
        
        qa_total += 1
        
        if qa_res["is_flagged"]:
            qa_flagged += 1
            attempts += 1
            
            # Log the flag in the database
            if session_id:
                try:
                    async with async_session() as db:
                        obs = ObservabilityService(db)
                        if qa_res["bias_flag"]:
                            await obs.record(TraceEntryCreate(
                                agent_name="qa_agent",
                                action_type="bias_detected",
                                session_id=session_id,
                                input_summary=f"Question: {parsed_q.get('question')}",
                                reasoning_summary=qa_res["bias_flag"]["details"],
                                output_summary=f"Bias Flagged. Type: {qa_res['bias_flag']['type']}",
                                confidence_score=1.0,
                                duration_ms=qa_res["evaluation_time_ms"]
                            ))
                        elif qa_res["is_off_topic"]:
                            await obs.record(TraceEntryCreate(
                                agent_name="qa_agent",
                                action_type="off_topic_detected",
                                session_id=session_id,
                                input_summary=f"Question: {parsed_q.get('question')}",
                                reasoning_summary=f"Cosine similarity: {qa_res['relevance_score']:.3f} is below 0.4 threshold. Closest skill: {qa_res['closest_skill']}",
                                output_summary=f"Off-Topic Flagged",
                                confidence_score=1.0,
                                duration_ms=qa_res["evaluation_time_ms"]
                            ))
                except Exception as log_err:
                    logger.error(f"Failed to log QA TraceEntry: {log_err}")
            
            # Modify system prompt to avoid repeating the flagged question or style
            system_prompt += f"\n\nCRITICAL: The previous question '{parsed_q.get('question')}' was FLAGGED by the QA Auditor as containing bias or being irrelevant. Do not use that wording or topic. Ensure the question is strictly neutral and relevant."
            continue
        else:
            # Not flagged, proceed!
            break

    # If quality score falls below 0.7, trigger admin pause
    if qa_total >= 3 and (qa_total - qa_flagged) / qa_total < 0.7:
        qa_paused_flag = True
        if session_id_str:
            try:
                alert_msg = {
                    "type": "qa_quality_alert",
                    "session_id": session_id_str,
                    "quality_score": (qa_total - qa_flagged) / qa_total,
                    "message": f"QA quality score has fallen below 0.7. Question generation paused."
                }
                await manager.broadcast_to_hr(alert_msg, session_id_str)
            except Exception as broadcast_err:
                logger.error(f"Failed to send QA websocket alert: {broadcast_err}")

    # Check if we failed to get a non-flagged question after max attempts
    if attempts >= max_attempts and parsed_q:
        # Escalate to HR via WebSocket
        if session_id_str:
            try:
                esc_msg = {
                    "type": "qa_escalation",
                    "session_id": session_id_str,
                    "question": parsed_q.get("question"),
                    "bias_details": last_eval_res.get("bias_flag") or {"type": "off_topic", "details": f"Question relevance {last_eval_res.get('relevance_score', 0.0):.3f} is below 0.4."}
                }
                await manager.broadcast_to_hr(esc_msg, session_id_str)
            except Exception as broadcast_err:
                logger.error(f"Failed to send QA websocket escalation: {broadcast_err}")

    # Return success or fallback
    if parsed_q:
        is_coding = current_phase in ['technical', 'stress'] and (idx + 1) % 4 == 0
        return {
            "next_question": parsed_q,
            "messages": [{"role": "assistant", "content": parsed_q['question']}],
            "current_phase": current_phase,
            "phase_transition": phase_transition,
            "previous_phase": previous_phase,
            "is_coding_mode": is_coding,
            "code_language": "python" if is_coding else None,
            "follow_up_requested": False,
            "previous_topic": parsed_q.get('follow_up_topic'),
            "difficulty": difficulty,
            "plan_phase_index": plan_phase_idx,
            "qa_total_questions": qa_total,
            "qa_flagged_questions": qa_flagged,
            "qa_paused": qa_paused_flag
        }
    else:
        # Fallback question logic
        fallback_questions = {
            "greeting": ["Hello! Welcome to your interview. How are you feeling today?"],
            "welcome": ["Could you tell me a bit about yourself and your background?"],
            "warmup": ["What was your most recent role and what did you enjoy most about it?"],
            "technical": ["Can you describe a technical challenge you solved recently?"],
            "stress": ["Tell me about a time you had to handle a difficult situation under pressure."],
            "behavioral": ["Can you share an experience where you had to work with a difficult team member?"],
            "closing": ["Do you have any questions for me? What are your key takeaways from this interview?"]
        }

        fallback_q = fallback_questions.get(current_phase, fallback_questions["technical"])[idx % 3]

        return {
            "next_question": {
                "id": idx + 1,
                "question": fallback_q,
                "category": current_phase,
                "difficulty": difficulty,
                "time_limit": 120,
                "skill_tested": "general",
                "follow_up_topic": None
            },
            "messages": [{"role": "assistant", "content": fallback_q}],
            "current_phase": current_phase,
            "phase_transition": phase_transition,
            "is_coding_mode": False,
            "code_language": None,
            "difficulty": difficulty,
            "plan_phase_index": plan_phase_idx,
            "qa_total_questions": qa_total,
            "qa_flagged_questions": qa_flagged,
            "qa_paused": qa_paused_flag
        }


async def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """Evaluator Agent — scores answers and extracts skills."""
    llm = get_strong_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)

    last_question = state.get('next_question', {})
    q_text = last_question.get('question', '') if isinstance(last_question, dict) else ''
    q_skill = last_question.get('skill_tested', 'general') if isinstance(last_question, dict) else 'general'
    rag_context = (state.get("rag_context") or "").strip()

    last_message = state['messages'][-1]['content'] if state.get('messages') else ""

    # Check for "thinking pause" — candidate explicitly asking for time to think.
    # We don't penalize these — flag them so generate_question_node can re-prompt kindly.
    is_thinking = (
        last_message.lower().strip() in THINKING_INDICATORS or
        any(thinking_phrase in last_message.lower() for thinking_phrase in THINKING_INDICATORS)
    ) and len(last_message.strip()) < 50

    if is_thinking:
        # Don't penalize — return a "patient" eval that signals the next node to gently re-prompt
        return {
            "last_evaluation": {
                "score": 5.0,  # neutral
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": "thinking_pause",
                "skill_category": "behavioral",
                "should_deep_dive": False,
                "needs_easier": False,
                "low_effort": False,
                "is_thinking_pause": True,  # flag for generate_question to re-prompt kindly
                "skill_identified": "patience"
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "total_responses": state.get('total_responses', 0),  # don't increment
        }

    # Check for low effort responses
    low_effort_indicators = ['ok', 'yes', 'no', 'okay', 'uh', 'um', 'idk', 'maybe', 'shrug', '🤷']
    is_low_effort = (
        len(last_message.strip()) < 15 or
        last_message.lower().strip() in low_effort_indicators or
        all(last_message.lower().count(c) < 3 for c in 'aeiou')
    )

    if is_low_effort:
        return {
            "last_evaluation": {
                "score": 2.0,
                "metrics": {"accuracy": 1, "clarity": 2, "depth": 1, "communication": 3},
                "topic": "engagement",
                "skill_category": "behavioral",
                "should_deep_dive": False,
                "needs_easier": True,
                "low_effort": True,
                "skill_identified": "engagement"
            },
            "latest_score": 2.0,
            "metrics": {"accuracy": 1, "clarity": 2, "depth": 1, "communication": 3},
            "total_responses": state.get('total_responses', 0) + 1,
            "low_quality_count": state.get('low_quality_count', 0) + 1,
        }

    system_prompt = f"""You are a senior hiring manager evaluating a candidate for {state['job_role']}.

SCORING (0.0–10.0):
- Accuracy: Technical correctness
- Clarity: How well they communicate
- Depth: Level of insight and detail
- Communication: Professionalism and structure

QUESTION ASKED: {q_text}
SKILL BEING TESTED: {q_skill}
CANDIDATE'S ANSWER: {last_message}

CANDIDATE BACKGROUND CONTEXT:
{rag_context[:1500] if rag_context else state.get('resume_text', '')[:1500]}

Evaluate the answer carefully. Consider:
1. Did they answer the question?
2. How detailed was their response?
3. Did they provide examples?
4. Was their communication clear?
5. Did they show relevant skills?

Also identify:
- The PRIMARY skill category they demonstrated (technical, soft_skill, behavioral)
- The specific skill they used (e.g., leadership, python, teamwork)
- Whether you should follow up for deeper evaluation
- Whether they need an easier question
- If the answer is low effort (too short or meaningless)

BIAS MITIGATION — CRITICAL:
- Evaluate solely on demonstrated skills and knowledge in this answer.
- Do not penalize for communication style differences, cultural background, or non-native English.
- Focus on substance over eloquence — a technically correct but brief answer can still score well.
- Consider that candidates may express knowledge differently based on their background.
- Never assume lack of experience equals lack of ability.
- Score based on what IS present in the answer, not what is absent.

{parser.get_format_instructions()}"""

    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        clean_content = _strip_markdown(response.content)
        parsed = parser.parse(clean_content)

        return {
            "last_evaluation": parsed,
            "latest_score": parsed['score'],
            "metrics": parsed['metrics'],
            "total_responses": state.get('total_responses', 0) + 1,
            "high_quality_count": state.get('high_quality_count', 0) + (1 if parsed.get('score', 0) >= 6 else 0),
            "low_quality_count": state.get('low_quality_count', 0),
        }
    except Exception as e:
        logger.error(f"evaluate_answer_node failed: {e}")
        return {
            "last_evaluation": {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": "general",
                "skill_category": "behavioral",
                "should_deep_dive": False,
                "needs_easier": False,
                "low_effort": False,
                "skill_identified": "general"
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "total_responses": state.get('total_responses', 0) + 1,
        }


async def evaluate_code_node(state: InterviewState) -> Dict[str, Any]:
    """Code Evaluator Agent — specialized evaluation for code submissions."""
    llm = get_code_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)

    code = state.get('code_snippet', "")
    question = state.get('next_question', {})
    q_text = question.get('question', '') if isinstance(question, dict) else ""
    rag_context = (state.get("rag_context") or "").strip()

    last_message = state['messages'][-1]['content'] if state.get('messages') else ""
    execution_info = ""
    if "Status:" in last_message and "Output:" in last_message:
        execution_info = f"\nEXECUTION RESULTS:\n{last_message}"

    system_prompt = f"""You are a Principal Software Engineer evaluating a code submission for {state['job_role']}.

CHALLENGE: {q_text}
CODE:\n{code}
{execution_info}

CANDIDATE BACKGROUND CONTEXT:
{rag_context[:1500] if rag_context else state.get('resume_text', '')[:1500]}

CRITERIA: Logic & Correctness, Time/Space Complexity, Readability, Best Practices.

Evaluate the code carefully and provide scores.

{parser.get_format_instructions()}"""

    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        clean_content = _strip_markdown(response.content)
        parsed = parser.parse(clean_content)

        return {
            "last_evaluation": parsed,
            "latest_score": parsed['score'],
            "metrics": parsed['metrics'],
            "is_coding_mode": False,
        }
    except Exception as e:
        logger.error(f"evaluate_code_node failed: {e}")
        return {
            "last_evaluation": {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": "coding",
                "skill_category": "technical",
                "should_deep_dive": False,
                "needs_easier": False,
                "low_effort": False,
                "skill_identified": "programming"
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "is_coding_mode": False,
        }


async def update_memory_node(state: InterviewState) -> Dict[str, Any]:
    """Decision & Memory Agent — adaptive difficulty, skill tracking, completion detection."""
    try:
        eval_result = state.get('last_evaluation', {})

        # ── Thinking-pause short-circuit ──────────────────────────────────────
        # Don't advance the question index, don't mark complete, just pass through.
        if isinstance(eval_result, dict) and eval_result.get("is_thinking_pause"):
            logger.info("update_memory_node: thinking pause — skipping index advance.")
            return {
                "is_coding_mode": False,
            }

        score = eval_result.get('score', 5.0)
        topic = eval_result.get('topic', 'general')
        skill_category = eval_result.get('skill_category', 'behavioral')
        skill_identified = eval_result.get('skill_identified', topic)

        # Update difficulty based on performance
        diff = state['difficulty']
        if eval_result.get('needs_easier', False) or score < 4.0:
            diff = "easy" if diff not in ["easy"] else "easy"
        elif score > 7.5:
            if diff == "easy":
                diff = "medium"
            elif diff == "medium":
                diff = "hard"

        # Update topic scores
        new_topic_scores = state.get('topic_scores', {}).copy()
        new_topic_scores[skill_identified] = score

        # Update topic strengths
        new_strengths = state.get('topic_strengths', {}).copy()
        if score >= 7.5:
            new_strengths[skill_identified] = "strong"
        elif score >= 4.5:
            new_strengths[skill_identified] = "improving"
        else:
            new_strengths[skill_identified] = "weak"

        # Update skill coverage
        covered_skills = state.get('covered_skills', []).copy()
        pending_skills = state.get('pending_skills', []).copy()

        if skill_identified and skill_identified not in covered_skills:
            covered_skills.append(skill_identified)
            if skill_identified in pending_skills:
                pending_skills.remove(skill_identified)

        # Calculate coverage percentage
        total_skills = len(state.get('skills_to_cover', []))
        if total_skills > 0:
            coverage_pct = (len(covered_skills) / total_skills) * 100
        else:
            coverage_pct = 100.0

        # Calculate running average
        current_avg = state.get('avg_score', 0)
        idx = state['current_question_index']
        new_avg = ((current_avg * idx) + score) / (idx + 1) if idx > 0 else score

        # Determine phase
        idx = state['current_question_index'] + 1
        plan_phase_idx, phase_details = determine_phase_details_from_plan(state, idx)
        current_phase = phase_details.get("phase", _determine_phase_from_index(idx))

        # Track consecutive low quality responses
        low_effort = eval_result.get("low_effort", False)
        is_low_quality = (score < 4.0 or low_effort)
        consecutive_low_q = state.get("consecutive_low_quality", 0)
        if is_low_quality:
            consecutive_low_q += 1
        else:
            consecutive_low_q = 0

        revised_updates = {}
        if consecutive_low_q >= 2:
            from app.services.interview_engine.planner_node import planner_node
            from app.db.session import async_session
            try:
                async with async_session() as db:
                    temp_state = state.copy()
                    temp_state["consecutive_low_quality"] = consecutive_low_q
                    temp_state["plan_phase_index"] = plan_phase_idx
                    revised_updates = await planner_node.revise_plan(temp_state, db)
            except Exception as rev_err:
                logger.error(f"Failed to revise plan: {rev_err}")

        # AUTO-COMPLETION DETECTION
        interview_complete = False
        completion_reason = None

        max_q = state.get('max_questions', 15)
        high_q = state.get('high_quality_count', 0)
        low_q = state.get('low_quality_count', 0)

        # Completion condition 1: Maximum questions reached with good coverage
        if idx >= max_q:
            if coverage_pct >= 60:
                interview_complete = True
                completion_reason = f"Completed with {coverage_pct:.0f}% skill coverage and avg score {new_avg:.1f}"
            else:
                interview_complete = True
                completion_reason = f"Maximum questions ({max_q}) reached"

        # Completion condition 2: All skills covered and good average
        elif coverage_pct >= 85 and new_avg >= 6.0:
            interview_complete = True
            completion_reason = f"All major skills covered ({coverage_pct:.0f}%) with quality average {new_avg:.1f}"

        # Completion condition 3: Too many low quality responses
        elif low_q >= 3 and idx >= 5:
            interview_complete = True
            completion_reason = "Multiple low-effort responses detected"

        # Completion condition 4: Consistently high performance
        elif high_q >= 5 and new_avg >= 8.0 and idx >= 10:
            interview_complete = True
            completion_reason = f"Excellent performance ({high_q} high-quality responses, avg {new_avg:.1f})"

        # Completion condition 5: User unresponsive in closing phase
        elif current_phase == "closing" and idx >= 12:
            interview_complete = True
            completion_reason = "Interview closing phase complete"

        # Don't complete too early
        if idx < 6 and interview_complete:
            interview_complete = False
            completion_reason = None

        if interview_complete:
            from app.db.session import async_session
            from sqlmodel import select
            from app.models.interview import InterviewSession

            async def run_merge():
                try:
                    async with async_session() as db:
                        session_id_val = state.get("supervisor_session_id")
                        if session_id_val:
                            try:
                                session_id_int = int(session_id_val)
                            except ValueError:
                                session_id_int = 0
                            if session_id_int:
                                # NOTE: candidate_id is not directly in InterviewState;
                                # it should be passed in when the session is initialized.
                                # For now, we derive it from the InterviewSession record.
                                stmt = select(InterviewSession).where(InterviewSession.id == session_id_int)
                                res = await db.execute(stmt)
                                session_rec = res.scalars().first()
                                if session_rec:
                                    await memory_service.merge_session_skills(
                                        candidate_id=session_rec.candidate_id,
                                        session_id=session_id_int,
                                        skill_scores=new_topic_scores,
                                        db=db
                                    )
                except Exception as merge_err:
                    logger.error(f"Failed to merge skills in update_memory_node: {merge_err}")

            asyncio.create_task(run_merge())

        ret = {
            "difficulty": diff,
            "topic_strengths": new_strengths,
            "topic_scores": new_topic_scores,
            "covered_skills": covered_skills,
            "pending_skills": pending_skills,
            "skill_coverage_percentage": coverage_pct,
            "avg_score": new_avg,
            "current_phase": current_phase,
            "current_question_index": idx,
            "interview_complete": interview_complete,
            "completion_reason": completion_reason,
            "is_coding_mode": False,
            "consecutive_low_quality": consecutive_low_q,
            "plan_phase_index": plan_phase_idx,
        }
        if revised_updates:
            ret.update(revised_updates)
        return ret
    except Exception as e:
        logger.error(f"update_memory_node failed: {e}")
        return {
            "current_question_index": state['current_question_index'] + 1,
            "interview_complete": state['current_question_index'] + 1 >= state.get('max_questions', 15),
            "completion_reason": "Maximum questions reached",
        }


# ── AI Advisor Monitor Node (Phase 1A) ─────────────────────────────────────────

async def advisor_monitor_node(state: InterviewState) -> Dict[str, Any]:
    """
    Silent advisor that monitors interview and notifies HR when ready to close.
    Never forces termination — only suggests to interviewer.

    This node runs after update_memory_node and before the should_continue check.
    It analyzes interview signals and returns advisor state fields.
    """
    from .advisor_service import assess_interview_advisor

    # Don't suggest before question 6 (minimum data needed)
    if state.get('current_question_index', 0) < 6:
        return {
            "advisor_ready_to_close": False,
            "advisor_notified": False,
        }

    # Don't suggest again if already notified and interviewer hasn't acted
    if state.get('advisor_notified') and not state.get('advisor_action_taken'):
        return {}  # No change — already notified

    try:
        decision = await assess_interview_advisor(state)

        return {
            "advisor_ready_to_close": decision.ready_to_close,
            "advisor_confidence": decision.confidence,
            "advisor_reason": decision.reason,
            "advisor_reason_category": decision.reason_category,
            "advisor_notified": decision.ready_to_close,
            "advisor_action_taken": False,
        }
    except Exception as e:
        logger.error(f"advisor_monitor_node failed: {e}")
        # Return empty dict — no advisor suggestion on failure
        # Interview continues normally
        return {}


# ── NEXT-GEN AGENTIC NODES ─────────────────────────────────────────────────────

async def empathy_analyzer_node(state: InterviewState) -> Dict[str, Any]:
    """Next-Gen Agentic: Analyzes candidate stress levels based on response length and hesitation indicators."""
    logger.info("Running empathy_analyzer_node...")
    messages = state.get("messages", [])
    if not messages:
        return {"empathy_metrics": {"stress_level": 0.0, "hesitation_rating": 0.0, "typing_speed": 0.0}}
        
    last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if not last_user_message:
        return {}
        
    # Analyze text features for stress
    text_len = len(last_user_message)
    hesitation_indicators = ["um", "uh", "like", "i think", "maybe", "sorry", "difficult", "unsure", "hard to say"]
    hesitation_count = sum(last_user_message.lower().count(word) for word in hesitation_indicators)
    
    # Calculate a simple stress score out of 10
    stress_score = 0.0
    if text_len < 30: # extremely short answer
        stress_score += 3.0
    if hesitation_count >= 3:
        stress_score += 4.0
    elif hesitation_count > 0:
        stress_score += 2.0
        
    # Add randomness/pacing simulating real dynamic analysis
    stress_level = min(10.0, max(0.0, stress_score + random.uniform(0, 2)))
    
    # Track metrics
    empathy_metrics = {
        "stress_level": round(stress_level, 2),
        "hesitation_rating": min(10.0, hesitation_count * 2.0),
        "typing_speed": round(text_len / max(1, len(last_user_message.split()) * 0.5), 1)
    }
    
    logger.info(f"Empathy metrics: {empathy_metrics}")
    
    # Dynamic difficulty mitigation
    updates: Dict[str, Any] = {"empathy_metrics": empathy_metrics}
    if stress_level >= 7.0:
        updates["difficulty"] = "easy"
        
    return updates


async def skeptic_evaluation_node(state: InterviewState) -> Dict[str, Any]:
    """Debate Agent — Skeptic persona: Critiques logic, errors, and depth of the answer."""
    logger.info("Running skeptic_evaluation_node...")
    llm = get_fast_llm()
    last_question = state.get('next_question', {})
    q_text = last_question.get('question', '') if isinstance(last_question, dict) else ''
    last_message = state['messages'][-1]['content'] if state.get('messages') else ""
    code_snippet = state.get('code_snippet')
    rag_context = (state.get("rag_context") or "").strip()
    
    content = f"Question: {q_text}\nAnswer: {last_message}"
    if code_snippet:
        content += f"\nSubmitted Code:\n{code_snippet}"
    if rag_context:
        content += f"\nCandidate Background Context:\n{rag_context[:1200]}"
        
    prompt = f"""You are a Skeptical Technical Reviewer. Criticize the following candidate response. 
Identify logical flaws, potential bugs, edge cases they missed, or general lack of depth.
Focus solely on technical gaps, flaws, and shortcomings. Be critical and direct.

{content}

Provide your critique in 2-3 bullet points."""
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a Skeptical Technical Reviewer. Be critical, concise and analytical."),
            HumanMessage(content=prompt)
        ])
        return {"skeptic_critique": response.content.strip()}
    except Exception as e:
        logger.error(f"Skeptic critique failed: {e}")
        return {"skeptic_critique": "Candidate response has potential gaps in deep technical concepts."}


async def pragmatist_evaluation_node(state: InterviewState) -> Dict[str, Any]:
    """Debate Agent — Pragmatist persona: Focuses on readability, design patterns, and real-world efficiency."""
    logger.info("Running pragmatist_evaluation_node...")
    llm = get_fast_llm()
    last_question = state.get('next_question', {})
    q_text = last_question.get('question', '') if isinstance(last_question, dict) else ''
    last_message = state['messages'][-1]['content'] if state.get('messages') else ""
    code_snippet = state.get('code_snippet')
    rag_context = (state.get("rag_context") or "").strip()
    
    content = f"Question: {q_text}\nAnswer: {last_message}"
    if code_snippet:
        content += f"\nSubmitted Code:\n{code_snippet}"
    if rag_context:
        content += f"\nCandidate Background Context:\n{rag_context[:1200]}"
        
    prompt = f"""You are a Pragmatic Tech Lead. Evaluate the candidate response for readability, production-readiness, best practices, and real-world trade-offs.
What are the strengths and practical limitations of their approach?

{content}

Provide your evaluation in 2-3 bullet points."""
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a Pragmatic Tech Lead focused on practical, clean code and design."),
            HumanMessage(content=prompt)
        ])
        return {"pragmatist_critique": response.content.strip()}
    except Exception as e:
        logger.error(f"Pragmatist critique failed: {e}")
        return {"pragmatist_critique": "The proposed solution is acceptable for basic usage but requires optimizations for production scale."}


async def bias_auditor_node(state: InterviewState) -> Dict[str, Any]:
    """Debate Agent — Bias Auditor: Evaluates content fairly, ignoring grammar/fluency/accent issues."""
    logger.info("Running bias_auditor_node...")
    llm = get_fast_llm()
    last_question = state.get('next_question', {})
    q_text = last_question.get('question', '') if isinstance(last_question, dict) else ''
    last_message = state['messages'][-1]['content'] if state.get('messages') else ""
    rag_context = (state.get("rag_context") or "").strip()
    
    prompt = f"""You are a Diversity & Fairness Auditor. Analyze the candidate response.
Your job is to identify if the response contains correct core ideas, regardless of:
- Grammar mistakes, stuttering words, or sentence structuring issues.
- Language fluency barriers or accents.
- Typing typos.

Confirm if the candidate genuinely understands the concept. Ignore presentation style and audit for core value.

Question: {q_text}
Candidate Answer: {last_message}
Candidate Background Context:
{rag_context[:1200] if rag_context else state.get('resume_text', '')[:1200]}

Provide your assessment in 1-2 bullet points."""
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a Bias Auditor. Your role is to ensure maximum fairness by looking only at candidate intent and core knowledge."),
            HumanMessage(content=prompt)
        ])
        return {"bias_auditor_critique": response.content.strip()}
    except Exception as e:
        logger.error(f"Bias auditor critique failed: {e}")
        return {"bias_auditor_critique": "Candidate shows correct conceptual understanding despite minor delivery flaws."}


async def consensus_synthesizer_node(state: InterviewState) -> Dict[str, Any]:
    """Debate Agent — Consensus Synthesizer: Reconciles all three critiques into structured EvaluationSchema."""
    logger.info("Running consensus_synthesizer_node...")

    # ── Thinking-pause short-circuit ──────────────────────────────────────
    # The candidate said something like "hmm, let me think" — don't penalize.
    # Return a neutral eval with is_thinking_pause=True so generate_question_node
    # gently re-prompts/rephrases instead of asking a new question.
    last_user_message = ""
    for m in reversed(state.get("messages", [])):
        if m.get("role") == "user":
            last_user_message = m.get("content", "")
            break

    is_thinking = (
        last_user_message
        and len(last_user_message.strip()) < 50
        and (
            last_user_message.lower().strip() in THINKING_INDICATORS
            or any(p in last_user_message.lower() for p in THINKING_INDICATORS)
        )
    )

    if is_thinking:
        logger.info("Detected thinking pause — skipping debate, returning neutral eval.")
        return {
            "last_evaluation": {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": "thinking_pause",
                "skill_category": "behavioral",
                "should_deep_dive": False,
                "needs_easier": False,
                "low_effort": False,
                "is_thinking_pause": True,
                "skill_identified": "patience",
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "total_responses": state.get("total_responses", 0),  # don't increment
            "skeptic_critique": None,
            "pragmatist_critique": None,
            "bias_auditor_critique": None,
        }

    llm = get_strong_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)
    
    last_question = state.get('next_question', {})
    q_text = last_question.get('question', '') if isinstance(last_question, dict) else ''
    q_skill = last_question.get('skill_tested', 'general') if isinstance(last_question, dict) else 'general'
    last_message = state['messages'][-1]['content'] if state.get('messages') else ""
    code_snippet = state.get('code_snippet')
    rag_context = (state.get("rag_context") or "").strip()
    
    skeptic = state.get("skeptic_critique", "No critique provided.")
    pragmatist = state.get("pragmatist_critique", "No critique provided.")
    bias_auditor = state.get("bias_auditor_critique", "No critique provided.")
    
    system_prompt = f"""You are a Principal Hiring Committee Director evaluating a candidate for the role: {state['job_role']}.
You must synthesize three distinct critiques (Skeptic, Pragmatist, and Bias Auditor) to produce a single objective score and feedback.

CRITIQUES:
1. SKEPTIC CRITIQUE:
{skeptic}

2. PRAGMATIST CRITIQUE:
{pragmatist}

3. BIAS AUDITOR CRITIQUE:
{bias_auditor}

QUESTION: {q_text}
SKILL TESTED: {q_skill}
CANDIDATE RESPONSE: {last_message}
{f"CODE SUBMITTED: {code_snippet}" if code_snippet else ""}
CANDIDATE BACKGROUND CONTEXT:
{rag_context[:1500] if rag_context else state.get('resume_text', '')[:1500]}

Compile these reviews into a unified JSON schema. Ensure the final score (0.0-10.0) is a fair reflection of the critiques, giving high weight to conceptual understanding and practical scaling while ignoring linguistic biases.

{parser.get_format_instructions()}"""
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a Principal Hiring Committee Director synthesizing debates into clean structured JSON."),
            HumanMessage(content=system_prompt)
        ])
        clean_content = _strip_markdown(response.content)
        parsed = parser.parse(clean_content)
        
        return {
            "last_evaluation": parsed,
            "latest_score": parsed['score'],
            "metrics": parsed['metrics'],
            "total_responses": state.get('total_responses', 0) + 1,
            "high_quality_count": state.get('high_quality_count', 0) + (1 if parsed.get('score', 0) >= 6 else 0),
            "low_quality_count": state.get('low_quality_count', 0),
            # Clear intermediate critiques
            "skeptic_critique": None,
            "pragmatist_critique": None,
            "bias_auditor_critique": None
        }
    except Exception as e:
        logger.error(f"consensus_synthesizer_node failed: {e}")
        # Return fallback
        return {
            "last_evaluation": {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": q_skill,
                "skill_category": "technical" if state.get("is_coding_mode") else "behavioral",
                "should_deep_dive": False,
                "needs_easier": False,
                "low_effort": False,
                "skill_identified": q_skill
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "total_responses": state.get('total_responses', 0) + 1,
            # Clear intermediate critiques in fallback
            "skeptic_critique": None,
            "pragmatist_critique": None,
            "bias_auditor_critique": None,
        }


async def code_copilot_node(state: InterviewState) -> Dict[str, Any]:
    """Next-Gen Agentic: Formulates a friendly interactive hint for coding sandboxes without giving away the solution."""
    logger.info("Running code_copilot_node...")
    
    # Check if a copilot suggestion is actually needed (requested, or idle/compilation issues flagged)
    is_requested = state.get("copilot_request_pending", False)
    
    # Check compile error counts if available (e.g. from supervisor observations)
    has_compile_errors = False
    for obs in state.get("supervisor_observations", []):
        if obs.get("type") == "difficulty_observation" and "compile" in obs.get("message", "").lower():
            has_compile_errors = True
            break
            
    if not is_requested and not has_compile_errors:
        return {"copilot_request_pending": False} # Skip suggestion
        
    llm = get_code_llm()
    code = state.get("code_snippet", "")
    question = state.get("next_question", {})
    q_text = question.get("question", "") if isinstance(question, dict) else ""
    
    prompt = f"""You are a friendly, encouraging AI Pair Programmer assisting a candidate in a coding interview.
The candidate is working on the challenge:
{q_text}

Here is their current draft code:
```python
{code}
```

Formulate a helpful, subtle hint. 
Rules:
1. DO NOT write the corrected code for them.
2. Highlight syntax issues, logical bugs, or edge cases they should think about.
3. Be supportive and conversational (e.g., "I notice you are... have you thought about...").
4. Keep it under 3 sentences."""
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a supportive, encouraging coding peer. Never provide complete solutions, only hints."),
            HumanMessage(content=prompt)
        ])
        
        suggestion = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hint": response.content.strip(),
            "trigger": "manual_request" if is_requested else "compiler_assist"
        }
        
        suggestions = list(state.get("copilot_suggestions", [])) + [suggestion]
        
        logger.info(f"Generated Co-Pilot suggestion: {suggestion}")
        return {
            "copilot_suggestions": suggestions,
            "copilot_request_pending": False, # Reset request flag
            # Push a user-facing message to chat history so they see the hint
            "messages": [{"role": "assistant", "content": f"🤖 [Co-Pilot Tip]: {suggestion['hint']}"}]
        }
    except Exception as e:
        logger.error(f"Code copilot failed: {e}")
        fallback = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hint": "The coding assistant is temporarily unavailable. Re-check the failing line, simplify the input, and test one assumption at a time.",
            "trigger": "provider_fallback",
            "provider_error": type(e).__name__,
        }
        return {
            "copilot_suggestions": list(state.get("copilot_suggestions", [])) + [fallback],
            "copilot_request_pending": False,
            "messages": [{"role": "assistant", "content": f"[Co-Pilot Tip]: {fallback['hint']}"}],
        }


async def debate_router_node(state: InterviewState) -> Dict[str, Any]:
    """Pass-through node to split graph execution into parallel debate paths."""
    logger.info("Passing through debate_router...")
    return {}

