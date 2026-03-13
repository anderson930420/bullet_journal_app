from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from services.capture_service import (
    create_future_entry,
    fetch_future_entries,
    migrate_to_monthly,
    migrate_to_today,
    reorder_entries,
    remove_entry,
    toggle_entry,
)
from ui.entry_list_view import EntryListView


class FutureView(EntryListView):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)
        content_row.addStretch(1)

        content = QFrame()
        content.setMaximumWidth(1160)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(56, 42, 56, 36)
        content_layout.setSpacing(22)

        content_row.addWidget(content, 0)
        content_row.addStretch(1)
        layout.addLayout(content_row)

        title = QLabel("Future Log")
        title.setStyleSheet("font-size: 36px; font-weight: 700; color: #1D1D1F;")

        subtitle = QLabel("Hold entries you want to revisit later.")
        subtitle.setStyleSheet("font-size: 15px; color: #86868B; padding-bottom: 6px;")

        input_card = QFrame()
        input_card.setStyleSheet("""
            QFrame {
                background: #F5F5F7;
                border: none;
                border-radius: 12px;
            }
        """)
        input_layout = QHBoxLayout(input_card)
        input_layout.setContentsMargins(26, 26, 26, 26)
        input_layout.setSpacing(16)

        self.entry_input = QLineEdit()
        self.entry_input.setPlaceholderText("Add something for later...")
        self.entry_input.setStyleSheet(self._text_input_style())
        self.entry_input.setMinimumHeight(58)
        self.entry_input.setMinimumWidth(640)
        self.entry_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.entry_type = QComboBox()
        self.entry_type.addItems(["task", "event", "note"])
        self.entry_type.setStyleSheet(self._combo_style())
        self.entry_type.setMinimumHeight(58)
        self.entry_type.setMaximumWidth(124)

        self.add_button = QPushButton("Add Entry")
        self.add_button.clicked.connect(self._add_entry)
        self.add_button.setStyleSheet(self._primary_button_style())
        self.add_button.setMinimumHeight(58)
        self.add_button.setMaximumWidth(116)

        input_layout.addWidget(self.entry_input, 1)
        input_layout.addWidget(self.entry_type)
        input_layout.addWidget(self.add_button)

        self.entry_list = self._create_list_widget(reorderable=True)
        self.entry_list.itemDoubleClicked.connect(self._toggle_complete)

        self.move_to_today_button = QPushButton("Move to Today")
        self.move_to_today_button.clicked.connect(self._move_to_today)
        self.move_to_today_button.setStyleSheet(self._button_style())

        self.move_to_monthly_button = QPushButton("Move to Monthly")
        self.move_to_monthly_button.clicked.connect(self._move_to_monthly)
        self.move_to_monthly_button.setStyleSheet(self._button_style())

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_entry)
        self.delete_button.setStyleSheet(self._button_style())

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.addWidget(self.move_to_today_button)
        actions_layout.addWidget(self.move_to_monthly_button)
        actions_layout.addWidget(self.delete_button)

        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addWidget(input_card)
        content_layout.addWidget(self.entry_list, 1)
        content_layout.addSpacing(18)
        content_layout.addLayout(actions_layout)

    def _button_style(self) -> str:
        return """
            QPushButton {
                background: transparent;
                color: #4C4C52;
                border: 1px solid #E5E5E5;
                border-radius: 12px;
                padding: 13px 16px;
                font-weight: 600;
            }
        """

    def _primary_button_style(self) -> str:
        return """
            QPushButton {
                background: #007AFF;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 22px;
                font-weight: 600;
                min-width: 116px;
            }
        """

    def _text_input_style(self) -> str:
        return """
            QLineEdit {
                background: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 16px 18px;
                font-size: 15px;
                color: #1D1D1F;
            }
        """

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 16px 18px;
                font-size: 15px;
                min-width: 132px;
                color: #1D1D1F;
            }
        """

    def _add_entry(self) -> None:
        content = self.entry_input.text().strip()
        entry_type = self.entry_type.currentText()

        if not content:
            return

        create_future_entry(content, entry_type)

        self.entry_input.clear()
        self.refresh_entries()
        self.entries_changed.emit()

    def _move_to_today(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        migrate_to_today(data["id"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _move_to_monthly(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        migrate_to_monthly(data["id"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _fetch_entries(self):
        return fetch_future_entries()

    def _remove_entry(self, entry_id: int) -> None:
        remove_entry(entry_id)

    def _toggle_entry(self, entry_id: int, completed: bool) -> None:
        toggle_entry(entry_id, completed)

    def _save_order(self, item_ids: list[int]) -> None:
        reorder_entries("future", item_ids)
