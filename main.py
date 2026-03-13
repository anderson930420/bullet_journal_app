import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from database import init_db


def main():
    init_db()

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget {
            color: #1D1D1F;
        }
        QAbstractItemView {
            selection-background-color: #EAF3FF;
            selection-color: #1D1D1F;
        }
        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 6px 2px 6px 2px;
        }
        QScrollBar::handle:vertical {
            background: #D7D7DC;
            border-radius: 5px;
            min-height: 28px;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background: transparent;
            border: none;
        }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
