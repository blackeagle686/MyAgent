#  MyAgent - Autonomous AI Agent Framework

> A production-ready Python framework for building autonomous AI agents with ReAct reasoning, tool integration, and agentic memory management. Now featuring a professional PySide6 Desktop GUI!

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Work in Progress](https://img.shields.io/badge/Status-WIP-yellow)](/)
---

##  Overview

**MyAgent** is a sophisticated autonomous agent framework designed to bridge the gap between large language models and real-world task execution. It implements the **ReAct** (Reasoning + Acting) pattern, enabling agents to think through complex problems, select appropriate tools, execute them safely, and adapt based on observations.

###  New in v1.1
- **Professional Desktop GUI**: A sleek PySide6-based dashboard to visualize thinking/planning live.
- **Hybrid AI & Failover**: Automatic local fallback to Qwen models if OpenRouter APIs fail.
- **Local Embeddings**: High-performance local vector operations using `sentence-transformers/all-MiniLM-L6-v2`.
- **Tool-Aware Decomposition**: The Thinker now "knows" available tools during the first analysis phase.
- **Workspace Sandboxing**: Restricted file operations to the project root for production safety.

---

##  Key Features

###  **Desktop & CLI Interfaces**
- **PySide6 Dashboard**: A premium dark-themed desktop app with "Internal Process" monitoring.
- **Rich CLI**: Beautiful terminal output with panels, tables, and live status updates.
- **Multithreaded**: Agent runs in the background to keep the UI responsive.

###  **Intelligence Layer**
- **Hybrid Reasoning**: Automatic failover to local LLMs (Qwen2.5) for reliability.
- **ReAct Loop**: Reasoning → Acting → Observing cycle for adaptive decision-making.
- **Brain Agent**: Central orchestrator managing thought processes and tool selection.
- **Episodic Memory**: High-speed local embeddings using `SentenceTransformers`.

### 🛠️ **Tool Ecosystem (Secured)**
- **11+ Built-in Tools**: File system, Python REPL, web search, FastAnswer, and more.
- **Production Security**: `@restrict_path`, `@validate_code`, and `@safe_execution` decorators.
- **Workspace Root Control**: Configurable sandbox boundaries for file tools.

---

##  Architecture

```mermaid
graph TD
    UI[Desktop GUI / Rich CLI] --> Agent[BrainAgent]
    Agent --> Thinker[Tool-Aware Thinker]
    Agent --> Planner[Dynamic Planner]
    Agent --> Memory[Episodic Memory]
    
    Thinker -.-> LocalThink[Local Thinker Fallback]
    Planner -.-> LocalPlan[Local Planner Fallback]
    Memory -.-> LocalEmbed[SentenceTransformer Embeddings]
    
    Planner --> Actor[AgentActor]
    Actor --> Security[Security Decorators]
    Security --> Tools[Tool Registry]
    
    Tools --> FST[File System]
    Tools --> REPL[Python REPL]
    Tools --> SRCH[RAG Search]
    Tools --> FAST[Fast Answer]
```

---

##  Installation

### Prerequisites
- Python 3.12 or higher
- `libxcb-cursor0` (for Linux GUI support)

```bash
# Ubuntu/Debian
sudo apt-get install libxcb-cursor0
```

### Quick Start

```bash
# Clone and enter
git clone https://github.com/blackeagle686/myAgent.git
cd myAgent

# Setup environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

##  Usage

### Option 1: The Desktop GUI (Recommended)
Launch the premium dashboard to see the agent's internal thought process in real-time.
```bash
python3 run_gui.py
```

### Option 2: The Rich CLI
Run the agent directly from your terminal with visual status updates.
```bash
python3 run_agent.py "What is the capital of Egypt?" --verbose
```

---

##  Project Structure

- `core/agent/`: The heart of the framework (Brain, Planner, Loop).
- `core/tools/`: The secure tool ecosystem and decorators.
- `gui/`: PySide6 implementation and modern dark styling.
- `config.py`: Central configuration for models (OpenRouter/Local) and API keys.
- `ARCHITECTURE.md`: Deep dive into core module logic.

---

##  Core Components

### **Hybrid Intelligence & Fallback**
The agent uses a **Hybrid LLM Stack**. By default, it uses powerful models via OpenRouter (e.g., Llama 3.1 405B). If an API error occurs, it automatically switches to local models (Qwen2.5-3B for Thinking, Qwen2.5-Coder for Planning) to ensure continuous operation.

### **Local Embeddings**
VDB operations and episodic memory now use `sentence-transformers/all-MiniLM-L6-v2` locally on **CPU**, providing consistent performance and 384-dimensional vector support without external dependencies.

### **Security Stack**
Every tool is wrapped in a multi-layer security stack:
- `@safe_execution`: Catches crashes and returns them as observations.
- `@restrict_path`: Confines the agent to the `WORKSPACE_ROOT`.
- `@validate_code`: Blocks dangerous Python patterns (e.g., `os.system`).

---

##  License & Authors

**Mohammed Alaa**
- GitHub: [@blackeagle686](https://github.com/blackeagle686)
- Email: mathematecs1@gmail.com
