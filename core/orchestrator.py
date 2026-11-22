"""
Core Orchestrator — manages the multi-agent pipeline with full state tracking.
"""
import time
import uuid
import logging
from typing import Optional, Callable

from core.state import ResearchState
from core.communication import bus, MessageType, AgentStatus
from config.settings import MAX_REVIEW_ITERATIONS, QUALITY_THRESHOLD

logger = logging.getLogger(__name__)


def run_multi_agent_pipeline(
    topic: str,
    depth: str = "standard",
    report_format: str = "academic",
    additional_instructions: str = "",
    quality_threshold: int = QUALITY_THRESHOLD,
    max_iterations: int = MAX_REVIEW_ITERATIONS,
    progress_callback: Optional[Callable] = None,
) -> ResearchState:
    """
    Execute the full multi-agent research pipeline.
    Returns the final ResearchState.
    """
    from agents.planner import run_planner
    from agents.researcher import run_researcher
    from agents.analyst import run_analyst
    from agents.writer import run_writer
    from agents.fact_checker import run_fact_checker
    from agents.reviewer import run_reviewer
    from agents.coordinator import run_conflict_resolver

    # Initialize state
    state = ResearchState(
        session_id=str(uuid.uuid4()),
        topic=topic,
        depth=depth,
        report_format=report_format,
        additional_instructions=additional_instructions,
        quality_threshold=quality_threshold,
        max_iterations=max_iterations,
        mode="multi_agent",
    )

    bus.reset()
    bus.post("system", f"🚀 Starting Multi-Agent Research Pipeline for: **{topic}**",
             message_type=MessageType.SYSTEM,
             metadata={"session_id": state.session_id, "depth": depth, "mode": "multi_agent"})

    start_time = time.time()

    def notify(step: str):
        bus.set_current_state(state)
        if progress_callback:
            try:
                progress_callback(step, state)
            except Exception:
                pass

    # ── Step 1: Research Planner ─────────────────────────────────────────────
    bus.post("system", "📋 Step 1/7: Research Planner — decomposing topic",
             message_type=MessageType.SYSTEM)
    notify("planning")
    state = run_planner(state)
    notify("planning_done")
    if "planner" in state.failed_agents:
        bus.post("system", "⚠️ Planner failed — continuing with default plan",
                 message_type=MessageType.SYSTEM)

    # ── Step 2: Research Agent ────────────────────────────────────────────────
    bus.post("system", "🔍 Step 2/7: Research Agent — gathering information",
             message_type=MessageType.SYSTEM)
    notify("researching")
    state = run_researcher(state)
    notify("researching_done")
    if "researcher" in state.failed_agents:
        bus.post("system", "❌ Research agent failed — cannot continue without research data",
                 message_type=MessageType.ERROR)
        state.pipeline_complete = False
        state.execution_time_seconds = time.time() - start_time
        bus.set_current_state(state)
        return state

    # ── Step 3: Data Analyst ──────────────────────────────────────────────────
    bus.post("system", "📊 Step 3/7: Data Analyst — analyzing findings",
             message_type=MessageType.SYSTEM)
    notify("analyzing")
    state = run_analyst(state)
    notify("analyzing_done")

    # ── Step 4: Conflict Detection ────────────────────────────────────────────
    if state.conflicts_detected:
        bus.post("system", f"⚖️ Conflicts detected ({len(state.conflicts_detected)}) — routing to Conflict Resolver",
                 message_type=MessageType.SYSTEM)
        notify("resolving_conflicts")
        state = run_conflict_resolver(state)
        notify("conflicts_resolved")

    # ── Step 5: Content Writer (iterative) ───────────────────────────────────
    bus.post("system", "✍️ Step 4/7: Content Writer — drafting report",
             message_type=MessageType.SYSTEM)
    notify("writing")
    state = run_writer(state)
    notify("writing_done")
    if "writer" in state.failed_agents:
        state.pipeline_complete = False
        state.execution_time_seconds = time.time() - start_time
        bus.set_current_state(state)
        return state

    # ── Step 6: Fact Checker ──────────────────────────────────────────────────
    bus.post("system", "✅ Step 5/7: Fact Checker — verifying claims",
             message_type=MessageType.SYSTEM)
    notify("fact_checking")
    state = run_fact_checker(state)
    notify("fact_checking_done")

    # ── Step 7: Reviewer + Iterative Improvement Loop ─────────────────────────
    bus.post("system", "⭐ Step 6/7: Reviewer — evaluating report quality",
             message_type=MessageType.SYSTEM)
    notify("reviewing")
    state = run_reviewer(state)
    notify("reviewing_done")

    while (
        state.review_result is not None
        and not state.review_result.approved
        and state.review_iteration < state.max_iterations
    ):
        score = state.review_result.score
        bus.post(
            "system",
            f"🔄 Quality score {score}/{state.quality_threshold} — "
            f"starting improvement iteration {state.review_iteration}/{state.max_iterations}",
            message_type=MessageType.SYSTEM,
        )
        notify(f"improving_{state.review_iteration}")

        # Writer revises based on reviewer feedback
        feedback = state.review_result.improvement_instructions
        state = run_writer(state, feedback=feedback)

        # Re-check facts on new draft
        state = run_fact_checker(state)

        # Re-review
        bus.post("system", f"⭐ Re-reviewing (iteration {state.review_iteration + 1})…",
                 message_type=MessageType.SYSTEM)
        state = run_reviewer(state)

    # Final quality gate
    if state.review_result:
        final_score = state.review_result.score
        if final_score >= state.quality_threshold:
            bus.post("system",
                     f"🎉 Quality threshold met: {final_score}/{state.quality_threshold}",
                     message_type=MessageType.SYSTEM)
        else:
            bus.post("system",
                     f"⚠️ Max iterations reached. Final score: {final_score}/{state.quality_threshold}. "
                     f"Proceeding with best available report.",
                     message_type=MessageType.SYSTEM)

    # ── Step 8: Human Approval Gate ──────────────────────────────────────────
    state.final_report = state.draft_report
    state.awaiting_human_approval = True
    bus.set_agent_status("human", AgentStatus.WAITING,
                         task="Review and approve the generated research report")
    bus.post("system", "👤 Step 7/7: Requesting human approval before finalizing report",
             message_type=MessageType.APPROVAL_REQUEST)
    bus.post("human", "⏳ Please review the report and approve or reject it",
             message_type=MessageType.APPROVAL_REQUEST)

    state.execution_time_seconds = time.time() - start_time
    state.pipeline_complete = True

    bus.post("system",
             f"⌛ Pipeline complete in {state.execution_time_seconds:.1f}s | "
             f"{state.total_agent_calls} agent calls | "
             f"Awaiting human approval",
             message_type=MessageType.SYSTEM,
             metadata={"execution_time": state.execution_time_seconds,
                        "agent_calls": state.total_agent_calls})

    return state


def run_single_agent_pipeline(
    topic: str,
    depth: str = "standard",
    additional_instructions: str = "",
    progress_callback: Optional[Callable] = None,
) -> ResearchState:
    """Execute single-agent research for comparison."""
    from agents.single_agent import run_single_agent

    state = ResearchState(
        session_id=str(uuid.uuid4()),
        topic=topic,
        depth=depth,
        additional_instructions=additional_instructions,
        mode="single_agent",
    )

    bus.reset()
    bus.post("system", f"🤖 Starting Single-Agent Mode for: **{topic}**",
             message_type=MessageType.SYSTEM)

    start_time = time.time()
    state = run_single_agent(state)
    state.execution_time_seconds = time.time() - start_time
    state.pipeline_complete = True
    state.awaiting_human_approval = False

    return state


def finalize_report(state: ResearchState, approved: bool, feedback: str = "") -> ResearchState:
    """
    Process human approval/rejection.
    If rejected, marks for revision. If approved, marks complete.
    """
    state.human_approved = approved
    state.human_feedback = feedback
    state.awaiting_human_approval = False

    if approved:
        bus.set_agent_status("human", AgentStatus.COMPLETED)
        bus.post("human", "✅ Report approved! Finalizing and generating export files…",
                 message_type=MessageType.SYSTEM)
        bus.post("system", "🎊 Research complete! Report is ready for download.",
                 message_type=MessageType.SYSTEM)
    else:
        bus.set_agent_status("human", AgentStatus.COMPLETED)
        bus.post("human", f"🔄 Report rejected. Feedback: {feedback[:200]}",
                 message_type=MessageType.FEEDBACK)
        bus.post("system", "📝 Human rejection received — feedback sent to Writer for revision",
                 message_type=MessageType.SYSTEM)

    return state

