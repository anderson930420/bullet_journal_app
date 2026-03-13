from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TodayView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        title_label = QLabel("Today / Daily Log")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")

        input_layout = QHBoxLayout()

        self.entry_input = QLineEdit()
        self.entry_input.setPlaceholderText("Write a task, event, or note...")

        self.entry_type = QComboBox()
        self.entry_type.addItems(["task", "event", "note"])

        self.add_button = QPushButton("Add Entry")
        self.add_button.clicked.connect(self._add_entry)

        input_layout.addWidget(self.entry_input)
        input_layout.addWidget(self.entry_type)
        input_layout.addWidget(self.add_button)

        self.entry_list = QListWidget()

        main_layout.addWidget(title_label)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.entry_list)

    def _add_entry(self) -> None:
        content = self.entry_input.text().strip()
        entry_type = self.entry_type.currentText()

        if not content:
            return

        symbol = self._get_symbol(entry_type)
        self.entry_list.addItem(f"{symbol} {content}")

        self.entry_input.clear()
        self.entry_input.setFocus()

    def _get_symbol(self, entry_type: str) -> str:
        symbols = {
            "task": "•",
            "event": "○",
            "note": "—",
        }
        return symbols.get(entry_type, "•")