from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
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
        self.entry_list.itemDoubleClicked.connect(self._toggle_complete)

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_entry)

        main_layout.addWidget(title_label)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.entry_list)
        main_layout.addWidget(self.delete_button)

    def _add_entry(self) -> None:
        content = self.entry_input.text().strip()
        entry_type = self.entry_type.currentText()

        if not content:
            return

        symbol = self._get_symbol(entry_type)

        item = QListWidgetItem(f"{symbol} {content}")
        item.setData(Qt.UserRole, {"completed": False})

        self.entry_list.addItem(item)

        self.entry_input.clear()
        self.entry_input.setFocus()

    def _delete_entry(self) -> None:
        selected = self.entry_list.currentRow()
        if selected >= 0:
            self.entry_list.takeItem(selected)

    def _toggle_complete(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        completed = data["completed"]

        text = item.text()

        if completed:
            # remove ×
            if text.startswith("× "):
                text = text[2:]
        else:
            # add ×
            text = "× " + text

        data["completed"] = not completed
        item.setData(Qt.UserRole, data)
        item.setText(text)

    def _get_symbol(self, entry_type: str) -> str:
        symbols = {
            "task": "•",
            "event": "○",
            "note": "—",
        }
        return symbols.get(entry_type, "•")