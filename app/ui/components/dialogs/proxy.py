import re
from ui.components.dialogs.base import StyledDialog
from urllib.parse import urlparse
from PySide6.QtWidgets import  QFrame, QVBoxLayout, QLabel, QGroupBox, QLineEdit, QFormLayout, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtGui import QIntValidator, QFont


class ProxyDialog(StyledDialog):    
    def __init__(self, profiles, parent=None, current_proxy=None):
        super().__init__(parent, "Изменение прокси")
        self.profiles = profiles
        self.current_proxy = current_proxy
        self.setMinimumWidth(500)
        self._setup_ui()
    
    
    def _setup_ui(self):
        info_panel = QFrame()
        info_panel.setProperty("class", "info-panel")
        info_layout = QVBoxLayout(info_panel)
        
        profiles_label = QLabel(f"Выбрано профилей: {len(self.profiles)}")
        profiles_label.setFont(QFont(profiles_label.font().family(), 10, QFont.Bold))
        info_layout.addWidget(profiles_label)
        
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
        
        if self.current_proxy:
            try:
                parsed = urlparse(self.current_proxy)
                if parsed.username and parsed.password:
                    self.proxy_user.setText(parsed.username)
                    self.proxy_pass.setText(parsed.password)
                if parsed.hostname and parsed.port:
                    self.proxy_host.setText(parsed.hostname)
                    self.proxy_port.setText(str(parsed.port))
            except Exception:
                pass

        proxy_layout.addRow("IP:", self.proxy_host)
        proxy_layout.addRow("Порт:", self.proxy_port)
        proxy_layout.addRow("Логин:", self.proxy_user)
        proxy_layout.addRow("Пароль:", self.proxy_pass)
        proxy_group.setLayout(proxy_layout)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        
        clear_btn = QPushButton("Очистить")
        clear_btn.clicked.connect(self._clear_fields)
        
        self.ok_btn = QPushButton("Применить")
        self.ok_btn.setProperty("type", "primary")
        self.ok_btn.clicked.connect(self.validate_and_accept)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setProperty("type", "secondary")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(clear_btn)
        buttons.addStretch()
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.ok_btn)
        
        self.container_layout.addWidget(info_panel)
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


    def _clear_fields(self):
        self.proxy_host.clear()
        self.proxy_port.clear()
        self.proxy_user.clear()
        self.proxy_pass.clear()
    
    
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
    
    
    def _show_error(self, title: str, message: str):
        QMessageBox.warning(self, title, message)
    
    
    def get_proxy_string(self) -> str:
        if not self.proxy_host.text().strip():
            return ""
        return f"http://{self.proxy_user.text()}:{self.proxy_pass.text()}@{self.proxy_host.text()}:{self.proxy_port.text()}"
    