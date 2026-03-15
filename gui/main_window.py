import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Slot
from .styles import MODERN_DARK_STYLE
from .agent_thread import AgentWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Baby Agent - Professional Dashboard")
        self.resize(1100, 800)
        self.setStyleSheet(MODERN_DARK_STYLE)
        
        self.setup_ui()
        self.worker = None

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Left Panel: Chat ---
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        
        title = QLabel("Agent Chat")
        title.setObjectName("titleLabel")
        chat_layout.addWidget(title)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("Agent responses will appear here...")
        chat_layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Ask me anything...")
        self.user_input.returnPressed.connect(self.send_request)
        
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_request)
        
        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.send_button)
        chat_layout.addLayout(input_layout)

        # --- Right Panel: Thought Process ---
        self.thought_panel = QFrame()
        self.thought_panel.setObjectName("thoughtPanel")
        self.thought_panel.setFixedWidth(400)
        thought_layout = QVBoxLayout(self.thought_panel)

        thought_title = QLabel("Internal Process")
        thought_title.setObjectName("titleLabel")
        thought_layout.addWidget(thought_title)

        self.thought_display = QTextEdit()
        self.thought_display.setReadOnly(True)
        self.thought_display.setPlaceholderText("Thinking process...")
        thought_layout.addWidget(self.thought_display)

        self.task_list_display = QTextEdit()
        self.task_list_display.setReadOnly(True)
        self.task_list_display.setFixedHeight(200)
        self.task_list_display.setPlaceholderText("Decomposed tasks...")
        thought_layout.addWidget(QLabel("<b>Task Breakdown</b>"))
        thought_layout.addWidget(self.task_list_display)

        # Assemble
        main_layout.addWidget(chat_container, stretch=1)
        main_layout.addWidget(self.thought_panel)

    def append_chat(self, sender, message):
        color = "#3D5AFE" if sender == "Agent" else "#00C853"
        formatted = f'<p><b style="color: {color};">{sender}:</b> {message}</p>'
        self.chat_display.append(formatted)

    def append_thought(self, message):
        self.thought_display.append(f'<p style="color: #9E9E9E;">{message}</p>')

    def send_request(self):
        prompt = self.user_input.text().strip()
        if not prompt:
            return

        self.user_input.clear()
        self.append_chat("You", prompt)
        self.user_input.setEnabled(False)
        self.send_button.setEnabled(False)
        
        self.thought_display.clear()
        self.task_list_display.clear()

        # Start background worker
        self.worker = AgentWorker(prompt)
        self.worker.signals.thinker_done.connect(self.on_thinker_done)
        self.worker.signals.plan_updated.connect(self.on_plan_updated)
        self.worker.signals.observation_ready.connect(self.on_observation_ready)
        self.worker.signals.final_answer_ready.connect(self.on_final_answer)
        self.worker.signals.finished.connect(self.on_finished)
        self.worker.signals.error.connect(self.on_error)
        
        self.worker.start()

    @Slot(dict)
    def on_thinker_done(self, data):
        analysis = data.get("analysis", "")
        tasks = data.get("tasks", [])
        self.append_thought(f"<b>Thinker Analysis:</b><br>{analysis}")
        
        task_text = "<br>".join([f"- {t}" for t in tasks])
        self.task_list_display.setHtml(f"<ul>{''.join([f'<li>{t}</li>' for t in tasks])}</ul>")

    @Slot(dict)
    def on_plan_updated(self, data):
        step = data.get("step")
        task = data.get("task")
        decision = data.get("decision", {})
        action = decision.get("action")
        reasoning = decision.get("reasoning")
        
        self.append_thought(f"<hr><b>Step {step}: Planning</b><br>Task: {task}<br>Action: <i>{action}</i><br>Reasoning: {reasoning}")

    @Slot(dict)
    def on_observation_ready(self, data):
        tool = data.get("tool")
        obs = data.get("observation", "")
        # Truncate long observations for UI
        if len(obs) > 500:
            obs = obs[:500] + "... (truncated)"
        self.append_thought(f"<b style='color: #FF4081;'>Observation ({tool}):</b><br>{obs}")

    @Slot(dict)
    def on_final_answer(self, data):
        answer = data.get("answer", "")
        self.append_chat("Agent", answer)

    @Slot()
    def on_finished(self):
        self.user_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.worker = None

    @Slot(str)
    def on_error(self, error_msg):
        self.append_chat("System Error", error_msg)
        self.on_finished()
