import logging
from PySide6.QtCore import QThread
from .signals import AgentSignals
from core.agent.agent_build import BrainAgent
from core.agent.agent_loop import agent_loop

logger = logging.getLogger(__name__)

class AgentWorker(QThread):
    """
    Runs the agent loop in a separate thread.
    """
    def __init__(self, user_prompt: str):
        super().__init__()
        self.user_prompt = user_prompt
        self.signals = AgentSignals()
        self.agent = BrainAgent(sys_prompt="You are the Baby Agent, a professional AI assistant with GUI visualization.")

    def run(self):
        self.signals.started.emit()
        try:
            # The agent_loop will call this internal function to emit signals
            def gui_notifier(event_type, data):
                if event_type == "analysis":
                    self.signals.thinker_done.emit(data)
                elif event_type == "plan":
                    self.signals.plan_updated.emit(data)
                elif event_type == "observation":
                    self.signals.observation_ready.emit(data)
                elif event_type == "final_answer":
                    self.signals.final_answer_ready.emit(data)
                elif event_type == "status":
                    self.signals.status_update.emit(data["msg"])

            # Run the actual agent loop
            agent_loop(self.agent, self.user_prompt, ui_callback=gui_notifier)
            
        except Exception as e:
            logger.error(f"Error in AgentWorker: {e}", exc_info=True)
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
