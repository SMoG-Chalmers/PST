"""
Copyright 2019 Meta Berghauser Pont

This file is part of PST.

PST is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. The GNU Lesser General Public License
is intended to guarantee your freedom to share and change all versions
of a program--to make sure it remains free software for all its users.

PST is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with PST. If not, see <http://www.gnu.org/licenses/>.
"""

from qgis.PyQt.QtCore import QRectF, QPoint, QPointF
from qgis.PyQt.QtGui import (
		QBrush,
		QColor,
		QPen,
		QPainter,
		QPainterPath,
		QPolygonF,
)
from qgis.core import (
		QgsRectangle,
)
from qgis.gui import (
		QgsMapCanvasItem,
)

# from qgis.core import QgsMessageLog
# QgsMessageLog.logMessage("Some logging text")

# Caching of QPen-object
LastPen = None
LastPenWidth = 1
LastPenColor = QColor("#000000")
def GetPen(width, color):
	global LastPen, LastPenWidth, LastPenColor
	if LastPen is None or LastPenWidth != width or LastPenColor != color:
		LastPen = QPen(color)
		LastPen.setWidthF(width)
		LastPenWidth = width
		LastPenColor = color
	return LastPen


class BaseMapCanvasItem(QgsMapCanvasItem):

	def __init__(self, canvas, originX: float, originY: float):
		""" bbLocal is relative to (originX, originY) """
		self._canvas = canvas
		self._bbCanvas = None
		self._pixelsPerMapUnit = 1
		super().__init__(canvas)
		self._setMapPosition(originX, originY)
		self.updatePosition()

	def updatePosition(self):
		""" Called by QGIS on zoom/pan etc """
		super().updatePosition()  # If we don't do this QGIS will crash when the canvas item is removed...
		self._pixelsPerMapUnit = 1.0 / self._canvas.getCoordinateTransform().mapUnitsPerPixel()

	def boundingRect(self):
		""" Called by QGIS """
		return self._bbCanvas

	def _setMapPosition(self, x, y):
		# Annoying workaround needed for setting map position (min(x) and max(y) of rectangle is used as position)
		small_value = 0.01
		self.setRect(QgsRectangle(x, y - small_value, x + small_value, y))


class SymbolMapCanvasItem(BaseMapCanvasItem):

	def __init__(self, canvas, centerX: float, centerY: float, width: float, height: float):
		super().__init__(canvas, centerX, centerY)
		self._bbCanvas = QRectF(
			-0.5 * width, 
			-0.5 * height, 
			width, 
			height)


class ScalableMapCanvasItem(BaseMapCanvasItem):

	def __init__(self, canvas, originX: float, originY: float, bbLocal: QRectF):
		""" bbLocal is relative to (originX, originY) """
		self._bbLocal = bbLocal
		super().__init__(canvas, originX, originY)

	def updatePosition(self):
		""" Called by QGIS on zoom/pan etc """
		super().updatePosition()
		pixelsPerMapUnit = self._pixelsPerMapUnit
		self._bbCanvas = QRectF(
			self._bbLocal.x() * pixelsPerMapUnit, 
			self._bbLocal.y() * pixelsPerMapUnit, 
			self._bbLocal.width() * pixelsPerMapUnit, 
			self._bbLocal.height() * pixelsPerMapUnit)


class CircleMapCanvasItem(SymbolMapCanvasItem):

	def __init__(self, canvas, centerX: float, centerY: float, radiusPixels: float, brush : QBrush, pen: QPen):
		""" bbLocal is relative to (originX, originY) """
		self._brush = brush
		self._pen = pen
		super().__init__(canvas, centerX, centerY, radiusPixels * 2, radiusPixels * 2)

	def paint(self, painter, option, widget):
		""" Called by QGIS """
		painter.setRenderHint(QPainter.Antialiasing)
		painter.setRenderHint(QPainter.HighQualityAntialiasing)
		painter.setBrush(self._brush)
		painter.setPen(self._pen)
		painter.drawEllipse(self._bbCanvas)


class PolygonMapCanvasItem(ScalableMapCanvasItem):

	def __init__(self, canvas, originX: float, originY: float, bbLocal: QRectF, polygon: QPolygonF, brush : QBrush, penColor: QColor):
		""" bbLocal is relative to (originX, originY) """
		super().__init__(canvas, originX, originY, bbLocal)
		self._polygon = polygon
		self._brush = brush
		self._penColor = penColor

	def paint(self, painter, option, widget):
		""" Called by QGIS """
		painter.scale(self._pixelsPerMapUnit, -self._pixelsPerMapUnit)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.setRenderHint(QPainter.HighQualityAntialiasing)
		painter.setBrush(self._brush)
		painter.setPen(GetPen(1.0 / self._pixelsPerMapUnit, self._penColor))
		painter.drawPolygon(self._polygon)
		

class PathMapCanvasItem(ScalableMapCanvasItem):

	def __init__(self, canvas, originX: float, originY: float, bbLocal: QRectF, path: QPainterPath, brush : QBrush, penColor: QColor):
		""" bbLocal is relative to (originX, originY) """
		super().__init__(canvas, originX, originY, bbLocal)
		self._path = path
		self._brush = brush
		self._penColor = penColor

	def paint(self, painter, option, widget):
		""" Called by QGIS """
		painter.scale(self._pixelsPerMapUnit, -self._pixelsPerMapUnit)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.setRenderHint(QPainter.HighQualityAntialiasing)
		painter.setBrush(self._brush)
		painter.setPen(GetPen(1.0 / self._pixelsPerMapUnit, self._penColor))
		painter.drawPath(self._path)