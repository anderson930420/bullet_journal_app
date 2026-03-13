from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget


class EntryListView(QWidget):
    entries_changed = Signal()

    def _create_list_widget(self) -> QListWidget:
        entry_list = QListWidget()
        entry_list.setSpacing(6)
        entry_list.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: 1px solid #d9dde3;
                border-radius: 14px;
                padding: 10px;
                outline: none;
                font-size: 14px;
            }
            QListWidget::item {
                background: #f8f9fb;
                border: 1px solid #edf0f4;
                border-radius: 10px;
                padding: 10px 12px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background: #e9eef5;
                border: 1px solid #d5dde8;
                color: #1f2933;
            }
        """)
        return entry_list

    def refresh_entries(self) -> None:
        self.entry_list.clear()

        rows = self._fetch_entries()

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

    def _delete_entry(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        self._remove_entry(data["id"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _toggle_complete(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        if not data:
            return

        self._toggle_entry(data["id"], data["completed"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _get_current_item_data(self) -> dict | None:
        item = self.entry_list.currentItem()
        if item is None:
            return None

        return item.data(Qt.UserRole)

    def _fetch_entries(self):
        raise NotImplementedError

    def _remove_entry(self, entry_id: int) -> None:
        raise NotImplementedError

    def _toggle_entry(self, entry_id: int, completed: bool) -> None:
        raise NotImplementedError

    def _get_symbol(self, entry_type: str) -> str:
        symbols = {
            "task": "•",
            "event": "○",
            "note": "—",
        }
        return symbols.get(entry_type, "•")
