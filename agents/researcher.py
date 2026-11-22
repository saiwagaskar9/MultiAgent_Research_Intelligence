"""
Research Agent — gathers information using web search + LLM synthesis.
"""
import logging
from core.llm import call_llm_with_retry
from core.state import ResearchState, ResearchFinding
from core.communication import bus, AgentStatus, MessageType
from tools.search import multi_query_search

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Research Agent. Your job is to conduct thorough research on a topic using the provided web search results and your knowledge.

Produce a COMPREHENSIVE research document with the following structure:

## Key Findings
[Detailed findings with specific facts, statistics, and insights]

## Background and Context
[Historical context, definitions, foundational concepts]

## Current State and Developments
[Latest trends, recent developments, state-of-the-art]

## Technical Details
[Technical aspects, mechanisms, components, methodologies]

## Applications and Use Cases
[Real-world applications, examples, case studies]

## Challenges and Limitations
[Current challenges, limitations, criticisms, unsolved problems]

## Expert Perspectives
[Various viewpoints, expert opinions, academic consensus]

## Sources
[List all source URLs from search results, numbered]

IMPORTANT RULES:
- Use ONLY information from search results and established knowledge
- Do NOT fabricate statistics, quotes, or specific numbers
- Clearly note if information is from search results vs. general knowledge
- If a source URL is available, cite it
- Be comprehensive — this feeds directly into the final research report
"""


def run_researcher(state: ResearchState) -> ResearchState:
    """Execute the Research Agent."""
    agent = "researcher"
    bus.set_agent_status(agent, AgentStatus.WORKING, task=f"Researching: {state.topic}")
    bus.post(agent, f"🔍 Starting web research for: **{state.topic}**",
             message_type=MessageType.TASK_ASSIGN)

    plan = state.plan
    if plan is None:
        bus.post(agent, "⚠️ No research plan found, proceeding with topic directly",
                 message_type=MessageType.SYSTEM)

    # Build search queries from the plan
    if plan and plan.sub_questions:
        search_queries = [state.topic] + plan.sub_questions[:3]
    else:
        search_queries = [
            state.topic,
            f"{state.topic} overview",
            f"{state.topic} challenges applications",
        ]

    bus.post(agent, f"Executing {len(search_queries)} web search queries…",
             message_type=MessageType.SYSTEM)

    # Perform web search
    search_results = multi_query_search(search_queries, max_per_query=5)
    has_web_results = "No web search results" not in search_results

    if has_web_results:
        bus.post(agent, "✅ Web search completed. Synthesizing findings with AI…",
                 message_type=MessageType.SYSTEM)
    else:
        bus.post(agent, "⚠️ Web search unavailable. Using LLM internal knowledge base…",
                 message_type=MessageType.SYSTEM)

    # Depth configuration
    depth_instructions = {
        "quick":    "Provide a concise overview (600-800 words total).",
        "standard": "Provide comprehensive coverage (1000-1500 words total).",
        "deep":     "Provide exhaustive, detailed coverage (1500-2500 words total).",
    }.get(state.depth, "Provide comprehensive coverage.")

    plan_context = ""
    if plan:
        plan_context = f"""
Research Objectives:
{chr(10).join(f'- {o}' for o in plan.objectives)}

Sub-questions to address:
{chr(10).join(f'- {q}' for q in plan.sub_questions)}
"""

    user_prompt = f"""Topic: {state.topic}
{plan_context}
{search_results}

{depth_instructions}

Conduct thorough research following the structured format. Include specific details, cite sources where available."""

    try:
        response = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, temperature=0.3)
        state.total_agent_calls += 1
        state.raw_research = response

        # Extract findings as structured items
        findings = []
        lines = response.split("\n")
        current_section = ""
        current_content = []

        for line in lines:
            if line.startswith("## "):
                if current_section and current_content:
                    findings.append(ResearchFinding(
                        title=current_section,
                        content="\n".join(current_content),
                        source="Research Agent Synthesis",
                        relevance_score=0.9,
                    ))
                current_section = line[3:].strip()
                current_content = []
            elif line.strip():
                current_content.append(line)

        if current_section and current_content:
            findings.append(ResearchFinding(
                title=current_section,
                content="\n".join(current_content),
                source="Research Agent Synthesis",
                relevance_score=0.9,
            ))

        state.findings = findings
        state.mark_agent_complete(agent)

        preview = f"Research complete: {len(findings)} sections, {len(response.split())} words"
        bus.set_agent_status(agent, AgentStatus.COMPLETED, output_preview=preview)
        bus.post(agent, f"✅ Research completed. {preview}",
                 recipient="analyst", message_type=MessageType.TASK_RESULT,
                 metadata={"word_count": len(response.split()), "sections": len(findings),
                            "has_web_results": has_web_results})

    except Exception as e:
        error_msg = str(e)
        state.mark_agent_failed(agent, error_msg)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error_msg)
        bus.post(agent, f"❌ Research agent failed: {error_msg}", message_type=MessageType.ERROR)
        logger.error(f"Researcher agent error: {e}")

    return state

