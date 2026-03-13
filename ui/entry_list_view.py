from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget


class ReorderableListWidget(QListWidget):
    order_changed = Signal()

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.order_changed.emit()


class EntryListView(QWidget):
    entries_changed = Signal()

    def _create_list_widget(self, reorderable: bool = False) -> QListWidget:
        entry_list = ReorderableListWidget() if reorderable else QListWidget()
        entry_list.setSpacing(10)
        entry_list.setStyleSheet("""
            QListWidget {
                background: #f9f7f2;
                border: 1px solid #e3dfd6;
                border-radius: 22px;
                padding: 14px;
                outline: none;
                font-size: 15px;
            }
            QListWidget::item {
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid #ece7df;
                border-radius: 16px;
                padding: 14px 16px;
                margin: 4px 0;
                color: #212833;
            }
            QListWidget::item:selected {
                background: #ffffff;
                border: 1px solid #ddd8cf;
                color: #161c24;
            }
            QListWidget::item:hover {
                background: #fffdfa;
            }
        """)

        if reorderable:
            entry_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            entry_list.setDefaultDropAction(Qt.DropAction.MoveAction)
            entry_list.setDragEnabled(True)
            entry_list.setAcceptDrops(True)
            entry_list.setDropIndicatorShown(True)
            entry_list.order_changed.connect(self._handle_reorder)

        return entry_list

    def refresh_entries(self) -> None:
        self.entry_list.clear()

        rows = self._fetch_entries()

        for row in rows:
            entry_id, content, entry_type, completed, *rest = row

            item_data = {
                "id": entry_id,
                "content": content,
                "type": entry_type,
                "completed": bool(completed),
            }

            if rest:
                item_data["bucket"] = rest[0]

            if len(rest) > 1:
                item_data["kind"] = rest[1]

            text = self._format_item_text(item_data)

            item = QListWidgetItem(text)
            item.setData(
                Qt.UserRole,
                item_data,
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

    def _format_item_text(self, data: dict) -> str:
        symbol = self._get_symbol(data["type"])
        text = f"{symbol} {data['content']}"

        if data["completed"]:
            text = f"× {text}"

        return text

    def _handle_reorder(self) -> None:
        item_ids = []

        for index in range(self.entry_list.count()):
            item = self.entry_list.item(index)
            data = item.data(Qt.UserRole)
            if data:
                item_ids.append(data["id"])

        if not item_ids:
            return

        self._save_order(item_ids)
        self.refresh_entries()
        self.entries_changed.emit()

    def _save_order(self, item_ids: list[int]) -> None:
        raise NotImplementedError
