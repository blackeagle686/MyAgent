MODERN_DARK_STYLE = """
QMainWindow {
    background-color: #121212;
}

QWidget {
    background-color: #121212;
    color: #E0E0E0;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
}

QTextEdit, QPlainTextEdit {
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 8px;
    color: #E0E0E0;
    selection-background-color: #3D5AFE;
}

QLineEdit {
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 10px;
    color: #FFFFFF;
}

QPushButton {
    background-color: #3D5AFE;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #536DFE;
}

QPushButton:pressed {
    background-color: #304FFE;
}

QPushButton#sendButton {
    background-color: #00C853;
}

QPushButton#sendButton:hover {
    background-color: #00E676;
}

QFrame#thoughtPanel {
    background-color: #1A1A1A;
    border-left: 2px solid #3D5AFE;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #3D5AFE;
}

QScrollBar:vertical {
    border: none;
    background: #121212;
    width: 10px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""
