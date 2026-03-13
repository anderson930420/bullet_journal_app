from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
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
    reorder_collections,
    remove_collection,
    save_collection,
)


class CollectionEditorView(QWidget):
    collection_saved = Signal(int)
    collection_deleted = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.collection_id = None
        self._setup_ui()
        self.set_collection(None)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        editor_card = QFrame()
        editor_card.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: none;
                border-radius: 12px;
            }
        """)
        editor_layout = QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(36, 28, 36, 24)
        editor_layout.setSpacing(22)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Title")
        self.title_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 38px;
                font-weight: 700;
                color: #1D1D1F;
                padding: 6px 0 12px 0;
            }
        """)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write freely in this collection...")
        self.editor.setStyleSheet("""
            QTextEdit {
                border: none;
                background: transparent;
                font-size: 18px;
                line-height: 1.5;
                color: #1D1D1F;
                padding: 0;
            }
        """)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_collection)
        self.save_button.setStyleSheet("""
            QPushButton {
                background: #007AFF;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px 22px;
                font-weight: 600;
                min-width: 96px;
            }
        """)

        self.delete_button = QPushButton("Delete Note")
        self.delete_button.clicked.connect(self._delete_collection)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #4C4C52;
                border: 1px solid #E5E5E5;
                border-radius: 12px;
                padding: 14px 20px;
                font-weight: 600;
                min-width: 118px;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.save_button)

        editor_layout.addWidget(self.title_input)
        editor_layout.addWidget(self.editor, 1)
        editor_layout.addSpacing(24)
        editor_layout.addLayout(button_layout)

        layout.addWidget(editor_card, 1)

    def set_collection(self, collection_id: int | None) -> None:
        self.collection_id = collection_id
        self.refresh_content()

    def refresh_content(self) -> None:
        if self.collection_id is None:
            self.title_input.clear()
            self.editor.clear()
            self.title_input.setEnabled(True)
            self.editor.setEnabled(True)
            self.save_button.setEnabled(True)
            self.delete_button.setEnabled(False)
            return

        self.title_input.setEnabled(True)
        self.editor.setEnabled(True)
        self.save_button.setEnabled(True)
        self.delete_button.setEnabled(True)

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
        self.delete_button.setEnabled(False)
        self.title_input.setFocus()

    def _delete_collection(self) -> None:
        if self.collection_id is None:
            return

        remove_collection(self.collection_id)
        self.start_new_note()
        self.collection_deleted.emit()


class CollectionsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self.refresh_collections()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(56, 42, 56, 36)
        layout.setSpacing(22)

        content = QFrame()
        content_layout_outer = QVBoxLayout(content)
        content_layout_outer.setContentsMargins(0, 0, 0, 0)
        content_layout_outer.setSpacing(22)

        title = QLabel("Notes")
        title.setStyleSheet("font-size: 36px; font-weight: 700; color: #1D1D1F;")

        subtitle = QLabel("A quiet place for longer notes and ideas.")
        subtitle.setStyleSheet("font-size: 15px; color: #86868B; padding-bottom: 6px;")

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(26)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        left_card = QFrame()
        left_card.setStyleSheet("""
            QFrame {
                background: #F5F5F7;
                border: none;
                border-radius: 12px;
            }
        """)
        left_card_layout = QVBoxLayout(left_card)
        left_card_layout.setContentsMargins(16, 16, 16, 16)
        left_card_layout.setSpacing(14)

        list_label = QLabel("Notes")
        list_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #86868B; letter-spacing: 1px;")

        self.collection_list = QListWidget()
        self.collection_list.currentItemChanged.connect(self._select_collection)
        self.collection_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.collection_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.collection_list.setDragEnabled(True)
        self.collection_list.setAcceptDrops(True)
        self.collection_list.setDropIndicatorShown(True)
        self.collection_list.setMinimumWidth(250)
        self.collection_list.setMaximumWidth(320)
        self.collection_list.setSpacing(8)
        self.collection_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                font-size: 15px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                border-radius: 12px;
                padding: 14px 16px;
                margin: 3px 0;
                color: #53535A;
            }
            QListWidget::item:selected {
                background: #FFFFFF;
                color: #1D1D1F;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.7);
            }
        """)
        self.collection_list.model().rowsMoved.connect(self._save_collection_order)

        self.new_note_button = QPushButton("New Note")
        self.new_note_button.clicked.connect(self._new_note)
        self.new_note_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #4C4C52;
                border: 1px solid #E5E5E5;
                border-radius: 12px;
                padding: 14px 16px;
                font-weight: 600;
            }
        """)

        self.collection_editor_view = CollectionEditorView()
        self.collection_editor_view.collection_saved.connect(self._handle_collection_saved)
        self.collection_editor_view.collection_deleted.connect(self._handle_collection_deleted)

        left_card_layout.addWidget(list_label)
        left_card_layout.addWidget(self.collection_list, 1)
        left_layout.addWidget(left_card, 1)
        left_layout.addWidget(self.new_note_button)

        content_layout.addLayout(left_layout, 0)
        content_layout.addWidget(self.collection_editor_view, 1)

        content_layout_outer.addWidget(title)
        content_layout_outer.addWidget(subtitle)
        content_layout_outer.addSpacing(2)
        content_layout_outer.addLayout(content_layout, 1)
        layout.addWidget(content, 1)

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

    def _handle_collection_deleted(self) -> None:
        self.refresh_collections()

    def _save_collection_order(self, *args) -> None:
        collection_ids = []

        for row in range(self.collection_list.count()):
            item = self.collection_list.item(row)
            data = item.data(Qt.UserRole)
            if data:
                collection_ids.append(data["id"])

        if not collection_ids:
            return

        reorder_collections(collection_ids)
