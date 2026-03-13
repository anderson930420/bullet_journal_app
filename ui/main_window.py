from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
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
from ui.recently_deleted_view import RecentlyDeletedView
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
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(0)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        sidebar_container = QFrame()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(18, 20, 18, 18)
        sidebar_layout.setSpacing(14)
        sidebar_container.setFixedWidth(228)
        sidebar_container.setStyleSheet("""
            QFrame {
                background: #f6f4ef;
                border: 1px solid #dfdbd2;
                border-radius: 28px;
            }
        """)

        app_label = QLabel("Bullet Journal")
        app_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #18202a;
            padding-left: 6px;
        """)

        app_subtitle = QLabel("A quiet place to plan and write.")
        app_subtitle.setWordWrap(True)
        app_subtitle.setStyleSheet("""
            font-size: 13px;
            color: #7b817c;
            padding: 0 6px 6px 6px;
            line-height: 1.35;
        """)

        sidebar_label = QLabel("Navigate")
        sidebar_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 700;
            color: #8a908b;
            letter-spacing: 1px;
            padding-left: 10px;
            text-transform: uppercase;
        """)

        self.sidebar = QListWidget()
        self.sidebar.setSpacing(6)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                border-radius: 20px;
                padding: 6px 0;
                outline: none;
                font-size: 15px;
            }
            QListWidget::item {
                background: rgba(255, 255, 255, 0.55);
                border: none;
                border-radius: 16px;
                padding: 15px 16px;
                color: #59616b;
                font-weight: 600;
            }
            QListWidget::item:selected {
                background: #ffffff;
                border: 1px solid #ded9d1;
                color: #18202a;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.9);
            }
        """)

        self.today_view = TodayView()
        self.monthly_view = MonthlyView()
        self.future_view = FutureView()
        self.collections_view = CollectionsView()
        self.recently_deleted_view = RecentlyDeletedView()

        content_panel = QFrame()
        content_panel.setStyleSheet("""
            QFrame {
                background: #fcfbf8;
                border: 1px solid #dfdbd2;
                border-radius: 30px;
            }
        """)
        content_panel_layout = QVBoxLayout(content_panel)
        content_panel_layout.setContentsMargins(0, 0, 0, 0)

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background: transparent;
                border: none;
                border-radius: 28px;
            }
        """)
        content_panel_layout.addWidget(self.content_stack)

        self._add_navigation_item("Daily", self.today_view)
        self._add_navigation_item("Monthly", self.monthly_view)
        self._add_navigation_item("Future", self.future_view)
        self._add_navigation_item("Notes", self.collections_view)
        self._add_navigation_item("Trash", self.recently_deleted_view)

        sidebar_layout.addWidget(app_label)
        sidebar_layout.addWidget(app_subtitle)
        sidebar_layout.addWidget(sidebar_label)
        sidebar_layout.addWidget(self.sidebar, 1)

        content_layout.addWidget(sidebar_container)
        content_layout.addWidget(content_panel, 1)
        main_layout.addLayout(content_layout)

        self.sidebar.setCurrentRow(0)

        central_widget.setStyleSheet("background: #ece8e1;")
        self.setCentralWidget(central_widget)

    def _add_navigation_item(self, label: str, view: QWidget) -> None:
        self.sidebar.addItem(QListWidgetItem(label))
        self.content_stack.addWidget(view)

    def _connect_signals(self) -> None:
        self.today_view.entries_changed.connect(self._refresh_all_views)
        self.monthly_view.entries_changed.connect(self._refresh_all_views)
        self.future_view.entries_changed.connect(self._refresh_all_views)
        self.recently_deleted_view.entries_changed.connect(self._refresh_all_views)
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
        self.recently_deleted_view.refresh_entries()

    def _refresh_current_views(self) -> None:
        self.today_view.refresh_entries()
        self.monthly_view.refresh_entries()
        self.future_view.refresh_entries()
        self.collections_view.refresh_collections()
        self.recently_deleted_view.refresh_entries()
