from PySide6.QtWidgets import QLabel, QCheckBox
from PySide6.QtCore import Qt


class FixedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("font-size: 10pt !important;")
     
        
    def enterEvent(self, event):
        event.ignore()
        
        
    def leaveEvent(self, event):
        event.ignore()
      
        
class HeaderCheckBox(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("")