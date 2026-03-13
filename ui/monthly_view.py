from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.capture_service import (
    fetch_monthly_entries,
    migrate_to_today,
    remove_entry,
    toggle_entry,
)


class MonthlyView(QWidget):
    entries_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Monthly Log")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")

        self.entry_list = QListWidget()
        self.entry_list.itemDoubleClicked.connect(self._toggle_complete)

        self.migrate_back_button = QPushButton("Move Back to Today")
        self.migrate_back_button.clicked.connect(self._move_back_to_today)

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_entry)

        layout.addWidget(title)
        layout.addWidget(self.entry_list)
        layout.addWidget(self.migrate_back_button)
        layout.addWidget(self.delete_button)

    def refresh_entries(self) -> None:
        self.entry_list.clear()

        rows = fetch_monthly_entries()

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

    def _move_back_to_today(self) -> None:
        item = self.entry_list.currentItem()
        if item is None:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        entry_id = data["id"]
        migrate_to_today(entry_id)

        self.refresh_entries()
        self.entries_changed.emit()

    def _delete_entry(self) -> None:
        item = self.entry_list.currentItem()
        if item is None:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        entry_id = data["id"]
        remove_entry(entry_id)

        self.refresh_entries()
        self.entries_changed.emit()

    def _toggle_complete(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        if not data:
            return

        entry_id = data["id"]
        completed = data["completed"]

        toggle_entry(entry_id, completed)

        self.refresh_entries()
        self.entries_changed.emit()

    def _get_symbol(self, entry_type: str) -> str:
        symbols = {
            "task": "•",
            "event": "○",
            "note": "—",
        }
        return symbols.get(entry_type, "•")
