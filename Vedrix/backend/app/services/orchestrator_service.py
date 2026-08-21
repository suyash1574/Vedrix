"""
OrchestratorService — Agentic Notification and Workflow Orchestration.

Design: Orchestrator (Section 8 of design.md)
Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.10, 8.11

Key guarantees
--------------
* State machine: WORKFLOW_TRANSITIONS defines all valid (state, trigger) → new_state.
* "decided" is terminal — no transitions without explicit Admin override.
* Every transition is logged as a Trace_Entry.
* SELECT FOR UPDATE row lock prevents concurrent state corruption.
* bulk_transition() applies independently to each candidate.
* run_scheduled_checks(): 48h invite reminder, 24h pre-interview reminder,
  escalate stale "evaluated" after 5 business days, retry up to 3× exponential backoff.
* All async methods decorated with @trace_agent_action("orchestrator", ...).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_workflow import CandidateWorkflow
from app.models.hiring_workflow import WorkflowAuditEvent
from app.models.interview import InterviewSession, JobDrive
from app.models.trace_entry import TraceEntryCreate
from app.models.user import User
from app.services.observability_service import ObservabilityService, trace_agent_action

logger = logging.getLogger(__name__)


# ── State Machine Definition ──────────────────────────────────────────────────

WORKFLOW_TRANSITIONS: Dict[str, Dict[str, str]] = {
    # Legacy invite path remains valid for existing drives.
    "invited": {
        "apply": "screening",
        "schedule": "scheduled",
        "withdraw": "decided",
    },
    "screening": {
        "assign_assessment": "assessment_assigned",
        "skip_assessment": "interview_scheduled",
        "manual_interview": "manual_interview",
        "reject": "decided",
        "withdraw": "decided",
    },
    "assessment_assigned": {
        "start": "assessment_in_progress",
        "skip": "interview_scheduled",
        "cancel": "screening",
        "withdraw": "decided",
    },
    "assessment_in_progress": {
        "complete": "assessment_review",
        "abandon": "assessment_assigned",
    },
    "assessment_review": {
        "pass": "interview_scheduled",  # legacy compatibility
        "pass_to_ai": "ai_interview_scheduled",
        "flag_cheat": "cheat_review",
        "retake": "assessment_assigned",
        "manual_interview": "manual_interview",
        "reject": "decided",
    },
    "cheat_review": {
        "clear": "interview_scheduled",  # legacy compatibility
        "clear_to_ai": "ai_interview_scheduled",
        "confirm_cheat": "decided",
        "retake": "assessment_assigned",
        "manual_interview": "manual_interview",
    },
    "ai_interview_scheduled": {
        "start": "ai_interview_in_progress",
        "reschedule": "ai_interview_scheduled",
        "cancel": "assessment_review",
        "bypass": "human_interview_scheduled",
        "withdraw": "decided",
    },
    "ai_interview_in_progress": {
        "complete": "ai_interview_review",
        "abandon": "ai_interview_scheduled",
        "takeover": "ai_interview_review",
    },
    "ai_interview_review": {
        "approve_human": "human_interview_scheduled",
        "follow_up": "ai_interview_scheduled",
        "reject": "decided",
        "hold": "ai_interview_review",
        "bypass": "human_interview_scheduled",
    },
    "human_interview_scheduled": {
        "start": "human_interview",
        "reschedule": "human_interview_scheduled",
        "cancel": "ai_interview_review",
        "bypass": "final_review",
        "withdraw": "decided",
    },
    "human_interview": {
        "submit": "final_review",
        "reschedule": "human_interview_scheduled",
        "cancel": "human_interview_scheduled",
        "bypass": "final_review",
    },
    "final_review": {
        "hire": "decided",
        "reject": "decided",
        "withdraw": "decided",
        "hold": "final_review",
    },
    "scheduled": {
        "start": "in_progress",
        "manual_interview": "manual_interview",
        "cancel": "invited",
        "withdraw": "decided",
    },
    "interview_scheduled": {
        "start": "in_progress",
        "manual_interview": "manual_interview",
        "cancel": "screening",
        "withdraw": "decided",
    },
    "in_progress": {
        "complete": "evaluated",
        "manual_entry": "manual_interview",
        "abandon": "invited",
    },
    "manual_interview": {
        "submit": "evaluated",
        "schedule": "interview_scheduled",
        "reject": "decided",
    },
    "evaluated": {
        "shortlist": "shortlisted",
        "manual_interview": "manual_interview",
        "reject": "decided",
    },
    "shortlisted": {"hire": "decided", "reject": "decided"},
    "decided": {},  # terminal — no transitions without Admin override
}


VALID_STATES = set(WORKFLOW_TRANSITIONS.keys())

# ── Reminder / Escalation Configuration ───────────────────────────────────────

INVITE_REMINDER_HOURS = 48
PRE_INTERVIEW_REMINDER_HOURS = 24
STALE_EVALUATED_BUSINESS_DAYS = 5
MAX_NOTIFICATION_RETRIES = 3


# ── Custom Exceptions ─────────────────────────────────────────────────────────

class InvalidTransitionError(Exception):
    """Raised when a trigger is not valid for the current workflow state."""

    def __init__(self, current_state: str, trigger: str):
        self.current_state = current_state
        self.trigger = trigger
        super().__init__(
            f"Invalid transition: trigger '{trigger}' is not valid "
            f"for state '{current_state}'. "
            f"Valid triggers: {list(WORKFLOW_TRANSITIONS.get(current_state, {}).keys())}"
        )


# ── Result Types ──────────────────────────────────────────────────────────────

class WorkflowTransitionResult:
    """Result of a single transition attempt (used in bulk operations)."""

    def __init__(
        self,
        candidate_id: int,
        success: bool,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.candidate_id = candidate_id
        self.success = success
        self.previous_state = previous_state
        self.new_state = new_state
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "success": self.success,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "error": self.error,
        }


# ── OrchestratorService ──────────────────────────────────────────────────────

class OrchestratorService:
    """
    Agentic Notification and Workflow Orchestration Agent.

    Manages CandidateWorkflow state transitions through the recruitment
    pipeline: invited → scheduled → in_progress → evaluated → shortlisted → decided.
    """

    @trace_agent_action("orchestrator", "state_transition")
    async def transition(
        self,
        candidate_id: int,
        job_drive_id: int,
        trigger: str,
        actor_id: Optional[int] = None,
        admin_override: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> CandidateWorkflow:
        """
        Transition a candidate's workflow state.

        Uses SELECT FOR UPDATE row lock to prevent concurrent state corruption.
        Logs every transition as a Trace_Entry. Rejects invalid triggers with
        InvalidTransitionError. "decided" is terminal without Admin override.

        Parameters
        ----------
        candidate_id : The candidate's user ID.
        job_drive_id : The job drive ID.
        trigger : The trigger to apply (e.g. "schedule", "start", "complete").
        actor_id : The user ID of the actor performing the transition.
        admin_override : If True, allows transitions from "decided" state.
        db : AsyncSession for DB operations.

        Returns
        -------
        CandidateWorkflow with updated state.

        Raises
        ------
        InvalidTransitionError : If the trigger is not valid for the current state.
        ValueError : If the workflow record is not found.
        """
        if db is None:
            raise ValueError("Database session (db) is required")

        # SELECT FOR UPDATE — row-level lock to prevent concurrent modifications
        stmt = (
            select(CandidateWorkflow)
            .where(
                CandidateWorkflow.candidate_id == candidate_id,
                CandidateWorkflow.job_drive_id == job_drive_id,
            )
            .with_for_update()
        )
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if workflow is None:
            raise ValueError(
                f"No workflow found for candidate_id={candidate_id}, "
                f"job_drive_id={job_drive_id}"
            )

        current_state = workflow.current_state

        # Terminal state check — "decided" allows no transitions without Admin override
        if current_state == "decided" and not admin_override:
            raise InvalidTransitionError(current_state, trigger)

        # Validate trigger against current state
        valid_triggers = WORKFLOW_TRANSITIONS.get(current_state, {})
        if trigger not in valid_triggers:
            raise InvalidTransitionError(current_state, trigger)

        new_state = valid_triggers[trigger]
        previous_state = current_state

        # Apply transition
        workflow.current_state = new_state
        workflow.updated_at = datetime.now(timezone.utc)

        # Record decision metadata if transitioning to "decided"
        if new_state == "decided":
            if trigger == "hire":
                workflow.decision = "hired"
            elif trigger in ("reject", "withdraw"):
                workflow.decision = "rejected"
            workflow.decided_by = actor_id
            workflow.decided_at = datetime.now(timezone.utc)

        # Append to transition history
        history_entry = {
            "from_state": previous_state,
            "to_state": new_state,
            "trigger": trigger,
            "actor_id": actor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if workflow.transition_history is None:
            workflow.transition_history = []
        workflow.transition_history = [*workflow.transition_history, history_entry]

        # Record an immutable business audit event in addition to the agent trace.
        db.add(WorkflowAuditEvent(
            job_drive_id=job_drive_id,
            candidate_id=candidate_id,
            actor_id=actor_id,
            actor_type="recruiter" if actor_id is not None else "system",
            entity_type="candidate_workflow",
            entity_id=workflow.id,
            action=f"workflow_transition:{trigger}",
            from_state=previous_state,
            to_state=new_state,
            rationale=f"Transition via trigger '{trigger}'",
            payload={"admin_override": admin_override},
        ))

        # Log transition as Trace_Entry
        obs = ObservabilityService(db)
        await obs.record(TraceEntryCreate(
            agent_name="orchestrator",
            action_type="state_transition",
            workflow_id=workflow.id,
            candidate_id=candidate_id,
            input_summary=f"trigger={trigger}, from={previous_state}",
            output_summary=f"new_state={new_state}",
            reasoning_summary=(
                f"Transition {previous_state} → {new_state} via trigger '{trigger}'"
            ),
        ))

        await db.commit()
        await db.refresh(workflow)

        return workflow

    @trace_agent_action("orchestrator", "bulk_state_transition")
    async def bulk_transition(
        self,
        candidate_ids: List[int],
        job_drive_id: int,
        trigger: str,
        actor_id: int,
        db: Optional[AsyncSession] = None,
    ) -> List[WorkflowTransitionResult]:
        """
        Apply a state transition independently to each candidate.

        Each transition is logged as a separate Trace_Entry. Failures for
        individual candidates do not prevent others from transitioning.

        Parameters
        ----------
        candidate_ids : List of candidate user IDs.
        job_drive_id : The job drive ID.
        trigger : The trigger to apply.
        actor_id : The user ID of the actor performing the transitions.
        db : AsyncSession for DB operations.

        Returns
        -------
        List of WorkflowTransitionResult — one per candidate.
        """
        if db is None:
            raise ValueError("Database session (db) is required")

        results: List[WorkflowTransitionResult] = []

        for candidate_id in candidate_ids:
            try:
                workflow = await self.transition(
                    candidate_id=candidate_id,
                    job_drive_id=job_drive_id,
                    trigger=trigger,
                    actor_id=actor_id,
                    db=db,
                )
                results.append(WorkflowTransitionResult(
                    candidate_id=candidate_id,
                    success=True,
                    previous_state=workflow.transition_history[-1]["from_state"]
                    if workflow.transition_history else None,
                    new_state=workflow.current_state,
                ))
            except (InvalidTransitionError, ValueError) as exc:
                results.append(WorkflowTransitionResult(
                    candidate_id=candidate_id,
                    success=False,
                    error=str(exc),
                ))

        return results

    @trace_agent_action("orchestrator", "get_workflow_state")
    async def get_workflow_state(
        self,
        candidate_id: int,
        job_drive_id: int,
        db: Optional[AsyncSession] = None,
    ) -> Optional[CandidateWorkflow]:
        """
        Retrieve the current workflow state for a candidate in a drive.

        Parameters
        ----------
        candidate_id : The candidate's user ID.
        job_drive_id : The job drive ID.
        db : AsyncSession for DB operations.

        Returns
        -------
        CandidateWorkflow or None if not found.
        """
        if db is None:
            raise ValueError("Database session (db) is required")

        stmt = select(CandidateWorkflow).where(
            CandidateWorkflow.candidate_id == candidate_id,
            CandidateWorkflow.job_drive_id == job_drive_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @trace_agent_action("orchestrator", "get_transition_history")
    async def get_transition_history(
        self,
        candidate_id: int,
        job_drive_id: int,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the full transition history for a candidate in a drive.

        Parameters
        ----------
        candidate_id : The candidate's user ID.
        job_drive_id : The job drive ID.
        db : AsyncSession for DB operations.

        Returns
        -------
        List of transition history entries (dicts).
        """
        if db is None:
            raise ValueError("Database session (db) is required")

        workflow = await self.get_workflow_state(candidate_id, job_drive_id, db=db)
        if workflow is None:
            return []
        return workflow.transition_history or []

    @trace_agent_action("orchestrator", "scheduled_checks")
    async def run_scheduled_checks(self, db: Optional[AsyncSession] = None) -> None:
        """
        Run periodic workflow checks. Called by APScheduler every 15 minutes.

        Checks performed:
        1. Send 48h invite reminder for candidates stuck in "invited".
        2. Send 24h pre-interview reminder for candidates in "scheduled".
        3. Escalate stale "evaluated" states after 5 business days.

        Each notification is retried up to 3 times with exponential backoff.

        Parameters
        ----------
        db : AsyncSession for DB operations.
        """
        if db is None:
            raise ValueError("Database session (db) is required")

        now = datetime.now(timezone.utc)

        # 1. 48h invite reminders
        await self._send_invite_reminders(db, now)

        # 2. 24h pre-interview reminders
        await self._send_pre_interview_reminders(db, now)

        # 3. Escalate stale "evaluated"
        await self._escalate_stale_evaluated(db, now)

    # ── Private Helper Methods ────────────────────────────────────────────────

    async def _send_invite_reminders(
        self, db: AsyncSession, now: datetime
    ) -> None:
        """
        Send reminder to candidates who have been in "invited" state for 48+ hours
        without scheduling.
        """
        cutoff = now - timedelta(hours=INVITE_REMINDER_HOURS)

        stmt = select(CandidateWorkflow).where(
            CandidateWorkflow.current_state == "invited",
            CandidateWorkflow.created_at <= cutoff,
        )
        result = await db.execute(stmt)
        workflows = list(result.scalars().all())

        for workflow in workflows:
            # Skip if reminder was already sent recently (within 24h)
            if (
                workflow.last_reminder_sent_at is not None
                and workflow.last_reminder_sent_at > now - timedelta(hours=24)
            ):
                continue

            # Fetch candidate email
            candidate = await self._get_user(db, workflow.candidate_id)
            if candidate is None:
                continue

            # Send reminder with retry
            success = await self._send_with_retry(
                db=db,
                workflow=workflow,
                notification_type="invite_reminder",
                recipient_email=candidate.email,
                recipient_name=candidate.first_name,
            )

            if success:
                workflow.last_reminder_sent_at = now
                workflow.reminder_count = (workflow.reminder_count or 0) + 1
                await db.commit()

    async def _send_pre_interview_reminders(
        self, db: AsyncSession, now: datetime
    ) -> None:
        """
        Send reminder to candidates in "scheduled" state whose interview is
        within 24 hours.
        """
        # Find scheduled workflows where the interview session is within 24h
        stmt = select(CandidateWorkflow).where(
            CandidateWorkflow.current_state == "scheduled",
        )
        result = await db.execute(stmt)
        workflows = list(result.scalars().all())

        for workflow in workflows:
            # Skip if reminder was already sent recently (within 12h)
            if (
                workflow.last_reminder_sent_at is not None
                and workflow.last_reminder_sent_at > now - timedelta(hours=12)
            ):
                continue

            # Check if there's a scheduled session within 24h
            session_stmt = select(InterviewSession).where(
                InterviewSession.candidate_id == workflow.candidate_id,
                InterviewSession.job_drive_id == workflow.job_drive_id,
                InterviewSession.status == "scheduled",
            )
            session_result = await db.execute(session_stmt)
            session = session_result.scalar_one_or_none()

            if session is None:
                continue

            # Check if session start_time is within 24h
            if session.start_time is None:
                continue
            if session.start_time > now + timedelta(hours=PRE_INTERVIEW_REMINDER_HOURS):
                continue
            if session.start_time < now:
                continue  # Already past

            # Fetch candidate and send reminder
            candidate = await self._get_user(db, workflow.candidate_id)
            if candidate is None:
                continue

            success = await self._send_with_retry(
                db=db,
                workflow=workflow,
                notification_type="pre_interview_reminder",
                recipient_email=candidate.email,
                recipient_name=candidate.first_name,
            )

            if success:
                workflow.last_reminder_sent_at = now
                workflow.reminder_count = (workflow.reminder_count or 0) + 1
                await db.commit()

    async def _escalate_stale_evaluated(
        self, db: AsyncSession, now: datetime
    ) -> None:
        """
        Escalate workflows that have been in "evaluated" state for more than
        5 business days without HR action.
        """
        stmt = select(CandidateWorkflow).where(
            CandidateWorkflow.current_state == "evaluated",
        )
        result = await db.execute(stmt)
        workflows = list(result.scalars().all())

        def count_business_days(start: datetime, end: datetime) -> int:
            """Count the number of business days (Monday-Friday) between start and end."""
            if start > end:
                return 0
            current = start.date()
            target = end.date()
            days = 0
            while current < target:
                current += timedelta(days=1)
                if current.weekday() < 5:  # Monday to Friday
                    days += 1
            return days

        for workflow in workflows:
            # Skip if already escalated recently (within 48h)
            if (
                workflow.last_reminder_sent_at is not None
                and workflow.last_reminder_sent_at > now - timedelta(hours=48)
            ):
                continue

            # Verify it is stale for >= 5 business days
            if not workflow.updated_at:
                continue

            if count_business_days(workflow.updated_at, now) < STALE_EVALUATED_BUSINESS_DAYS:
                continue

            # Fetch the job drive to find the HR user
            drive_stmt = select(JobDrive).where(JobDrive.id == workflow.job_drive_id)
            drive_result = await db.execute(drive_stmt)
            drive = drive_result.scalar_one_or_none()

            if drive is None:
                continue

            # Send escalation notification to HR
            success = await self._send_with_retry(
                db=db,
                workflow=workflow,
                notification_type="stale_evaluated_escalation",
                recipient_email=None,  # Will be resolved from drive HR
                recipient_name=None,
                job_drive=drive,
            )

            if success:
                workflow.last_reminder_sent_at = now
                workflow.reminder_count = (workflow.reminder_count or 0) + 1

                # Log escalation as Trace_Entry
                obs = ObservabilityService(db)
                await obs.record(TraceEntryCreate(
                    agent_name="orchestrator",
                    action_type="escalation",
                    workflow_id=workflow.id,
                    candidate_id=workflow.candidate_id,
                    input_summary=(
                        f"Stale 'evaluated' state for candidate_id={workflow.candidate_id}, "
                        f"drive_id={workflow.job_drive_id}"
                    ),
                    output_summary="Escalation notification sent to HR",
                    reasoning_summary=(
                        f"Candidate has been in 'evaluated' state since "
                        f"{workflow.updated_at.isoformat()} (>{STALE_EVALUATED_BUSINESS_DAYS} "
                        f"business days)"
                    ),
                ))

                await db.commit()

    async def _send_with_retry(
        self,
        db: AsyncSession,
        workflow: CandidateWorkflow,
        notification_type: str,
        recipient_email: Optional[str],
        recipient_name: Optional[str],
        job_drive: Optional[JobDrive] = None,
        max_retries: int = MAX_NOTIFICATION_RETRIES,
    ) -> bool:
        """
        Send a notification with exponential backoff retry.

        Logs each attempt as a Trace_Entry.

        Returns True if notification was delivered successfully.
        """
        from app.services.email_service import (
            send_invite_email,
        )

        obs = ObservabilityService(db)

        for attempt in range(max_retries):
            try:
                if notification_type == "invite_reminder":
                    if recipient_email:
                        # Use a simple reminder — reuse invite email pattern
                        await send_invite_email(
                            to=recipient_email,
                            job_role=job_drive.job_role if job_drive else "Open Position",
                            drive_title=job_drive.title if job_drive else "Recruitment Drive",
                            invite_link="",  # Reminder — no new link needed
                            expires_hours=72,
                        ) if job_drive else None
                        # If no job_drive context, log and skip
                        if job_drive is None:
                            drive_stmt = select(JobDrive).where(
                                JobDrive.id == workflow.job_drive_id
                            )
                            drive_result = await db.execute(drive_stmt)
                            jd = drive_result.scalar_one_or_none()
                            if jd:
                                await send_invite_email(
                                    to=recipient_email,
                                    job_role=jd.job_role,
                                    drive_title=jd.title,
                                    invite_link="",
                                    expires_hours=72,
                                )

                elif notification_type == "pre_interview_reminder":
                    if recipient_email:
                        # Fetch drive info for context
                        if job_drive is None:
                            drive_stmt = select(JobDrive).where(
                                JobDrive.id == workflow.job_drive_id
                            )
                            drive_result = await db.execute(drive_stmt)
                            job_drive = drive_result.scalar_one_or_none()

                        if job_drive:
                            await send_invite_email(
                                to=recipient_email,
                                job_role=job_drive.job_role,
                                drive_title=job_drive.title,
                                invite_link="",
                                expires_hours=24,
                            )

                elif notification_type == "stale_evaluated_escalation":
                    # Resolve HR email from drive
                    if job_drive:
                        from app.models.profile import HRProfile

                        hr_stmt = select(HRProfile).where(
                            HRProfile.id == job_drive.hr_id
                        )
                        hr_result = await db.execute(hr_stmt)
                        hr_profile = hr_result.scalar_one_or_none()

                        if hr_profile:
                            hr_user = await self._get_user(db, hr_profile.user_id)
                            if hr_user:
                                await send_invite_email(
                                    to=hr_user.email,
                                    job_role=job_drive.job_role,
                                    drive_title=job_drive.title,
                                    invite_link="",
                                    expires_hours=0,
                                )

                # Log successful delivery
                await obs.record(TraceEntryCreate(
                    agent_name="orchestrator",
                    action_type="notification_sent",
                    workflow_id=workflow.id,
                    candidate_id=workflow.candidate_id,
                    input_summary=f"type={notification_type}, attempt={attempt + 1}",
                    output_summary="Notification delivered successfully",
                ))

                return True

            except Exception as exc:
                # Log failed attempt
                await obs.record(TraceEntryCreate(
                    agent_name="orchestrator",
                    action_type="notification_retry",
                    workflow_id=workflow.id,
                    candidate_id=workflow.candidate_id,
                    input_summary=(
                        f"type={notification_type}, attempt={attempt + 1}/{max_retries}"
                    ),
                    output_summary=f"Failed: {str(exc)[:200]}",
                    reasoning_summary=(
                        f"Retry attempt {attempt + 1} with exponential backoff"
                    ),
                ))

                logger.warning(
                    "Orchestrator notification failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    exc,
                )

                # Exponential backoff: 1s, 2s, 4s
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)

        # All retries exhausted
        logger.error(
            "Orchestrator notification failed after %d retries: "
            "type=%s, candidate_id=%s, drive_id=%s",
            max_retries,
            notification_type,
            workflow.candidate_id,
            workflow.job_drive_id,
        )
        return False

    async def _get_user(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Fetch a user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
