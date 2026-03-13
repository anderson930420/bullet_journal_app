from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.collections_view import CollectionsView
from ui.future_view import FutureView
from ui.monthly_view import MonthlyView
from ui.today_view import TodayView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Bullet Journal App")
        self.resize(1000, 700)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        title_label = QLabel("Bullet Journal App")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #1f2933;
            padding: 8px 0 4px 0;
            letter-spacing: 0.3px;
        """)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        sidebar_label = QLabel("Navigate")
        sidebar_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 700;
            color: #66707a;
            letter-spacing: 0.5px;
            padding-left: 8px;
        """)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setSpacing(6)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: 1px solid #d9dde3;
                border-radius: 18px;
                padding: 10px;
                outline: none;
                font-size: 14px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                border-radius: 10px;
                padding: 12px 14px;
                color: #4a5562;
                font-weight: 600;
            }
            QListWidget::item:selected {
                background: #e9eef5;
                color: #1f2933;
            }
        """)

        self.today_view = TodayView()
        self.monthly_view = MonthlyView()
        self.future_view = FutureView()
        self.collections_view = CollectionsView()

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background: #f7f8fa;
                border: 1px solid #d9dde3;
                border-radius: 18px;
            }
        """)

        self._add_navigation_item("Today", self.today_view)
        self._add_navigation_item("Monthly", self.monthly_view)
        self._add_navigation_item("Future", self.future_view)
        self._add_navigation_item("Collections", self.collections_view)

        sidebar_layout.addWidget(sidebar_label)
        sidebar_layout.addWidget(self.sidebar, 1)

        content_layout.addWidget(sidebar_container)
        content_layout.addWidget(self.content_stack, 1)

        main_layout.addWidget(title_label)
        main_layout.addLayout(content_layout)

        self.sidebar.setCurrentRow(0)

        central_widget.setStyleSheet("background: #eef1f4;")
        self.setCentralWidget(central_widget)

    def _add_navigation_item(self, label: str, view: QWidget) -> None:
        self.sidebar.addItem(QListWidgetItem(label))
        self.content_stack.addWidget(view)

    def _connect_signals(self) -> None:
        self.today_view.entries_changed.connect(self._refresh_all_views)
        self.monthly_view.entries_changed.connect(self._refresh_all_views)
        self.future_view.entries_changed.connect(self._refresh_all_views)
        self.sidebar.currentRowChanged.connect(self._change_view)

    def _change_view(self, index: int) -> None:
        if index < 0:
            return

        self.content_stack.setCurrentIndex(index)
        self._refresh_current_views()

    def _refresh_all_views(self) -> None:
        self.today_view.refresh_entries()
        self.monthly_view.refresh_entries()
        self.future_view.refresh_entries()

    def _refresh_current_views(self) -> None:
        self.today_view.refresh_entries()
        self.monthly_view.refresh_entries()
        self.future_view.refresh_entries()
        self.collections_view.refresh_collections()
