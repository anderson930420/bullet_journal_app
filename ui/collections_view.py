from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.collections_service import (
    fetch_collection,
    fetch_collections,
    save_collection,
)


class CollectionEditorView(QWidget):
    collection_saved = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.collection_id = None
        self._setup_ui()
        self.set_collection(None)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Title")
        self.title_input.setStyleSheet("font-size: 24px; font-weight: bold; padding: 8px;")

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write freely in this collection...")
        self.editor.setStyleSheet("font-size: 16px; padding: 8px;")

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_collection)

        layout.addWidget(self.title_input)
        layout.addWidget(self.editor, 1)
        layout.addWidget(self.save_button)

    def set_collection(self, collection_id: int | None) -> None:
        self.collection_id = collection_id
        self.refresh_content()

    def refresh_content(self) -> None:
        if self.collection_id is None:
            self.title_input.clear()
            self.editor.clear()
            self.title_input.setEnabled(True)
            self.editor.setEnabled(False)
            self.save_button.setEnabled(False)
            return

        self.title_input.setEnabled(True)
        self.editor.setEnabled(True)
        self.save_button.setEnabled(True)

        row = fetch_collection(self.collection_id)
        if row is None:
            self.title_input.clear()
            self.editor.clear()
            return

        _, title, content = row
        self.title_input.setText(title or "")
        self.editor.setPlainText(content or "")

    def _save_collection(self) -> None:
        title = self.title_input.text().strip()
        if not title:
            return

        self.collection_id = save_collection(
            self.collection_id,
            title,
            self.editor.toPlainText(),
        )
        self.collection_saved.emit(self.collection_id)

    def start_new_note(self) -> None:
        self.collection_id = None
        self.title_input.clear()
        self.editor.clear()
        self.title_input.setEnabled(True)
        self.editor.setEnabled(True)
        self.save_button.setEnabled(True)
        self.title_input.setFocus()


class CollectionsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_collections()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Collections")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")

        content_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        self.collection_list = QListWidget()
        self.collection_list.currentItemChanged.connect(self._select_collection)

        self.new_note_button = QPushButton("New Note")
        self.new_note_button.clicked.connect(self._new_note)

        self.collection_editor_view = CollectionEditorView()
        self.collection_editor_view.collection_saved.connect(self._handle_collection_saved)

        left_layout.addWidget(self.collection_list)
        left_layout.addWidget(self.new_note_button)

        content_layout.addLayout(left_layout)
        content_layout.addWidget(self.collection_editor_view)

        layout.addWidget(title)
        layout.addLayout(content_layout)

    def refresh_collections(self) -> None:
        current_collection_id = self.collection_editor_view.collection_id
        self.collection_list.clear()

        rows = fetch_collections()
        selected_row = None

        for index, (collection_id, title) in enumerate(rows):
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, {"id": collection_id, "title": title})
            self.collection_list.addItem(item)

            if collection_id == current_collection_id:
                selected_row = index

        if self.collection_list.count() == 0:
            self.collection_editor_view.start_new_note()
            return

        if selected_row is not None:
            self.collection_list.setCurrentRow(selected_row)
        elif current_collection_id is None:
            self.collection_editor_view.start_new_note()

    def _select_collection(self) -> None:
        item = self.collection_list.currentItem()
        if item is None:
            self.collection_editor_view.start_new_note()
            return

        data = item.data(Qt.UserRole)
        if not data:
            self.collection_editor_view.start_new_note()
            return

        self.collection_editor_view.set_collection(data["id"])

    def _new_note(self) -> None:
        self.collection_list.clearSelection()
        self.collection_editor_view.start_new_note()

    def _handle_collection_saved(self, collection_id: int) -> None:
        self.refresh_collections()

        for row in range(self.collection_list.count()):
            item = self.collection_list.item(row)
            data = item.data(Qt.UserRole)
            if data and data["id"] == collection_id:
                self.collection_list.setCurrentRow(row)
                break
