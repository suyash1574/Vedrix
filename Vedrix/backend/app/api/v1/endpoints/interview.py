from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
import logging
import traceback
from app.core.rate_limit import limiter
from app.services.session_cleanup import session_cleanup

from jose import jwt, JWTError
from sqlalchemy import select

from app.core.config import settings
from app.core import security
from app.core.security import ALGORITHM
from app.services.interview_engine import graph as interview_graph_module
from app.services.interview_engine.nodes import _initialize_skills_to_cover
from app.services.interview_engine.state import InterviewState
from app.services.interview_engine.coordination import build_turn_id, coordination_event
from app.services.interview_engine.response_handling import decide_response, response_notice, response_state_update
from app.services.interview_engine.timing import TimingProbe, elapsed_ms
from app.services.voice_service import voice_service
from app.services.supervisor_service import supervisor_registry, SupervisorObservation
import time as time_module
import base64
from app.services.evaluation_service import evaluation_service
from app.services.code_execution_service import code_execution_service
from app.services.rag_service import rag_service
from app.services.memory_service import memory_service
from app.services.email_service import (
    send_interview_started_email,
    send_report_to_candidate,
    send_report_to_hr,
)
from app.models.interview import InterviewSession, DriveInviteToken, JobDrive
from app.models.candidate_workflow import CandidateWorkflow
from app.models.hiring_workflow import CandidateApplication
from app.models.pipeline import HiringPipelineStageRun
from app.services.hiring_workflow_service import record_workflow_event
from app.models.profile import HRProfile, StudentProfile
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session, get_session
from app.models.trace_entry import TraceEntryRead
from app.api import deps
from app.schemas.scheduling import BookingCreate, BookingRead
from app.services.scheduling_service import SchedulingService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _advance_ordered_ai_stage(db, session_record: InterviewSession, report_dict: dict) -> None:
    """Move a V2 AI session into recruiter review without affecting legacy sessions."""
    if not session_record.job_drive_id:
        return
    application = (await db.execute(select(CandidateApplication).where(
        CandidateApplication.candidate_id == session_record.candidate_id,
        CandidateApplication.job_drive_id == session_record.job_drive_id,
    ))).scalars().first()
    if not application or not application.workflow_policy_snapshot:
        return
    stage = (await db.execute(select(HiringPipelineStageRun).where(
        HiringPipelineStageRun.application_id == application.id,
        HiringPipelineStageRun.stage_key == "ai_interview",
    ).order_by(HiringPipelineStageRun.attempt_number.desc()))).scalars().first()
    if not stage:
        return
    stage.status = "needs_review"
    stage.outcome = "completed"
    stage.completed_at = datetime.now(timezone.utc)
    stage.score = session_record.overall_score
    stage.confidence = session_record.advisor_confidence
    stage.related_entity_type = "interview_session"
    stage.related_entity_id = session_record.id
    workflow = (await db.execute(select(CandidateWorkflow).where(
        CandidateWorkflow.candidate_id == session_record.candidate_id,
        CandidateWorkflow.job_drive_id == session_record.job_drive_id,
    ))).scalars().first()
    if workflow and workflow.current_state in {"ai_interview_scheduled", "ai_interview_in_progress"}:
        previous = workflow.current_state
        workflow.current_state = "ai_interview_review"
        workflow.updated_at = datetime.now(timezone.utc)
        workflow.transition_history = [*(workflow.transition_history or []), {
            "from_state": previous,
            "to_state": "ai_interview_review",
            "trigger": "ai_interview_completed",
            "actor_id": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        await record_workflow_event(
            db,
            action="ai_interview_completed",
            entity_type="interview_session",
            job_drive_id=session_record.job_drive_id,
            candidate_id=session_record.candidate_id,
            application_id=application.id,
            entity_id=session_record.id,
            from_state=previous,
            to_state="ai_interview_review",
            stage_key="ai_interview",
            payload={"overall_score": session_record.overall_score, "report_keys": list(report_dict.keys())[:20]},
            source="ai_interview_engine",
        )


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.hr_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, is_hr: bool = False):
        await websocket.accept()
        if is_hr:
            if session_id not in self.hr_connections:
                self.hr_connections[session_id] = []
            self.hr_connections[session_id].append(websocket)
        else:
            self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str, websocket: Optional[WebSocket] = None, is_hr: bool = False):
        if is_hr:
            if session_id in self.hr_connections:
                if websocket in self.hr_connections[session_id]:
                    self.hr_connections[session_id].remove(websocket)
                if not self.hr_connections[session_id]:
                    self.hr_connections.pop(session_id, None)
        else:
            if websocket:
                if self.active_connections.get(session_id) == websocket:
                    self.active_connections.pop(session_id, None)
            else:
                self.active_connections.pop(session_id, None)

    async def send_json(self, message: Dict[str, Any], session_id: str):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(session_id, websocket=ws)
        
        await self.broadcast_to_hr(message, session_id)

    async def broadcast_to_hr(self, message: Dict[str, Any], session_id: str):
        hr_list = self.hr_connections.get(session_id, [])
        for ws in list(hr_list):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(session_id, websocket=ws, is_hr=True)


manager = ConnectionManager()


async def _deliver_question(
    *,
    session_id: str,
    question: dict,
    job_role: Optional[str] = None,
    is_coding: bool = False,
    language: str = "python",
) -> None:
    """Send text immediately; attach TTS later so audio never blocks turn progress."""
    question_id = question.get("id") if isinstance(question, dict) else None
    await manager.send_json({
        "type": "question",
        "data": question,
        "question_id": question_id,
        "job_role": job_role,
        "is_coding": is_coding,
        "language": language,
    }, session_id)

    async def _audio_task() -> None:
        try:
            question_text = question.get("question", "") if isinstance(question, dict) else ""
            if not question_text:
                return
            audio = await asyncio.wait_for(
                voice_service.speak_text(question_text),
                timeout=float(getattr(settings, "INTERVIEW_TTS_TIMEOUT_SECONDS", 3.0)),
            )
            if audio:
                await manager.send_json({
                    "type": "question_audio",
                    "question_id": question_id,
                    "audio": audio,
                }, session_id)
        except Exception as exc:
            logger.debug("Question TTS skipped for %s: %s", session_id, exc)

    asyncio.create_task(_audio_task())


async def _collect_graph_updates(graph: Any, config: dict) -> list[dict]:
    """Collect one graph turn under the configured critical-path timeout."""
    updates: list[dict] = []
    async for chunk in graph.astream(None, config=config, stream_mode="updates"):
        updates.append(chunk)
    return updates


def _verify_ws_token(token: str) -> Optional[int]:
    """Validate a JWT passed as a WebSocket query param. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except (JWTError, Exception):
        return None


def _build_student_profile_context(profile: Optional[StudentProfile]) -> str:
    """Build compact candidate context from profile fields available at session start."""
    if not profile:
        return ""

    profile_parts = []
    if profile.university:
        profile_parts.append(f"University: {profile.university}")
    if profile.degree:
        grad = f" (Graduation: {profile.graduation_year})" if profile.graduation_year else ""
        profile_parts.append(f"Degree: {profile.degree}{grad}")
    if profile.major:
        profile_parts.append(f"Major: {profile.major}")
    if profile.gpa:
        profile_parts.append(f"GPA: {profile.gpa}")
    if profile.skills:
        profile_parts.append(f"Skills: {profile.skills}")
    if profile.work_experience:
        profile_parts.append(f"Work Experience: {profile.work_experience}")
    if profile.internships:
        profile_parts.append(f"Internships: {profile.internships}")
    if profile.projects:
        profile_parts.append(f"Projects: {profile.projects}")
    if profile.certifications:
        profile_parts.append(f"Certifications: {profile.certifications}")
    if profile.languages:
        profile_parts.append(f"Languages: {profile.languages}")
    if profile.github_url:
        profile_parts.append(f"GitHub: {profile.github_url}")
    if profile.linkedin_url:
        profile_parts.append(f"LinkedIn: {profile.linkedin_url}")
    if profile.portfolio_url:
        profile_parts.append(f"Portfolio: {profile.portfolio_url}")
    if profile.hackathons:
        profile_parts.append(f"Hackathons: {profile.hackathons}")
    if profile.interests:
        profile_parts.append(f"Interests: {profile.interests}")
    if profile.experience_level:
        profile_parts.append(f"Experience Level: {profile.experience_level}")
    if profile.availability:
        profile_parts.append(f"Availability: {profile.availability}")
    if profile.expected_salary:
        profile_parts.append(f"Expected Salary: {profile.expected_salary}")
    if profile.preferred_locations:
        profile_parts.append(f"Preferred Locations: {profile.preferred_locations}")

    return " | ".join(profile_parts)


async def _load_candidate_context(
    db: AsyncSession,
    candidate_id: Optional[int],
    base_resume_text: str,
) -> Dict[str, Any]:
    """
    Load profile, resume, and longitudinal memory context for a candidate.

    Returns a conservative context bundle. Missing profile/memory is normal and
    falls back to the caller-provided resume/job context.
    """
    context: Dict[str, Any] = {
        "resume_text": base_resume_text,
        "profile_context": "",
        "memory_context": "",
        "rag_seed_context": base_resume_text,
        "github_url": None,
        "profile": None,
    }
    if not candidate_id:
        return context

    profile_res = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == candidate_id)
    )
    profile = profile_res.scalars().first()
    context["profile"] = profile

    profile_context = _build_student_profile_context(profile)
    if profile:
        context["github_url"] = profile.github_url
        candidate_resume = profile.resume_text or profile_context
        context["resume_text"] = "\n\n".join(
            part for part in [base_resume_text, candidate_resume] if part
        ) or base_resume_text
        context["profile_context"] = profile_context

    try:
        memory_profile = await memory_service.get_profile_for_planner(candidate_id=candidate_id, db=db)
    except Exception as e:
        logger.warning("Failed to load longitudinal memory for candidate %s: %s", candidate_id, e)
        memory_profile = None

    if memory_profile:
        scores = memory_profile.get("skill_scores") or {}
        trends = memory_profile.get("growth_trends") or {}
        memory_parts = []
        if scores:
            score_text = ", ".join(
                f"{skill}: {score:.1f}" if isinstance(score, (int, float)) else f"{skill}: {score}"
                for skill, score in list(scores.items())[:8]
            )
            memory_parts.append(f"Prior skill averages: {score_text}")
        if trends:
            trend_text = ", ".join(f"{skill}: {trend}" for skill, trend in list(trends.items())[:8])
            memory_parts.append(f"Growth trends: {trend_text}")
        context["memory_context"] = " | ".join(memory_parts)

    seed_parts = [
        part for part in [
            f"Session context: {base_resume_text}" if base_resume_text else "",
            context["resume_text"],
            f"Candidate profile: {context['profile_context']}" if context["profile_context"] else "",
            f"Interview history: {context['memory_context']}" if context["memory_context"] else "",
        ]
        if part
    ]
    context["rag_seed_context"] = "\n\n".join(seed_parts)
    return context


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    drive_id: Optional[int] = None,
    token: Optional[str] = None,
    auth_token: Optional[str] = None,  # JWT for authenticated practice sessions
    scheduled_session_id: Optional[int] = None,  # For resuming scheduled sessions
):
    await manager.connect(websocket, session_id)
    config = {"configurable": {"thread_id": session_id}}
    db_session_id: Optional[int] = None
    session_start = datetime.now(timezone.utc)

    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    hr_email: Optional[str] = None
    hr_name: Optional[str] = None
    drive_title: Optional[str] = None
    candidate_id: Optional[int] = None
    candidate_context: Dict[str, Any] = {}

    try:
        # Fallback to cookies if parameters are not provided
        if not auth_token:
            cookie_token = websocket.cookies.get("access_token")
            if cookie_token:
                auth_token = cookie_token

        # Validate that authentication parameters are provided
        if not (drive_id and token) and not auth_token:
            await manager.send_json({"type": "error", "data": "Authentication parameters missing or invalid."}, session_id)
            return

        # ── 1. Determine Context ──────────────────────────────────────────
        job_role = "Software Engineer"
        resume_text = "General software engineering background."

        if drive_id and token:
            # ── Guest / Invite flow ──
            async with async_session() as db:
                result = await db.execute(
                    select(DriveInviteToken).where(
                        DriveInviteToken.token == token,
                        DriveInviteToken.drive_id == drive_id,
                        DriveInviteToken.is_used == False,
                    )
                )
                invite = result.scalars().first()
                if not invite:
                    await manager.send_json({"type": "error", "data": "Invalid or expired invite link."}, session_id)
                    return
                if invite.expires_at:
                    # Make timezone-aware for comparison if naive
                    expires = invite.expires_at
                    if expires.tzinfo is None:
                        expires = expires.replace(tzinfo=timezone.utc)
                    if expires < datetime.now(timezone.utc):
                        await manager.send_json({"type": "error", "data": "This invite link has expired."}, session_id)
                        return

                candidate_email = invite.candidate_email
                candidate_name = (candidate_email or "").split("@")[0]
                invite.is_used = True
                db.add(invite)

                # Find or create shadow user
                user_result = await db.execute(select(User).where(User.email == candidate_email))
                user = user_result.scalars().first()
                if not user:
                    base = (candidate_email or "guest").split("@")[0]
                    username, n = base, 0
                    while (await db.execute(select(User).where(User.username == username))).scalars().first():
                        n += 1
                        username = f"{base}_{n}"
                    # Generate secure random password for guest users
                    import secrets
                    guest_password = secrets.token_urlsafe(16)
                    # Audit: Use to_thread for password hashing (CPU intensive)
                    password_hash = await asyncio.to_thread(security.get_password_hash, guest_password)
                    user = User(
                        email=candidate_email, username=username,
                        password_hash=password_hash, user_type="student",
                        first_name="Guest", last_name="Candidate", is_active=True,
                    )
                    db.add(user)
                    await db.flush()

                candidate_id = user.id

                # Fetch drive
                drive_res = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
                drive = drive_res.scalars().first()
                if drive:
                    job_role = drive.job_role
                    drive_title = drive.title
                    resume_text = f"Applying for: {drive.job_role}. Required skills: {drive.skills_required or 'General'}"
                    hr_prof_res = await db.execute(select(HRProfile).where(HRProfile.id == drive.hr_id))
                    hr_profile = hr_prof_res.scalars().first()
                    if hr_profile:
                        hr_user_res = await db.execute(select(User).where(User.id == hr_profile.user_id))
                        hr_user = hr_user_res.scalars().first()
                        if hr_user:
                            hr_email, hr_name = hr_user.email, hr_user.first_name

                candidate_context = await _load_candidate_context(db, candidate_id, resume_text)
                resume_text = candidate_context["resume_text"]

                new_session = InterviewSession(
                    candidate_id=candidate_id, job_drive_id=drive_id,
                    session_type="actual", status="in_progress",
                    start_time=datetime.now(timezone.utc),
                )
                db.add(new_session)
                await db.commit()
                await db.refresh(new_session)
                db_session_id = new_session.id

            await manager.send_json({"type": "status", "data": f"Session verified for {candidate_email}."}, session_id)
            if candidate_email:
                asyncio.create_task(send_interview_started_email(candidate_email, candidate_name, job_role))

        elif auth_token:
            # ── Authenticated session (practice or scheduled) — validate JWT (#4) ──
            user_id = _verify_ws_token(auth_token)
            if not user_id:
                await manager.send_json({"type": "error", "data": "Invalid authentication token."}, session_id)
                return

            async with async_session() as db:
                user_res = await db.execute(select(User).where(User.id == user_id))
                user = user_res.scalars().first()
                if not user:
                    await manager.send_json({"type": "error", "data": "User not found."}, session_id)
                    return

                # ── Security Audit: Enforce Thread Isolation ──────────────────
                # Verify that the user has permission to access this session_id (thread_id)
                # If scheduled_session_id is provided, check ownership.
                if scheduled_session_id:
                    session_res = await db.execute(
                        select(InterviewSession).where(
                            InterviewSession.id == scheduled_session_id,
                            InterviewSession.candidate_id == user_id
                        )
                    )
                    if not session_res.scalars().first():
                        await manager.send_json({"type": "error", "data": "Access denied to this session."}, session_id)
                        return
                
                # If this is a resume or join by session_id (used as thread_id), verify it belongs to user
                # Note: session_id in the URL is our thread_id.
                try:
                    int_session_id = int(session_id)
                    check_res = await db.execute(
                        select(InterviewSession).where(
                            InterviewSession.id == int_session_id
                        )
                    )
                    existing_session = check_res.scalars().first()
                    if existing_session and existing_session.candidate_id != user_id:
                        # HR might be allowed to join for live proctoring (Phase 1.1)
                        is_hr = user.user_type in ("hr", "admin")
                        if is_hr:
                            # Check if HR owns the drive
                            drive_res = await db.execute(
                                select(JobDrive).join(HRProfile).where(
                                    JobDrive.id == existing_session.job_drive_id,
                                    HRProfile.user_id == user_id
                                )
                            )
                            if not drive_res.scalars().first():
                                await manager.send_json({"type": "error", "data": "Access denied. You do not manage this session."}, session_id)
                                return
                        else:
                            await manager.send_json({"type": "error", "data": "Access denied. Thread isolation violation."}, session_id)
                            return
                except (ValueError, TypeError):
                    # For practice sessions, session_id might be a string (uuid), 
                    # we still allow it as long as it's a new unique thread.
                    pass

                candidate_name = user.first_name
                candidate_email = user.email
                candidate_id = user_id

                if scheduled_session_id:
                    # Use existing scheduled session
                    session_res = await db.execute(
                        select(InterviewSession).where(
                            InterviewSession.id == scheduled_session_id,
                            InterviewSession.candidate_id == user_id,
                            InterviewSession.status == "scheduled"
                        )
                    )
                    existing_session = session_res.scalars().first()
                    if not existing_session:
                        await manager.send_json({"type": "error", "data": "Scheduled session not found or already started."}, session_id)
                        return
                    
                    # Update session to in_progress
                    existing_session.status = "in_progress"
                    existing_session.start_time = datetime.now(timezone.utc)
                    db.add(existing_session)
                    await db.commit()
                    db_session_id = existing_session.id
                    
                    # Get job role from drive
                    if existing_session.job_drive_id:
                        drive_res = await db.execute(select(JobDrive).where(JobDrive.id == existing_session.job_drive_id))
                        drive = drive_res.scalars().first()
                        if drive:
                            job_role = drive.job_role
                            resume_text = f"Applying for: {drive.job_role}. Required skills: {drive.skills_required or 'General'}"
                    candidate_context = await _load_candidate_context(db, user_id, resume_text)
                    resume_text = candidate_context["resume_text"]
                else:
                    candidate_context = await _load_candidate_context(db, user_id, resume_text)
                    resume_text = candidate_context["resume_text"]
                    profile = candidate_context.get("profile")
                    if profile:
                        # Create better job role from profile
                        skills = profile.skills or "General"
                        job_role = f"Candidate for {profile.degree or 'Software'} role (Skills: {skills})"

                    new_session = InterviewSession(
                        candidate_id=user_id, session_type="practice",
                        status="in_progress", start_time=datetime.now(timezone.utc),
                    )
                    db.add(new_session)
                    await db.commit()
                    await db.refresh(new_session)
                    db_session_id = new_session.id

            await manager.send_json({"type": "status", "data": f"Interview ready, {candidate_name}."}, session_id)

        # ── 2. Build initial state ────────────────────────────────────────
        # Initialize skills to cover based on resume and job role
        skills_to_cover = _initialize_skills_to_cover(resume_text, job_role)

        # Register session with AI Supervisor
        supervisor_registry.register(str(db_session_id or session_id), control_mode="suggest")

        rag_seed_context = candidate_context.get("rag_seed_context") or resume_text

        # Background index candidate context in ChromaDB
        if db_session_id:
            try:
                async def _index_task():
                    g_url = candidate_context.get("github_url")

                    await rag_service.index_resume(str(db_session_id), rag_seed_context)
                    if g_url:
                        await rag_service.index_github_profile(str(db_session_id), g_url)
                        
                asyncio.create_task(_index_task())
            except Exception as e:
                logger.warning(f"Failed to kick off background RAG indexing: {e}")

        initial_state: InterviewState = {
            "messages": [],
            "resume_text": resume_text,
            "job_role": job_role,
            "candidate_first_name": candidate_name,
            "current_question_index": 0,
            "max_questions": 15,
            "interview_complete": False,
            "completion_reason": None,
            "current_phase": "greeting",
            "phase_transition": False,
            "previous_phase": None,
            "difficulty": "medium",
            "latest_score": 0.0,
            "metrics": {"accuracy": 0, "clarity": 0, "depth": 0, "communication": 0},
            "avg_score": 0.0,
            "covered_skills": [],
            "skills_to_cover": skills_to_cover,
            "pending_skills": skills_to_cover,
            "skill_coverage_percentage": 0.0,
            "topic_scores": {},
            "topic_strengths": {},
            "total_responses": 0,
            "low_quality_count": 0,
            "high_quality_count": 0,
            "interviewer_mode": "ai",
            "hr_instructions": None,
            "last_evaluation": None,
            "evaluation_history": [],
            "turn_id": None,
            "coordination_round_id": None,
            "coordination_trace": [],
            "last_candidate_answer": None,
            "awaiting_candidate_response": True,
            "last_response_turn_id": None,
            "last_response_fingerprint": None,
            "last_response_id": None,
            "last_response_kind": None,
            "active_question_id": None,
            "turn_timing": {},
            "precision_flags": [],
            "response_degraded": False,
            "next_question": None,
            "code_snippet": None,
            "code_language": None,
            "is_coding_mode": False,
            "follow_up_requested": False,
            "previous_topic": None,
            # ── AI Supervisor fields ─────────────────────────────────────
            "supervisor_session_id": str(db_session_id or session_id),
            "supervisor_mode": "suggest",                    # suggest by default
            "supervisor_observations": [],
            "supervisor_last_action": None,
            "supervisor_paused": False,
            "session_start_epoch": time_module.time(),
            "question_start_epoch": time_module.time(),
            "per_question_times": [],
            "score_history": [],
            "difficulty_history": ["medium"],
            # ── Next-Gen Agentic Fields ──────────────────────────────────
            "copilot_suggestions": [],
            "copilot_request_pending": False,
            "hr_whisper_instructions": None,
            "empathy_metrics": {"stress_level": 0.0, "hesitation_rating": 0.0, "typing_speed": 0.0},
            "stress_history": [],
            "empathy_timeline": [],
            "rag_context": rag_seed_context[:2500] if rag_seed_context else None,
            "debate_rounds": None,
            "skeptic_critique": None,
            "pragmatist_critique": None,
            "bias_auditor_critique": None,
            "interview_plan": None,
            "plan_phase_index": 0,
            "consecutive_low_quality": 0,
            "qa_regeneration_count": 0,
            "qa_session_quality_score": 1.0,
            "qa_flags": [],
            "qa_total_questions": 0,
            "qa_flagged_questions": 0,
            "qa_paused": False,
            "advisor_ready_to_close": False,
            "advisor_confidence": None,
            "advisor_reason": None,
            "advisor_reason_category": None,
            "advisor_notified": False,
            "advisor_action_taken": False,
        }

        # ── 3. Start Interview ────────────────────────────────────────────
        try:
            current_values = None
            try:
                async with asyncio.timeout(float(getattr(settings, "INTERVIEW_TURN_TIMEOUT_SECONDS", 20.0))):
                    async for event in interview_graph_module.interview_graph.astream(initial_state, config=config, stream_mode="values"):
                        if event.get("next_question"):
                            current_values = event
            except asyncio.TimeoutError:
                raise ValueError("AI engine timed out generating question")

            if not (current_values and current_values.get("next_question")):
                raise ValueError("AI engine failed to generate opening question")

            q = current_values["next_question"]
            await interview_graph_module.interview_graph.aupdate_state(config, {
                "active_question_id": str(q.get("id")) if isinstance(q, dict) and q.get("id") is not None else None,
                "awaiting_candidate_response": True,
            })

            await _deliver_question(
                session_id=session_id,
                question=q,
                job_role=job_role,
                is_coding=current_values.get("is_coding_mode", False),
                language=current_values.get("code_language", "python"),
            )
        except Exception as e:
            logger.error(f"Interview start failed [{session_id}]: {e}")
            await manager.send_json({"type": "error", "data": f"Engine Error: {str(e)}"}, session_id)
            return

        # ── 4. Main Communication Loop ────────────────────────────────────
        all_questions = [current_values["next_question"]]  # track for #18

        # Phase 1.4: Register session for timeout tracking
        session_cleanup.record_activity(session_id)

        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            # Phase 1.4: Record activity for timeout tracking
            session_cleanup.record_activity(session_id)

            user_answer = ""
            user_code = ""
            typing_duration = None
            turn_probe = TimingProbe()

            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                    if payload.get("type") in ("answer", "code"):
                        current_state = await interview_graph_module.interview_graph.aget_state(config)
                        current_values = current_state.values if current_state else {}
                        response_decision = decide_response(payload, current_values)
                        if not response_decision.accepted:
                            await manager.send_json({
                                "type": "response_rejected",
                                "data": response_notice(response_decision),
                            }, session_id)
                            continue

                        await manager.send_json({
                            "type": "response_ack",
                            "data": response_notice(response_decision),
                        }, session_id)
                        if response_decision.kind == "answer":
                            user_answer = response_decision.content
                            typing_duration = payload.get("duration_seconds")
                        else:
                            user_code = response_decision.content
                    elif payload.get("type") == "proctor_event":
                        # Route browser events to ProctorService.handle_browser_event()
                        # Message format: {"type": "proctor_event", "event": "tab_switch"|"paste"|"keystroke", ...}
                        from app.services.proctor_service import proctor_service
                        event = payload.get("event", "")
                        if db_session_id and event in ("tab_switch", "paste", "keystroke", "multiple_faces", "no_face", "gaze_deviation"):
                            async with async_session() as db:
                                # Fetch session to get status and consent
                                sess_res = await db.execute(
                                    select(InterviewSession).where(InterviewSession.id == db_session_id)
                                )
                                sess_rec = sess_res.scalars().first()
                                if sess_rec:
                                    session_status = sess_rec.status
                                    # proctor_consent_granted added via migration; use getattr for safety
                                    consent_granted = getattr(sess_rec, "proctor_consent_granted", None) or False

                                    # Build event-specific payload
                                    if event == "tab_switch":
                                        event_payload = {"timestamp": payload.get("timestamp")}
                                    elif event == "paste":
                                        event_payload = {
                                            "content_length": payload.get("content_length"),
                                            "phase": payload.get("phase"),
                                        }
                                    elif event == "keystroke":
                                        event_payload = {"timestamps": payload.get("timestamps", [])}
                                    elif event in ("multiple_faces", "no_face", "gaze_deviation"):
                                        event_payload = {
                                            "timestamp": payload.get("timestamp"),
                                            "confidence": payload.get("confidence", 1.0),
                                            "duration_seconds": payload.get("duration_seconds", 0.0),
                                        }
                                    else:
                                        event_payload = {}

                                    # Map event names to violation_type expected by proctor_service
                                    event_type_map = {
                                        "tab_switch": "tab_switch",
                                        "paste": "paste_detected",
                                        "keystroke": "anomalous_typing",
                                        "multiple_faces": "multiple_faces",
                                        "no_face": "no_face",
                                        "gaze_deviation": "gaze_deviation",
                                    }
                                    violation_type = event_type_map.get(event, event)

                                    # For keystroke events, run typing cadence analysis first
                                    if event == "keystroke":
                                        timestamps = payload.get("timestamps", [])
                                        if len(timestamps) >= 2:
                                            # Use session baseline (simplified: use overall mean/std from timestamps)
                                            # The proctor_service.analyze_typing_cadence handles the detection
                                            await proctor_service.analyze_typing_cadence(
                                                keystroke_timestamps=timestamps,
                                                baseline_mean=0.15,  # default baseline ~150ms between keystrokes
                                                baseline_std=0.05,   # default std
                                                db=db,
                                                session_id=db_session_id,
                                                consent_granted=consent_granted,
                                            )
                                    else:
                                        await proctor_service.handle_browser_event(
                                            session_id=db_session_id,
                                            event_type=violation_type,
                                            payload=event_payload,
                                            session_status=session_status,
                                            consent_granted=consent_granted,
                                            db=db,
                                        )
                        continue
                    # ── Phase 1A: HR closes interview smoothly ──────────────────
                    elif payload.get("type") == "hr_close_interview":
                        # HR triggered smooth closing — transition to closing phase
                        closing_msg = payload.get("data", {}).get("message", "")
                        if closing_msg:
                            await manager.send_json({
                                "type": "status",
                                "data": closing_msg,
                            }, session_id)
                        # Mark interview complete with advisor action
                        await interview_graph_module.interview_graph.aupdate_state(config, {
                            "interview_complete": True,
                            "completion_reason": "Interviewer closed the interview",
                            "advisor_action_taken": True,
                        })
                        await manager.send_json({"type": "status", "data": "Interview closing..."}, session_id)
                        continue  # Skip normal processing, next loop will see interview_complete

                    # ── Phase 1B: AI Supervisor Control Messages ──────────────
                    elif payload.get("type") == "supervisor_control":
                        control = payload.get("data", {})
                        action = control.get("action", "")

                        if action == "override_difficulty":
                            new_diff = control.get("difficulty", "medium")
                            await interview_graph_module.interview_graph.aupdate_state(config, {
                                "difficulty": new_diff,
                                "supervisor_observations": [{
                                    "type": "manual_override",
                                    "subtype": "difficulty_overridden",
                                    "severity": "info",
                                    "message": f"Difficulty manually set to {new_diff}",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }],
                            })
                            await manager.send_json({"type": "status", "data": f"Difficulty set to {new_diff}"}, session_id)

                        elif action == "override_phase":
                            new_phase = control.get("phase", "technical")
                            await interview_graph_module.interview_graph.aupdate_state(config, {
                                "current_phase": new_phase,
                                "phase_transition": True,
                                "previous_phase": None,
                                "supervisor_observations": [{
                                    "type": "manual_override",
                                    "subtype": "phase_overridden",
                                    "severity": "info",
                                    "message": f"Phase manually set to {new_phase}",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }],
                            })
                            await manager.send_json({"type": "status", "data": f"Phase set to {new_phase}"}, session_id)

                        elif action == "set_control_mode":
                            mode = control.get("mode", "suggest")
                            await interview_graph_module.interview_graph.aupdate_state(config, {
                                "supervisor_mode": mode,
                                "supervisor_observations": [{
                                    "type": "control_mode_change",
                                    "severity": "info",
                                    "message": f"Supervisor mode set to {mode}",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }],
                            })
                            supervisor_registry.set_control_mode(str(db_session_id or session_id), mode)
                            await manager.send_json({"type": "supervisor_mode", "mode": mode}, session_id)
                            await manager.send_json({"type": "status", "data": f"Supervisor mode: {mode}"}, session_id)

                        elif action == "force_close":
                            await interview_graph_module.interview_graph.aupdate_state(config, {
                                "interview_complete": True,
                                "completion_reason": "Supervisor/admin force-closed the interview",
                                "advisor_action_taken": True,
                            })
                            supervisor_registry.record_observation(
                                str(db_session_id or session_id),
                                SupervisorObservation(
                                    observation_type="force_close",
                                    severity="critical",
                                    message="Supervisor force-closed the interview",
                                )
                            )
                            await manager.send_json({"type": "status", "data": "Interview force-closed by supervisor."}, session_id)

                        continue

                    elif payload.get("type") == "hr_whisper":
                        whisper_text = payload.get("data", "")
                        await interview_graph_module.interview_graph.aupdate_state(config, {"hr_whisper_instructions": whisper_text})
                        await manager.send_json({"type": "status", "data": "Whisper queued for next turn."}, session_id)
                        continue

                    elif payload.get("type") == "copilot_request":
                        current_code = payload.get("data", "")
                        await manager.send_json({"type": "status", "data": "Co-Pilot: Analyzing your workspace..."}, session_id)
                        await interview_graph_module.interview_graph.aupdate_state(config, {
                            "copilot_request_pending": True,
                            "code_snippet": current_code
                        })
                        async for chunk in interview_graph_module.interview_graph.astream(None, config=config, stream_mode="updates"):
                            for node_name, output in chunk.items():
                                if node_name == "code_copilot" and output.get("copilot_suggestions"):
                                    await manager.send_json({
                                        "type": "copilot_update",
                                        "data": output["copilot_suggestions"][-1]
                                    }, session_id)
                        continue
                except (json.JSONDecodeError, ValueError) as e:
                    await manager.send_json({"type": "error", "data": "Invalid message format. Send valid JSON."}, session_id)
                    logger.warning(f"Invalid JSON from session {session_id}: {e}")
                    continue

            elif "bytes" in message:
                await manager.send_json({"type": "status", "data": "Voice Engine: Transcribing..."}, session_id)
                user_answer = await voice_service.transcribe_audio(message["bytes"])
                if not user_answer:
                    await manager.send_json({"type": "error", "data": "Could not understand audio. Please try again."}, session_id)
                    continue
                current_state = await interview_graph_module.interview_graph.aget_state(config)
                current_values = current_state.values if current_state else {}
                response_decision = decide_response({"type": "answer", "data": user_answer}, current_values)
                if not response_decision.accepted:
                    await manager.send_json({
                        "type": "response_rejected",
                        "data": response_notice(response_decision),
                    }, session_id)
                    continue
                user_answer = response_decision.content
                await manager.send_json({
                    "type": "response_ack",
                    "data": response_notice(response_decision),
                }, session_id)
                await manager.send_json({"type": "status", "data": f'Understood: "{user_answer}"'}, session_id)

            if user_answer or user_code:
                try:
                    # Run proctoring typing cadence check if we have a text answer
                    if user_answer and db_session_id:
                        if not typing_duration:
                            try:
                                q_start = current_values.get("question_start_epoch")
                                if q_start:
                                    typing_duration = time.time() - q_start
                            except Exception as state_err:
                                logger.warning(f"Failed to fetch state for typing cadence: {state_err}")
                        
                        if typing_duration and typing_duration > 0:
                            from app.services.proctor_service import proctor_service
                            async with async_session() as db:
                                await proctor_service.analyze_typing_cadence(
                                    session_id=db_session_id,
                                    text=user_answer,
                                    duration_seconds=typing_duration,
                                    db=db
                                )

                    # Query RAG context under a short optional budget. The
                    # answer itself remains usable when retrieval is slow.
                    rag_context = ""
                    rag_started = time_module.perf_counter()
                    if db_session_id:
                        try:
                            query_str = user_answer if user_answer else user_code
                            async with asyncio.timeout(float(getattr(settings, "INTERVIEW_RAG_TIMEOUT_SECONDS", 0.8))):
                                rag_context = await asyncio.to_thread(
                                    rag_service.query_context,
                                    session_id=str(db_session_id),
                                    query=query_str[:300]
                                )
                        except Exception as e:
                            logger.debug(f"RAG context skipped: {e}")
                    turn_probe.mark("rag_context", rag_started)
                    if not rag_context:
                        rag_context = rag_seed_context[:2500] if rag_seed_context else ""

                    state_values = current_values if isinstance(current_values, dict) else {}
                    turn_seed = {
                        "current_question_index": state_values.get("current_question_index", 0),
                        "total_responses": state_values.get("total_responses", 0),
                        "messages": state_values.get("messages", []),
                    }
                    turn_id = build_turn_id(turn_seed)
                    coordination_state = {**turn_seed, "turn_id": turn_id, "coordination_round_id": f"{turn_id}:debate"}
                    turn_update = {
                        **response_state_update(response_decision),
                        "turn_id": turn_id,
                        "coordination_round_id": f"{turn_id}:debate",
                        "last_candidate_answer": user_answer or "[Code Submitted]",
                        "coordination_trace": [
                            coordination_event(
                                agent="orchestrator",
                                event="candidate_turn_started",
                                state=coordination_state,
                                details={"has_code": bool(user_code), "has_text": bool(user_answer)},
                            )
                        ],
                    }
                    update = (
                        {**turn_update, "code_snippet": user_code, "messages": [{"role": "user", "content": "[Code Submitted]"}, {"role": "system", "content": "[Evaluation debate in progress...]"}], "rag_context": rag_context}
                        if user_code
                        else {**turn_update, "messages": [{"role": "user", "content": user_answer}], "rag_context": rag_context}
                    )

                    # Execute code via Judge0 before AI evaluation
                    if user_code:
                        code_started = time_module.perf_counter()
                        await manager.send_json({"type": "status", "data": "Judge0: Executing code..."}, session_id)
                        
                        # Audit #17: Fetch current state to get correct code_language
                        current_lang = state_values.get("code_language") or "python"
                        
                        exec_result = await code_execution_service.execute(
                            source_code=user_code,
                            language=current_lang,
                        )
                        await manager.send_json({"type": "execution_result", "data": exec_result}, session_id)
                        # Enrich the code snippet with execution output for AI evaluation
                        enriched_content = (
                            f"[Code Submitted]\n"
                            f"Status: {exec_result['status']}\n"
                            f"Output: {exec_result['stdout'][:500]}\n"
                            f"Errors: {exec_result['stderr'][:300]}"
                        )
                        update = {**turn_update, "code_snippet": user_code, "last_candidate_answer": enriched_content, "messages": [{"role": "user", "content": enriched_content}], "rag_context": rag_context}
                        turn_probe.mark("code_execution", code_started)
                    graph_started = time_module.perf_counter()
                    await interview_graph_module.interview_graph.aupdate_state(config, update)

                    graph_chunks = await asyncio.wait_for(
                        _collect_graph_updates(interview_graph_module.interview_graph, config),
                        timeout=float(getattr(settings, "INTERVIEW_TURN_TIMEOUT_SECONDS", 20.0)),
                    )
                    for chunk in graph_chunks:
                        for node_name, output in chunk.items():
                            if output.get("coordination_trace"):
                                await manager.send_json({
                                    "type": "agent_coordination_update",
                                    "data": {
                                        "node": node_name,
                                        "events": output["coordination_trace"],
                                        "round": output.get("debate_rounds"),
                                    },
                                }, session_id)
                            if node_name in ("evaluate_answer", "evaluate_code", "consensus_synthesizer"):
                                await manager.send_json({"type": "status", "data": "AI: Evaluating response..."}, session_id)
                                if output.get("metrics"):
                                    await manager.send_json({"type": "metrics_update", "data": output["metrics"]}, session_id)
                            elif node_name == "supervisor" and output.get("supervisor_observations"):
                                # Forward supervisor observations to the client
                                obs = output.get("_supervisor_summary") or {}
                                await manager.send_json({
                                    "type": "supervisor_update",
                                    "data": {
                                        "observations": output["supervisor_observations"],
                                        "summary": obs,
                                        "last_action": output.get("supervisor_last_action"),
                                    }
                                }, session_id)
                            elif node_name == "generate_question" and output.get("next_question"):
                                q = output["next_question"]
                                all_questions.append(q)

                                await interview_graph_module.interview_graph.aupdate_state(config, {
                                    "active_question_id": str(q.get("id")) if isinstance(q, dict) and q.get("id") is not None else None,
                                    "awaiting_candidate_response": True,
                                })
                                await _deliver_question(
                                    session_id=session_id,
                                    question=q,
                                    job_role=job_role,
                                    is_coding=output.get("is_coding_mode", False),
                                    language=output.get("code_language", "python"),
                                )

                    turn_probe.mark("graph_execution", graph_started)
                    final_state = await interview_graph_module.interview_graph.aget_state(config)
                    precision_flags = []
                    final_values = final_state.values if final_state else {}
                    if not rag_context:
                        precision_flags.append("rag_context_unavailable")
                    evaluation = final_values.get("last_evaluation") if isinstance(final_values, dict) else None
                    if isinstance(evaluation, dict):
                        confidence = evaluation.get("confidence")
                        if confidence is not None and float(confidence) < 0.55:
                            precision_flags.append("low_confidence_evaluation")
                        if not evaluation.get("evidence"):
                            precision_flags.append("evaluation_without_evidence")
                    timing_snapshot = turn_probe.snapshot()
                    await interview_graph_module.interview_graph.aupdate_state(config, {
                        "turn_timing": timing_snapshot,
                        "precision_flags": precision_flags,
                        "response_degraded": bool(precision_flags),
                    })
                    await manager.send_json({
                        "type": "turn_timing",
                        "data": {**timing_snapshot, "precision_flags": precision_flags},
                    }, session_id)
                    final_state = await interview_graph_module.interview_graph.aget_state(config)
                    if final_state and final_state.values:
                        await manager.broadcast_to_hr({
                            "type": "state_sync",
                            "data": {
                                "messages": final_state.values.get("messages", []),
                                "empathy_metrics": final_state.values.get("empathy_metrics", {}),
                                "copilot_suggestions": final_state.values.get("copilot_suggestions", []),
                                "debate_rounds": final_state.values.get("debate_rounds", {}),
                                "topic_scores": final_state.values.get("topic_scores", {}),
                                "current_question": final_state.values.get("messages", [])[-1]["content"] if final_state.values.get("messages") else "",
                                "supervisor_mode": final_state.values.get("supervisor_mode", "suggest"),
                                "coordination_round": final_state.values.get("debate_rounds"),
                                "coordination_trace": (final_state.values.get("coordination_trace", []) or [])[-20:],
                                "turn_timing": final_state.values.get("turn_timing", {}),
                                "precision_flags": final_state.values.get("precision_flags", []),
                                "response_degraded": final_state.values.get("response_degraded", False),
                            }
                        }, session_id)

                    # ── Phase 1A: Advisor Notification ──────────────────────────────
                    # If advisor suggests closing, notify HR and persist to DB
                    if (final_state.values.get("advisor_ready_to_close")
                            and not final_state.values.get("advisor_action_taken")):
                        # Persist advisor suggestion to DB for HR dashboard polling
                        if db_session_id:
                            try:
                                async with async_session() as db:
                                    res = await db.execute(select(InterviewSession).where(InterviewSession.id == db_session_id))
                                    rec = res.scalars().first()
                                    if rec and not rec.advisor_ready_to_close:
                                        rec.advisor_ready_to_close = True
                                        rec.advisor_confidence = final_state.values.get("advisor_confidence")
                                        rec.advisor_reason = final_state.values.get("advisor_reason")
                                        rec.advisor_reason_category = final_state.values.get("advisor_reason_category")
                                        rec.advisor_suggested_at = datetime.now(timezone.utc)
                                        db.add(rec)
                                        await db.commit()
                            except Exception as db_err:
                                logger.warning(f"Failed to persist advisor state: {db_err}")

                        await manager.send_json({
                            "type": "advisor_suggestion",
                            "data": {
                                "ready_to_close": True,
                                "confidence": final_state.values.get("advisor_confidence"),
                                "reason": final_state.values.get("advisor_reason"),
                                "reason_category": final_state.values.get("advisor_reason_category"),
                                "recommended_closing_message": final_state.values.get("advisor_reason"),
                            }
                        }, session_id)

                    if final_state.values.get("interview_complete"):
                        await manager.send_json({"type": "status", "data": "Assessment complete. Generating report..."}, session_id)

                        final_history = final_state.values.get("messages", [])
                        report = await evaluation_service.generate_final_report(
                            job_role,
                            final_history,
                            evaluation_history=final_state.values.get("evaluation_history", []),
                        )
                        report_dict = report.model_dump()

                        # Persist session (#5 duration, #18 questions)
                        if db_session_id:
                            end_time = datetime.now(timezone.utc)
                            duration_secs = int((end_time - session_start).total_seconds())
                            async with async_session() as db:
                                res = await db.execute(select(InterviewSession).where(InterviewSession.id == db_session_id))
                                rec = res.scalars().first()
                                if rec:
                                    rec.status = "completed"
                                    rec.end_time = end_time
                                    rec.duration = duration_secs
                                    rec.questions = all_questions          # native JSON
                                    rec.responses = final_history          # native JSON
                                    rec.ai_feedback = report_dict          # native JSON
                                    rec.overall_score = report.overall_score
                                    rec.skill_matrix = final_state.values.get("topic_scores") # #19: persist scores
                                    # Phase 1A: Persist advisor fields
                                    if final_state.values.get("advisor_ready_to_close"):
                                        rec.advisor_ready_to_close = True
                                        rec.advisor_confidence = final_state.values.get("advisor_confidence")
                                        rec.advisor_reason = final_state.values.get("advisor_reason")
                                        rec.advisor_reason_category = final_state.values.get("advisor_reason_category")
                                        rec.advisor_suggested_at = datetime.now(timezone.utc)
                                        rec.advisor_action_taken = final_state.values.get("advisor_action_taken", False)
                                    db.add(rec)
                                    await _advance_ordered_ai_stage(db, rec, report_dict)
                                    await db.commit()

                            # Finalize proctor session: attach all ViolationRecords to evidence_log
                            try:
                                from app.services.proctor_service import proctor_service
                                async with async_session() as db:
                                    await proctor_service.finalize_session(session_id=db_session_id, db=db)
                            except Exception as proctor_err:
                                logger.warning(f"Proctor finalize_session failed for {db_session_id}: {proctor_err}")

                            # Trigger Coaching Agent: generate coaching plan as background task
                            try:
                                from app.services.coaching_service import coaching_service

                                coaching_session_id = db_session_id
                                coaching_evaluation_report = report_dict
                                coaching_skill_matrix = final_state.values.get("topic_scores", {})

                                if coaching_skill_matrix:
                                    async def _coaching_task():
                                        try:
                                            async with async_session() as coaching_db:
                                                # Resolve candidate_id from the session record
                                                sess_res = await coaching_db.execute(
                                                    select(InterviewSession).where(InterviewSession.id == coaching_session_id)
                                                )
                                                sess_rec = sess_res.scalars().first()
                                                if not sess_rec:
                                                    return

                                                plan = await coaching_service.generate_coaching_plan(
                                                    session_id=coaching_session_id,
                                                    candidate_id=sess_rec.candidate_id,
                                                    evaluation_report=coaching_evaluation_report,
                                                    skill_matrix=coaching_skill_matrix,
                                                    db=coaching_db,
                                                )
                                                # Send notification if candidate email is available
                                                if candidate_email and plan:
                                                    await coaching_service.send_coaching_notification(
                                                        candidate_email=candidate_email,
                                                        coaching_plan=plan,
                                                        db=coaching_db,
                                                    )
                                        except Exception as coaching_err:
                                            logger.error(f"Coaching plan generation failed for session {coaching_session_id}: {coaching_err}")

                                    asyncio.create_task(_coaching_task())
                            except Exception as coaching_trigger_err:
                                logger.warning(f"Failed to trigger coaching plan generation for {db_session_id}: {coaching_trigger_err}")

                            # Trigger Matching Engine: compute match score as background task
                            try:
                                from app.services.matching_service import matching_service

                                matching_session_id = db_session_id

                                async def _matching_task():
                                    try:
                                        async with async_session() as matching_db:
                                            await matching_service.compute_match_score(
                                                session_id=matching_session_id,
                                                db=matching_db,
                                            )
                                    except Exception as matching_err:
                                        logger.error(f"Match score computation failed for session {matching_session_id}: {matching_err}")

                                asyncio.create_task(_matching_task())
                            except Exception as matching_trigger_err:
                                logger.warning(f"Failed to trigger match score computation for {db_session_id}: {matching_trigger_err}")

                            # Trigger Orchestrator: transition workflow state to "evaluated"
                            try:
                                from app.services.orchestrator_service import OrchestratorService

                                orchestrator_session_id = db_session_id

                                async def _orchestrator_task():
                                    try:
                                        async with async_session() as orch_db:
                                            # Resolve candidate_id and job_drive_id from the session
                                            sess_res = await orch_db.execute(
                                                select(InterviewSession).where(InterviewSession.id == orchestrator_session_id)
                                            )
                                            sess_rec = sess_res.scalars().first()
                                            if not sess_rec or not sess_rec.job_drive_id:
                                                return

                                            orchestrator = OrchestratorService()
                                            await orchestrator.transition(
                                                candidate_id=sess_rec.candidate_id,
                                                job_drive_id=sess_rec.job_drive_id,
                                                trigger="complete",
                                                db=orch_db,
                                            )
                                    except Exception as orch_err:
                                        logger.warning(f"Orchestrator transition failed for session {orchestrator_session_id}: {orch_err}")

                                asyncio.create_task(_orchestrator_task())
                            except Exception as orch_trigger_err:
                                logger.warning(f"Failed to trigger orchestrator transition for {db_session_id}: {orch_trigger_err}")

                        await manager.send_json({
                            "type": "complete",
                            "report": report_dict,
                            "session_id": db_session_id,
                            # Phase 1A: Include advisor metadata
                            "termination_reason": final_state.values.get("completion_reason"),
                            "termination_category": final_state.values.get("advisor_reason_category"),
                            "assessment_confidence": final_state.values.get("advisor_confidence"),
                        }, session_id)

                        if candidate_email:
                            asyncio.create_task(send_report_to_candidate(candidate_email, candidate_name or "Candidate", job_role, report_dict))
                        if hr_email:
                            asyncio.create_task(send_report_to_hr(hr_email, hr_name or "HR", candidate_email or "Guest", job_role, drive_title or job_role, report_dict, str(db_session_id)))
                        break

                except Exception as e:
                    logger.error(f"Processing error [{session_id}]: {e}")
                    traceback.print_exc()
                    await manager.send_json({"type": "error", "data": "An error occurred while processing your response."}, session_id)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket fatal error [{session_id}]: {e}")
        traceback.print_exc()
        try:
            await manager.send_json({"type": "error", "data": "Internal server error during interview session."}, session_id)
        except Exception:
            pass
    finally:
        manager.disconnect(session_id)
        session_cleanup.remove_session(session_id)
        if db_session_id:
            try:
                async with async_session() as db:
                    res = await db.execute(select(InterviewSession).where(InterviewSession.id == db_session_id))
                    rec = res.scalars().first()
                    if rec and rec.status == "in_progress":
                        rec.status = "completed"
                        rec.end_time = datetime.now(timezone.utc)
                        if rec.start_time:
                            rec.duration = int((rec.end_time - rec.start_time.replace(tzinfo=timezone.utc)).total_seconds())
                        
                        # Try to capture whatever responses were made before disconnect
                        try:
                            final_state = await interview_graph_module.interview_graph.aget_state(config)
                            if final_state and final_state.values:
                                rec.responses = final_state.values.get("messages", [])
                                rec.skill_matrix = final_state.values.get("topic_scores", {})
                        except Exception:
                            pass
                        
                        db.add(rec)
                        await db.commit()

                        # Finalize proctor session on disconnect-completion
                        try:
                            from app.services.proctor_service import proctor_service
                            async with async_session() as proctor_db:
                                await proctor_service.finalize_session(session_id=db_session_id, db=proctor_db)
                        except Exception as proctor_err:
                            logger.warning(f"Proctor finalize_session failed on disconnect for {db_session_id}: {proctor_err}")
            except Exception as e:
                logger.error(f"Failed to finalize session {db_session_id} on disconnect: {e}")


# ── HR Live Instruction Injection (audit #14: requires HR auth) ──────────────
@router.post("/sessions/{session_id}/hr-instruction")
@limiter.limit("20/minute")
async def send_hr_instruction(
    request: Request,
    session_id: str,
    instruction: Dict[str, str],
    current_hr: User = Depends(deps.get_current_hr),  # #14: auth required
):
    config = {"configurable": {"thread_id": session_id}}
    await interview_graph_module.interview_graph.aupdate_state(config, {
        "hr_instructions": instruction.get("text", ""),
        "hr_whisper_instructions": instruction.get("text", "")
    })
    return {"status": "ok", "message": "Instruction queued for next AI turn."}


# ── Observability: Session Explanation ────────────────────────────────────────

from app.services.observability_service import ObservabilityService


@router.get("/{session_id}/explanation", response_model=List[TraceEntryRead])
async def get_session_explanation(
    session_id: int,
    score_type: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve human-readable Trace_Entries explaining a score or decision for a session.

    Accessible by HR users (who manage the drive), Admins, and the Candidate who owns the session.
    Sensitive fields (raw_input, raw_output) are redacted for non-Admin callers.

    Query params:
        score_type: Optional action_type filter (e.g. "bias_check", "evaluation").
                    If omitted, returns all trace entries for the session.

    Requirements: 10.7
    """
    # 1. Fetch the interview session to verify access permissions
    stmt = select(InterviewSession).where(InterviewSession.id == session_id)
    res = await db.execute(stmt)
    session_record = res.scalars().first()
    if not session_record:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # 2. Role-Based Access Control
    if current_user.user_type == "admin":
        pass  # Admin has full access
    elif current_user.user_type == "student":
        # Candidate can only see their own sessions
        if session_record.candidate_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied. You do not own this session.")
    elif current_user.user_type == "hr":
        # HR can only see sessions associated with a drive they manage
        drive_res = await db.execute(
            select(JobDrive).join(HRProfile).where(
                JobDrive.id == session_record.job_drive_id,
                HRProfile.user_id == current_user.id
            )
        )
        if not drive_res.scalars().first():
            raise HTTPException(status_code=403, detail="Access denied. You do not manage this session.")
    else:
        raise HTTPException(status_code=403, detail="Role not authorized to access explanations.")

    # 3. Query the observability service
    obs_service = ObservabilityService(db)

    if score_type:
        entries = await obs_service.get_explanation(
            session_id=session_id,
            score_type=score_type,
        )
    else:
        entries = await obs_service.query(session_id=session_id, requester_role="hr")

    return entries


@router.get("/{session_id}/report/pdf")
async def download_interview_report_pdf(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> StreamingResponse:
    """
    Download a high-fidelity PDF report of the candidate evaluation.
    Only accessible by the candidate who owns the session, management HR, or an administrator.
    """
    from fastapi.responses import StreamingResponse
    import io
    from app.services.pdf_service import generate_interview_pdf
    from app.core.metrics import pdf_generated_total

    # 1. Fetch the interview session and candidate
    stmt = (
        select(InterviewSession, User)
        .join(User, InterviewSession.candidate_id == User.id)
        .where(InterviewSession.id == session_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Interview session not found")

    session_record, candidate = row

    # 2. Access Control
    if current_user.user_type == "admin":
        pass
    elif current_user.user_type == "student":
        if session_record.candidate_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied. You do not own this session.")
    elif current_user.user_type == "hr":
        if not session_record.job_drive_id:
            raise HTTPException(status_code=403, detail="Access denied. You do not manage this practice session.")
        drive_res = await db.execute(
            select(JobDrive).join(HRProfile).where(
                JobDrive.id == session_record.job_drive_id,
                HRProfile.user_id == current_user.id
            )
        )
        if not drive_res.scalars().first():
            raise HTTPException(status_code=403, detail="Access denied. You do not manage this session.")
    else:
        raise HTTPException(status_code=403, detail="Role not authorized to access this report.")

    # 3. Check if evaluation is complete
    if session_record.status != "completed" or session_record.overall_score is None or not session_record.ai_feedback:
        raise HTTPException(status_code=404, detail="Evaluation is incomplete or report is not ready yet.")

    # 4. Resolve job role
    job_role = "Practice Candidate"
    if session_record.job_drive_id:
        drive_res = await db.execute(select(JobDrive).where(JobDrive.id == session_record.job_drive_id))
        drive = drive_res.scalars().first()
        if drive:
            job_role = drive.job_role

    # 5. Generate PDF
    pdf_bytes = await asyncio.to_thread(
        generate_interview_pdf,
        candidate_name=f"{candidate.first_name} {candidate.last_name}",
        job_role=job_role,
        report=session_record.ai_feedback,
        transcript=session_record.responses or [],
        skill_matrix=session_record.skill_matrix
    )

    # 6. Increment PDF generated total counter
    pdf_generated_total.inc()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Vedrix_Report_{session_id}.pdf"
        }
    )


@router.post("/schedule", response_model=BookingRead)
async def schedule_interview_slot(
    payload: BookingCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Allow a candidate to book a specific interview slot.
    Enforces capacity checks and double-booking prevention.
    """
    from fastapi import status

    if current_user.user_type != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can book interview slots."
        )

    sched_service = SchedulingService(db)
    booking = await sched_service.book_slot(
        candidate_id=current_user.id,
        slot_id=payload.slot_id
    )
    return booking


# ── Video Interview WebRTC Signaling ─────────────────────────────────────────
class VideoRoomManager:
    """Manages WebRTC video connections for live interviews."""
    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}  # room_id -> {candidate: ws, hr: ws}
    
    async def join_room(self, room_id: str, role: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][role] = websocket
    
    def leave_room(self, room_id: str, role: str):
        if room_id in self.rooms:
            self.rooms[room_id].pop(role, None)
            if not self.rooms[room_id]:
                self.rooms.pop(room_id, None)
    
    async def broadcast(self, room_id: str, message: Dict[str, Any], exclude: str = None):
        if room_id in self.rooms:
            for role, ws in self.rooms[room_id].items():
                if role != exclude:
                    try:
                        await ws.send_json(message)
                    except Exception:
                        pass

video_manager = VideoRoomManager()


@router.websocket("/video/{room_id}")
async def video_websocket(
    websocket: WebSocket,
    room_id: str,
    role: str = "candidate",  # "candidate" or "hr"
    token: Optional[str] = None,
):
    """WebRTC signaling endpoint for video interviews."""
    await video_manager.join_room(room_id, role, websocket)
    
    try:
        # Notify others in room about new participant
        await video_manager.broadcast(room_id, {
            "type": "peer_joined",
            "role": role
        }, exclude=role)
        
        # Handle signaling messages
        while True:
            message = await websocket.receive()
            
            if message.get("type") == "websocket.disconnect":
                break
            
            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type")
                    
                    # Forward signaling messages to other participant
                    if msg_type in ("offer", "answer", "ice_candidate"):
                        await video_manager.broadcast(room_id, payload, exclude=role)
                    
                    elif msg_type == "toggle_video":
                        await video_manager.broadcast(room_id, {
                            "type": "peer_video_toggled",
                            "role": role,
                            "enabled": payload.get("enabled", True)
                        }, exclude=role)
                    
                    elif msg_type == "toggle_audio":
                        await video_manager.broadcast(room_id, {
                            "type": "peer_audio_toggled",
                            "role": role,
                            "enabled": payload.get("enabled", True)
                        }, exclude=role)
                        
                except (json.JSONDecodeError, ValueError):
                    pass
                    
    except Exception as e:
        logger.error(f"Video room error [{room_id}]: {e}")
    finally:
        video_manager.leave_room(room_id, role)
        await video_manager.broadcast(room_id, {"type": "peer_left", "role": role})


@router.websocket("/ws/{session_id}/hr")
async def hr_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None,
):
    """Real-time monitoring and takeover endpoint for HR."""
    cookie_token = websocket.cookies.get("access_token")
    auth_token = token or cookie_token

    if not auth_token:
        await websocket.accept()
        await websocket.send_json({"type": "error", "data": "Authentication token missing."})
        await websocket.close()
        return

    user_id = _verify_ws_token(auth_token)
    if not user_id:
        await websocket.accept()
        await websocket.send_json({"type": "error", "data": "Invalid token."})
        await websocket.close()
        return

    async with async_session() as db:
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalars().first()
        if not user or user.user_type not in ("hr", "admin"):
            await websocket.accept()
            await websocket.send_json({"type": "error", "data": "Access denied. HR/Admin role required."})
            await websocket.close()
            return

    await manager.connect(websocket, session_id, is_hr=True)
    logger.info(f"HR user {user.email} connected to session {session_id}")

    config = {"configurable": {"thread_id": session_id}}

    try:
        # Send initial state sync to HR observer
        try:
            state = await interview_graph_module.interview_graph.aget_state(config)
            if state and state.values:
                await websocket.send_json({
                    "type": "state_sync",
                    "data": {
                        "messages": state.values.get("messages", []),
                        "empathy_metrics": state.values.get("empathy_metrics", {}),
                        "copilot_suggestions": state.values.get("copilot_suggestions", []),
                        "debate_rounds": state.values.get("debate_rounds", {}),
                        "coordination_trace": (state.values.get("coordination_trace", []) or [])[-20:],
                        "topic_scores": state.values.get("topic_scores", {}),
                        "current_question": state.values.get("messages", [])[-1]["content"] if state.values.get("messages") else "",
                        "supervisor_mode": state.values.get("supervisor_mode", "suggest"),
                    }
                })
        except Exception as e:
            logger.warning(f"Failed to sync state for HR: {e}")

        # Listen for whisper / control updates from HR
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if payload.get("type") == "hr_whisper":
                    whisper_text = payload.get("data", "")
                    await interview_graph_module.interview_graph.aupdate_state(config, {
                        "hr_instructions": whisper_text,
                        "hr_whisper_instructions": whisper_text
                    })
                    await websocket.send_json({"type": "status", "data": "Whisper queued for next turn."})
                elif payload.get("type") == "supervisor_control":
                    action = payload.get("action")
                    if action == "set_mode":
                        mode = payload.get("mode")
                        await interview_graph_module.interview_graph.aupdate_state(config, {
                            "supervisor_mode": mode,
                            "supervisor_observations": [{
                                "type": "control_mode_change",
                                "severity": "info",
                                "message": f"HR set mode to {mode}",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }]
                        })
                        supervisor_registry.set_control_mode(session_id, mode)
                        await websocket.send_json({"type": "status", "data": f"Control mode set to: {mode}"})
                        await manager.send_json({"type": "supervisor_mode", "mode": mode}, session_id)
                        await manager.send_json({"type": "status", "data": f"Supervisor mode: {mode}"}, session_id)
                    elif action == "force_close":
                        await interview_graph_module.interview_graph.aupdate_state(config, {
                            "interview_complete": True,
                            "completion_reason": "HR force-closed the interview",
                            "advisor_action_taken": True,
                        })
                        supervisor_registry.record_observation(
                            session_id,
                            SupervisorObservation(
                                observation_type="force_close",
                                severity="critical",
                                message="HR force-closed the interview",
                            )
                        )
                        await websocket.send_json({"type": "status", "data": "Interview force-closed."})
                        await manager.send_json({"type": "status", "data": "Interview force-closed by supervisor."}, session_id)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": "Invalid JSON payload."})
            except Exception as e:
                logger.warning(f"Error handling HR payload: {e}")
                await websocket.send_json({"type": "error", "data": str(e)})

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket=websocket, is_hr=True)
        logger.info(f"HR user {user.email} disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"Error in HR WebSocket connection: {e}")
        manager.disconnect(session_id, websocket=websocket, is_hr=True)
