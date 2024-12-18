"""
Copyright 2019 Meta Berghauser Pont

This file is part of PST.

PST is free software: you can redistribute it and/or modify
it unrder the terms of the GNU Lesser General Public License as published by
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
		QPolygonF,
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

from ...model import GeometryType
from ...ui.widgets import ProgressDialog
from .isovistmapcanvasitem import IsovistMapCanvasItem
from .isovisttoolwindow import IsovistToolWindow
from .mapcanvasitems import CircleMapCanvasItem, PolygonMapCanvasItem, PathMapCanvasItem

from .common import (
	ISOVIST_PERIMETER_RESOLUTION,
	POINT_FIELDS, 
	POLYGON_FIELDS, 
	FIELD_NAME_X, 
	FIELD_NAME_Y, 
	FIELD_NAME_MAX_DISTANCE,
	FIELD_NAME_FOV, 
	FIELD_NAME_DIRECTION, 
	FIELD_NAME_AREA,
	isPointLayer, 
	isPolygonLayer, 
	IsovistLayer,
	CreateIsovistContext,
)


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

OBSTACLE_EDGE_WIDTH = 1
QCOLOR_OBSTACLE_FILL = QColor("#C04040")
QCOLOR_OBSTACLE_EDGE = QColor("#400000")
QCOLOR_ATTRACTION_FILL = QColor("#40C040")
QCOLOR_ATTRACTION_EDGE = QColor("#000000")

BRUSH_OBSTACLE = QBrush(QCOLOR_OBSTACLE_FILL)
BRUSH_ATTRACTION = QBrush(QCOLOR_ATTRACTION_FILL)
PEN_ATTRACTION = QPen(QCOLOR_ATTRACTION_EDGE, 1)


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
		self._obstacleLayers = []
		self._attractionPointLayers = []
		self._attractionPolygonLayers = []
		self._toolWindow = None
		self._area = 0
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
		#log("activate")

		mapCenter = self.mapCenter()
		self.originX = mapCenter.x()
		self.originY = mapCenter.y()

		if self._toolWindow:
			self._toolWindow.reset()
		else:
			self._toolWindow = self._createToolWindow()

		self._recreateIsovistContext()

		self._toolWindow.show()

		QgsMapTool.activate(self)
		self.setCursor(Qt.ArrowCursor)

	def _updateToolWindow(self, viewCone):
		if self._toolWindow is None:
			return
		self._toolWindow.setPosition(self.originX, self.originY)
		self._toolWindow.setMaxDistance(viewCone.maxViewDistance())
		self._toolWindow.setFov(viewCone.fieldOfView())
		self._toolWindow.setDirection(viewCone.viewDirection())
		self._toolWindow.setArea(self._area)
		# TODO: Set visibility counters
		color = viewCone.color()
		self._toolWindow.setColor(QColor(color.red(), color.green(), color.blue()))
		self._toolWindow.setOpacity(color.alpha())

	def _createIsovistContext(self, obstacleLayers, attractionPointLayers, attractionPolygonLayers, progressContext = None):
		feature_ids_per_layer = {}
		isovistContext = CreateIsovistContext(
			self.model, 
			[isovistLayer.qgisLayer for isovistLayer in obstacleLayers],
			[isovistLayer.qgisLayer for isovistLayer in attractionPointLayers],
			[isovistLayer.qgisLayer for isovistLayer in attractionPolygonLayers],
			outFeatureIdsPerLayer = feature_ids_per_layer,
			progressContext=progressContext)
		for isovistLayer in obstacleLayers + attractionPointLayers + attractionPolygonLayers:
			isovistLayer.featureIds = feature_ids_per_layer[isovistLayer.qgisLayer.id()]
		return isovistContext

	def mapCenter(self):
		canvasCenter = QPoint(int(self.canvas.width() / 2), int(self.canvas.height() / 2))
		return self.toMapCoordinates(canvasCenter)

	def updateIsovist(self, originX, originY):
		self._freeIsovist()
		viewCone = self.currentItem()
		if not viewCone:
			return
		if not self.pstalgo:
			import pstalgo
			self.pstalgo = pstalgo
		(point_count, points, self.isovistHandle, self._area, visibleObstacles, visibleAttractionPoints, visibleAttractionPolygons) = self.pstalgo.CalculateIsovist(
			self.isovistContext, 
			originX, originY, 
			viewCone.maxViewDistance(), 
			viewCone.fieldOfView(), 
			viewCone.viewDirection(), 
			ISOVIST_PERIMETER_RESOLUTION)
		# Update visibility count for each isovist layer
		for visibleObjects, isovistLayers in [(visibleObstacles, self._obstacleLayers), (visibleAttractionPoints, self._attractionPointLayers), (visibleAttractionPolygons, self._attractionPolygonLayers)]:
			assert(visibleObjects.GroupCount == len(isovistLayers))
			for i in range(visibleObjects.GroupCount):
				isovistLayers[i].visibleCount = visibleObjects.CountPerGroup[i]
		# Update tool window
		if self._toolWindow:
			self._toolWindow.setArea(self._area)
			self._toolWindow.updateVisibilityCounters()

		viewCone.setPolygonPoints(points, point_count)

		def UpdateCanvasItems(isovistLayers, visibleObjects, brush, pen):
			newCanvasItemsWereCreated = False
			objectIndex = 0
			for groupIndex, isovistLayer in enumerate(isovistLayers):
				deprecatedFeatureIndices = set(isovistLayer.canvasItemsByIndex)
				
				if visibleObjects and visibleObjects.CountPerGroup:
					for i in range(visibleObjects.CountPerGroup[groupIndex]):
						featureIndex = visibleObjects.Indices[objectIndex]
						if featureIndex in isovistLayer.canvasItemsByIndex:
							deprecatedFeatureIndices.remove(featureIndex)
						else:
							#log(f'Creating new canvas item for layer "{isovistLayer.qgisLayer.name()}" ({groupIndex}:{featureIndex}) objectIndex={objectIndex}')
							feature = isovistLayer.qgisLayer.getFeature(isovistLayer.featureIds[featureIndex])
							canvasItem = self._createCanvasItemFromGeometry(feature.geometry(), brush, pen)
							if canvasItem is not None:
								isovistLayer.canvasItemsByIndex[featureIndex] = canvasItem
								#canvasItem.update()  # Necessary?
								newCanvasItemsWereCreated = True
						objectIndex += 1

				if deprecatedFeatureIndices:
					scene = self.canvas.scene()
					for featureIndex in deprecatedFeatureIndices:
						#log(f'Removing canvas item {groupIndex}:{featureIndex}')
						canvasItem = isovistLayer.canvasItemsByIndex.pop(featureIndex)
						canvasItem.hide()
						scene.removeItem(canvasItem)
						# del canvasItem
			
			if newCanvasItemsWereCreated:
				viewCone = self.currentItem()
				if viewCone:
					# Make sure view cone is drawn on top of all other canvas items by removing it and then adding it last
					scene = self.canvas.scene()
					viewCone.hide()
					scene.removeItem(viewCone)
					scene.addItem(viewCone)
					viewCone.show()

		UpdateCanvasItems(self._obstacleLayers, visibleObstacles, BRUSH_OBSTACLE, QCOLOR_OBSTACLE_EDGE)
		UpdateCanvasItems(self._attractionPointLayers, visibleAttractionPoints, BRUSH_ATTRACTION, PEN_ATTRACTION)
		UpdateCanvasItems(self._attractionPolygonLayers, visibleAttractionPolygons, BRUSH_ATTRACTION, PEN_ATTRACTION)

	def _freeIsovist(self):
		if self.isovistHandle != None:
			self.pstalgo.Free(self.isovistHandle)
			self.isovistHandle = None
		viewCone = self.currentItem()
		if viewCone:
			viewCone.setPolygonPoints(None, 0)

	def deactivate(self):
		""" Called by QGIS """
		#log("deactivate")
		if self._toolWindow is not None:
			self._toolWindow.hide()
		self._removeAllItems()
		self._freeIsovist()
		self._freeIsovistContext()
		self._setLayers([])
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
		toolWindow.layersSelected.connect(self.onLayersSelected)
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

	def _pointFields(self):
		return POINT_FIELDS + [(isovistLayer.qgisLayer.name(), QVariant.Int) for isovistLayer in self._isovistLayers()]

	def _polygonFields(self):
		return POLYGON_FIELDS + [(isovistLayer.qgisLayer.name(), QVariant.Int) for isovistLayer in self._isovistLayers()]

	def addToPointLayer(self, layer):
		if layer is None:
			(layerName, ok) = QInputDialog.getText(self._toolWindow, "New point layer", "Layer name", text = "View points")
			if not ok:
				return
			layer = self._createPointLayer(layerName)
		elif not self._checkMissingAttributes(layer, self._pointFields()):
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
		elif not self._checkMissingAttributes(layer, self._polygonFields()):
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
		for isovistLayer in self._isovistLayers():
			values[isovistLayer.qgisLayer.name().lower()] = isovistLayer.visibleCount
		return values

	def _createPointLayer(self, name):
		layer = QgsVectorLayer("Point", name, "memory")
		layer.startEditing()
		layer.setCrs(QgsProject.instance().crs())
		dataProvider = layer.dataProvider()
		dataProvider.addAttributes([QgsField(name, dataType) for name, dataType in self._pointFields()])
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
		dataProvider.addAttributes([QgsField(name, dataType) for name, dataType in self._polygonFields()])
		layer.updateFields()
		layer.commitChanges()
		QgsProject.instance().addMapLayer(layer)
		return layer

	def onLayersSelected(self, isovistLayers):
		self._setLayers(isovistLayers)
		self._recreateIsovistContext()

	def _setLayers(self, isovistLayers=[]):
		# Remove old canvas items
		scene = self.canvas.scene() if self.canvas else None
		if scene:
			for layerSet in [self._obstacleLayers, self._attractionPointLayers, self._attractionPolygonLayers]:
				if layerSet:
					for isovistLayer in layerSet:
						for canvasItem in isovistLayer.canvasItemsByIndex.values():
							canvasItem.hide()
							scene.removeItem(canvasItem)
		self._obstacleLayers = [isovistLayer for isovistLayer in isovistLayers if isovistLayer.obstacle]
		self._attractionPointLayers = [isovistLayer for isovistLayer in isovistLayers if not isovistLayer.obstacle and isPointLayer(isovistLayer.qgisLayer)]
		self._attractionPolygonLayers = [isovistLayer for isovistLayer in isovistLayers if not isovistLayer.obstacle and isPolygonLayer(isovistLayer.qgisLayer)]

	def _isovistLayers(self):
		return self._obstacleLayers + self._attractionPointLayers + self._attractionPolygonLayers

	def _recreateIsovistContext(self):
		self._freeIsovist()
		self._freeIsovistContext()
		
		progressDialog = None
		try:		
			if self._obstacleLayers or self._attractionPointLayers or self._attractionPolygonLayers:
				progressDialog = ProgressDialog(title="Loading layers", text="Reading tables...", parent=self._toolWindow)
				progressDialog.open()
			self.isovistContext = self._createIsovistContext(self._obstacleLayers, self._attractionPointLayers, self._attractionPolygonLayers, progressDialog)
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

	def _createCanvasItemFromGeometry(self, geometry: QgsGeometry, brush, pen):
		def PolygonFromRing(ring, translateX, translateY):
			polygon = QPolygonF()
			for qgsPoint in ring:
				polygon.append(QPointF(qgsPoint.x() + translateX, qgsPoint.y() + translateY))
			return polygon
		def PathFromPolygonRings(rings, translateX, translateY):
			path = QPainterPath()
			for ring in rings:
				path.addPolygon(PolygonFromRing(ring, translateX, translateY))
			return path
		geo_type = geometry.type()
		if geo_type == QgsWkbTypes.PointGeometry:
			point = geometry.centroid().asPoint()
			return CircleMapCanvasItem(self.canvas, point.x(), point.y(), 5, brush, pen)
		if geo_type == QgsWkbTypes.PolygonGeometry:
			if geometry.isMultipart():  # not QgsWkbTypes.isSingleType(g.wkbType()):
				polygons = geometry.asMultiPolygon()
				# if len(polygons) != 1:
				# 	log("Multipart polygons not supported")					
				rings = polygons[0]
			else:
				rings = geometry.asPolygon()
			bb = geometry.boundingBox()  # QgsRectangle
			width = bb.width()
			height = bb.height()
			originX = bb.xMinimum() + width * 0.5
			originY = bb.yMinimum() + height * 0.5
			bbLocal = QRectF(-width * 0.5, -height * 0.5, width, height)
			if len(rings) == 1:
				polygon = PolygonFromRing(rings[0], -originX, -originY)
				return PolygonMapCanvasItem(self.canvas, originX, originY, bbLocal, polygon, brush, pen)
			path = PathFromPolygonRings(rings, -originX, -originY)
			return PathMapCanvasItem(self.canvas, originX, originY, bbLocal, path, brush, pen)
		return None