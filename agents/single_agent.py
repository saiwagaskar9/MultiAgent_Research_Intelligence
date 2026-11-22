"""
Single-Agent Research Mode — entire research done by one agent for comparison.
"""
import logging
from core.llm import call_llm_with_retry
from core.state import ResearchState, ResearchPlan, ResearchFinding
from core.communication import bus, AgentStatus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a comprehensive Research AI. Conduct complete research on the given topic and write a full report in a single pass.

Write a complete research report with these sections:
# [Topic]: Research Report

## Abstract
## 1. Introduction
## 2. Background
## 3. Current State
## 4. Analysis
## 5. Key Findings
## 6. Advantages
## 7. Challenges
## 8. Future Scope
## 9. Conclusion
## 10. References (note: sources based on general knowledge)

Be thorough, professional, and accurate. Minimum 1000 words."""


def run_single_agent(state: ResearchState) -> ResearchState:
    """Execute research using a single agent (for comparison mode)."""
    agent = "system"
    state.mode = "single_agent"
    bus.post(agent, f"🤖 Single-Agent Mode: Starting unified research for **{state.topic}**",
             message_type=MessageType.SYSTEM)
    bus.set_agent_status(agent, AgentStatus.WORKING,
                         task=f"Single-agent research: {state.topic}")

    user_prompt = f"""Research Topic: {state.topic}
Depth: {state.depth}
Additional Instructions: {state.additional_instructions or 'None'}

Conduct comprehensive research and write a complete report."""

    try:
        response = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, temperature=0.4)
        state.total_agent_calls += 1

        # Populate state fields for downstream use
        state.raw_research = response
        state.analysis = f"[Single-agent analysis embedded in report]"
        state.draft_report = response
        state.final_report = response
        state.plan = ResearchPlan(
            topic=state.topic,
            objectives=["Complete research on topic"],
            sub_questions=["What is the topic?", "What are the key aspects?"],
            methodology="Single-agent synthesis",
            scope=state.topic,
            expected_sections=["Introduction", "Background", "Analysis", "Conclusion"],
        )
        state.mark_agent_complete(agent)
        bus.set_agent_status(agent, AgentStatus.COMPLETED,
                             output_preview=f"Single-agent report: {len(response.split())} words")
        bus.post(agent, f"✅ Single-agent research complete: {len(response.split())} words",
                 message_type=MessageType.TASK_RESULT)

    except Exception as e:
        error_msg = str(e)
        state.mark_agent_failed(agent, error_msg)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error_msg)
        bus.post(agent, f"❌ Single-agent research failed: {error_msg}", message_type=MessageType.ERROR)
        logger.error(f"Single agent error: {e}")

    return state

