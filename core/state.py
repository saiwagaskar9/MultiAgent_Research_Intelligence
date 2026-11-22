"""
Shared research state passed between agents.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ResearchPlan:
    topic: str = ""
    objectives: List[str] = field(default_factory=list)
    sub_questions: List[str] = field(default_factory=list)
    methodology: str = ""
    scope: str = ""
    expected_sections: List[str] = field(default_factory=list)


@dataclass
class ResearchFinding:
    title: str = ""
    content: str = ""
    source: str = ""
    relevance_score: float = 0.0


@dataclass
class FactCheckResult:
    claim: str = ""
    status: str = ""   # verified | unsupported | conflicting | unverifiable
    evidence: str = ""
    confidence: float = 0.0


@dataclass
class ReviewResult:
    score: int = 0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    improvement_instructions: str = ""
    approved: bool = False


@dataclass
class ResearchState:
    # Session metadata
    session_id: str = ""
    topic: str = ""
    depth: str = "standard"       # quick | standard | deep
    report_format: str = "academic"
    additional_instructions: str = ""
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())

    # Agent outputs
    plan: Optional[ResearchPlan] = None
    raw_research: str = ""
    findings: List[ResearchFinding] = field(default_factory=list)
    analysis: str = ""
    draft_report: str = ""
    final_report: str = ""
    fact_check_results: List[FactCheckResult] = field(default_factory=list)
    review_result: Optional[ReviewResult] = None

    # Iteration tracking
    review_iteration: int = 0
    max_iterations: int = 3
    quality_threshold: int = 75

    # Human-in-the-loop
    awaiting_human_approval: bool = False
    human_approved: Optional[bool] = None
    human_feedback: str = ""

    # Conflict tracking
    conflicts_detected: List[Dict] = field(default_factory=list)
    conflicts_resolved: List[Dict] = field(default_factory=list)

    # Pipeline tracking
    completed_agents: List[str] = field(default_factory=list)
    failed_agents: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    pipeline_complete: bool = False

    # Execution mode
    mode: str = "multi_agent"   # multi_agent | single_agent

    # Comparison metrics (for single vs multi evaluation)
    execution_time_seconds: float = 0.0
    total_agent_calls: int = 0

    def mark_agent_complete(self, agent_name: str):
        if agent_name not in self.completed_agents:
            self.completed_agents.append(agent_name)

    def mark_agent_failed(self, agent_name: str, error: str):
        if agent_name not in self.failed_agents:
            self.failed_agents.append(agent_name)
        self.errors.append(f"[{agent_name}] {error}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "depth": self.depth,
            "report_format": self.report_format,
            "mode": self.mode,
            "review_iteration": self.review_iteration,
            "quality_score": self.review_result.score if self.review_result else 0,
            "approved": self.human_approved,
            "completed_agents": self.completed_agents,
            "failed_agents": self.failed_agents,
            "execution_time": self.execution_time_seconds,
            "total_agent_calls": self.total_agent_calls,
            "fact_checks": len(self.fact_check_results),
            "conflicts_detected": len(self.conflicts_detected),
            "conflicts_resolved": len(self.conflicts_resolved),
        }

