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

from qgis.PyQt.QtCore import Qt, QPoint, QPointF

from qgis.PyQt.QtGui import (
		QBrush,
		QColor,
		QPen,
		QPainter,
		QPolygonF
)

from qgis.core import (
		Qgis,
		QgsMessageLog,
)

from qgis.gui import (
		QgsMapCanvasItem,
)

from .viewconemapcanvasitem import ViewConeMapCanvasItem

def log(msg):
	QgsMessageLog.logMessage("(IsovistMapCanvasItem) " + msg, 'PST', level=Qgis.Info)

EDGE_WIDTH = 1
MID_POINT_DIAMETER = 8

QCOLOR_INSIDE = QColor("#80fce94f")
QCOLOR_EDGE   = QColor("#c4a000")

BRUSH_INSIDE = QBrush(QCOLOR_INSIDE)
BRUSH_EDGE = QBrush(QCOLOR_EDGE)

PEN_EDGE = QPen(QCOLOR_EDGE, EDGE_WIDTH)

class IsovistMapCanvasItem(ViewConeMapCanvasItem):

	def __init__(self, context, canvas, _id, map_pos, _range, fov, directionAngle):
		self.polygon = QPolygonF()
		self.polygonMapCoords = None
		self.polygonPointCount = 0
		self.setColor(QCOLOR_INSIDE)
		super().__init__(context, canvas, _id, map_pos, _range, fov, directionAngle)
		
	def setColor(self, color):
		self._colorInside = color
		self._penEdge = QPen(QColor(int(color.red() * 0.7), int(color.green() * 0.7), int(color.blue() * 0.7)))

	def color(self):
		return self._colorInside

	def setPolygonPoints(self, ptrToDoubles, pointCount):  # ptrToDoubles = ctypes.POINTER(ctypes.c_double) in map coordinates
		#log("setPolygonPoints")
		self.polygonMapCoords = ptrToDoubles
		self.polygonPointCount = pointCount
		self.updatePolygon()

	def polygonPoints(self):
		return (self.polygonMapCoords, self.polygonPointCount)

	def updatePosition(self):
		#log("updatePosition")
		super().updatePosition()
		self.updatePolygon()

	def updatePolygon(self):
		self.polygon.clear()
		if self.polygonPointCount <= 0:
			return

		pixelsPerMapUnit = 1 / self.mapUnitsPerPixel
		mapPos = self.currentMapOrigin()
		mapPosX = mapPos.x()
		mapPosY = mapPos.y()

		#log("updatePolygon: (%.2f %.2f) (%.2f %.2f)" % (self.pos().x(), self.pos().y(), mapPosX, mapPosY))

		polygon = self.polygon
		
		pointIndex = 0
		pointCount = self.polygonPointCount
		ptrToDoubles = self.polygonMapCoords
		while pointIndex < pointCount:
			x = (ptrToDoubles[pointIndex * 2] - mapPosX) * pixelsPerMapUnit
			y = (mapPosY - ptrToDoubles[pointIndex * 2 + 1]) * pixelsPerMapUnit
			if pointIndex < polygon.size():
				polygon.setPoint(pointIndex, x, y)
			else:
				polygon.append(QPointF(x, y))
			pointIndex += 1

		size = polygon.size()
		while size > self.polygonPointCount:
			size -= 1
			polygon.remove(size)

	def currentMapOrigin(self):
		pos = self.pos()
		return self.toMapCoordinates(QPoint(round(pos.x()), round(pos.y())))

	def paintBackground(self, painter, option, widget):
		#super().paintBackground(painter, option, widget)

		transform = painter.transform()

		#log("paintBackground: (%.2f %.2f) (%.2f %.2f)" % (self.pos().x(), self.pos().y(), transform.m31(), transform.m32()))


		if not self.polygon.isEmpty():
			painter.setBrush(self._colorInside)
			painter.setPen(self._penEdge)
			painter.drawPolygon(self.polygon)

			painter.setPen(Qt.NoPen)
			painter.setBrush(BRUSH_EDGE)
			painter.drawEllipse(int(MID_POINT_DIAMETER * -0.5), int(MID_POINT_DIAMETER * -0.5), MID_POINT_DIAMETER, MID_POINT_DIAMETER)

