from PySide6.QtCore import QObject, Signal

class AgentSignals(QObject):
    """
    Custom signals for communicating from the Agent Thread to the Main Window.
    """
    # Emitted when the agent analysis/thinking is complete
    # data: {"analysis": str, "tasks": List[str]}
    thinker_done = Signal(dict)
    
    # Emitted when a new plan step is decided
    # data: {"step": int, "task": str, "decision": dict}
    plan_updated = Signal(dict)
    
    # Emitted when a tool observation is ready
    # data: {"tool": str, "observation": str}
    observation_ready = Signal(dict)
    
    # Emitted when the final answer is ready
    # data: {"answer": str}
    final_answer_ready = Signal(dict)
    
    # Emitted for general log or status updates
    status_update = Signal(str)
    
    # Emitted when the agent execution starts/stops
    started = Signal()
    finished = Signal()
    error = Signal(str)
