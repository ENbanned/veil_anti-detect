from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt

from ui.components.profile_list.labels import FixedLabel


def createEditableCell(text, edit_callback):
    container = QWidget()
    container.setAttribute(Qt.WA_TranslucentBackground, True)
    container.setStyleSheet("background: transparent; font-size: 10pt !important;")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(2, 2, 2, 2)
    layout.setSpacing(4)
    layout.setAlignment(Qt.AlignCenter)
    
    display_text = text.strip() if text.strip() else "-"
    label = FixedLabel(display_text)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet("background: transparent; border: none; font-size: 10pt !important;")
    
    btn = QPushButton()
    btn.setFixedSize(20, 20)
    btn.setObjectName("editButton")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setVisible(False)
    btn.clicked.connect(edit_callback)
    
    layout.addWidget(label)
    layout.addWidget(btn)
    
    return container