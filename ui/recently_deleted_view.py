from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from services.capture_service import (
    fetch_deleted_entries,
    permanently_remove_entry,
    restore_deleted_entry,
)
from ui.entry_list_view import EntryListView


class RecentlyDeletedView(EntryListView):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Recently Deleted")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1f2933;")

        subtitle = QLabel("Restore planning entries or remove them permanently.")
        subtitle.setStyleSheet("font-size: 13px; color: #66707a;")

        self.entry_list = self._create_list_widget()

        self.restore_button = QPushButton("Restore")
        self.restore_button.clicked.connect(self._restore_entry)
        self.restore_button.setStyleSheet(self._button_style())

        self.delete_button = QPushButton("Delete Permanently")
        self.delete_button.clicked.connect(self._delete_entry)
        self.delete_button.setStyleSheet(self._button_style())

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.addWidget(self.restore_button)
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

    def _restore_entry(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        restore_deleted_entry(data["id"])
        self.refresh_entries()
        self.entries_changed.emit()

    def _fetch_entries(self):
        return fetch_deleted_entries()

    def _remove_entry(self, entry_id: int) -> None:
        permanently_remove_entry(entry_id)

    def _toggle_entry(self, entry_id: int, completed: bool) -> None:
        return None

    def _format_item_text(self, data: dict) -> str:
        text = super()._format_item_text(data)
        bucket = data.get("bucket", "")
        bucket_label = bucket.capitalize() if bucket else "Entry"
        return f"[{bucket_label}] {text}"
