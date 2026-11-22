"""
Fact Checker Agent — verifies factual claims in the report.
"""
import json
import logging
from core.llm import call_llm_with_retry
from core.state import ResearchState, FactCheckResult
from core.communication import bus, AgentStatus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a rigorous Fact Checker AI. Your job is to verify factual claims in research reports.

Analyze the report and identify 8-15 specific factual claims that can be evaluated.

For each claim, evaluate against the provided research data and return ONLY a valid JSON array.

JSON format:
[
  {
    "claim": "The specific claim text (verbatim or paraphrased)",
    "status": "verified|unsupported|conflicting|unverifiable",
    "evidence": "Brief evidence or reason for this status",
    "confidence": 0.0-1.0
  },
  ...
]

Status definitions:
- "verified": claim is directly supported by the research data provided
- "unsupported": claim makes a specific assertion not backed by the research data
- "conflicting": claim contradicts information in the research data
- "unverifiable": claim cannot be confirmed or denied from available data (general knowledge)

IMPORTANT:
- Do NOT fabricate evidence
- If a claim is general knowledge not from search results, mark as "unverifiable"
- Specific numbers/statistics should be "unsupported" unless from the provided data
- Be honest — a mix of statuses is expected and shows thorough checking
- Focus on factual assertions, not subjective claims
"""


def run_fact_checker(state: ResearchState) -> ResearchState:
    """Execute the Fact Checker agent."""
    agent = "fact_checker"
    bus.set_agent_status(agent, AgentStatus.WORKING, task="Verifying factual claims")
    bus.post(agent, "✅ Starting fact verification of all claims in the report…",
             message_type=MessageType.TASK_ASSIGN)

    if not state.draft_report:
        error = "No draft report available for fact checking"
        state.mark_agent_failed(agent, error)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error)
        bus.post(agent, f"❌ {error}", message_type=MessageType.ERROR)
        return state

    user_prompt = f"""Topic: {state.topic}

=== RESEARCH DATA (ground truth) ===
{state.raw_research[:3000]}

=== REPORT TO FACT-CHECK ===
{state.draft_report[:3000]}

Identify and verify 8-15 specific factual claims from the report. Return ONLY the JSON array."""

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

        # Find JSON array
        start = clean.find("[")
        end = clean.rfind("]") + 1
        if start >= 0 and end > start:
            clean = clean[start:end]

        fc_data = json.loads(clean)
        fact_checks = []
        for item in fc_data:
            fc = FactCheckResult(
                claim=item.get("claim", ""),
                status=item.get("status", "unverifiable"),
                evidence=item.get("evidence", ""),
                confidence=float(item.get("confidence", 0.5)),
            )
            fact_checks.append(fc)

        state.fact_check_results = fact_checks
        state.mark_agent_complete(agent)

        # Summarize results
        verified = sum(1 for fc in fact_checks if fc.status == "verified")
        unsupported = sum(1 for fc in fact_checks if fc.status == "unsupported")
        conflicting = sum(1 for fc in fact_checks if fc.status == "conflicting")
        unverifiable = sum(1 for fc in fact_checks if fc.status == "unverifiable")

        summary = (f"Fact check: {len(fact_checks)} claims — "
                   f"✅{verified} verified, ⚠️{unsupported} unsupported, "
                   f"❌{conflicting} conflicting, ❓{unverifiable} unverifiable")

        bus.set_agent_status(agent, AgentStatus.COMPLETED, output_preview=summary)
        bus.post(agent, f"✅ {summary}",
                 recipient="reviewer", message_type=MessageType.TASK_RESULT,
                 metadata={"verified": verified, "unsupported": unsupported,
                            "conflicting": conflicting, "total": len(fact_checks)})

        # Flag conflicts
        if conflicting > 0:
            state.conflicts_detected.append({
                "type": "fact_conflict",
                "description": f"{conflicting} conflicting claims detected during fact-checking",
                "detected_by": "fact_checker",
                "details": [fc.claim for fc in fact_checks if fc.status == "conflicting"][:3],
            })
            bus.post(agent, f"⚠️ {conflicting} conflicting claims found — routing to Conflict Resolver",
                     recipient="conflict_resolver", message_type=MessageType.ESCALATION)

    except json.JSONDecodeError as e:
        logger.warning(f"Fact checker JSON parse failed: {e}")
        # Create basic fact checks from response text
        state.fact_check_results = [
            FactCheckResult(
                claim=f"General claims in report about {state.topic}",
                status="unverifiable",
                evidence="Fact checker encountered a formatting issue; manual review recommended",
                confidence=0.5,
            )
        ]
        state.mark_agent_complete(agent)
        bus.set_agent_status(agent, AgentStatus.COMPLETED,
                             output_preview="Fact check completed with limited detail")
        bus.post(agent, "✅ Fact check completed (simplified due to parsing issue)",
                 message_type=MessageType.TASK_RESULT)

    except Exception as e:
        error_msg = str(e)
        state.mark_agent_failed(agent, error_msg)
        bus.set_agent_status(agent, AgentStatus.FAILED, error=error_msg)
        bus.post(agent, f"❌ Fact checker failed: {error_msg}", message_type=MessageType.ERROR)
        logger.error(f"Fact checker error: {e}")

    return state

