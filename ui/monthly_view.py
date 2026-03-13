from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from services.capture_service import (
    fetch_monthly_entries,
    migrate_to_today,
    remove_entry,
    toggle_entry,
)
from ui.entry_list_view import EntryListView


class MonthlyView(EntryListView):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Monthly Log")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1f2933;")

        subtitle = QLabel("Keep the month in view without clutter.")
        subtitle.setStyleSheet("font-size: 13px; color: #66707a;")

        self.entry_list = self._create_list_widget()
        self.entry_list.itemDoubleClicked.connect(self._toggle_complete)

        self.migrate_back_button = QPushButton("Move Back to Today")
        self.migrate_back_button.clicked.connect(self._move_back_to_today)
        self.migrate_back_button.setStyleSheet(self._button_style())

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_entry)
        self.delete_button.setStyleSheet(self._button_style())

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.addWidget(self.migrate_back_button)
        actions_layout.addWidget(self.delete_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.entry_list, 1)
        layout.addLayout(actions_layout)

    def _button_style(self) -> str:
        return """
            QPushButton {
                background: #ffffff;
                color: #344150;
                border: 1px solid #d9dde3;
                border-radius: 10px;
                padding: 10px 14px;
                font-weight: 600;
            }
        """

    def _move_back_to_today(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        migrate_to_today(data["id"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _fetch_entries(self):
        return fetch_monthly_entries()

    def _remove_entry(self, entry_id: int) -> None:
        remove_entry(entry_id)

    def _toggle_entry(self, entry_id: int, completed: bool) -> None:
        toggle_entry(entry_id, completed)
