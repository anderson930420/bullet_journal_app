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
from services.collections_service import (
    permanently_remove_collection,
    restore_deleted_collection,
)
from ui.entry_list_view import EntryListView


class RecentlyDeletedView(EntryListView):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 34, 34, 30)
        layout.setSpacing(20)

        title = QLabel("Trash")
        title.setStyleSheet("font-size: 30px; font-weight: 700; color: #242a31;")

        subtitle = QLabel("Review deleted items before removing them permanently.")
        subtitle.setStyleSheet("font-size: 15px; color: #82857e; padding-bottom: 4px;")

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
                background: #f8f6f1;
                color: #49515b;
                border: 1px solid #e1dcd3;
                border-radius: 14px;
                padding: 13px 16px;
                font-weight: 600;
            }
        """

    def _restore_entry(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        if data.get("kind") == "collection":
            restore_deleted_collection(data["id"])
        else:
            restore_deleted_entry(data["id"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _fetch_entries(self):
        return fetch_deleted_entries()

    def _remove_entry(self, entry_id: int) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        if data.get("kind") == "collection":
            permanently_remove_collection(entry_id)
        else:
            permanently_remove_entry(entry_id)

    def _toggle_entry(self, entry_id: int, completed: bool) -> None:
        return None

    def _format_item_text(self, data: dict) -> str:
        if data.get("kind") == "collection":
            text = data["content"]
        else:
            text = super()._format_item_text(data)

        bucket = data.get("bucket", "")
        bucket_label = bucket.capitalize() if bucket else "Entry"
        return f"[{bucket_label}] {text}"
