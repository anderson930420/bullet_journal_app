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
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(0)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        sidebar_container = QFrame()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(18, 24, 18, 18)
        sidebar_layout.setSpacing(16)
        sidebar_container.setFixedWidth(220)
        sidebar_container.setStyleSheet("""
            QFrame {
                background: #F5F5F7;
                border: none;
                border-radius: 18px;
            }
        """)

        app_label = QLabel("Bullet Journal")
        app_label.setStyleSheet("""
            font-size: 22px;
            font-weight: 700;
            color: #1D1D1F;
            padding-left: 8px;
        """)

        app_subtitle = QLabel("A quiet place to plan and write.")
        app_subtitle.setWordWrap(True)
        app_subtitle.setStyleSheet("""
            font-size: 13px;
            color: #86868B;
            padding: 0 8px 8px 8px;
            line-height: 1.35;
        """)

        sidebar_label = QLabel("Navigate")
        sidebar_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 700;
            color: #86868B;
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
                border-radius: 14px;
                padding: 6px 0;
                outline: none;
                font-size: 15px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                border-radius: 12px;
                padding: 12px 14px;
                color: #53535A;
                font-weight: 600;
            }
            QListWidget::item:selected {
                background: #FFFFFF;
                color: #1D1D1F;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.72);
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
                background: #FFFFFF;
                border: none;
                border-radius: 20px;
            }
        """)
        content_panel_layout = QVBoxLayout(content_panel)
        content_panel_layout.setContentsMargins(0, 0, 0, 0)

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background: transparent;
                border: none;
                border-radius: 20px;
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

        central_widget.setStyleSheet("background: #FFFFFF;")
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
