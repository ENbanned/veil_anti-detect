from PySide6.QtWidgets import QLabel, QPushButton, QHBoxLayout
from ui.components.dialogs.base import StyledDialog


class DeleteConfirmDialog(StyledDialog):
    def __init__(self, count: int, parent=None):
        super().__init__(parent, "Подтверждение удаления")
        self.setMinimumWidth(400)
        self._setup_ui(count)
    
    
    def _setup_ui(self, count: int):
        message = QLabel(f"Вы уверены, что хотите удалить {count} профил{'ь' if count == 1 else 'я' if 1 < count < 5 else 'ей'}?")
        message.setWordWrap(True)
        message.setStyleSheet("font-size: 11pt;")
        self.container_layout.addWidget(message)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.no_btn = QPushButton("Нет")
        self.no_btn.setProperty("type", "danger")
        self.no_btn.clicked.connect(self.reject)
        
        self.yes_btn = QPushButton("Да")
        self.yes_btn.setProperty("type", "success")
        self.yes_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.no_btn)
        btn_layout.addWidget(self.yes_btn)
        
        self.container_layout.addSpacing(20)
        self.container_layout.addLayout(btn_layout)