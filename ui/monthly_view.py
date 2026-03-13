from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from services.capture_service import (
    fetch_monthly_entries,
    migrate_to_today,
)
from ui.entry_list_view import EntryListView


class MonthlyView(EntryListView):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Monthly Log")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")

        self.entry_list = self._create_list_widget()
        self.entry_list.itemDoubleClicked.connect(self._toggle_complete)

        self.migrate_back_button = QPushButton("Move Back to Today")
        self.migrate_back_button.clicked.connect(self._move_back_to_today)

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_entry)

        layout.addWidget(title)
        layout.addWidget(self.entry_list)
        layout.addWidget(self.migrate_back_button)
        layout.addWidget(self.delete_button)

    def _move_back_to_today(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        migrate_to_today(data["id"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _fetch_entries(self):
        return fetch_monthly_entries()
