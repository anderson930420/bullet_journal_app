from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

from services.capture_service import fetch_future_entries


class FutureView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self._refresh_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Future Log")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")

        self.entry_list = QListWidget()

        layout.addWidget(title)
        layout.addWidget(self.entry_list)

    def _refresh_entries(self) -> None:
        self.entry_list.clear()

        rows = fetch_future_entries()

        for _, content, entry_type, completed in rows:
            symbol = self._get_symbol(entry_type)
            text = f"{symbol} {content}"

            if completed:
                text = f"× {text}"

            self.entry_list.addItem(text)

    def _get_symbol(self, entry_type: str) -> str:
        symbols = {
            "task": "•",
            "event": "○",
            "note": "—",
        }
        return symbols.get(entry_type, "•")