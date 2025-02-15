import sys
import traceback
import os
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.ui import MainWindow
from app.utils.logger import get_logger


def main():
    try:
        QApplication.setOrganizationName("Veil")
        QApplication.setApplicationName("Veil")
        
        logger = get_logger("main", console_output=True)

        if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )

        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        window = MainWindow()
        window.showMaximized()
        window.activateWindow()
        window.raise_()

        sys.exit(app.exec())

    except Exception as e:
        logger.critical(f"Critical error during startup: {str(e)}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main()