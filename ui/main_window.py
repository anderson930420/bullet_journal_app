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

        title_label = QLabel("Bullet Journal App")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 12px;")

        self.tabs = QTabWidget()

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
