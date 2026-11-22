"""
Research Planner Agent — decomposes the research topic into a structured plan.
"""
import json
import logging
from core.llm import call_llm_with_retry
from core.state import ResearchState, ResearchPlan
from core.communication import bus, AgentStatus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Research Planner AI. Your job is to analyze a research topic and create a comprehensive, structured research plan.

You MUST respond ONLY with a valid JSON object — no markdown fences, no explanations outside the JSON.

JSON schema:
{
  "objectives": ["objective 1", "objective 2", ...],
  "sub_questions": ["question 1", "question 2", ...],
  "methodology": "description of research methodology",
  "scope": "scope and boundaries of the research",
  "expected_sections": ["Introduction", "Background", ...]
}

Guidelines:
- objectives: 3-5 clear, measurable research objectives
- sub_questions: 5-8 specific research questions to answer
- methodology: how to collect and analyze information
- scope: what is included/excluded
- expected_sections: 8-12 report sections
"""


def run_planner(state: ResearchState) -> ResearchState:
    """Execute the Research Planner agent."""
    agent = "planner"
    bus.set_agent_status(agent, AgentStatus.WORKING, task=f"Planning research for: {state.topic}")
    bus.post(agent, f"Analyzing topic and creating research plan for: **{state.topic}**",
             message_type=MessageType.TASK_ASSIGN)

    depth_guidance = {
        "quick":    "Create a concise plan with 3 objectives and 4 sub-questions.",
        "standard": "Create a balanced plan with 4 objectives and 6 sub-questions.",
        "deep":     "Create a comprehensive plan with 5 objectives and 8 sub-questions.",
    }.get(state.depth, "")

    user_prompt = f"""Research Topic: {state.topic}
Depth: {state.depth}
{depth_guidance}
Additional Instructions: {state.additional_instructions or 'None'}

Create a detailed research plan following the JSON schema."""

    try:
        response = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, temperature=0.2)
        state.total_agent_calls += 1

        # Parse JSON
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        plan_data = json.loads(clean)
        plan = ResearchPlan(
            topic=state.topic,
            objectives=plan_data.get("objectives", []),
            sub_questions=plan_data.get("sub_questions", []),
            methodology=plan_data.get("methodology", ""),
            scope=plan_data.get("scope", ""),
            expected_sections=plan_data.get("expected_sections", []),
        )
        state.plan = plan
        state.mark_agent_complete(agent)

        summary = f"Plan created: {len(plan.objectives)} objectives, {len(plan.sub_questions)} sub-questions, {len(plan.expected_sections)} sections"
        bus.set_agent_status(agent, AgentStatus.COMPLETED, output_preview=summary)
        bus.post(agent, f"✅ Research plan generated. {summary}",
                 recipient="researcher", message_type=MessageType.TASK_RESULT,
                 metadata={"objectives": plan.objectives[:2]})

    except json.JSONDecodeError as e:
        logger.warning(f"Planner JSON parse failed, using fallback: {e}")
        # Fallback plan
        state.plan = ResearchPlan(
            topic=state.topic,
            objectives=[
                f"Understand the fundamentals of {state.topic}",
                f"Analyze current developments in {state.topic}",
                f"Evaluate challenges and opportunities in {state.topic}",
                f"Identify future directions for {state.topic}",
            ],
            sub_questions=[
                f"What is {state.topic} and how does it work?",
                f"What are the key components of {state.topic}?",
                f"What are the latest advancements in {state.topic}?",
                f"What challenges exist in {state.topic}?",
                f"What are the practical applications of {state.topic}?",
                f"What is the future outlook for {state.topic}?",
            ],
            methodology="Literature review, web research, expert analysis, and comparative evaluation.",
            scope=f"Comprehensive analysis of {state.topic} covering technical, practical, and future aspects.",
            expected_sections=["Abstract", "Introduction", "Background", "Current State",
                               "Analysis", "Applications", "Challenges", "Future Scope", "Conclusion", "References"],
        )
        state.mark_agent_complete(agent)
        bus.set_agent_status(agent, AgentStatus.COMPLETED, output_preview="Fallback research plan created")
        bus.post(agent, "✅ Research plan created (using intelligent fallback due to format issue)",
                 message_type=MessageType.TASK_RESULT)

    except Exception as e:
        error_msg = str(e)
        state.mark_agent_failed(agent, error_msg)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error_msg)
        bus.post(agent, f"❌ Planner failed: {error_msg}", message_type=MessageType.ERROR)
        logger.error(f"Planner agent error: {e}")

    return state

