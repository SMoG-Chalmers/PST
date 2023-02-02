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
NOTE: This file is deprecated and will likely be removed soon.
"""

import math
import sip

from qgis.PyQt.QtGui import (
		QBrush,
		QColor,
		QPen,
		QPainterPath,
		QCursor,
)

from qgis.PyQt.QtCore import Qt, QVariant, QRectF, QPointF

from qgis.PyQt.QtWidgets import QMenu, QMessageBox, QToolTip, QWidget

from qgis.core import (
		Qgis,
		QgsFeatureRequest,
		QgsField,
		QgsVectorLayer,
		QgsMapLayerType,
		QgsPoint,
		QgsPointXY,
		QgsProject,
		QgsGeometry,
		QgsMapRendererJob,
		QgsWkbTypes,
		QgsMessageLog,
		QgsRectangle,
)

from qgis.gui import (
		QgsMapCanvas,
		QgsVertexMarker,
		QgsMapCanvasItem,
		QgsMapMouseEvent,
		QgsMapTool,
)

from .viewconemapcanvasitem import ViewConeMapCanvasItem

MAX_CONE_COUNT = 30

RANGE_FIELD_NAME     = 'range'
FOV_FIELD_NAME       = 'fov'
DIRECTION_FIELD_NAME = 'dir'

DEFAULT_RANGE        = 100
DEFAULT_FOV          = 360
DEFAULT_DIRECTION    = 0


def log(msg):
	QgsMessageLog.logMessage("(ViewconeMapTool) " + msg, 'PST', level=Qgis.Info)


class ViewconeMapTool(QgsMapTool):
	def __init__(self, iface, canvas):
		self.iface = iface
		self.canvas = canvas
		self._items = []
		self._currentLayer = None
		self._currentItem = None
		self._mousePress = False
		self._needsToolTipRefresh = False
		self._toolTipIsOdd = False
		QgsMapTool.__init__(self, canvas)

	def flags(self):
		return QgsMapTool.EditTool  # + QgsMapTool.ShowContextMenu

	def canEdit(self):
		return self._currentLayer and self._currentLayer.isEditable()

	def setAttribute(self, featureId, fieldName, value, final):
		if not self._currentLayer or not final:
			return False
		fieldIndex = self._currentLayer.fields().indexFromName(fieldName)
		if fieldIndex < 0:
			return False
		if not self._currentLayer.isEditable():
			return False
		return self._currentLayer.changeAttributeValue(featureId, fieldIndex, value)

	def setPosition(self, featureId, x, y, final):
		if not self._currentLayer or not final:
			return False
		feature = self._currentLayer.getFeature(featureId)
		if not feature:
			return False
		geometry = feature.geometry()
		if not geometry:
			return False
		point = geometry.asPoint()
		if not point:
			return False
		if not self._currentLayer.isEditable():
			return False
		layerCoords = self.toLayerCoordinates(self._currentLayer, QgsPointXY(x, y))
		self._currentLayer.translateFeature(featureId, layerCoords.x() - point.x(), layerCoords.y() - point.y())

	def checkAttributes(self, layer):
		# Get list of missing attributes (if any)
		fields = layer.fields()
		field_names = [RANGE_FIELD_NAME, FOV_FIELD_NAME, DIRECTION_FIELD_NAME]
		missing_fields = [field_name for field_name in field_names if fields.indexFromName(field_name) < 0]
		if not missing_fields:
			return True
		# Ask user if missing fields should be added to layer
		plural_suffix = 's' if len(missing_fields) > 1 else ''
		msg = "The layer '%s' is missing the following view cone attribute%s: %s\n\nDo you want %s attribute%s to be added?" % (layer.name(), plural_suffix, ', '.join(missing_fields), 'these' if plural_suffix else 'this', plural_suffix)
		reply = QMessageBox.question(self.iface.mainWindow(), "PST - Missing attributes", msg, QMessageBox.Yes | QMessageBox.No);
		if reply != QMessageBox.Yes:
			return False
		# Add missing fields to layer
		fields_to_add = [QgsField(field_name, QVariant.Double) for field_name in missing_fields]
		"""
		if not layer.dataProvider().addAttributes(fields_to_add):
			QMessageBox.critical(self.iface.mainWindow(), "PST - Error", "Couldn't add attributes to layer '%s'." % layer.name(), QMessageBox.Ok)
			return False
		layer.updateFields()	
		layer.commitChanges()
		"""
		for field in fields_to_add:
			if not layer.addAttribute(field):
				QMessageBox.critical(self.iface.mainWindow(), "PST - Error", "Couldn't add attribute '%s' to layer '%s'." % (field.name(), layer.name()), QMessageBox.Ok)
				return False
		layer.updateFields()	
		msg = "The missing attribute%s %s successfully added to table '%s'." % (plural_suffix, 'were' if plural_suffix else 'was', layer.name())
		QMessageBox.information(self.iface.mainWindow(), "PST - New attributes added", msg, QMessageBox.Ok)
		return True

	def activate(self):
		""" Called by QGIS """
		log("activating...")
		QgsMapTool.activate(self)
		self.iface.layerTreeView().currentLayerChanged.connect(self.onActiveLayerChanged)
		self.setCurrentLayer(self.iface.layerTreeView().currentLayer())
		self.setCursor(Qt.ArrowCursor)
		log("activated")

	def deactivate(self):
		""" Called by QGIS """
		log("deactivating...")
		self._removeAllItems()
		self.iface.layerTreeView().currentLayerChanged.disconnect(self.onActiveLayerChanged)
		self.setCurrentLayer(None)
		QgsMapTool.deactivate(self)
		log("deactivated")

	def canvasToolTipEvent(self, e):
		""" Called by QGIS """
		if self._currentItem:
			QToolTip.showText(e.globalPos(), self.toolTipText())
		else:
			QToolTip.hideText()
			e.ignore()
		return True

	def toolTipText(self):
		if self._currentItem == None:
			return ""
		text = "<html><table><tr><td>View Range:<br/>Field of View:</td><td>%d m<br/>%d deg</td></tr></table></html>" % (self._currentItem.range, self._currentItem.fov)

		# Make sure we get an update if needed, by making sure text is different by appending or not appending a space
		if self._needsToolTipRefresh:
			self._toolTipIsOdd = not self._toolTipIsOdd
			self._needsToolTipRefresh = False
		if self._toolTipIsOdd:
			text += " "

		return text

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

	def onActiveLayerChanged(self, layer):
		log("onActiveLayerChanged: " + ("None" if layer is None else str(layer.name())))
		if not self.isActive():
			log("Got activeLayerChanged signal when not active")
			return
		self.setCurrentLayer(layer)

	def setCurrentLayer(self, layer):
		self._removeAllItems()
		self._currentLayer = None
		if layer is None:
			log("No layer")
			return
		if layer.type() != QgsMapLayerType.VectorLayer:
			log("Non-vector layer selected")
			return
		if layer.geometryType() != QgsWkbTypes.PointGeometry:
			log("Non-point layer selected")
			return
		self.checkAttributes(layer)
		if not self.isActive():  # We can get deactivated during call to checkAttributes, so we need to make sure we're active before continuing here.
			log("Deactivated during call to checkAttributes")
			return
		self._currentLayer = layer
		if layer.featureCount() > MAX_CONE_COUNT:
			log("Too many point features in selected layer!")
			return
		log("New layer selected : " + layer.name())
		self.createViewConesForLayer(layer)

	def createViewConesForLayer(self, layer):
		fields = layer.fields()
		range_field = fields.indexFromName(RANGE_FIELD_NAME)
		fov_field = fields.indexFromName(FOV_FIELD_NAME)
		direction_field = fields.indexFromName(DIRECTION_FIELD_NAME)
		field_indices = [field_index for field_index in [range_field, fov_field, direction_field] if field_index >= 0]
		request = QgsFeatureRequest()
		request.setSubsetOfAttributes(field_indices)
		for feature in layer.getFeatures(request):
			g = feature.geometry()
			if g is None:
				continue
			position = self.toMapCoordinates(layer, g.centroid().asPoint())
			range_value     = feature[range_field]     if range_field >= 0     else DEFAULT_RANGE
			fov_value       = feature[fov_field]       if fov_field >= 0       else DEFAULT_FOV
			direction_value = feature[direction_field] if direction_field >= 0 else DEFAULT_DIRECTION
			self.createViewCone(feature.id(), position, range_value, fov_value, direction_value)

	def createViewCone(self, id, position, range_value, fov_value, direction_value):
		log("Creating view cone at (%d, %d)" % (position.x(), position.y()))
		range_value = range_value if range_value != None and range_value >= 0 else DEFAULT_RANGE
		fov_value   = fov_value   if fov_value != None and fov_value >= 0   else DEFAULT_FOV
		direction_value = max(0, min(direction_value, 360)) if direction_value else DEFAULT_DIRECTION
		cone = ViewConeMapCanvasItem(self, self.canvas, id, position, range_value, fov_value, direction_value)
		self._items.append(cone)

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
		self._needsToolTipRefresh = True
		if self._currentItem:
			self._currentItem.onMouseLeave()
		self._currentItem = item
		if item == None:
			self.setCursor(Qt.ArrowCursor)