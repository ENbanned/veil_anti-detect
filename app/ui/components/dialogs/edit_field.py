from PySide6.QtWidgets import QFormLayout, QLineEdit, QPushButton, QHBoxLayout
from ui.components.dialogs.base import StyledDialog


class EditFieldDialog(StyledDialog):
    def __init__(self, parent=None, title="Редактировать", field_label="Поле:", initial_value=""):
        super().__init__(parent, title)
        self.setMinimumWidth(400)
        self.field_label = field_label
        self.initial_value = initial_value
        self._setup_ui()
    
    
    def _setup_ui(self):
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setText(self.initial_value)
        self.input_field.setMinimumWidth(300)
        
        form_layout.addRow(self.field_label, self.input_field)
        
        self.container_layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.ok_btn = QPushButton("ОК")
        self.ok_btn.setProperty("type", "primary")
        self.ok_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setProperty("type", "secondary")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        
        self.container_layout.addSpacing(20)
        self.container_layout.addLayout(btn_layout)
    
    
    def getValue(self):
        return self.input_field.text()


def show_edit_field_dialog(parent, title, field_label, initial_value):
    dialog = EditFieldDialog(parent, title, field_label, initial_value)
    if dialog.exec():
        return dialog.getValue(), True
    return initial_value, False