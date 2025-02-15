from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QFont
from ui.components.dialogs.overlay import Overlay
                               

class StyledDialog(QDialog):
    def __init__(self, parent=None, title="Dialog"):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QWidget(self)
        self.container.setObjectName("dialogContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(20, 20, 20, 20)
        
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 10)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(title_label.font().family(), 11, QFont.Bold))
        
        close_button = QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.reject)
        
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(close_button)
        
        self.container_layout.addLayout(header)
        self.main_layout.addWidget(self.container)
        
        if parent:
            self.overlay = Overlay(parent)


    def showEvent(self, event):
        super().showEvent(event)
        
        if hasattr(self, 'overlay'):
            self.overlay.show()
            
            if self.parentWidget():
                self.overlay.resize(self.parentWidget().size())
            else:
                self.overlay.resize(self.size())
        parent_geom = self.parentWidget().geometry() if self.parentWidget() else self.geometry()
        self.move(parent_geom.center() - self.rect().center())


    def closeEvent(self, event):
        if hasattr(self, 'overlay'):
            self.overlay.hide()
            self.overlay.deleteLater()
        super().closeEvent(event)


    def reject(self):
        if hasattr(self, 'overlay'):
            self.overlay.hide()
            self.overlay.deleteLater()
        super().reject()
        
        
    def accept(self):
        if hasattr(self, 'overlay'):
            self.overlay.hide()
            self.overlay.deleteLater()
        super().accept()