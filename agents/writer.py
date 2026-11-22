"""
Content Writer Agent — transforms research and analysis into a professional report.
"""
import logging
from core.llm import call_llm_with_retry
from core.state import ResearchState
from core.communication import bus, AgentStatus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Academic Research Writer. Your job is to write professional, well-structured research reports.

Write a complete, detailed research report following this EXACT structure:

---

# [Research Topic]: A Comprehensive Analysis

## Abstract
[150-200 word executive summary capturing the essence of the research, key findings, and conclusions]

## 1. Introduction
[Engaging introduction establishing context, importance, and relevance of the topic. 200-300 words]

## 2. Research Objectives
[Clear, numbered list of what this research aims to achieve]

## 3. Methodology
[How the research was conducted — data collection methods, analysis approach, limitations]

## 4. Background and Context
[Historical context, definitions, foundational concepts. 300-400 words]

## 5. Current State and Developments
[Latest trends, recent breakthroughs, state-of-the-art. 400-500 words]

## 6. Detailed Analysis
[In-depth analysis organized by themes or categories. 500-700 words]

## 7. Key Findings
[Bulleted list of the most important discoveries and insights]

## 8. Advantages and Opportunities
[Positive aspects, benefits, opportunities]

## 9. Challenges and Limitations
[Current challenges, limitations, risks, controversies]

## 10. Practical Applications
[Real-world applications, use cases, examples]

## 11. Future Scope and Directions
[Future trends, research directions, predictions. 300-400 words]

## 12. Conclusion
[Strong, synthesizing conclusion. 200-300 words]

## 13. References
[List of sources in numbered format - ONLY real sources from search results]

---

CRITICAL RULES:
- Write in professional academic style
- Use ONLY information from the provided research and analysis
- Do NOT invent statistics, quotes, or references
- Every claim must be supported by the research data
- If you cite a source URL, use ONLY URLs from the search results provided
- Minimum 1500 words for standard depth, 2500 for deep
"""


def run_writer(state: ResearchState, feedback: str = "") -> ResearchState:
    """Execute the Content Writer agent."""
    agent = "writer"

    if feedback:
        task = f"Revising report (iteration {state.review_iteration}) based on reviewer feedback"
        bus.set_agent_status(agent, AgentStatus.WORKING, task=task)
        bus.post(agent, f"✍️ Revising report based on reviewer feedback (iteration {state.review_iteration})…",
                 message_type=MessageType.FEEDBACK)
    else:
        bus.set_agent_status(agent, AgentStatus.WORKING, task="Drafting research report")
        bus.post(agent, "✍️ Drafting comprehensive research report…",
                 message_type=MessageType.TASK_ASSIGN)

    if not state.raw_research and not state.analysis:
        error = "No research or analysis data available"
        state.mark_agent_failed(agent, error)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error)
        bus.post(agent, f"❌ {error}", message_type=MessageType.ERROR)
        return state

    # Format context
    plan_context = ""
    if state.plan:
        plan_context = f"""
Research Plan:
- Objectives: {', '.join(state.plan.objectives[:3])}
- Methodology: {state.plan.methodology}
- Expected Sections: {', '.join(state.plan.expected_sections)}
"""

    depth_instructions = {
        "quick":    "Write a concise but complete report (1000-1500 words).",
        "standard": "Write a comprehensive report (1500-2500 words).",
        "deep":     "Write an exhaustive, highly detailed report (2500-4000 words).",
    }.get(state.depth, "")

    format_instructions = {
        "academic":    "Use formal academic language, structured argument flow.",
        "technical":   "Use precise technical terminology, detailed specifications.",
        "executive":   "Use executive summary style, focus on business value and decisions.",
        "simplified":  "Use clear, accessible language suitable for a general audience.",
    }.get(state.report_format, "")

    feedback_section = ""
    if feedback:
        feedback_section = f"""
=== REVIEWER FEEDBACK (MUST ADDRESS ALL POINTS) ===
{feedback}
=== END FEEDBACK ===

This is revision {state.review_iteration}. Address ALL feedback points explicitly.
"""

    # Fact check context
    fc_context = ""
    if state.fact_check_results:
        unsupported = [fc for fc in state.fact_check_results if fc.status == "unsupported"]
        if unsupported:
            fc_context = f"\n=== FACT CHECK WARNINGS ===\nRemove or qualify these unsupported claims:\n"
            for fc in unsupported[:5]:
                fc_context += f"- UNSUPPORTED: {fc.claim[:100]}\n"

    user_prompt = f"""Topic: {state.topic}
{plan_context}
{feedback_section}

=== RESEARCH DATA ===
{state.raw_research[:4000]}

=== ANALYTICAL INSIGHTS ===
{state.analysis[:3000]}

{fc_context}

{depth_instructions}
{format_instructions}

Write the complete, professional research report now."""

    try:
        response = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, temperature=0.4)
        state.total_agent_calls += 1
        state.draft_report = response
        state.mark_agent_complete(agent)

        word_count = len(response.split())
        bus.set_agent_status(agent, AgentStatus.COMPLETED,
                             output_preview=f"Report: {word_count} words drafted")
        bus.post(agent, f"✅ Report drafted: {word_count} words across all sections",
                 recipient="fact_checker", message_type=MessageType.TASK_RESULT,
                 metadata={"word_count": word_count, "iteration": state.review_iteration})

    except Exception as e:
        error_msg = str(e)
        state.mark_agent_failed(agent, error_msg)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error_msg)
        bus.post(agent, f"❌ Writer failed: {error_msg}", message_type=MessageType.ERROR)
        logger.error(f"Writer agent error: {e}")

    return state

