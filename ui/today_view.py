from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from services.capture_service import (
    create_entry,
    fetch_entries,
    migrate_to_future,
    migrate_to_monthly,
    reorder_entries,
    remove_entry,
    toggle_entry,
)
from ui.entry_list_view import EntryListView


class TodayView(EntryListView):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(34, 34, 34, 30)
        main_layout.setSpacing(20)

        title_label = QLabel("Daily Log")
        title_label.setStyleSheet("font-size: 32px; font-weight: 700; color: #171e27;")

        subtitle_label = QLabel("Capture tasks, events, and notes for the day.")
        subtitle_label.setStyleSheet("font-size: 15px; color: #737a74; padding-bottom: 4px;")

        input_card = QFrame()
        input_card.setStyleSheet("""
            QFrame {
                background: #f7f4ef;
                border: 1px solid #e2ddd4;
                border-radius: 24px;
            }
        """)
        input_layout = QHBoxLayout(input_card)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(14)

        self.entry_input = QLineEdit()
        self.entry_input.setPlaceholderText("Write a task, event, or note...")
        self.entry_input.setStyleSheet("""
            QLineEdit {
                background: #fffdf9;
                border: 1px solid #e7e2da;
                border-radius: 16px;
                padding: 14px 16px;
                font-size: 15px;
                color: #1d2430;
            }
        """)

        self.entry_type = QComboBox()
        self.entry_type.addItems(["task", "event", "note"])
        self.entry_type.setStyleSheet("""
            QComboBox {
                background: #fffdf9;
                border: 1px solid #e7e2da;
                border-radius: 16px;
                padding: 14px 16px;
                font-size: 15px;
                min-width: 126px;
                color: #1d2430;
            }
        """)

        self.add_button = QPushButton("Add Entry")
        self.add_button.clicked.connect(self._add_entry)
        self.add_button.setStyleSheet("""
            QPushButton {
                background: #1d2530;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 14px 20px;
                font-weight: 600;
                min-width: 112px;
            }
        """)

        input_layout.addWidget(self.entry_input)
        input_layout.addWidget(self.entry_type)
        input_layout.addWidget(self.add_button)

        self.entry_list = self._create_list_widget(reorderable=True)
        self.entry_list.itemDoubleClicked.connect(self._toggle_complete)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.monthly_button = QPushButton("Migrate to Monthly")
        self.monthly_button.clicked.connect(self._migrate_to_monthly)
        self.monthly_button.setStyleSheet(self._secondary_button_style())

        self.migrate_button = QPushButton("Migrate to Future")
        self.migrate_button.clicked.connect(self._migrate_entry)
        self.migrate_button.setStyleSheet(self._secondary_button_style())

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_entry)
        self.delete_button.setStyleSheet(self._secondary_button_style())

        actions_layout.addWidget(self.monthly_button)
        actions_layout.addWidget(self.migrate_button)
        actions_layout.addWidget(self.delete_button)

        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addWidget(input_card)
        main_layout.addWidget(self.entry_list, 1)
        main_layout.addLayout(actions_layout)

    def _secondary_button_style(self) -> str:
        return """
            QPushButton {
                background: #f8f6f1;
                color: #38424d;
                border: 1px solid #e1dcd3;
                border-radius: 14px;
                padding: 13px 16px;
                font-weight: 600;
            }
        """

    def _add_entry(self) -> None:
        content = self.entry_input.text().strip()
        entry_type = self.entry_type.currentText()

        if not content:
            return

        create_entry(content, entry_type)

        self.entry_input.clear()
        self.refresh_entries()
        self.entries_changed.emit()

    def _migrate_entry(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        migrate_to_future(data["id"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _migrate_to_monthly(self) -> None:
        data = self._get_current_item_data()
        if not data:
            return

        migrate_to_monthly(data["id"])

        self.refresh_entries()
        self.entries_changed.emit()

    def _fetch_entries(self):
        return fetch_entries()

    def _remove_entry(self, entry_id: int) -> None:
        remove_entry(entry_id)

    def _toggle_entry(self, entry_id: int, completed: bool) -> None:
        toggle_entry(entry_id, completed)

    def _save_order(self, item_ids: list[int]) -> None:
        reorder_entries("today", item_ids)
