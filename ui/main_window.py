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

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("Bullet Journal App")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 12px;")

        tabs = QTabWidget()
        tabs.addTab(TodayView(), "Today")
        tabs.addTab(MonthlyView(), "Monthly")
        tabs.addTab(FutureView(), "Future")
        tabs.addTab(CollectionsView(), "Collections")

        main_layout.addWidget(title_label)
        main_layout.addWidget(tabs)

        self.setCentralWidget(central_widget)