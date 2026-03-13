from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


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
        tabs.addTab(self._build_placeholder_page("Today / Daily Log"), "Today")
        tabs.addTab(self._build_placeholder_page("Monthly Log"), "Monthly")
        tabs.addTab(self._build_placeholder_page("Future Log"), "Future")
        tabs.addTab(self._build_placeholder_page("Collections"), "Collections")

        main_layout.addWidget(title_label)
        main_layout.addWidget(tabs)

        self.setCentralWidget(central_widget)

    def _build_placeholder_page(self, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; padding: 24px;")

        layout.addWidget(label)
        return page