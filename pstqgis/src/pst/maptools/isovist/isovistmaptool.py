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

import math, sip, ctypes

from qgis.PyQt.QtGui import (
		QBrush,
		QColor,
		QPen,
		QPainterPath,
		QCursor,
)

from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import Qt, QVariant, QRectF, QPoint, QPointF

from qgis.PyQt.QtWidgets import QMenu, QMessageBox, QInputDialog

from qgis.core import (
		Qgis,
		QgsFeature,
		QgsField,
		QgsFillSymbol,
		QgsVectorLayer,
		QgsMapLayerType,
		QgsPoint,
		QgsPointXY,
		QgsProject,
		QgsGeometry,
		QgsMapRendererJob,
		QgsWkbTypes,
		QgsMarkerSymbol,
		QgsMessageLog,
		QgsRectangle,
		QgsSettings,
)

from qgis.gui import (
		QgsMapCanvas,
		QgsMapCanvasItem,
		QgsMapTool,
)

from ...analyses.memory import stack_allocator
from ...model import GeometryType
from ...ui.widgets import ProgressDialog
from .isovistmapcanvasitem import IsovistMapCanvasItem
from .isovisttoolwindow import IsovistToolWindow

from .common import (
	POINT_FIELDS, 
	POLYGON_FIELDS, 
	FIELD_NAME_X, 
	FIELD_NAME_Y, 
	FIELD_NAME_MAX_DISTANCE,
	FIELD_NAME_FOV, 
	FIELD_NAME_DIRECTION, 
	FIELD_NAME_AREA,
)


ISOVIST_PERIMETER_RESOLUTION = 64
MAX_CONE_COUNT = 30

ENABLE_LOGGING = True

RANGE_FIELD_NAME     = 'range'
FOV_FIELD_NAME       = 'fov'
DIRECTION_FIELD_NAME = 'dir'

DEFAULT_RANGE        = 100
DEFAULT_FOV          = 360
DEFAULT_DIRECTION    = 0

# Settings
SETTINGS_ROOT       = "pst/isovisttool/"
COLOR_SETTING_KEY   = SETTINGS_ROOT + "color"
OPACITY_SETTING_KEY = SETTINGS_ROOT + "opacity"


def log(msg):
	if ENABLE_LOGGING:
		QgsMessageLog.logMessage("(IsovistMapTool) " + msg, 'PST', level=Qgis.Info)

def QColorToHtml(color):
	if color.alpha() == 255:
		return "#%.2x%.2x%.2x" % (color.red(), color.green(), color.blue())
	return "#%.2x%.2x%.2x%.2x" % (color.alpha(), color.red(), color.green(), color.blue())

class IsovistMapTool(QgsMapTool):
	def __init__(self, iface, canvas, model):
		self.iface = iface
		self.canvas = canvas
		self._items = []
		self._currentItem = None
		self._mousePress = False
		self.originX = 0
		self.originY = 0
		self.pstalgo = None  # Lazy load when it is actually needed
		self.model = model
		self.isovistContext = None
		self.isovistHandle = None
		self._currentObstacleLayers = []
		self._currentAttractionLayers = []
		self._toolWindow = None
		self._area = 0
		self._attractionCount = 0
		QgsMapTool.__init__(self, canvas)

	#def flags(self):
	#	return 0

	def currentItem(self):
		return self._items[0] if self._items else None

	def canActivate(self):
		""" Called by PST """
		return True

	def canEdit(self):
		
		return True

	def setAttribute(self, featureId, fieldName, value, final):
		if self._toolWindow:
			if fieldName == 'dir':
				self._toolWindow.setDirection(value)
			elif fieldName == 'fov':
				self._toolWindow.setFov(value)
			elif fieldName == 'range':
				self._toolWindow.setMaxDistance(value)
		self.updateIsovist(self.originX, self.originY)

	def setPosition(self, featureId, x, y, final):
		self.onPositionChanged(x, y)
		if self._toolWindow:
			self._toolWindow.setPosition(x, y)

	def tryActivate(self):
		""" Called by PST """
		return True

	def activate(self):
		""" Called by QGIS """
		log("activate")

		mapCenter = self.mapCenter()
		self.originX = mapCenter.x()
		self.originY = mapCenter.y()

		if self._toolWindow:
			self._toolWindow.reset()
		else:
			self._toolWindow = self._createToolWindow()

		self._currentObstacleLayers = []
		self._recreateIsovistContext()

		self._toolWindow.show()

		QgsMapTool.activate(self)
		self.setCursor(Qt.ArrowCursor)

	def _tryAutoChooseObstacleLayer(self):
		layers = self._polygonLayers()
		return layers[0] if len(layers) == 1 else None

	def _updateToolWindow(self, viewCone):
		if self._toolWindow is None:
			return
		self._toolWindow.setPosition(self.originX, self.originY)
		self._toolWindow.setMaxDistance(viewCone.maxViewDistance())
		self._toolWindow.setFov(viewCone.fieldOfView())
		self._toolWindow.setDirection(viewCone.viewDirection())
		self._toolWindow.setArea(self._area)
		self._toolWindow.setAttractionCount(self._attractionCount)
		color = viewCone.color()
		self._toolWindow.setColor(QColor(color.red(), color.green(), color.blue()))
		self._toolWindow.setOpacity(color.alpha())
		#self._toolWindow.setObstacleLayers(self._currentObstacleLayers)
		#self._toolWindow.setAttractionLayers(self._currentAttractionLayers)

	def _polygonLayers(self):
		return [layer for layer in self._layers() if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry]

	def _layers(self):
		return QgsProject.instance().mapLayers().values()

	def _createIsovistContext(self, obstacle_tables, attraction_tables, progressContext = None):
		# Load pstalgo here when it is needed instead of on plugin load
		if not self.pstalgo:
			import pstalgo
			self.pstalgo = pstalgo
		initial_alloc_state = stack_allocator.state()
		try:
			# Obstacles
			if obstacle_tables:
				# Read Polygons
				max_polygon_count = 0
				for table in obstacle_tables:
					max_polygon_count += self.model.rowCount(table.name())
				point_count_per_polygon = self.pstalgo.Vector(ctypes.c_uint, max_polygon_count, stack_allocator)
				polygon_points = None
				for table in obstacle_tables:
					polygon_points = self.model.readPolygons(table.name(), point_count_per_polygon, progress=progressContext, out_coords = polygon_points)
			else:
				point_count_per_polygon = self.pstalgo.Vector(ctypes.c_uint, 0, stack_allocator)
				polygon_points = self.pstalgo.Vector(ctypes.c_double, 0, stack_allocator)
			# Attractions
			if attraction_tables:
				# Read Points
				max_count = 0
				for table in attraction_tables:
					max_count += self.model.rowCount(table.name())
				attraction_coords = self.pstalgo.Vector(ctypes.c_double, max_count * 2, stack_allocator)
				for table in attraction_tables:
					self.model.readPoints(table.name(), attraction_coords, out_rowids=None, progress=progressContext)
			else:
				attraction_coords = self.pstalgo.Vector(ctypes.c_double, 0, stack_allocator)
			if progressContext:
				progressContext.setProgress(1)
			# Create context
			isovistContext = self.pstalgo.CreateIsovistContext(point_count_per_polygon, polygon_points, attraction_coords)
			return isovistContext
		finally:
			stack_allocator.restore(initial_alloc_state)

	def mapCenter(self):
		canvasCenter = QPoint(int(self.canvas.width() / 2), int(self.canvas.height() / 2))
		return self.toMapCoordinates(canvasCenter)

	def updateIsovist(self, originX, originY):
		self._freeIsovist()
		viewCone = self.currentItem()
		if not viewCone:
			return
		(point_count, points, self.isovistHandle, self._area, self._attractionCount) = self.pstalgo.CalculateIsovist(
			self.isovistContext, 
			originX, originY, 
			viewCone.maxViewDistance(), 
			viewCone.fieldOfView(), 
			viewCone.viewDirection(), 
			ISOVIST_PERIMETER_RESOLUTION)
		if self._toolWindow:
			self._toolWindow.setArea(self._area)
			self._toolWindow.setAttractionCount(self._attractionCount)
		viewCone.setPolygonPoints(points, point_count)

	def _freeIsovist(self):
		if self.isovistHandle != None:
			self.pstalgo.Free(self.isovistHandle)
			self.isovistHandle = None
		viewCone = self.currentItem()
		if viewCone:
			viewCone.setPolygonPoints(None, 0)

	def deactivate(self):
		""" Called by QGIS """
		log("deactivate")
		if self._toolWindow is not None:
			self._toolWindow.hide()
		self._removeAllItems()
		self._freeIsovist()
		self._freeIsovistContext()
		self._currentObstacleLayers = []
		self._currentAbstractionLayers = []
		super().deactivate()

	def _freeIsovistContext(self):
		if self.isovistContext != None:
			self.pstalgo.Free(self.isovistContext)
			self.isovistContext = None

	def _createToolWindow(self):
		toolWindow = IsovistToolWindow(self.iface.mainWindow())
		toolWindow.close.connect(self.onWndClose)
		toolWindow.maxDistanceChanged.connect(self.onWndMaxDistanceChanged)
		toolWindow.fovChanged.connect(self.onWndFovChanged)
		toolWindow.directionChanged.connect(self.onWndDirectionChanged)
		toolWindow.positionChanged.connect(self.onPositionChanged)
		toolWindow.colorChanged.connect(lambda color: self.onWndColorChanged(color, True))
		toolWindow.colorSelected.connect(lambda color: self.onWndColorChanged(color, False))
		toolWindow.opacityChanged.connect(lambda value: self.onWndOpacityChanged(value, True))
		toolWindow.opacitySelected.connect(lambda value: self.onWndOpacityChanged(value, False))
		toolWindow.addToPointLayer.connect(self.addToPointLayer)
		toolWindow.addToPolygonLayer.connect(self.addToPolygonLayer)
		toolWindow.obstacleLayersSelected.connect(self.setObstacleLayers)
		toolWindow.attractionLayersSelected.connect(self.setAttractionLayers)
		return toolWindow

	def onWndClose(self):
		self.canvas.unsetMapTool(self)
		
	def onWndMaxDistanceChanged(self, value):
		self.currentItem().setMaxViewDistance(value)
		self.updateIsovist(self.originX, self.originY)
		self.currentItem().updatePosition()

	def onWndFovChanged(self, value):
		self.currentItem().setFieldOfView(value)
		self.updateIsovist(self.originX, self.originY)
		self.currentItem().update()
		
	def onWndDirectionChanged(self, value):
		self.currentItem().setViewDirection(value)
		self.updateIsovist(self.originX, self.originY)
		self.currentItem().update()
		
	def onPositionChanged(self, x, y):
		self.originX = x
		self.originY = y
		self.updateIsovist(x, y)
		self.currentItem().setMapPosition(x, y)
		self.currentItem().updatePosition()

	def addToPointLayer(self, layer):
		if layer is None:
			(layerName, ok) = QInputDialog.getText(self._toolWindow, "New point layer", "Layer name", text = "View points")
			if not ok:
				return
			layer = self._createPointLayer(layerName)
		elif not self._checkMissingAttributes(layer, POINT_FIELDS):
			return

		viewCone = self.currentItem()

		feature = QgsFeature()

		# Geometry
		map_point = QgsPointXY(self.originX, self.originY)
		layer_point = self.toLayerCoordinates(layer, map_point)
		feature.setGeometry( QgsGeometry.fromPointXY(layer_point) )

		# Attributes
		values = self.getViewConeAttributes(viewCone)
		fieldNames = [field.name() for field in layer.fields()]
		feature.initAttributes(len(fieldNames))
		for fieldIndex, fieldName in enumerate(fieldNames):
			value = values.get(fieldName.lower())
			if value is not None:
				feature.setAttribute(fieldIndex, value)

		# Make sure layer is in editing mode
		if not layer.isEditable():
			layer.startEditing()

		layer.addFeature(feature)

	def addToPolygonLayer(self, layer):
		if layer is None:
			(layerName, ok) = QInputDialog.getText(self._toolWindow, "New polygon layer", "Layer name", text = "Isovists")
			if not ok:
				return
			layer = self._createPolygonLayer(layerName)
		elif not self._checkMissingAttributes(layer, POLYGON_FIELDS):
			return

		viewCone = self.currentItem()

		feature = QgsFeature()

		# Geometry
		(coordinate_elements, pointCount) = viewCone.polygonPoints()
		map_points = [QgsPointXY(coordinate_elements[i * 2], coordinate_elements[i * 2 + 1]) for i in range(pointCount)]
		layer_points = [self.toLayerCoordinates(layer, point) for point in map_points]
		feature.setGeometry(QgsGeometry.fromPolygonXY([layer_points]))

		# Attributes
		values = self.getViewConeAttributes(viewCone)
		fieldNames = [field.name() for field in layer.fields()]
		feature.initAttributes(len(fieldNames))
		for fieldIndex, fieldName in enumerate(fieldNames):
			value = values.get(fieldName.lower())
			if value is not None:
				feature.setAttribute(fieldIndex, value)

		# Make sure layer is in editing mode
		if not layer.isEditable():
			layer.startEditing()

		layer.addFeature(feature)

	def _checkMissingAttributes(self, layer, fields):
		current_fields = layer.fields()
		missing_fields = [field for field in fields if current_fields.indexFromName(field[0]) < 0]
		if missing_fields:
			# Ask user if missing fields should be added to layer
			plural_suffix = 's' if len(missing_fields) > 1 else ''
			missing_field_names = [field[0] for field in missing_fields]
			msg = "The layer '%s' is missing the following attribute%s: %s\n\nDo you want %s attribute%s to be added?" % (layer.name(), plural_suffix, ', '.join(missing_field_names), 'these' if plural_suffix else 'this', plural_suffix)
			reply = QMessageBox.question(self.iface.mainWindow(), "PST - Missing attributes", msg, QMessageBox.Yes | QMessageBox.No);
			if reply == QMessageBox.Yes:
				# Add missing fields to layer
				if not layer.isEditable():
					layer.startEditing()
				layer.dataProvider()
				fields_to_add = [QgsField(field[0], field[1]) for field in missing_fields]
				if not layer.dataProvider().addAttributes(fields_to_add):
					QMessageBox.critical(self.iface.mainWindow(), "PST - Error", "Couldn't add attributes to layer '%s'." % layer.name(), QMessageBox.Ok)
					return False
				layer.updateFields()	
			elif reply != QMessageBox.No:
				# Assume "Cancel"
				return False
		return True

	def getViewConeAttributes(self, viewCone):
		values = {}
		values[FIELD_NAME_X]            = self.originX
		values[FIELD_NAME_Y]            = self.originY
		values[FIELD_NAME_MAX_DISTANCE] = viewCone.maxViewDistance()
		values[FIELD_NAME_FOV]          = viewCone.fieldOfView()
		values[FIELD_NAME_DIRECTION]    = viewCone.viewDirection()
		values[FIELD_NAME_AREA]         = self._area
		return values

	def _createPointLayer(self, name):
		layer = QgsVectorLayer("Point", name, "memory")
		layer.startEditing()
		layer.setCrs(QgsProject.instance().crs())
		dataProvider = layer.dataProvider()
		dataProvider.addAttributes([QgsField(name, dataType) for name, dataType in POINT_FIELDS])
		QgsProject.instance().addMapLayer(layer)
		layer.updateFields()
		layer.commitChanges()
		return layer

	def _createPolygonLayer(self, name):
		layer = QgsVectorLayer("Polygon", name, "memory")
		layer.startEditing()
		symbol = QgsFillSymbol.createSimple({'color' : QColorToHtml(self.currentItem().color())})
		layer.renderer().setSymbol(symbol)
		layer.setCrs(QgsProject.instance().crs())
		dataProvider = layer.dataProvider()
		dataProvider.addAttributes([QgsField(name, dataType) for name, dataType in POLYGON_FIELDS])
		layer.updateFields()
		layer.commitChanges()
		QgsProject.instance().addMapLayer(layer)
		return layer

	def setObstacleLayers(self, layers):
		self._currentObstacleLayers = list(layers)  # Clone
		self._recreateIsovistContext()

	def setAttractionLayers(self, layers):
		self._currentAttractionLayers = list(layers)  # Clone
		self._recreateIsovistContext()

	def _recreateIsovistContext(self):
		self._freeIsovist()
		self._freeIsovistContext()
		
		progressDialog = None
		try:		
			if self._currentObstacleLayers or self._currentAttractionLayers:
				progressDialog = ProgressDialog(title="Loading obstacle layers", text="Reading tables...", parent=self._toolWindow)
				progressDialog.open()
			self.isovistContext = self._createIsovistContext(self._currentObstacleLayers, self._currentAttractionLayers, progressDialog)
		finally:
			if progressDialog:
				progressDialog.close()

		viewCone = self.currentItem()
		if viewCone is None:
			viewCone = self.createViewCone(123, QgsPointXY(self.originX, self.originY), 100, 360, 0)
			settings = QgsSettings()
			color = QColor(settings.value(COLOR_SETTING_KEY, '#fce94f'))
			opacity = settings.value(OPACITY_SETTING_KEY, 128)
			color.setAlpha(int(opacity))
			viewCone.setColor(color)

		self.updateIsovist(self.originX, self.originY)
		self._updateToolWindow(viewCone)
		viewCone.update()

	def _updateViewConeColor(self):
		color = QColor(self._toolWindow.color())
		color.setAlpha(self._toolWindow.opacity())
		viewCone = self.currentItem()
		viewCone.setColor(color)
		viewCone.update()

	@QtCore.pyqtSlot(QColor)
	def onWndColorChanged(self, color, temporary):
		self._updateViewConeColor()
		if not temporary:
			QgsSettings().setValue(COLOR_SETTING_KEY, "#%.2X%.2x%.2x" % (color.red(), color.green(), color.blue()))
		
	def onWndOpacityChanged(self, value, temporary):
		self._updateViewConeColor()
		if not temporary:
			QgsSettings().setValue(OPACITY_SETTING_KEY, value)
		
	def canvasPressEvent(self, e):
		""" Called by QGIS """
		self._mousePress = True
		if self._currentItem:
			self._currentItem.onMousePress(e)

	def canvasReleaseEvent(self, e):
		""" Called by QGIS """
		self._mousePress = False
		if self._currentItem:
			self._currentItem.onMouseRelease(e)
			self.canvasMoveEvent(e)

	def canvasMoveEvent(self, e):
		canvas_pos = e.pos()  # QPointF
		x = canvas_pos.x()
		y = canvas_pos.y()

		if self._mousePress and self._currentItem:
			self._currentItem.onMouseMove(x, y)
			return
	
		self.updateHover(x, y)

		if self._currentItem:
			self._currentItem.onMouseMove(x, y)

	def createViewCone(self, id, position, range_value, fov_value, direction_value):
		range_value = range_value if range_value != None and range_value >= 0 else DEFAULT_RANGE
		fov_value   = fov_value   if fov_value != None and fov_value >= 0   else DEFAULT_FOV
		direction_value = max(0, min(direction_value, 360)) if direction_value else DEFAULT_DIRECTION
		cone = IsovistMapCanvasItem(self, self.canvas, id, position, range_value, fov_value, direction_value)
		self._items.append(cone)
		return cone

	def setCursor(self, qtCursor):
		if self.canvas:
			self.canvas.setCursor(qtCursor)

	def updateHover(self, x, y):
		if self._currentItem:
			if self._currentItem.testIntersection(x, y):
				return
			self._setCurrentItem(None)
		for item in self._items:
			if item.tryMouseEnter(x, y):
				self._setCurrentItem(item)
				return

	def _removeAllItems(self):
		self._setCurrentItem(None)
		if self.canvas:
			scene = self.canvas.scene()
			if scene:
				for item in self._items:
					scene.removeItem(item)
		self._items.clear()

	def _setCurrentItem(self, item):
		if self._currentItem == item:
			return
		if self._currentItem:
			self._currentItem.onMouseLeave()
		self._currentItem = item
		if item == None:
			self.setCursor(Qt.ArrowCursor)