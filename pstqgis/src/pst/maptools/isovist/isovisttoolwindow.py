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

from qgis.PyQt import QtCore

from qgis.PyQt.QtCore import (
	QLocale,
	Qt,
	QPoint,
)

from qgis.PyQt.QtGui import (
	QDoubleValidator,
	QColor,
	QBrush,
	QPen,
	QPainter,
)

from qgis.PyQt.QtWidgets import (
	QWidget,
	QDialog,
	QGridLayout,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QMessageBox,
	QPushButton,
	QVBoxLayout,
	QFrame,
	QSlider,
	QComboBox,
	QToolButton,
	QMenu,
	QAction,
)

from qgis.core import (
	Qgis,
	QgsMessageLog,
	QgsMapLayerType,
	QgsProject,
	QgsWkbTypes,
	QgsVectorLayer,
)

from ...ui.widgets import ColorPicker

DEFAULT_QCOLOR_INSIDE = QColor("#fce94f")
DEFAULT_OPACITY = 128

def clamp(value, minValue, maxValue):
	return max(minValue, min(maxValue, value))

def log(msg):
	QgsMessageLog.logMessage("(IsovistToolWindow) " + msg, 'PST', level=Qgis.Info)

def allPointLayers():
	return [layer for layer in allLayers() if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry]

def allPolygonLayers():
	return [layer for layer in allLayers() if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry]

def allLayers():
	return QgsProject.instance().mapLayers().values()

def layerFromId(id):
	for layer in allLayers():
		if layer.id() == id:
			return layer
	return None


class IsovistToolWindow(QWidget):
	# Signals
	close = QtCore.pyqtSignal()
	maxDistanceChanged = QtCore.pyqtSignal(float)
	fovChanged = QtCore.pyqtSignal(float)
	directionChanged = QtCore.pyqtSignal(float)
	positionChanged = QtCore.pyqtSignal(float, float)
	colorChanged = QtCore.pyqtSignal(QColor)
	colorSelected = QtCore.pyqtSignal(QColor)
	opacityChanged = QtCore.pyqtSignal(int)
	opacitySelected = QtCore.pyqtSignal(int)
	addToPointLayer = QtCore.pyqtSignal(QgsVectorLayer)
	addToPolygonLayer = QtCore.pyqtSignal(QgsVectorLayer)
	obstacleLayerSelected = QtCore.pyqtSignal(QgsVectorLayer)

	def __init__(self, parent):
		QWidget.__init__(self, parent, Qt.Tool)
		self.setWindowTitle("PST - View Cone Tool")
		self.readOnly = False
		self.locale = QLocale()  # Default (system)
		# self.locale = QLocale(QLocale.UnitedStates)

		self.positionX = 0
		self.positionY = 0
		self.fov = 360
		self.maxDistance = 0
		self.direction = 0
		self._color = DEFAULT_QCOLOR_INSIDE
		self._opacity = DEFAULT_OPACITY

		vlayout = QVBoxLayout()

		fieldsLayout = self._createFields()
		vlayout.addLayout(fieldsLayout)

		vlayout.addSpacing(10)

		buttonsLayout = self._createButtons()
		vlayout.addLayout(buttonsLayout)

		self.setLayout(vlayout)

	def reset(self):
		self._updateObstacleCombo()

	def color(self):
		return self._color

	def opacity(self):
		return self._opacity

	def setPosition(self, x, y):
		self.positionX = x
		self.positionY = y
		self._setFloatValue(self.editX, self.positionX)
		self._setFloatValue(self.editY, self.positionY)

	def setFov(self, value):
		self.fov = value
		self._setFloatValue(self.editFov, self.fov)

	def setMaxDistance(self, value):
		self.maxDistance = value
		self._setFloatValue(self.editMaxDistance, self.maxDistance)

	def setDirection(self, value):
		self.direction = value
		self._setFloatValue(self.editDirection, self.direction)

	def setArea(self, value):
		self._setFloatValue(self.editArea, value)

	def setColor(self, color):
		self._color = color
		self._colorPicker.setColor(color)

	def setOpacity(self, value):
		self._opacity = clamp(value, 0, 255)
		self._opacitySlider.setValue(self._opacity)

	def setObstacleLayer(self, layer):
		if layer is not None:
			layerId = layer.id()
			for i in range(self._obstacleCombo.count()-1):
				if self._obstacleCombo.itemData(i+1) == layerId:
					self._obstacleCombo.setCurrentIndex(i+1)
					return
		self._obstacleCombo.setCurrentIndex(0)

	def _createFields(self):
		glayout = QGridLayout()
		glayout.setColumnStretch(0, 0)
		glayout.setColumnStretch(1, 1)
		glayout.setColumnStretch(2, 0)

		self.editMaxDistance = self._createEditField("Max view distance", "m", glayout, changedSlot = self.onMaxDistanceChanged)
		self.editFov = self._createEditField("Field of view", "deg", glayout, changedSlot = self.onFovChanged)
		self.editDirection = self._createEditField("View direction", "deg", glayout, changedSlot = self.onDirectionChanged)
		self.editX = self._createEditField("X", None, glayout, changedSlot = self.onPositionChanged)
		self.editY = self._createEditField("Y", None, glayout, changedSlot = self.onPositionChanged)
		self.editArea = self._createEditField("Area", "m2", glayout, readOnly = True)
		
		self._colorPicker = ColorPicker(self, self._color)
		self._colorPicker.colorChanged.connect(lambda color: self.onColorChanged(color, True))
		self._colorPicker.colorSelected.connect(lambda color: self.onColorChanged(color, False))
		self._addField("Color", self._colorPicker, None, glayout)

		self._opacitySlider = QSlider(Qt.Horizontal, self)
		self._opacitySlider.setMinimum(0)
		self._opacitySlider.setMaximum(255)
		self._opacitySlider.setSliderPosition(self._opacity)
		self._opacitySlider.setTracking(False)  # only send valueChanged-signal when slider is released
		self._opacitySlider.sliderMoved.connect(lambda value: self.onOpacityChanged(value, True))
		self._opacitySlider.valueChanged.connect(lambda value: self.onOpacityChanged(value, False))
		self._addField("Opacity", self._opacitySlider, None, glayout)

		self._obstacleCombo = QComboBox(self)
		self._updateObstacleCombo()
		self._obstacleCombo.currentIndexChanged.connect(self._onObstacleComboIndexChanged)
		self._addField("Obstacles", self._obstacleCombo, None, glayout)
		
		return glayout

	def _updateObstacleCombo(self):
		self._obstacleCombo.clear()
		self._obstacleCombo.addItem("- None -")
		for layer in allPolygonLayers():
			self._obstacleCombo.addItem(layer.name(), layer.id())
		self._obstacleCombo.setCurrentIndex(0)

	def _createEditField(self, name, unit, glayout, changedSlot = None, readOnly = False):
		edit = self._createLineEdit(0, changedSlot = changedSlot, readOnly = readOnly)
		self._addField(name, edit, unit, glayout)
		return edit

	def _addField(self, name, widget, unit, glayout):
		row = glayout.rowCount()
		glayout.addWidget(QLabel(name), row, 0)
		glayout.addWidget(widget, row, 1)
		if unit:
			glayout.addWidget(QLabel(unit), row, 2)

	def _createLineEdit(self, value, minValue = 0, maxValue = 1000000, decimalCount = 2, changedSlot = None, readOnly = False):
		lineEdit = QLineEdit(self.locale.toString(float(value), 'f', 2))
		lineEdit.setAlignment(Qt.AlignRight)
		validator = QDoubleValidator(minValue, maxValue, decimalCount, self)
		validator.setLocale(self.locale)
		lineEdit.setValidator(validator)
		if readOnly:
			lineEdit.setReadOnly(True)
		elif changedSlot is not None:
			lineEdit.textEdited.connect(changedSlot)
		return lineEdit

	def _createButtons(self):
		hlayout = QHBoxLayout()
		
		self.btnAddToPointLayer = self.createDropDownButton("Add to point layer")
		self.btnAddToPointLayer.clicked.connect(self._onAddToPointLayer)
		hlayout.addWidget(self.btnAddToPointLayer)

		self.btnAddToPolygonLayer = self.createDropDownButton("Add to polygon layer")
		self.btnAddToPolygonLayer.clicked.connect(self._onAddToPolygonLayer)
		hlayout.addWidget(self.btnAddToPolygonLayer)

		return hlayout

	def _onObstacleComboIndexChanged(self, index):
		layer = None
		layerId = self._obstacleCombo.currentData()
		if layerId is not None:
			layer = layerFromId(layerId)
			if layer is None:
				raise Exception("Couldn't look up layer from id '%s'" % layerId)
		self.obstacleLayerSelected.emit(layer)

	@QtCore.pyqtSlot()
	def _onAddToPointLayer(self):
		menu = QMenu(self)
		action = QAction("New point layer...", menu)
		action.triggered.connect(lambda: self.addToPointLayer.emit(None))
		menu.addAction(action)
		action = menu.addSeparator()
		action.setParent(menu)
		for layer in allPointLayers():
			action = QAction(layer.name(), menu)
			action.triggered.connect(lambda: self.addToPointLayer.emit(layer))
			menu.addAction(action)
		menu.setAttribute(Qt.WA_DeleteOnClose)
		globalPos = self.btnAddToPointLayer.mapToGlobal(QPoint(0,self.btnAddToPointLayer.height()))
		menu.popup(globalPos)

	@QtCore.pyqtSlot()
	def _onAddToPolygonLayer(self):
		menu = QMenu(self)
		action = QAction("New polygon layer...", menu)
		action.triggered.connect(lambda: self.addToPolygonLayer.emit(None))
		menu.addAction(action)
		action = menu.addSeparator()
		action.setParent(menu)
		for layer in allPolygonLayers():
			action = QAction(layer.name(), menu)
			action.triggered.connect(lambda: self.addToPolygonLayer.emit(layer))
			menu.addAction(action)
		menu.setAttribute(Qt.WA_DeleteOnClose)
		globalPos = self.btnAddToPolygonLayer.mapToGlobal(QPoint(0,self.btnAddToPolygonLayer.height()))
		menu.popup(globalPos)

	def createDropDownButton(self, text):
		toolButton = QToolButton()
		toolButton.setArrowType(Qt.DownArrow)
		#toolButton.setPopupMode(QToolButton.InstantPopup)
		toolButton.setText(text)
		toolButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
		#toolButton.setMenu(self.menu)
		return toolButton

	def onTextEdited(self):
		try:
			self.parseInput(headless = True)
			self.onChanged.emit()
		except Exception as e:
			log(str(e))
			pass

	def _setFloatValue(self, edit, value):
		text = self.locale.toString(float(value), 'f', 2)		
		edit.setText(text)

	def _getFloatValue(self, lineEdit):
		try:
			(value, succeeded) = self.locale.toDouble(lineEdit.text()) 
			return value
		except Exception as e:			
			QMessageBox.information(self, "PST - Invalid input", "Not a valid number.", QMessageBox.Ok)
			lineEdit.selectAll()
			lineEdit.setFocus()
			#raise

	def onMaxDistanceChanged(self):
		self.maxDistance = self._getFloatValue(self.editMaxDistance)
		self.maxDistanceChanged.emit(self.maxDistance)

	def onFovChanged(self):
		self.fov = clamp(self._getFloatValue(self.editFov), 0, 360)
		self.fovChanged.emit(self.fov)

	def onDirectionChanged(self):
		self.direction = clamp(self._getFloatValue(self.editDirection), 0, 360)
		self.directionChanged.emit(self.direction)

	def onPositionChanged(self):
		self.positionX = self._getFloatValue(self.editX)
		self.positionY = self._getFloatValue(self.editY)
		self.positionChanged.emit(self.positionX, self.positionY)

	def closeEvent(self, event):
		event.ignore()
		self.close.emit()

	@QtCore.pyqtSlot(QColor)
	def onColorChanged(self, color, temporary):
		self._color = color
		self.colorChanged.emit(self._color)
		if not temporary:
			self.colorSelected.emit(self._color)

	def onOpacityChanged(self, value, tracking):
		if tracking and value == self._opacity:
			return
		self._opacity = clamp(value, 0, 255)
		self.opacityChanged.emit(self._opacity)
		if not tracking:
			self.opacitySelected.emit(self._opacity)