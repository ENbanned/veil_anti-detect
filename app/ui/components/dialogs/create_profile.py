from ui.components.dialogs.base import StyledDialog
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QGroupBox, QFormLayout, QLineEdit, QSpinBox, QAbstractSpinBox, QMessageBox
from PySide6.QtGui import QIntValidator
import re


class CreateProfileDialog(StyledDialog):
    def __init__(self, parent=None):
        super().__init__(parent, "Создание профилей")
        self.setMinimumWidth(500)
        self._setup_ui()
    
    
    def _setup_ui(self):
        basic_group = QGroupBox("Основные настройки")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(10)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите базовое имя")
        basic_layout.addRow("Базовое имя:", self.name_edit)
        
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(1)
        self.count_spin.setFixedWidth(100)
        self.count_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        basic_layout.addRow("Количество:", self.count_spin)
        basic_group.setLayout(basic_layout)
        
        proxy_group = QGroupBox("Настройки прокси (поддерживается только HTTP)")
        proxy_layout = QFormLayout()
        proxy_layout.setSpacing(10)

        self.proxy_host = QLineEdit()
        self.proxy_port = QLineEdit()
        self.proxy_user = QLineEdit()
        self.proxy_pass = QLineEdit()
        
        port_validator = QIntValidator(1, 65535, self)
        self.proxy_port.setValidator(port_validator)
        
        self.proxy_host.textChanged.connect(self._try_parse_proxy)
        
        proxy_layout.addRow("IP:", self.proxy_host)
        proxy_layout.addRow("Порт:", self.proxy_port)
        proxy_layout.addRow("Логин:", self.proxy_user)
        proxy_layout.addRow("Пароль:", self.proxy_pass)
        proxy_group.setLayout(proxy_layout)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        
        self.ok_btn = QPushButton("Создать")
        self.ok_btn.setProperty("type", "primary")
        self.ok_btn.clicked.connect(self.validate_and_accept)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setProperty("type", "secondary")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons.addStretch()
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.ok_btn)
        
        self.container_layout.addWidget(basic_group)
        self.container_layout.addWidget(proxy_group)
        self.container_layout.addStretch()
        self.container_layout.addLayout(buttons)


    def _try_parse_proxy(self, text):
        text = text.strip()
        
        if not text:
            return
        patterns = [
            r'^(?:http://)?(?:([^:@]+):([^@]+)@)?([^:@]+):(\d+)/?$',
            r'^([^:@]+):(\d+):([^:@]+):([^:@]+)$',
            r'^(?:([^:@]+):([^@]+)@)?([^:@]+):(\d+)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 4:
                    if '@' in text:
                        user, password, host, port = groups
                    else:
                        host, port, user, password = groups
                    self.proxy_host.setText(host)
                    self.proxy_port.setText(port)
                    if user: self.proxy_user.setText(user)
                    if password: self.proxy_pass.setText(password)
                break


    def validate_and_accept(self):
        if any([
            self.proxy_host.text().strip(),
            self.proxy_port.text().strip(),
            self.proxy_user.text().strip(),
            self.proxy_pass.text().strip()
        ]):
            if not all([
                self.proxy_host.text().strip(),
                self.proxy_port.text().strip(),
                self.proxy_user.text().strip(),
                self.proxy_pass.text().strip()
            ]):
                self._show_error("Ошибка прокси", 
                               "Заполните все поля прокси или оставьте их пустыми")
                return
        self.accept()
        return True


    def _show_error(self, title: str, message: str):
        QMessageBox.warning(self, title, message)


    def get_data(self):
        proxy = ""
        if self.proxy_host.text().strip():
            proxy = f"http://{self.proxy_user.text()}:{self.proxy_pass.text()}@{self.proxy_host.text()}:{self.proxy_port.text()}"
        return (
            self.name_edit.text().strip(),
            self.count_spin.value(),
            proxy
        )
        