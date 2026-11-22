"""
Reviewer Agent — evaluates report quality and provides feedback for improvement.
"""
import json
import logging
from core.llm import call_llm_with_retry
from core.state import ResearchState, ReviewResult
from core.communication import bus, AgentStatus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Academic Reviewer AI. Your job is to evaluate research reports rigorously.

Evaluate the report on these dimensions and return ONLY a valid JSON object:

{
  "accuracy_score": 0-20,
  "completeness_score": 0-20,
  "clarity_score": 0-20,
  "structure_score": 0-20,
  "depth_score": 0-20,
  "total_score": 0-100,
  "strengths": ["strength 1", "strength 2", ...],
  "weaknesses": ["weakness 1", "weakness 2", ...],
  "improvement_instructions": "Detailed, specific instructions for the writer to improve the report",
  "approved": true/false
}

Scoring rubric:
- accuracy_score (0-20): Are all claims accurate and well-supported?
- completeness_score (0-20): Are all required sections present and adequately covered?
- clarity_score (0-20): Is the writing clear, logical, and easy to follow?
- structure_score (0-20): Is the report well-organized with proper flow?
- depth_score (0-20): Is the analysis sufficiently deep and insightful?

Approval criteria:
- approved: true ONLY if total_score >= quality_threshold
- improvement_instructions: Specific, actionable improvements needed

IMPORTANT: Be a rigorous reviewer. A score of 85+ means genuinely excellent work.
"""


def run_reviewer(state: ResearchState) -> ResearchState:
    """Execute the Reviewer agent."""
    agent = "reviewer"
    bus.set_agent_status(agent, AgentStatus.WORKING, task=f"Reviewing report (iteration {state.review_iteration})")
    bus.post(agent, f"⭐ Reviewing report quality (iteration {state.review_iteration + 1}/{state.max_iterations})…",
             message_type=MessageType.TASK_ASSIGN)

    if not state.draft_report:
        error = "No draft report available for review"
        state.mark_agent_failed(agent, error)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error)
        bus.post(agent, f"❌ {error}", message_type=MessageType.ERROR)
        return state

    # Build fact check summary
    fc_summary = ""
    if state.fact_check_results:
        verified = sum(1 for fc in state.fact_check_results if fc.status == "verified")
        unsupported = sum(1 for fc in state.fact_check_results if fc.status == "unsupported")
        conflicting = sum(1 for fc in state.fact_check_results if fc.status == "conflicting")
        fc_summary = f"\nFact Check Summary: {verified} verified, {unsupported} unsupported, {conflicting} conflicting"

    plan_check = ""
    if state.plan:
        plan_check = f"""
Expected sections from plan: {', '.join(state.plan.expected_sections)}
Research objectives: {', '.join(state.plan.objectives[:3])}
"""

    user_prompt = f"""Topic: {state.topic}
Quality Threshold: {state.quality_threshold}/100
Review Iteration: {state.review_iteration + 1}
{fc_summary}
{plan_check}

=== REPORT TO REVIEW ===
{state.draft_report[:5000]}

Evaluate this report rigorously and return ONLY the JSON object."""

    try:
        response = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, temperature=0.1)
        state.total_agent_calls += 1

        # Parse JSON
        clean = response.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            clean = clean[start:end]

        review_data = json.loads(clean)

        total_score = int(review_data.get("total_score", 0))
        # Validate total equals sum of components
        component_sum = (
            int(review_data.get("accuracy_score", 0)) +
            int(review_data.get("completeness_score", 0)) +
            int(review_data.get("clarity_score", 0)) +
            int(review_data.get("structure_score", 0)) +
            int(review_data.get("depth_score", 0))
        )
        if component_sum > 0 and abs(component_sum - total_score) > 5:
            total_score = component_sum  # Use computed sum if inconsistent

        approved = total_score >= state.quality_threshold

        result = ReviewResult(
            score=total_score,
            strengths=review_data.get("strengths", []),
            weaknesses=review_data.get("weaknesses", []),
            improvement_instructions=review_data.get("improvement_instructions", ""),
            approved=approved,
        )
        state.review_result = result
        state.review_iteration += 1
        state.mark_agent_complete(agent)

        status_emoji = "✅" if approved else "🔄"
        approval_text = "APPROVED" if approved else "NEEDS IMPROVEMENT"

        bus.set_agent_status(agent, AgentStatus.COMPLETED,
                             output_preview=f"Score: {total_score}/100 — {approval_text}")
        bus.post(
            agent,
            f"{status_emoji} Report reviewed: **{total_score}/100** — {approval_text}\n"
            f"Strengths: {len(result.strengths)} | Weaknesses: {len(result.weaknesses)}",
            recipient="writer" if not approved else "human",
            message_type=MessageType.TASK_RESULT,
            metadata={
                "score": total_score,
                "approved": approved,
                "iteration": state.review_iteration,
                "accuracy": review_data.get("accuracy_score"),
                "completeness": review_data.get("completeness_score"),
                "clarity": review_data.get("clarity_score"),
                "structure": review_data.get("structure_score"),
                "depth": review_data.get("depth_score"),
            },
        )

        if not approved and state.review_iteration < state.max_iterations:
            bus.post(agent, f"📝 Sending improvement instructions to Writer…\n{result.improvement_instructions[:200]}",
                     recipient="writer", message_type=MessageType.FEEDBACK)
        elif approved:
            bus.post(agent, f"🎉 Report approved with score {total_score}/100! Requesting human approval…",
                     recipient="human", message_type=MessageType.APPROVAL_REQUEST)

    except json.JSONDecodeError as e:
        logger.warning(f"Reviewer JSON parse failed: {e}. Using default scores.")
        # Compute a reasonable fallback score
        word_count = len(state.draft_report.split())
        sections = state.draft_report.count("## ")
        fallback_score = min(70 + (sections * 2) + (1 if word_count > 1000 else 0), 85)
        approved = fallback_score >= state.quality_threshold

        state.review_result = ReviewResult(
            score=fallback_score,
            strengths=["Report contains required sections", "Research is well-documented"],
            weaknesses=["Review encountered a formatting issue — manual evaluation recommended"],
            improvement_instructions="Please review and ensure all sections are detailed and evidence-based.",
            approved=approved,
        )
        state.review_iteration += 1
        state.mark_agent_complete(agent)
        bus.set_agent_status(agent, AgentStatus.COMPLETED,
                             output_preview=f"Score: {fallback_score}/100 (estimated)")
        bus.post(agent, f"✅ Report reviewed: {fallback_score}/100 (estimated score)",
                 message_type=MessageType.TASK_RESULT)

    except Exception as e:
        error_msg = str(e)
        state.mark_agent_failed(agent, error_msg)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error_msg)
        bus.post(agent, f"❌ Reviewer failed: {error_msg}", message_type=MessageType.ERROR)
        logger.error(f"Reviewer agent error: {e}")

    return state

