"""
Data Analyst Agent — analyzes research findings and identifies patterns, insights, and gaps.
"""
import logging
from core.llm import call_llm_with_retry
from core.state import ResearchState
from core.communication import bus, AgentStatus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Data Analyst AI specializing in research analysis.

Analyze the provided research data and produce a structured analytical report with these sections:

## Executive Summary
[2-3 sentence high-level summary of key insights]

## Pattern Analysis
[Key patterns, trends, and recurring themes identified in the research]

## Comparative Analysis
[Comparison of different aspects, approaches, or viewpoints]

## Strengths and Advantages
[Identified strengths, benefits, positive aspects]

## Weaknesses and Challenges
[Identified weaknesses, limitations, challenges, risks]

## Critical Insights
[The most important non-obvious insights derived from analysis]

## Knowledge Gaps
[Areas where information is missing, contradictory, or insufficient]

## Statistical and Quantitative Observations
[Any numbers, percentages, metrics found (only real ones from research, not invented)]

## Recommendations for Report
[Specific sections and points the writer should emphasize]

RULES:
- Base ALL analysis strictly on the provided research data
- Do NOT invent facts, statistics, or examples not in the research
- If data is insufficient for a section, say so explicitly
- Identify any conflicting information between sources
"""


def run_analyst(state: ResearchState) -> ResearchState:
    """Execute the Data Analyst agent."""
    agent = "analyst"
    bus.set_agent_status(agent, AgentStatus.WORKING, task="Analyzing research findings")
    bus.post(agent, "📊 Starting deep analysis of research findings…",
             message_type=MessageType.TASK_ASSIGN)

    if not state.raw_research:
        error = "No research data available for analysis"
        state.mark_agent_failed(agent, error)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error)
        bus.post(agent, f"❌ {error}", message_type=MessageType.ERROR)
        return state

    # Build plan context
    plan_context = ""
    if state.plan:
        plan_context = f"""
Research Objectives to validate:
{chr(10).join(f'- {o}' for o in state.plan.objectives)}

Sub-questions to verify coverage:
{chr(10).join(f'- {q}' for q in state.plan.sub_questions)}
"""

    depth_instructions = {
        "quick":    "Provide a focused analysis highlighting only the most critical insights.",
        "standard": "Provide balanced analysis covering all key dimensions.",
        "deep":     "Provide exhaustive analysis with deep insights, correlations, and nuanced observations.",
    }.get(state.depth, "")

    user_prompt = f"""Topic: {state.topic}
{plan_context}

=== RESEARCH DATA TO ANALYZE ===
{state.raw_research[:6000]}

{depth_instructions}

Analyze the research thoroughly and produce structured analytical insights."""

    try:
        response = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, temperature=0.2)
        state.total_agent_calls += 1
        state.analysis = response
        state.mark_agent_complete(agent)

        # Detect potential conflicts in the research
        if any(word in response.lower() for word in ["contradict", "conflict", "disagree", "however", "contrary"]):
            state.conflicts_detected.append({
                "type": "analytical_conflict",
                "description": "Analyst identified potentially conflicting information in research data",
                "detected_by": "analyst",
            })
            bus.post(agent, "⚠️ Potential conflicting information detected — flagging for Conflict Resolver",
                     recipient="conflict_resolver", message_type=MessageType.ESCALATION)

        word_count = len(response.split())
        bus.set_agent_status(agent, AgentStatus.COMPLETED,
                             output_preview=f"Analysis: {word_count} words, {len(state.conflicts_detected)} conflicts flagged")
        bus.post(agent, f"✅ Analysis complete: {word_count} words, {len(state.conflicts_detected)} conflicts detected",
                 recipient="writer", message_type=MessageType.TASK_RESULT,
                 metadata={"word_count": word_count, "conflicts": len(state.conflicts_detected)})

    except Exception as e:
        error_msg = str(e)
        state.mark_agent_failed(agent, error_msg)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error_msg)
        bus.post(agent, f"❌ Analyst failed: {error_msg}", message_type=MessageType.ERROR)
        logger.error(f"Analyst agent error: {e}")

    return state

