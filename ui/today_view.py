from database import add_entry, delete_entry, get_entries, update_entry_completed
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
        self._refresh_entries()

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

        add_entry(content, entry_type)

        self.entry_input.clear()
        self._refresh_entries()

    def _delete_entry(self) -> None:
        item = self.entry_list.currentItem()

        if item is None:
            return

        data = item.data(Qt.UserRole)

        if not data:
            return

        entry_id = data["id"]
        delete_entry(entry_id)
        self._refresh_entries()
    
    def _refresh_entries(self) -> None:
        self.entry_list.clear()

        rows = get_entries()

        for entry_id, content, entry_type, completed in rows:
            symbol = self._get_symbol(entry_type)
            text = f"{symbol} {content}"

            if completed:
                text = f"× {text}"

            item = QListWidgetItem(text)
            item.setData(
                Qt.UserRole,
                {
                    "id": entry_id,
                    "content": content,
                    "type": entry_type,
                    "completed": bool(completed),
                },
            )

            self.entry_list.addItem(item)

    def _toggle_complete(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)

        if not data:
            return

        entry_id = data["id"]
        completed = data["completed"]

        new_completed = not completed

        update_entry_completed(entry_id, int(new_completed))
        self._refresh_entries()

    def _get_symbol(self, entry_type: str) -> str:
        symbols = {
            "task": "•",
            "event": "○",
            "note": "—",
        }
        return symbols.get(entry_type, "•")