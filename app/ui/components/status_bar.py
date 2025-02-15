from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPalette
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._opacity = 1.0

        self._setup_ui()
        self._setup_animations()
        self._progress = 0.0
        
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)
        
        self.message_label = QLabel()
        layout.addWidget(self.message_label)
        
        self.progress_widget = ProgressWidget(self)
        self.progress_widget.setFixedWidth(100)
        self.progress_widget.setVisible(False)
        layout.addWidget(self.progress_widget)
        
        layout.addStretch()
        
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        
    def _setup_animations(self):
        self.fade_animation = QPropertyAnimation(self, b"opacity", self)
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._opacity = 1.0
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.clear)
       
        
    def _get_opacity(self):
        return self._opacity
      
        
    def _set_opacity(self, value):
        self._opacity = value
        palette = self.message_label.palette()
        color = QColor(self.current_color)
        color.setAlphaF(value)
        palette.setColor(QPalette.WindowText, color)
        self.message_label.setPalette(palette)
        
    opacity = Property(float, _get_opacity, _set_opacity)
    
    
    def show_message(self, message: str, timeout: int = 3000):
        self.current_color = "#0d6efd"  
        self._show_notification(message, self.current_color, timeout)
    
    
    def show_warning(self, message: str, timeout: int = 3000):
        self.current_color = "#ffc107" 
      
        self._show_notification(message, self.current_color, timeout)
    
    def show_error(self, message: str, timeout: int = 3000):
        self.current_color = "#dc3545"
        self._show_notification(message, self.current_color, timeout)
    
    
    def _show_notification(self, message: str, color: str, timeout: int):
        self.fade_animation.stop()
        self.hide_timer.stop()
        
        self.message_label.setText(message)
        self.current_color = color
        
        self._opacity = 1.0
        
        if timeout > 0:
            self.hide_timer.start(timeout)
            
    
    def clear(self):
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()


class ProgressWidget(QWidget):    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self.setFixedHeight(6)
        
        
    def setProgress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        self.update()
       
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#e9ecef"))
        painter.drawRoundedRect(self.rect(), 3, 3)
        
        if self._progress > 0:
            progress_width = int(self.width() * self._progress)
            progress_rect = self.rect()
            progress_rect.setWidth(progress_width)
            
            gradient = QLinearGradient(0, 0, self.width(), 0)
            gradient.setColorAt(0, QColor("#0d6efd"))
            gradient.setColorAt(1, QColor("#0dcaf0"))
            
            painter.setBrush(gradient)
            painter.drawRoundedRect(progress_rect, 3, 3)
            