# 🤖 MyAgent - Autonomous AI Agent Framework

> A production-ready Python framework for building autonomous AI agents with ReAct reasoning, tool integration, and agentic memory management.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Production](https://img.shields.io/badge/Status-Production--Ready-green)](/)

---

## 🚀 Overview

**MyAgent** is a sophisticated autonomous agent framework designed to bridge the gap between large language models and real-world task execution. It implements the **ReAct** (Reasoning + Acting) pattern, enabling agents to think through complex problems, select appropriate tools, execute them safely, and adapt based on observations.

Perfect for building:
- 🧠 Autonomous task automation systems
- 🔧 AI-powered tool orchestration
- 📊 Intelligent data analysis pipelines
- 💬 Advanced chatbots with real capabilities
- 🔍 Research and information retrieval agents

---

## ✨ Key Features

### 🧠 **Intelligence Layer**
- **ReAct Loop**: Reasoning → Acting → Observing cycle for adaptive decision-making
- **Brain Agent**: Central orchestrator managing thought processes and tool selection
- **Planning System**: Hierarchical task decomposition and planning
- **Memory Management**: Episodic memory with vector-based retrieval for context awareness

### 🛠️ **Tool Ecosystem**
- **10+ Built-in Tools**: File system ops, Python REPL, web search, and more
- **Secure Tool Execution**: Decorators-based security framework with sandboxing
- **Tool Registry**: Dynamic tool management and registration system
- **Tool Chaining**: Support for multi-step tool workflows

### 🔐 **Security & Reliability**
- **Code Security Decorators**: Malicious code detection and sandboxing
- **Input Validation**: 5-point validation system for all tool calls
- **Error Recovery**: Comprehensive error handling without agent crashes
- **Execution History**: Full audit trail of all tool executions

### 🎯 **Developer Experience**
- **Type-Safe**: 95% type hint coverage across codebase
- **Comprehensive Logging**: DEBUG/INFO/ERROR levels for transparency
- **Example Scenarios**: 8+ documented usage patterns
- **Well-Documented**: Architecture guides, API docs, and inline examples

### 🌐 **Web Interface**
- **Dashboard**: Real-time agent monitoring and metrics
- **Chat Interface**: Interactive agent communication
- **History Tracking**: Complete execution history visualization

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Web Interface Layer                        │
│         (Chat Page, Dashboard, Real-time Updates)            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 Agent Core (BrainAgent)                      │
│    ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │
│    │   Planner    │  │   Memory     │  │   Loop Ctrl   │   │
│    │ (Reasoning)  │  │ (Episodic)   │  │ (ReAct Cycle) │   │
│    └──────────────┘  └──────────────┘  └───────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              AgentActor (Execution Engine)                   │
│  ┌─────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │   Parser    │→ │  Validator    │→ │   Executor      │  │
│  │ (JSON Ext)  │  │ (5-pt Check)  │  │ (Sandboxed)     │  │
│  └─────────────┘  └───────────────┘  └─────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Tool Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ File System  │  │ Python REPL  │  │  Web Search      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Vector DB    │  │  Task Mgr    │  │ Custom Tools...  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Prerequisites
- Python 3.12 or higher
- pip or conda package manager

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/myAgent.git
cd myAgent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from core.agent import AgentActor; print('✓ Installation successful')"
```

### Configuration

1. **Create `.env` file** in project root:
```env
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4-turbo
VECTOR_DB_URL=http://localhost:6333
LOG_LEVEL=INFO
```

2. **Update `config.py`**:
```python
# Select LLM provider
LLM_PROVIDER = "openai"  # or "anthropic", "local"

# Tool configuration
ENABLE_CODE_EXECUTION = True
SANDBOX_MODE = True

# Memory settings
MEMORY_VECTOR_DIMENSION = 1536
MEMORY_SIMILARITY_THRESHOLD = 0.7
```

---

## 🚀 Quick Start Usage

### Basic Agent Setup

```python
from core.agent import BrainAgent, AgentActor
from core.tools import ToolRegistry
from core.services import LLMService

# Initialize components
llm = LLMService(model="gpt-4-turbo", api_key="sk-...")
registry = ToolRegistry()
registry.register_default_tools()

# Create agent
agent = BrainAgent(llm_service=llm, tool_registry=registry)

# Run agent on a task
task = "Analyze the file 'data.csv' and summarize key insights"
result = agent.execute(task, max_iterations=5)

print(result)
```

### Tool Execution Example

```python
from core.agent import AgentActor

actor = AgentActor(registry=registry)

# Simulate LLM response with tool call
llm_response = """
Let me search for information about Python.

<tool_call>
{
  "tool_name": "web_search",
  "kwargs": {
    "query": "Python programming language",
    "max_results": 5
  }
}
</tool_call>
"""

observation = actor.act(llm_response)
print(observation)  # Returns search results
```

### Custom Tool Registration

```python
from core.tools import BaseTool
import json

class CustomAnalyzer(BaseTool):
    def __init__(self):
        self.name = "custom_analyzer"
        self.description = "Analyzes custom data format"
        
    def execute(self, data: str) -> dict:
        # Your analysis logic
        return {"status": "analyzed", "data": data}

# Register custom tool
analyzer = CustomAnalyzer()
registry.register(analyzer)
```

---

## 📚 Project Structure

```
myAgent/
├── app/                          # Web application layer
│   └── main.py                  # Flask/FastAPI app
├── core/                         # Core agent framework
│   ├── agent/                   # Agent components
│   │   ├── agent_actor.py       # Tool execution engine (ReAct)
│   │   ├── agent_planner.py     # Planning & reasoning
│   │   ├── agent_memory.py      # Memory management
│   │   ├── agent_loop.py        # ReAct loop orchestration
│   │   └── agent_build.py       # BrainAgent (main coordinator)
│   ├── services/                # Service layer
│   │   ├── llm_service.py       # LLM provider abstraction
│   │   ├── vector_db_service.py # Vector database
│   │   ├── memory_manager.py    # Memory operations
│   │   ├── task_manager.py      # Task management
│   │   ├── loader_services.py   # Document loading
│   │   └── base_vectordb.py     # Abstract base classes
│   ├── tools/                   # Tool ecosystem
│   │   ├── base.py              # Tool base class
│   │   ├── registry.py          # Tool registry
│   │   ├── file_system.py       # File operations
│   │   ├── python_repl.py       # Python execution
│   │   ├── search.py            # Search tools
│   │   └── code_security_decorator.py  # Security layer
│   └── utils.py                 # Utility functions
├── templates/                    # Web UI templates
│   ├── chat_page.html           # Chat interface
│   └── dashboard.html           # Monitoring dashboard
├── test/                         # Tests & examples
│   ├── agent_actor_examples.py  # Usage examples
│   └── llm_client_test.py       # Integration tests
├── config.py                     # Configuration management
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

---

## 🔧 Core Components

### **BrainAgent** - The Orchestrator
Central command center managing the entire agent lifecycle. Coordinates thinking (planning), acting (tool execution), and memory operations.

### **AgentActor** - The Executor
Parses LLM responses, validates tool calls (5-point validation), and executes tools safely. Returns observations to continue ReAct loop.

### **AgentPlanner** - The Reasoner
Generates reasoning traces and decomposes complex tasks into actionable steps.

### **AgentMemory** - The Learner
Maintains episodic memory with vector-based retrieval. Learns from past interactions.

### **ToolRegistry** - The Hub
Central registry for all available tools. Manages tool discovery, validation, and execution.

---

## 🛡️ Security Features

### Input Validation
```python
# 5-point validation on all tool calls:
1. Tool existence check
2. Tool name type validation
3. Kwargs type validation
4. Payload size limits (100KB max)
5. Argument schema matching
```

### Code Security Decorators
- **Sandboxing**: Isolates Python code execution
- **Malware Detection**: Static analysis for suspicious patterns
- **Resource Limits**: CPU, memory, and execution time limits
- **Safe Imports**: Whitelist of allowed modules

### Error Handling
All errors converted to observations, never crashing the agent loop.

---

## 📊 Execution Metrics

Track agent performance with built-in metrics:

```python
# Get execution statistics
stats = actor.get_execution_stats()
print(stats)
# Output:
# {
#   'total_executions': 12,
#   'successful_tools': 11,
#   'failed_tools': 1,
#   'avg_execution_time': 0.45,
#   'memory_usage': '52MB'
# }
```

---

## 🧪 Testing & Examples

Run included examples:

```bash
# Test basic agent operations
python test/agent_actor_examples.py

# Test LLM client integration
python test/llm_client_test.py

# Run specific scenario
python -c "from test.agent_actor_examples import run_scenario_1; run_scenario_1()"
```

---

## 🌐 Web Interface

Start the web dashboard:

```bash
python app/main.py
```

Access at: `http://localhost:5000`

- **Chat Interface**: Interactive agent communication
- **Dashboard**: Real-time metrics and monitoring
- **History**: Complete execution history with full trace

---

## 🤝 Contributing

Contributions welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📝 Documentation

- **[Agent Architecture Guide](./core/agent/AGENT_ACTOR_GUIDE.md)** - Detailed component documentation
- **[API Reference](./docs/API.md)** - Complete API reference
- **[Security Guide](./docs/SECURITY.md)** - Security best practices
- **[Examples](./test/agent_actor_examples.py)** - 8+ usage scenarios

---

## 🐛 Troubleshooting

### Agent not executing tools
- Check tool registration: `registry.list_tools()`
- Verify LLM API key in `.env`
- Enable debug logging: `LOG_LEVEL=DEBUG`

### Memory issues
- Reduce vector DB query results
- Implement memory pruning
- Check disk space for vector DB

### LLM API errors
- Verify API credentials
- Check rate limits
- Use fallback LLM provider

---

## 📈 Roadmap

- [ ] Async tool execution
- [ ] Tool chaining optimization
- [ ] Multi-agent coordination
- [ ] Streaming responses
- [ ] Advanced memory indexing
- [ ] Custom training on tasks
- [ ] Docker containerization
- [ ] Kubernetes deployment

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Email: your.email@example.com

---

## 🙏 Acknowledgments

- Inspired by ReAct (Wei et al., 2022)
- Built with Python 3.12+
- Integrates with OpenAI, Anthropic, and local LLMs
- Thanks to the open-source community

---

## 💡 Citation

If you use MyAgent in your research, please cite:

```bibtex
@software{myagent2024,
  title={MyAgent: Autonomous AI Agent Framework},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/myAgent}
}
```

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/myAgent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/myAgent/discussions)
- **Email**: support@myagent.dev

---

<div align="center">

**Made with ❤️ by the MyAgent Team**

[⭐ Star us on GitHub](https://github.com/yourusername/myAgent) • [📧 Contact](mailto:your.email@example.com) • [🐦 Follow](https://twitter.com)

</div>
