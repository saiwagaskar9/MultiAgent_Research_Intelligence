"""
Conflict Resolution Agent — detects and resolves disagreements between agents.
"""
import logging
from core.llm import call_llm_with_retry
from core.state import ResearchState
from core.communication import bus, AgentStatus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Conflict Resolution AI for multi-agent research systems.

Your job is to analyze conflicts between research agents and determine the most accurate resolution.

For each conflict, produce a structured resolution:

## Conflict Analysis
[Describe the nature of the conflict clearly]

## Evidence Comparison
[Compare the conflicting evidence from each perspective]

## Resolution
[State the final resolution — which position is most supported by evidence]

## Reasoning
[Explain WHY this resolution was chosen]

## Impact on Report
[How should the resolution change the research report?]

PRINCIPLES:
- Base resolution on evidence quality, not agent authority
- Acknowledge when evidence is insufficient to fully resolve a conflict
- Recommend reporting both perspectives if the conflict is legitimate academic debate
- Never fabricate evidence to resolve a conflict
"""


def run_conflict_resolver(state: ResearchState) -> ResearchState:
    """Execute the Conflict Resolution agent."""
    agent = "conflict_resolver"

    if not state.conflicts_detected:
        bus.post(agent, "⚖️ No conflicts to resolve — all agents in agreement",
                 message_type=MessageType.SYSTEM)
        bus.set_agent_status(agent, AgentStatus.COMPLETED,
                             output_preview="No conflicts detected")
        state.mark_agent_complete(agent)
        return state

    bus.set_agent_status(agent, AgentStatus.WORKING,
                         task=f"Resolving {len(state.conflicts_detected)} detected conflicts")
    bus.post(agent, f"⚖️ Analyzing {len(state.conflicts_detected)} detected conflicts…",
             message_type=MessageType.TASK_ASSIGN)

    conflicts_text = "\n\n".join([
        f"Conflict {i+1}: {c.get('type', 'unknown')}\n"
        f"Description: {c.get('description', '')}\n"
        f"Detected by: {c.get('detected_by', 'unknown')}\n"
        f"Details: {str(c.get('details', ''))[:300]}"
        for i, c in enumerate(state.conflicts_detected)
    ])

    user_prompt = f"""Research Topic: {state.topic}

=== DETECTED CONFLICTS ===
{conflicts_text}

=== RESEARCH DATA (for context) ===
{state.raw_research[:2000]}

=== ANALYSIS DATA ===
{state.analysis[:1000]}

Analyze each conflict and provide structured resolutions."""

    try:
        response = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, temperature=0.2)
        state.total_agent_calls += 1

        # Mark all conflicts as resolved
        for conflict in state.conflicts_detected:
            resolution = {
                "original_conflict": conflict,
                "resolution_summary": response[:500],
                "resolved_by": "conflict_resolver",
            }
            state.conflicts_resolved.append(resolution)

        state.mark_agent_complete(agent)
        bus.set_agent_status(agent, AgentStatus.COMPLETED,
                             output_preview=f"Resolved {len(state.conflicts_detected)} conflict(s)")
        bus.post(agent,
                 f"✅ All {len(state.conflicts_detected)} conflict(s) resolved.\n"
                 f"Resolution summary: {response[:200]}…",
                 message_type=MessageType.TASK_RESULT,
                 metadata={"conflicts_resolved": len(state.conflicts_resolved)})

    except Exception as e:
        error_msg = str(e)
        state.mark_agent_failed(agent, error_msg)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error_msg)
        bus.post(agent, f"❌ Conflict resolver failed: {error_msg}", message_type=MessageType.ERROR)
        logger.error(f"Conflict resolver error: {e}")

    return state

