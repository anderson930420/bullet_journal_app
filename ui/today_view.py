from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
)
from ui.entry_list_view import EntryListView


class TodayView(EntryListView):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        title_label = QLabel("Today / Daily Log")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")

        input_layout = QHBoxLayout()

        self.entry_input = QLineEdit()
        self.entry_input.setPlaceholderText("Write a task, event, or note...")

        self.entry_type = QComboBox()
        self.entry_type.addItems(["task", "event", "note"])

        self.add_button = QPushButton("Add Entry")
        self.add_button.clicked.connect(self._add_entry)

        input_layout.addWidget(self.entry_input)
        input_layout.addWidget(self.entry_type)
        input_layout.addWidget(self.add_button)

        self.entry_list = self._create_list_widget()
        self.entry_list.itemDoubleClicked.connect(self._toggle_complete)

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_entry)

        self.migrate_button = QPushButton("Migrate to Future")
        self.migrate_button.clicked.connect(self._migrate_entry)

        self.monthly_button = QPushButton("Migrate to Monthly")
        self.monthly_button.clicked.connect(self._migrate_to_monthly)

        main_layout.addWidget(title_label)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.entry_list)
        main_layout.addWidget(self.delete_button)
        main_layout.addWidget(self.migrate_button)
        main_layout.addWidget(self.monthly_button)

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
