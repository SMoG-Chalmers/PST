from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import Qt

from qgis.PyQt.QtGui import (
	QColor,
	QBrush,
	QPainter,
)

from qgis.PyQt.QtWidgets import (
	QFrame,
	QStyle,
	QStyleOptionFrame,
	QColorDialog,
	QLineEdit,
)


class ColorPicker(QFrame):
	colorChanged = QtCore.pyqtSignal(QColor)
	colorSelected = QtCore.pyqtSignal(QColor)

	def __init__(self, parent, color):
		QFrame.__init__(self, parent)
		#self.setFrameShape(QFrame.Box)
		#self.setLineWidth(1)
		self.setCursor(Qt.PointingHandCursor)
		self.setColor(color)
		self.styleoption = QStyleOptionFrame()  # QStyleOptionFrameV2
		editTemp = QLineEdit()
		editTemp.initStyleOption(self.styleoption)
		self._sizeHint = editTemp.sizeHint()

	def sizeHint(self):
		return self._sizeHint

	def color(self, color):
		return self._color

	def setColor(self, color):
		self._color = color
		self._brush = QBrush(color)
		self.repaint()

	def _selectColor(self):
		prevColor = self._color
		dialog = QColorDialog(self._color, self)
		dialog.currentColorChanged.connect(self.onColorChanged)
		dialog.colorSelected.connect(self.onColorChanged)
		if dialog.exec():
			self.colorSelected.emit(self._color)
		else:
			self.setColor(prevColor)
			self.colorChanged.emit(prevColor)

	def mouseReleaseEvent(self, event):
		self._selectColor()

	def paintEvent(self, paintEvent):
		painter = QPainter(self)
		painter.setPen(Qt.NoPen)
		painter.setBrush(self._brush)
		# painter.drawRect(paintEvent.rect().adjusted(1,1,-1-1))
		self.styleoption.rect = self.contentsRect()
		self.style().drawPrimitive(QStyle.PE_PanelLineEdit , self.styleoption, painter)

	@QtCore.pyqtSlot(QColor)
	def onColorChanged(self, color):
		self.setColor(color)
		self.colorChanged.emit(color)