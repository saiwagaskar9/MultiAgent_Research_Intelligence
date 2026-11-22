"""
Agent Communication Bus — structured message passing between agents.
Provides a thread-safe activity log and task handoff tracker.
"""
import uuid
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting_approval"


class MessageType(str, Enum):
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    FEEDBACK = "feedback"
    ESCALATION = "escalation"
    APPROVAL_REQUEST = "approval_request"
    SYSTEM = "system"
    ERROR = "error"


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    sender: str = ""
    recipient: str = ""
    message_type: MessageType = MessageType.SYSTEM
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    name: str
    display_name: str
    icon: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: str = ""
    output_preview: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: str = ""
    execution_count: int = 0

    @property
    def elapsed_seconds(self) -> float:
        import time
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return round(end - self.start_time, 2)


class CommunicationBus:
    """
    Central communication hub for all agents.
    Maintains message log, agent states, and task handoffs.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.messages: List[AgentMessage] = []
        self.agent_states: Dict[str, AgentState] = {}
        self.current_research_state: Optional[Any] = None
        self.is_pipeline_running: bool = False
        self.pipeline_error: str = ""
        self._initialize_agents()

    def set_current_state(self, state: Any):
        with self._lock:
            self.current_research_state = state

    def get_current_state(self) -> Optional[Any]:
        with self._lock:
            return self.current_research_state

    def set_pipeline_running(self, running: bool, error: str = ""):
        with self._lock:
            self.is_pipeline_running = running
            if error:
                self.pipeline_error = error
            elif running:
                self.pipeline_error = ""

    def is_running(self) -> bool:
        with self._lock:
            return self.is_pipeline_running

    def _initialize_agents(self):
        agents = [
            ("planner",          "Research Planner",       "🗺️"),
            ("researcher",       "Research Agent",         "🔍"),
            ("analyst",          "Data Analyst",           "📊"),
            ("writer",           "Content Writer",         "✍️"),
            ("fact_checker",     "Fact Checker",           "✅"),
            ("reviewer",         "Reviewer Agent",         "⭐"),
            ("conflict_resolver","Conflict Resolver",      "⚖️"),
            ("human",            "Human Supervisor",       "👤"),
            ("system",           "System Orchestrator",    "🤖"),
        ]
        for name, display, icon in agents:
            self.agent_states[name] = AgentState(
                name=name, display_name=display, icon=icon
            )

    def reset(self):
        """Reset for a new research session."""
        with self._lock:
            self.messages.clear()
            self._initialize_agents()

    def post(
        self,
        sender: str,
        content: str,
        recipient: str = "all",
        message_type: MessageType = MessageType.SYSTEM,
        metadata: Optional[Dict] = None,
    ) -> AgentMessage:
        msg = AgentMessage(
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
        )
        with self._lock:
            self.messages.append(msg)
        return msg

    def set_agent_status(
        self,
        agent_name: str,
        status: AgentStatus,
        task: str = "",
        output_preview: str = "",
        error: str = "",
    ):
        import time
        with self._lock:
            if agent_name not in self.agent_states:
                return
            state = self.agent_states[agent_name]
            state.status = status
            if task:
                state.current_task = task
            if output_preview:
                state.output_preview = output_preview[:300]
            if error:
                state.error_message = error

            if status == AgentStatus.WORKING:
                state.start_time = time.time()
                state.end_time = None
                state.execution_count += 1
            elif status in (AgentStatus.COMPLETED, AgentStatus.FAILED):
                state.end_time = time.time()

    def get_messages(self) -> List[AgentMessage]:
        with self._lock:
            return list(self.messages)

    def get_agent_states(self) -> Dict[str, AgentState]:
        with self._lock:
            return dict(self.agent_states)

    def get_timeline_entries(self) -> List[Dict]:
        """Return messages formatted for timeline display."""
        entries = []
        for msg in self.get_messages():
            state = self.agent_states.get(msg.sender, None)
            icon = state.icon if state else "💬"
            display = state.display_name if state else msg.sender.title()
            entries.append({
                "time": msg.timestamp,
                "agent": display,
                "icon": icon,
                "type": msg.message_type.value,
                "content": msg.content,
                "metadata": msg.metadata,
            })
        return entries


# Global singleton bus instance
bus = CommunicationBus()

