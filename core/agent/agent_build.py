import logging
from .agent_planner import ExperienceMemory, Exp
from .agent_memory import MemoryStore
from .agent_actor import AgentActor
from ..services.llm_service import client
from ..tools import ToolRegistry, PythonREPLTool, SearchTool, FileReadTool, FileWriteTool, ListDirTool

logger = logging.getLogger(__name__)

class BrainAgent:
    def __init__(self, sys_prompt: str, tools=None):
        self.sys_prompt = sys_prompt
        # Import dynamically here to avoid circular imports if any
        from ..services.llm_service import model
        
        self.memory = MemoryStore(encoder=model, llm=client)
        self.exp_memory = ExperienceMemory()
        
        # Initialize default ToolRegistry if no tools list is provided
        if tools is None:
            tools = [
                PythonREPLTool(), 
                SearchTool(),
                FileReadTool(),
                FileWriteTool(),
                ListDirTool()
            ]
            
        self.registry = ToolRegistry(tools=tools)
        self.actor = AgentActor(registry=self.registry)

    def think(self, user_prompt: str, trajectory: list = None) -> str:
        """
        Generates the next thought and tool command based on current state.
        """
        trajectory = trajectory or []
        context = self.memory.retrieve_context(user_prompt)
        
        # Retrieve past experiences
        exp_context = self.exp_memory.retrieve(user_prompt)
        exp_text = "\n".join([e.get("summary", "") for e in exp_context])
        
        # Use the registry to get exactly what the LLM needs to see
        tools_schema = self.registry.get_tools_schema_str()
        
        trajectory_str = ""
        for i, step in enumerate(trajectory):
            trajectory_str += f"Step {i+1}:\nThought and Action: {step['tool_call']}\nObservation: {step['observation']}\n\n"
        
        prompt = f"""
        System: {self.sys_prompt}
        
        You have access to the following tools:
        {tools_schema}
        
        Memory Context (Facts):
        {context}
        
        Past Experiences (Lessons Learned):
        {exp_context}
        
        User Request:
        {user_prompt}
        
        Current Trajectory:
        {trajectory_str}
        
        Decide the best next step by providing your reasoning.
        If you need to use a tool, return a JSON block anywhere in your response:
        ```json
        {{"tool": "tool_name", "kwargs": {{"arg_name": "value"}}}}
        ```
        If you have successfully completed the task, output your final answer starting with "FINAL_ANSWER: ".
        """
        return client.generate(user_prompt=prompt, temperature=0.2)

    def act(self, llm_response: str) -> str:
        """Executes the tool call parsed from the LLM response"""
        return self.actor.act(llm_response)

    def learn(self, exp: Exp):
        """Saves an experience and stores the final answer as a semantic memory"""
        self.exp_memory.add_exp(exp)
        if exp.final_answer:
            self.memory.add(content=exp.final_answer, metadata={"task": str(exp.task_prompt)})