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

"""
NOTE: This file is deprecated and will likely be merged into isovistmapcanvasitem.py soon.
"""

import math

from qgis.PyQt.QtCore import Qt, QRectF, QPoint, QPointF

from qgis.PyQt.QtGui import (
		QBrush,
		QColor,
		QPen,
		QPainter,
		QPainterPath,
)

from qgis.PyQt.QtWidgets import QToolTip 

from qgis.core import (
		Qgis,
		QgsMessageLog,
		QgsRectangle,
)

from qgis.gui import (
		QgsMapCanvasItem,
)

RANGE_FIELD_NAME     = 'range'
FOV_FIELD_NAME       = 'fov'
DIRECTION_FIELD_NAME = 'dir'

COLOR_INSIDE = QColor("#406d97c4")
COLOR_INSIDE_HOT = QColor("#806d97c4")
COLOR_EDGE = QColor("#4e7094")
COLOR_EDGE_HOT = QColor("#d765b1")  # QColor("#ff0000")

SNAP_RANGE = 7
ORIGIN_RADIUS = 5
EDGE_WIDTH = 1
EDGE_WIDTH_HOT = 2

QCOLOR_INSIDE = QColor(COLOR_INSIDE)
QCOLOR_INSIDE_HOT = QColor(COLOR_INSIDE_HOT)
QCOLOR_EDGE = QColor(COLOR_EDGE)
QCOLOR_EDGE_HOT = QColor(COLOR_EDGE_HOT)
QCOLOR_EDGE = QColor(COLOR_EDGE)
QCOLOR_EDGE_HOT = QColor(COLOR_EDGE_HOT)

BRUSH_INSIDE = QBrush(QCOLOR_INSIDE)
BRUSH_INSIDE_HOT = QBrush(QCOLOR_INSIDE_HOT)
BRUSH_EDGE = QBrush(QCOLOR_EDGE)
BRUSH_EDGE_HOT = QBrush(QCOLOR_EDGE_HOT)

PEN_EDGE = QPen(QCOLOR_EDGE, EDGE_WIDTH)
PEN_EDGE_HOT = QPen(QBrush(QCOLOR_EDGE), EDGE_WIDTH_HOT)
PEN_EDGE_HOVER = QPen(QBrush(QCOLOR_EDGE_HOT), EDGE_WIDTH_HOT)
PEN_EDGE_HOT_DOTTED = QPen(QBrush(QCOLOR_EDGE), EDGE_WIDTH_HOT, Qt.DashLine)
PEN_EDGE_HOVER_DOTTED = QPen(QBrush(QCOLOR_EDGE_HOT), EDGE_WIDTH_HOT, Qt.DashLine)

ORIGIN_QRECT = QRectF(-ORIGIN_RADIUS, -ORIGIN_RADIUS, ORIGIN_RADIUS * 2, ORIGIN_RADIUS * 2)


STATE_IDLE = 0
STATE_HOT  = 1
STATE_EDIT = 2

ELEMENT_NONE        = 0
ELEMENT_ARC         = 1
ELEMENT_SIDE_UPPER  = 2
ELEMENT_SIDE_LOWER  = 4
ELEMENT_SIDE_BOTH   = ELEMENT_SIDE_UPPER + ELEMENT_SIDE_LOWER
ELEMENT_EDGE        = ELEMENT_SIDE_BOTH + ELEMENT_ARC
ELEMENT_INSIDE      = 8
ELEMENT_ORIGIN      = 16
ELEMENT_CENTER_LINE = 32

QPOINTF_ZERO = QPointF(0, 0)

def log(msg):
	QgsMessageLog.logMessage("(IsovistTool) " + msg, 'PST', level=Qgis.Info)

def radToDeg(radians):
	return radians * 180 / math.pi

def degToRad(degrees):
	return degrees * math.pi / 180

def deltaAngleDegrees(a0, a1):
	""" Returns angle in degrees in range (-180,180]. Assumes a0 and a1 € [0, 360) """
	delta = a1 - a0
	if delta > 180:
		return delta - 360
	if delta <= -180:
		return delta + 360
	return delta

def oppositeAngleDegrees(degrees):
	degrees += 180
	if degrees >= 360:
		degrees -= 360
	return degrees

def angleFromLocalCoordsDegrees(x, y):
	angle = math.atan2(-y, x) * 180 / math.pi
	if angle < 0:
		angle += 360
	return angle

def pointDistanceFromLineSegment(px, py, x0, y0, x1, y1):
	tx = x1 - x0
	ty = y1 - y0
	line_length = math.sqrt(tx * tx + ty * ty)
	tx /= line_length
	ty /= line_length
	dx = px - x0
	dy = py - y0
	t = tx * dx + ty * dy
	if t <= 0:
		return math.sqrt(dx * dx + dy * dy)
	if t >= line_length:
		dx = px - x1
		dy = py - y1
		return math.sqrt(dx * dx + dy * dy)
	return abs(tx * dy + ty * -dx)

def clamp(value, minValue, maxValue):
	return max(minValue, min(maxValue, value))


class ViewConeMapCanvasItemContext:
	def canEdit(self):
		pass

	def setAttribute(self, featureId, fieldName, value, temporary):
		pass

	def setPosition(self, featureId, x, y, temporary):
		pass


class ViewConeMapCanvasItem(QgsMapCanvasItem):

	def __init__(self, context, canvas, id, map_pos, range, fov, directionAngle):
		self.context = context
		self.canvas = canvas
		self.id = id
		self.path = QPainterPath()
		self.range = range
		self.fov = fov
		self.directionAngle = directionAngle
		self.bbCanvas = QRectF(0,0,1,1)
		self.state = STATE_IDLE
		self.currentElement = ELEMENT_NONE
		self.refMouse = 0
		self.refValue = 0
		super().__init__(canvas)
		self.setMapPosition(map_pos.x(), map_pos.y())
		self.updatePosition()
		self.filled = True

	def setMaxViewDistance(self, distance):
		self.range = max(0, distance)

	def maxViewDistance(self):
		return self.range

	def setFieldOfView(self, fov):
		self.fov = clamp(fov, 0, 360)

	def fieldOfView(self):
		return self.fov

	def setViewDirection(self, direction):
		self.directionAngle = clamp(direction, 0, 360)

	def viewDirection(self):
		return self.directionAngle

	def setFilled(self, filled):
		self.filled = filled

	def setState(self, state):
		self.state = state
		self.updateCursor()
		self.update()

	def setCurrentElement(self, element):
		if element == self.currentElement:
			return
		self.currentElement = element
		self.updateCursor()

	def updateCursor(self):
		# if not self.context.canEdit():
		# 	self.context.setCursor(Qt.ArrowCursor if self.currentElement == ELEMENT_NONE else Qt.PointingHandCursor)
		# 	return
		if self.currentElement == ELEMENT_INSIDE:
			self.context.setCursor(Qt.ArrowCursor)
		elif self.currentElement & ELEMENT_EDGE:
			self.context.setCursor(Qt.ClosedHandCursor if self.state == STATE_EDIT else Qt.OpenHandCursor)
		elif self.currentElement == ELEMENT_CENTER_LINE:
			self.context.setCursor(Qt.CrossCursor)
		elif self.currentElement == ELEMENT_ORIGIN:
			self.context.setCursor(Qt.SizeAllCursor)
		else:
			self.context.setCursor(Qt.ArrowCursor)

	def elementFromCanvasCoords(self, x, y):
		pos = self.pos()
		x -= pos.x()
		y -= pos.y()
		dist_from_origin = math.sqrt(x*x + y*y)

		if dist_from_origin > max(self.canvasRange + SNAP_RANGE, ORIGIN_RADIUS):
			return ELEMENT_NONE

		# If the size of the view cone is small enough we can only hit ELEMENT_INSIDE
		if self.canvasRange < ORIGIN_RADIUS + SNAP_RANGE:
			return ELEMENT_INSIDE

		if dist_from_origin < ORIGIN_RADIUS + SNAP_RANGE:
			return ELEMENT_ORIGIN
		if self.fov < 360:
			perimeterCoords = self.perimeterCoordsFromAngle(degToRad(self.directionAngle - self.fov * 0.5))
			dLower = pointDistanceFromLineSegment(x, y, 0, 0, perimeterCoords[0], perimeterCoords[1])
			perimeterCoords = self.perimeterCoordsFromAngle(degToRad(self.directionAngle))
			dMiddle = pointDistanceFromLineSegment(x, y, 0, 0, perimeterCoords[0], perimeterCoords[1])
			perimeterCoords = self.perimeterCoordsFromAngle(degToRad(self.directionAngle + self.fov * 0.5))
			dUpper = pointDistanceFromLineSegment(x, y, 0, 0, perimeterCoords[0], perimeterCoords[1])
			dMin = min(dLower, dMiddle, dUpper)
			if dMin <= SNAP_RANGE:
				if dLower == dMin:
					return ELEMENT_SIDE_LOWER
				if dUpper == dMin:
					return ELEMENT_SIDE_UPPER
				return ELEMENT_CENTER_LINE
			angle = angleFromLocalCoordsDegrees(x, y)
			angle_low = self.directionAngle - self.fov * 0.5
			if angle_low < 0:
				angle_low += 360
			angle_high = angle_low + self.fov
			if angle_high >= 360:
				angle_high -= 360
			if angle_low < angle_high:
				if angle < angle_low or angle > angle_high:
					return ELEMENT_NONE
			elif angle < angle_low and angle > angle_high:
				return ELEMENT_NONE
		else:
			perimeterCoords = self.perimeterCoordsFromAngle(degToRad(self.directionAngle + 180))
			if pointDistanceFromLineSegment(x, y, 0, 0, perimeterCoords[0], perimeterCoords[1]) <= SNAP_RANGE:
				return ELEMENT_SIDE_BOTH

		if dist_from_origin > self.canvasRange - SNAP_RANGE:
			return ELEMENT_ARC
		return ELEMENT_INSIDE

	def perimeterCoordsFromAngle(self, angle_radians):
		return (math.cos(angle_radians) * self.canvasRange, -math.sin(angle_radians) * self.canvasRange)

	def testIntersection(self, x, y):
		return self.elementFromCanvasCoords(x, y) != ELEMENT_NONE

	def tryMouseEnter(self, x, y):
		self.setCurrentElement(self.elementFromCanvasCoords(x, y))
		if self.currentElement == ELEMENT_NONE:
			return False
		self.setState(STATE_HOT)
		return True

	def onMouseMove(self, x, y):
		if self.state == STATE_EDIT:
			pos = self.pos()
			dx = x - pos.x()
			dy = y - pos.y()
			if self.currentElement & ELEMENT_SIDE_BOTH:
				mouseDirectionAngle = angleFromLocalCoordsDegrees(dx ,dy)
				if self.currentElement == ELEMENT_SIDE_BOTH:
					# This is first time we moved since pressing doun mouse button. Decide
					# which edge we grab depending on this initial movement direction.
					deltaAngle = deltaAngleDegrees(self.refMouse, mouseDirectionAngle)
					if deltaAngle > 0:
						self.currentElement = ELEMENT_SIDE_LOWER
					elif deltaAngle < 0:						
						self.currentElement = ELEMENT_SIDE_UPPER
					else:
						# No movement yet
						return
				deltaAngle = deltaAngleDegrees(self.directionAngle, mouseDirectionAngle)
				if self.currentElement == ELEMENT_SIDE_UPPER and deltaAngle < 0 or self.currentElement == ELEMENT_SIDE_LOWER and deltaAngle > 0:
					self.fov = 0 if self.fov < 180 else 360
				else:
					self.fov = abs(deltaAngle) * 2
				self.context.setAttribute(self.id, FOV_FIELD_NAME, self.fov, final = False)
				QToolTip.showText(self.canvas.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))), "%d deg" % self.fov)
				self.update()
			elif self.currentElement == ELEMENT_ARC:
				self.range = (self.refValue + math.sqrt(dx*dx + dy*dy)) * self.mapUnitsPerPixel
				self.context.setAttribute(self.id, RANGE_FIELD_NAME, self.range, final = False)
				QToolTip.showText(self.canvas.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))), "%d m" % self.range)
				self.updatePosition()
			elif self.currentElement == ELEMENT_ORIGIN:
				(map_pos_x, map_pos_y) = self.currentDragMapPosFromMousePos(x, y)
				self.context.setPosition(self.id, map_pos_x, map_pos_y, final = False)
				self.setMapPosition(map_pos_x, map_pos_y)
				self.updatePosition()
			elif self.currentElement == ELEMENT_CENTER_LINE:
				self.directionAngle = math.atan2(-dy, dx) * 180 / math.pi
				if self.directionAngle < 0:
					self.directionAngle += 360
				self.context.setAttribute(self.id, DIRECTION_FIELD_NAME, self.directionAngle, final = False)
				self.update()
			return
		element = self.elementFromCanvasCoords(x, y)
		if not self.context.canEdit() and element != ELEMENT_NONE:
			element = ELEMENT_INSIDE
		if element != self.currentElement:
			self.setCurrentElement(element)
			self.update()

	def onMouseLeave(self):
		self.setCurrentElement(ELEMENT_NONE)
		self.setState(STATE_IDLE)

	def onMousePress(self, e):
		if self.currentElement == ELEMENT_ARC:
			pos = self.pos()
			mousePos = e.pos()
			dx = mousePos.x() - pos.x()
			dy = mousePos.y() - pos.y()
			self.refValue = self.canvasRange - math.sqrt(dx*dx + dy*dy)
			self.setState(STATE_EDIT)
		elif self.currentElement == ELEMENT_ORIGIN:
			item_canvas_pos = self.pos()
			mouse_canvas_pos = e.pos()
			item_map_pos = self.toMapCoordinates(QPoint(round(item_canvas_pos.x()), round(item_canvas_pos.y())))
			self.refMouse  = item_map_pos.x() - mouse_canvas_pos.x() * self.mapUnitsPerPixel
			self.refMouse2 = item_map_pos.y() + mouse_canvas_pos.y() * self.mapUnitsPerPixel
			self.setState(STATE_EDIT)
		elif self.currentElement & ELEMENT_SIDE_BOTH:
			mousePos = e.pos()
			pos = self.pos()
			dx = mousePos.x() - pos.x()
			dy = mousePos.y() - pos.y()
			self.refMouse = angleFromLocalCoordsDegrees(dx, dy)
			self.setState(STATE_EDIT)
		elif self.currentElement == ELEMENT_CENTER_LINE:
			self.refMouse = e.pos().y()
			self.refValue = self.fov
			self.setState(STATE_EDIT)

	def currentDragMapPosFromMousePos(self, x, y):
		return (self.refMouse + x * self.mapUnitsPerPixel, self.refMouse2 - y * self.mapUnitsPerPixel)

	def onMouseRelease(self, e):
		if self.state == STATE_EDIT:
			if self.currentElement == ELEMENT_ARC:
				self.context.setAttribute(self.id, RANGE_FIELD_NAME, self.range, final = True)
			elif self.currentElement & ELEMENT_SIDE_BOTH:
				self.context.setAttribute(self.id, FOV_FIELD_NAME, self.fov, final = True)
			elif self.currentElement & ELEMENT_ORIGIN:
				(map_pos_x, map_pos_y) = self.currentDragMapPosFromMousePos(e.pos().x(), e.pos().y())
				self.context.setPosition(self.id, map_pos_x, map_pos_y, final = True)
			else:
				self.context.setAttribute(self.id, DIRECTION_FIELD_NAME, self.directionAngle, final = True)
		elif self.currentElement == ELEMENT_INSIDE:
			pass


		self.setState(STATE_HOT)

	def setMapPosition(self, x, y):
		# Annoying workaround needed for setting map position (min(x) and max(y) of rectangle is used as position)
		small_value = 0.01
		self.setRect(QgsRectangle(x, y - small_value, x + small_value, y))

	def updatePosition(self):
		""" Called by QGIS on zoom/pan etc """
		super().updatePosition()  # If we don't do this QGIS will crash when the canvas item is removed...

		self.mapUnitsPerPixel = self.canvas.getCoordinateTransform().mapUnitsPerPixel()
		self.canvasRange = self.range / self.mapUnitsPerPixel
		self.bbCanvas = QRectF(-self.canvasRange, -self.canvasRange, self.canvasRange * 2, self.canvasRange * 2)

	def boundingRect(self):
		""" Called by QGIS """
		return self.bbCanvas

	def paintBackground(self, painter, option, widget):
		if self.fov >= 360:
			painter.setBrush(BRUSH_INSIDE if self.currentElement == ELEMENT_NONE else BRUSH_INSIDE_HOT)
			painter.setPen(Qt.NoPen)
			painter.drawEllipse(self.bbCanvas)
		else:
			start_angle_deg = self.directionAngle - self.fov * 0.5
			path = self.path
			path.clear()
			path.moveTo(0, 0)
			path.arcTo(self.bbCanvas, start_angle_deg, self.fov)
			painter.fillPath(path, QCOLOR_INSIDE if self.currentElement == ELEMENT_NONE else QCOLOR_INSIDE_HOT)

	def paintForeground(self, painter, option, widget):
		if self.fov >= 360:
			if self.currentElement == ELEMENT_NONE:
				painter.setPen(PEN_EDGE)
			elif self.currentElement == ELEMENT_ARC:
				painter.setPen(PEN_EDGE_HOVER)
			else:
				painter.setPen(PEN_EDGE_HOT)
			painter.setBrush(Qt.NoBrush)
			painter.drawEllipse(self.bbCanvas)
			if self.currentElement != ELEMENT_NONE and self.context.canEdit() and (self.state != STATE_EDIT or self.currentElement & ELEMENT_SIDE_BOTH):
				painter.setPen(PEN_EDGE_HOVER if self.currentElement & ELEMENT_SIDE_BOTH else PEN_EDGE_HOT)
				edge_angle_rad = degToRad(self.directionAngle + 180)
				perimeterCoords = self.perimeterCoordsFromAngle(edge_angle_rad)
				painter.drawLine(QPOINTF_ZERO, QPointF(perimeterCoords[0], perimeterCoords[1]))
		else:
			start_angle_deg = self.directionAngle - self.fov * 0.5
			path = self.path
			path.clear()
			path.moveTo(0, 0)
			path.arcTo(self.bbCanvas, start_angle_deg, self.fov)
			path.lineTo(0, 0)
			painter.setPen(PEN_EDGE if self.currentElement == ELEMENT_NONE else PEN_EDGE_HOT)
			painter.setBrush(Qt.NoBrush)
			painter.drawPath(path)

			# Center line
			if self.currentElement != ELEMENT_NONE:
				perimeterCenter = self.perimeterCoordsFromAngle(degToRad(self.directionAngle))
				painter.setPen(PEN_EDGE_HOVER_DOTTED if self.currentElement == ELEMENT_CENTER_LINE else PEN_EDGE_HOT_DOTTED)
				painter.drawLine(QPOINTF_ZERO, QPointF(perimeterCenter[0], perimeterCenter[1]))

			if self.currentElement == ELEMENT_ARC:
				painter.setPen(PEN_EDGE_HOVER)
				painter.drawArc(self.bbCanvas, int(start_angle_deg * 16), int(self.fov * 16))
			elif self.currentElement & ELEMENT_SIDE_BOTH:
				start_angle_rad = start_angle_deg * math.pi / 180
				end_angle_rad = start_angle_rad + self.fov * math.pi / 180
				path.clear()
				path.moveTo(math.cos(start_angle_rad) * self.canvasRange, -math.sin(start_angle_rad) * self.canvasRange)
				path.lineTo(0, 0)
				path.lineTo(math.cos(end_angle_rad) * self.canvasRange, -math.sin(end_angle_rad) * self.canvasRange)
				painter.setPen(PEN_EDGE_HOVER)
				painter.drawPath(path)

		# Origin
		if self.currentElement != ELEMENT_NONE:
			painter.setBrush(BRUSH_EDGE_HOT if self.currentElement == ELEMENT_ORIGIN else BRUSH_EDGE)
			painter.setPen(Qt.NoPen)
			painter.drawEllipse(ORIGIN_QRECT)
	
	def paint(self, painter, option, widget):
		""" Called by QGIS """
		painter.setRenderHint(QPainter.Antialiasing);
		painter.setRenderHint(QPainter.HighQualityAntialiasing);
		self.paintBackground(painter, option, widget)
		self.paintForeground(painter, option, widget)