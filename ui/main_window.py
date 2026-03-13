from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

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

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d9dde3;
                border-radius: 18px;
                background: #f7f8fa;
                top: -1px;
            }
            QTabBar::tab {
                background: transparent;
                border: none;
                padding: 10px 18px;
                margin-right: 6px;
                color: #5b6570;
                font-size: 14px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                color: #1f2933;
                background: #ffffff;
                border: 1px solid #d9dde3;
                border-bottom-color: #ffffff;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
        """)

        self.today_view = TodayView()
        self.monthly_view = MonthlyView()
        self.future_view = FutureView()
        self.collections_view = CollectionsView()

        self.tabs.addTab(self.today_view, "Today")
        self.tabs.addTab(self.monthly_view, "Monthly")
        self.tabs.addTab(self.future_view, "Future")
        self.tabs.addTab(self.collections_view, "Collections")

        main_layout.addWidget(title_label)
        main_layout.addWidget(self.tabs)

        central_widget.setStyleSheet("background: #eef1f4;")
        self.setCentralWidget(central_widget)

    def _connect_signals(self) -> None:
        self.today_view.entries_changed.connect(self._refresh_all_views)
        self.monthly_view.entries_changed.connect(self._refresh_all_views)
        self.future_view.entries_changed.connect(self._refresh_all_views)
        self.tabs.currentChanged.connect(self._refresh_current_views)

    def _refresh_all_views(self) -> None:
        self.today_view.refresh_entries()
        self.monthly_view.refresh_entries()
        self.future_view.refresh_entries()

    def _refresh_current_views(self) -> None:
        self.today_view.refresh_entries()
        self.monthly_view.refresh_entries()
        self.future_view.refresh_entries()
        self.collections_view.refresh_collections()
