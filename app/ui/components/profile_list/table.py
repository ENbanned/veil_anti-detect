from PySide6.QtWidgets import (
    QTableWidget, QWidget, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QEvent, QTimer, QPropertyAnimation
from PySide6.QtGui import QColor, QPalette


class HoverableTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hoveredRow = -1
        self._lastHoveredRow = None
        self._prevOverlay = None
        self.setMouseTracking(True)
        self._wheel_animation = None
        
        self.setStyleSheet("""
            QTableWidget::item { font-size: 10pt !important; }
            QTableWidget::item:hover { background: transparent !important; }
            QTableWidget::item:selected { background: transparent !important; }
            QTableWidget::item:focus { font-size: 10pt !important; }
        """)
        
        self.rowOverlay = QWidget(self.viewport())
        self.rowOverlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        bg_color = self.palette().color(QPalette.Window)
        luminance = 0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()
        overlay_rgb = (255, 255, 255) if luminance < 128 else (200, 200, 220)
        self.overlayColor = QColor(*overlay_rgb, 40)
        
        self.rowOverlay.setStyleSheet(
            f"background-color: rgba({self.overlayColor.red()}, {self.overlayColor.green()}, {self.overlayColor.blue()}, {self.overlayColor.alpha()});"
        )
        
        self.rowOverlay.hide()
        self.opacityEffect = QGraphicsOpacityEffect(self.rowOverlay)
        self.rowOverlay.setGraphicsEffect(self.opacityEffect)
        self.opacityEffect.setOpacity(0.0)
        
        self.overlayAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.overlayAnimation.setDuration(400)
        self.overlayAnimation.finished.connect(self._onOverlayAnimationFinished)
        
        self._leaveTimer = QTimer(self)
        self._leaveTimer.setSingleShot(True)
        self._leaveTimer.setInterval(100)
        
        self.setFocusPolicy(Qt.NoFocus)

    def viewportEvent(self, event):
        if event.type() == QEvent.MouseButtonPress:
            index = self.indexAt(event.pos())
            if index.isValid() and index.column() == 0:
                item = self.item(index.row(), index.column())
                if item is not None:
                    new_state = Qt.Checked if item.checkState() != Qt.Checked else Qt.Unchecked
                    item.setCheckState(new_state)
                    try:
                        self.itemChanged.emit(item)
                    except Exception:
                        pass
                    event.accept()
                    return True
        return super().viewportEvent(event)


    def _onOverlayAnimationFinished(self):
        if self.opacityEffect.opacity() == 0.0:
            self.rowOverlay.hide()


    def updateOverlay(self):
        if self._lastHoveredRow is not None and self._lastHoveredRow != self.hoveredRow:
            if self._prevOverlay is not None:
                try:
                    self._prevOverlay.deleteLater()
                except Exception:
                    pass
                self._prevOverlay = None
            self._prevOverlay = QWidget(self.viewport())
            self._prevOverlay.setAttribute(Qt.WA_TransparentForMouseEvents)
            self._prevOverlay.setStyleSheet(
                f"background-color: rgba({self.overlayColor.red()}, {self.overlayColor.green()}, {self.overlayColor.blue()}, {self.overlayColor.alpha()});"
            )
            y_prev = self.rowViewportPosition(self._lastHoveredRow)
            h_prev = self.rowHeight(self._lastHoveredRow)
            self._prevOverlay.setGeometry(0, y_prev, self.viewport().width(), h_prev)
            self._prevOverlay.show()
            self._prevOverlay.lower()
            prevEffect = QGraphicsOpacityEffect(self._prevOverlay)
            self._prevOverlay.setGraphicsEffect(prevEffect)
            prevEffect.setOpacity(1.0)
            fadeOut = QPropertyAnimation(prevEffect, b"opacity", self)
            fadeOut.setDuration(400)
            fadeOut.setStartValue(1.0)
            fadeOut.setEndValue(0.0)
            fadeOut.start()
            fadeOut.finished.connect(self._cleanupPrevOverlay)
        self._lastHoveredRow = self.hoveredRow
        
        if self.hoveredRow < 0:
            self.overlayAnimation.stop()
            self.overlayAnimation.setStartValue(self.opacityEffect.opacity())
            self.overlayAnimation.setEndValue(0.0)
            self.overlayAnimation.start()
        else:
            y = self.rowViewportPosition(self.hoveredRow)
            h = self.rowHeight(self.hoveredRow)
            self.rowOverlay.setGeometry(0, y, self.viewport().width(), h)
            self.rowOverlay.show()
            self.rowOverlay.lower()
            self.opacityEffect.setOpacity(0.0)
            self.overlayAnimation.stop()
            self.overlayAnimation.setStartValue(0.0)
            self.overlayAnimation.setEndValue(1.0)
            self.overlayAnimation.start()


    def _cleanupPrevOverlay(self):
        try:
            if self._prevOverlay is not None:
                self._prevOverlay.deleteLater()
        except Exception:
            pass
        self._prevOverlay = None


    def mouseMoveEvent(self, event):
        row = self.rowAt(event.pos().y())
        
        if row != self.hoveredRow:
            self.hoveredRow = row
            self._leaveTimer.stop()
            self.updateOverlay()
        super().mouseMoveEvent(event)


    def leaveEvent(self, event):
        self._leaveTimer.timeout.connect(self._clearHoveredRow)
        self._leaveTimer.start()
        super().leaveEvent(event)


    def _clearHoveredRow(self):
        self.hoveredRow = -1
        self.updateOverlay()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateOverlay()