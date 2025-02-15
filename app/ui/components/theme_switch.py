from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal, QSettings
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame


class ThemeSwitch(QFrame):    
    theme_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = None
        self._progress = 0.0
        
        settings = QSettings()
        saved_theme = settings.value("theme", "light")
        self._is_dark = saved_theme == "dark"
        
        self._setup_ui()
        
        self._progress = 1.0 if self._is_dark else 0.0
    
    def _setup_ui(self):
        self.setFixedSize(50, 26)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        self._animation = QPropertyAnimation(self, b'progress', self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
    
    
    def _get_progress(self):
        return self._progress
    
    
    def _set_progress(self, value):
        self._progress = value
        self.update()
    
    progress = Property(float, _get_progress, _set_progress)
    
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dark = not self._is_dark

            self._animation.setStartValue(0.0 if self._is_dark else 1.0)
            self._animation.setEndValue(1.0 if self._is_dark else 0.0)
            self._animation.start()
            
            self.theme_changed.emit("dark" if self._is_dark else "light")
    
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self._is_dark:
            bg_color = QColor("#212529")
            switch_color = QColor("#ffffff")
            icon_color = QColor("#ffc107")
        else:
            bg_color = QColor("#6c757d")
            switch_color = QColor("#ffffff")
            icon_color = QColor("#495057")
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 13, 13)
        painter.fillPath(path, bg_color)
        
        switch_size = self.height() - 4
        x = 2 + (self.width() - switch_size - 4) * (self._progress)
        
        switch_path = QPainterPath()
        switch_path.addEllipse(x, 2, switch_size, switch_size)
        painter.fillPath(switch_path, switch_color)
        
        icon_size = switch_size - 8
        icon_x = x + 4
        icon_y = 6
        
        if self._is_dark:
            painter.setPen(Qt.NoPen)
            painter.setBrush(icon_color)
            painter.drawEllipse(icon_x, icon_y, icon_size, icon_size)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(icon_color)
            painter.drawEllipse(icon_x, icon_y, icon_size, icon_size)
            
            painter.setBrush(switch_color)
            painter.drawEllipse(icon_x - 2, icon_y - 2, icon_size, icon_size)
            