"""
Agent pipeline for other Apps to connect and use the agent capabilities.
"""
from typing import Optional, Any, Dict, List

from ..core.agent.agent_build import BrainAgent
from ..core.agent.agent_loop import agent_loop

class AgentNotBuiltError(Exception):
    pass

class IRYM1AgentPipeline:
    def __init__(self, sys_prompt: Optional[str] = None):

        self.sys_prompt = sys_prompt or """
You are an autonomous AI agent.
Your tasks:
1 analyze datasets
2 apply data science pipelines
3 generate descriptive analysis
4 suggest improvements
"""
        self.agent: Optional[BrainAgent] = None
        # chat memory storage
        self.memory: Dict[str, List[Dict]] = {}

    def build_agent(self) -> BrainAgent:
        self.agent = BrainAgent(self.sys_prompt)
        return self.agent

    def get_agent(self) -> BrainAgent:
        if self.agent is None:
            self.build_agent()
        return self.agent

    def get_chat_memory(self, chat_id:str):
        if chat_id not in self.memory:
            self.memory[chat_id] = []
        return self.memory[chat_id]

    def run_agent(self,input_data:Any, chat_id:str):
        agent = self.get_agent()
        history = self.get_chat_memory(chat_id)

        # build context
        context = {
            "history":history,
            "input":input_data}

        answer = agent_loop(agent,context)
        # store conversation
        history.append({"role":"user", "content":input_data})

        history.append({"role":"assistant", "content":answer})
        if answer:
            return {
                "answer":answer,
                "chat_id":chat_id,
                "memory_size":len(history)
            }

        return {
            "status":"failed",
            "message":"Agent failed"
        }