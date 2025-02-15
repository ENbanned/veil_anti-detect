import logging
import sys
import traceback

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QMessageBox
from utils.logger import get_logger


logger = get_logger("exception_manager", console_output=True)


def setup_exception_handling(app):
    def exception_hook(exctype, value, tb):
        logger.critical("Unhandled exception occurred", exc_info=(exctype, value, tb))
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Critical error occurred")
        msg.setInformativeText(str(value))
        msg.setDetailedText(''.join(traceback.format_exception(exctype, value, tb)))
        msg.setWindowTitle("Error")
        msg.exec_()
        
        sys.__excepthook__(exctype, value, tb)
    
    sys.excepthook = exception_hook


    def qt_message_handler(mode, context, message):
        if mode == QtMsgType.Critical:
            logger.critical(f"Qt Critical Error: {message}")
        elif mode == QtMsgType.Warning:
            logger.warning(f"Qt Warning: {message}")
            
    qInstallMessageHandler(qt_message_handler)