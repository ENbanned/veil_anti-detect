from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtGui import QColor


class RowHighlightDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        if parent is not None:
            baseColor = parent.palette().highlight().color()
            self.highlightColor = QColor(baseColor.red(), baseColor.green(), baseColor.blue(), 20)
        else:
            self.highlightColor = QColor(100, 100, 100, 20)
        self.hoveredRow = -1


    def paint(self, painter, option, index):
        if index.row() == self.hoveredRow:
            painter.save()
            painter.fillRect(option.rect, self.highlightColor)
            painter.restore()
        super().paint(painter, option, index)