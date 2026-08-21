"""
SentimentNode — Real-Time Sentiment and Emotional Intelligence Agent.

Design: Sentiment_Agent (Section 6 of design.md)
Requirements: 6.1, 6.2, 6.3, 6.6, 6.7, 6.8, 6.9, 6.10

This LangGraph node analyzes candidate text responses using a lightweight
rule-based approach (no external API latency) and populates empathy_metrics
in InterviewState before the empathy_analyzer_node runs.
"""
from __future__ import annotations

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import async_session
from app.models.interview import InterviewSession
from app.schemas.interview import EmpathyMetrics
from app.services.observability_service import trace_agent_action
from app.services.interview_engine.state import InterviewState

logger = logging.getLogger(__name__)

# ── Rule-Based Indicator Word Lists ──────────────────────────────────────────

POSITIVE_INDICATORS = [
    "confident", "excited", "great", "love", "enjoy", "absolutely",
    "definitely", "excellent", "awesome", "perfect", "clear", "solved",
    "happy", "glad", "strong", "easy", "sure",
]

NEGATIVE_STRESS_INDICATORS = [
    "don't know", "not sure", "nervous", "confused", "lost",
    "struggling", "difficult", "anxious", "stressed", "stuck",
    "uncertain", "worried", "overwhelmed", "frustrated", "fail",
]

HESITATION_INDICATORS = [
    "um", "uh", "hmm", "well...", "err", "like...",
]

CONFIDENCE_INDICATORS = [
    "sure", "definitely", "absolutely", "clear", "know",
    "experience", "solved", "designed", "implemented", "correct",
]


_hf_pipeline = None
_hf_lock = asyncio.Lock()


async def _persist_empathy_snapshot(session_id: int, metrics: Dict[str, Any]) -> None:
    """Persist empathy asynchronously so a DB commit never delays the next question."""
    try:
        async with async_session() as persist_db:
            stmt = select(InterviewSession).where(InterviewSession.id == session_id)
            res = await persist_db.execute(stmt)
            session_rec = res.scalars().first()
            if not session_rec:
                return
            current_feedback = session_rec.ai_feedback or {}
            if not isinstance(current_feedback, dict):
                current_feedback = {"raw": current_feedback}
            snapshots = current_feedback.setdefault("empathy_snapshots", [])
            snapshots.append(metrics)
            session_rec.ai_feedback = current_feedback
            persist_db.add(session_rec)
            await persist_db.commit()
    except Exception as db_err:
        logger.error("Failed to save empathy snapshot to DB: %s", db_err)


async def get_hf_sentiment_pipeline():
    """Lazy loader for the HuggingFace sentiment analysis pipeline."""
    global _hf_pipeline
    async with _hf_lock:
        if _hf_pipeline is None:
            import transformers
            def _load():
                return transformers.pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english"
                )
            _hf_pipeline = await asyncio.to_thread(_load)
    return _hf_pipeline


class SentimentNode:
    """
    LangGraph node that performs real-time sentiment analysis on candidate
    responses using a lightweight rule-based approach for local inference.

    Methods:
        __call__: LangGraph node entry point
        analyze_text: Rule-based text sentiment analysis
        analyze_acoustic: Acoustic feature analysis (placeholder — returns defaults)
        merge_metrics: Combines text (0.7) and acoustic (0.3) metrics
        check_stress_alert: Emits high_stress_alert when stress > 0.8 for 3 consecutive responses
    """

    async def __call__(self, state: InterviewState) -> Dict[str, Any]:
        """
        LangGraph node entry point. Opens a DB session and delegates to the
        traced processing method.
        """
        async with async_session() as db:
            return await self._process(state, db=db)

    @trace_agent_action("sentiment_agent", "text_analysis")
    async def _process(self, state: InterviewState, db: AsyncSession) -> Dict[str, Any]:
        """
        Analyze the last candidate message and produce empathy_metrics.

        On timeout (>2s), preserves previous empathy_metrics from state.
        Stores metrics in empathy_timeline for post-session analysis.
        """
        start_time_ms = int(time.time() * 1000)
        messages = state.get("messages", [])
        session_id_str = state.get("supervisor_session_id")

        # No messages — nothing to analyze
        if not messages:
            return {}

        # Find the last candidate (user) message
        last_user_message = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            None,
        )
        if not last_user_message:
            return {}

        # ── 2-second timeout budget ──────────────────────────────────────────
        previous_metrics = state.get("empathy_metrics") or {
            "sentiment_score": 0.0,
            "stress_level": 0.0,
            "hesitation_rating": 0.0,
            "confidence_level": 0.5,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            empathy_metrics = await asyncio.wait_for(
                self._analyze(
                    text=last_user_message,
                    db=db,
                    session_id_str=session_id_str,
                    start_time_ms=start_time_ms
                ),
                timeout=2.0,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning(
                "Sentiment analysis timed out or failed: %s. Preserving previous empathy_metrics.",
                exc,
            )
            # Fallback: preserve previous empathy_metrics (Req 6.10)
            empathy_metrics = previous_metrics

        # ── Stress alert tracking ────────────────────────────────────────────
        stress_level = empathy_metrics.get("stress_level", 0.0)
        stress_history: List[float] = list(state.get("stress_history", []))
        stress_history.append(stress_level)

        # Check if we should emit a high_stress_alert (Req 6.7)
        if self.check_stress_alert(stress_history) and session_id_str:
            logger.warning(
                "High stress detected for session %s (3 consecutive responses with stress > 0.8)",
                session_id_str,
            )
            alert_msg = {
                "type": "high_stress_alert",
                "session_id": session_id_str,
                "stress_level": stress_level,
                "consecutive_turns": 3,
                "message": "Candidate is showing high stress levels over multiple turns.",
            }
            try:
                from app.api.v1.endpoints.interview import manager
                await manager.broadcast_to_hr(alert_msg, session_id_str)
            except Exception as ws_err:
                logger.error("Failed to broadcast high_stress_alert: %s", ws_err)

        # ── Stream empathy_metrics update to HR via WebSocket (Req 6.6) ──────
        if session_id_str:
            update_msg = {
                "type": "empathy_update",
                "session_id": session_id_str,
                "empathy_metrics": empathy_metrics,
            }
            try:
                from app.api.v1.endpoints.interview import manager
                await manager.broadcast_to_hr(update_msg, session_id_str)
            except Exception as ws_err:
                logger.error("Failed to broadcast empathy_update: %s", ws_err)

        # ── Persist snapshot to empathy_timeline (Req 6.9) ───────────────────
        empathy_timeline: List[Dict[str, Any]] = list(state.get("empathy_timeline", []))
        empathy_timeline.append(empathy_metrics)

        # Persist to InterviewSession.ai_feedback asynchronously. This is
        # observability work and must not delay the next candidate question.
        if session_id_str:
            try:
                asyncio.create_task(_persist_empathy_snapshot(int(session_id_str), empathy_metrics))
            except (TypeError, ValueError):
                logger.warning("Invalid sentiment session id: %s", session_id_str)

        return {
            "empathy_metrics": empathy_metrics,
            "stress_history": stress_history,
            "empathy_timeline": empathy_timeline,
        }

    # ── Core Analysis Methods ─────────────────────────────────────────────────

    async def _analyze(
        self,
        text: str,
        db: Optional[AsyncSession] = None,
        session_id_str: Optional[str] = None,
        start_time_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Orchestrate text + acoustic analysis and merge results."""
        if start_time_ms is None:
            start_time_ms = int(time.time() * 1000)
        session_id = int(session_id_str) if session_id_str else None

        rule_based_metrics = self.analyze_text(text)
        text_metrics = await self.analyze_text_hf(
            text=text,
            rule_based_metrics=rule_based_metrics,
            db=db,
            session_id=session_id,
            start_time_ms=start_time_ms
        )

        acoustic_metrics = self.analyze_acoustic()
        merged = self.merge_metrics(text_metrics, acoustic_metrics)
        return merged

    async def _analyze_response(
        self,
        text: str,
        state: InterviewState,
        db: Optional[AsyncSession] = None,
        session_id_str: Optional[str] = None,
        start_time_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Backward-compatible alias for _analyze (used by existing tests)."""
        return await self._analyze(
            text=text,
            db=db,
            session_id_str=session_id_str or state.get("supervisor_session_id"),
            start_time_ms=start_time_ms
        )

    async def analyze_text_hf(
        self,
        text: str,
        rule_based_metrics: EmpathyMetrics,
        db: Optional[AsyncSession] = None,
        session_id: Optional[int] = None,
        start_time_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        HuggingFace model-based sentiment analysis with a 2-second timeout.
        If it succeeds, it adjusts the rule-based metrics.
        If it fails/times out, logs a TraceEntry and returns rule_based_metrics.
        """
        if start_time_ms is None:
            start_time_ms = int(time.time() * 1000)

        try:
            pipeline = await get_hf_sentiment_pipeline()
            result = await asyncio.wait_for(
                asyncio.to_thread(pipeline, text),
                timeout=2.0
            )
            if result and isinstance(result, list) and len(result) > 0:
                label = result[0].get("label", "POSITIVE").upper()
                score = result[0].get("score", 0.0)

                rule_sentiment = rule_based_metrics.get("sentiment_score", 0.0)
                rule_stress = rule_based_metrics.get("stress_level", 0.0)
                rule_confidence = rule_based_metrics.get("confidence_level", 0.5)

                if "POS" in label:
                    sentiment_score = score
                    stress_level = max(0.0, rule_stress - 0.2)
                    confidence_level = min(1.0, rule_confidence + (score * 0.2))
                else:
                    sentiment_score = -score
                    stress_level = min(1.0, rule_stress + (score * 0.3))
                    confidence_level = max(0.0, rule_confidence - (score * 0.2))

                return {
                    "sentiment_score": round(max(-1.0, min(1.0, sentiment_score)), 3),
                    "stress_level": round(max(0.0, min(1.0, stress_level)), 3),
                    "hesitation_rating": rule_based_metrics.get("hesitation_rating", 0.0),
                    "confidence_level": round(max(0.0, min(1.0, confidence_level)), 3),
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            logger.warning(
                "Local HuggingFace sentiment analysis failed or timed out: %s. "
                "Logging to trace entries and falling back to rule-based metrics.",
                e,
            )
            if db and session_id:
                try:
                    from app.services.observability_service import ObservabilityService
                    from app.models.trace_entry import TraceEntryCreate
                    obs = ObservabilityService(db)
                    duration = int(time.time() * 1000) - start_time_ms
                    await obs.record(TraceEntryCreate(
                        agent_name="sentiment_agent",
                        action_type="sentiment_hf_failed",
                        session_id=session_id,
                        input_summary=f"Text length: {len(text)}",
                        reasoning_summary=f"HF model failed/timed out: {str(e)[:300]}",
                        output_summary="Falling back to rule-based metrics",
                        confidence_score=0.0,
                        duration_ms=duration,
                    ))
                except Exception as trace_err:
                    logger.error("Failed to record TraceEntry for sentiment failure: %s", trace_err)

        return rule_based_metrics

    def analyze_text(self, text: str) -> EmpathyMetrics:
        """
        Lightweight rule-based text sentiment analysis.

        Indicators:
        - Positive: "confident", "excited", "great", "love", "enjoy", "absolutely", "definitely"
        - Negative/stress: "don't know", "not sure", "nervous", "confused", "lost", "struggling", "difficult"
        - Hesitation: "um", "uh", "hmm", "well...", short responses (<20 chars), ellipsis
        - Confidence: "sure", "definitely", "absolutely", "clear", "know", etc.

        Returns:
            EmpathyMetrics with sentiment_score, stress_level, hesitation_rating,
            confidence_level, and analyzed_at.
        """
        text_lower = text.lower().strip()
        words = text_lower.split()
        word_count = len(words)

        # ── Sentiment Score (-1.0 to 1.0) ────────────────────────────────────
        positive_count = sum(
            1 for indicator in POSITIVE_INDICATORS if indicator in text_lower
        )
        negative_count = sum(
            1 for indicator in NEGATIVE_STRESS_INDICATORS if indicator in text_lower
        )

        if positive_count + negative_count > 0:
            sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
        else:
            sentiment_score = 0.0

        sentiment_score = max(-1.0, min(1.0, sentiment_score))

        # ── Stress Level (0.0 to 1.0) ────────────────────────────────────────
        stress_indicators_found = sum(
            1 for indicator in NEGATIVE_STRESS_INDICATORS if indicator in text_lower
        )
        # Normalize: more stress indicators = higher stress
        stress_level = min(1.0, stress_indicators_found * 0.3)

        # Short responses increase stress slightly
        if len(text) < 20:
            stress_level = min(1.0, stress_level + 0.2)

        # ── Hesitation Rating (0.0 to 1.0) ───────────────────────────────────
        hesitation_count = sum(
            1 for indicator in HESITATION_INDICATORS if indicator in text_lower
        )
        hesitation_rating = min(1.0, hesitation_count * 0.25)

        # Short responses (<20 chars) indicate hesitation
        if len(text) < 20:
            hesitation_rating = min(1.0, hesitation_rating + 0.3)

        # Ellipsis indicates trailing off / uncertainty
        if "..." in text:
            hesitation_rating = min(1.0, hesitation_rating + 0.2)

        # ── Confidence Level (0.0 to 1.0) ────────────────────────────────────
        confidence_count = sum(
            1 for indicator in CONFIDENCE_INDICATORS if indicator in text_lower
        )
        # Base confidence at 0.5, boosted by confidence indicators, reduced by stress/hesitation
        confidence_level = 0.5 + (confidence_count * 0.15) - (stress_level * 0.3) - (hesitation_rating * 0.2)
        confidence_level = max(0.0, min(1.0, confidence_level))

        return {
            "sentiment_score": round(sentiment_score, 3),
            "stress_level": round(stress_level, 3),
            "hesitation_rating": round(hesitation_rating, 3),
            "confidence_level": round(confidence_level, 3),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    def analyze_acoustic(self, audio_features: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Analyze acoustic features: speech rate, pause frequency, pitch variance.

        This is a placeholder that returns default neutral metrics since acoustic
        analysis requires audio features not available in the text-based graph turn.
        When audio_features are provided (from voice_service), they are used directly.

        Args:
            audio_features: Optional dict with speech_rate, pause_frequency, pitch_variance

        Returns:
            AcousticMetrics dict with speech_rate, pause_frequency, pitch_variance,
            and derived stress/confidence adjustments.
        """
        if audio_features:
            return {
                "speech_rate": audio_features.get("speech_rate", 130.0),
                "pause_frequency": audio_features.get("pause_frequency", 3.0),
                "pitch_variance": audio_features.get("pitch_variance", 25.0),
                "acoustic_stress_adjustment": 0.0,
                "acoustic_confidence_adjustment": 0.0,
            }

        # Default neutral acoustic metrics (no audio available)
        return {
            "speech_rate": 130.0,       # Normal speech rate (words per minute)
            "pause_frequency": 3.0,     # Normal pause frequency (pauses per minute)
            "pitch_variance": 25.0,     # Normal pitch variance (Hz std dev)
            "acoustic_stress_adjustment": 0.0,
            "acoustic_confidence_adjustment": 0.0,
        }

    def merge_metrics(
        self,
        text_metrics: EmpathyMetrics,
        acoustic_metrics: Optional[Dict[str, float]],
    ) -> EmpathyMetrics:
        """
        Combine text and acoustic metrics with text weighted 0.7 and acoustic 0.3.

        Args:
            text_metrics: EmpathyMetrics from analyze_text()
            acoustic_metrics: Acoustic metrics from analyze_acoustic()

        Returns:
            Merged EmpathyMetrics with weighted combination.
        """
        if not acoustic_metrics:
            return text_metrics

        # Extract acoustic adjustments (default to 0 if not present)
        acoustic_stress_adj = acoustic_metrics.get("acoustic_stress_adjustment", 0.0)
        acoustic_confidence_adj = acoustic_metrics.get("acoustic_confidence_adjustment", 0.0)

        # Weighted merge: text 0.7, acoustic 0.3
        # For sentiment_score and hesitation_rating, acoustic doesn't directly contribute
        # so we keep text values but apply acoustic adjustments to stress and confidence
        merged_stress = (text_metrics["stress_level"] * 0.7) + (
            (text_metrics["stress_level"] + acoustic_stress_adj) * 0.3
        )
        merged_confidence = (text_metrics["confidence_level"] * 0.7) + (
            (text_metrics["confidence_level"] + acoustic_confidence_adj) * 0.3
        )
        merged_hesitation = (text_metrics["hesitation_rating"] * 0.7) + (
            text_metrics["hesitation_rating"] * 0.3
        )
        merged_sentiment = (text_metrics["sentiment_score"] * 0.7) + (
            text_metrics["sentiment_score"] * 0.3
        )

        return {
            "sentiment_score": round(max(-1.0, min(1.0, merged_sentiment)), 3),
            "stress_level": round(max(0.0, min(1.0, merged_stress)), 3),
            "hesitation_rating": round(max(0.0, min(1.0, merged_hesitation)), 3),
            "confidence_level": round(max(0.0, min(1.0, merged_confidence)), 3),
            "analyzed_at": text_metrics.get("analyzed_at", datetime.now(timezone.utc).isoformat()),
        }

    def check_stress_alert(self, stress_history: List[float]) -> bool:
        """
        Check if stress_level > 0.8 for 3 consecutive responses.

        Emits high_stress_alert WebSocket event when condition is met.

        Args:
            stress_history: List of stress_level values from recent responses.

        Returns:
            True if the last 3 entries in stress_history all exceed 0.8.
        """
        if len(stress_history) < 3:
            return False

        last_three = stress_history[-3:]
        return all(s > 0.8 for s in last_three)


# Module-level instance used by the LangGraph graph
sentiment_node = SentimentNode()
