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
	QLayout,
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
	QListWidget,
	QListWidgetItem,
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


class MultiSelListDialog(QDialog):
	def __init__(self, parent, title, items):  # items = [(text, checked)..]
		QWidget.__init__(self, parent, Qt.Tool)
		self.setWindowTitle(title)
		vlayout = QVBoxLayout()
		self._list = QListWidget(self)
		for text, checked in items:
			item = QListWidgetItem(text, self._list)
			item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
			item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
			self._list.addItem(item)
		vlayout.addWidget(self._list)
		vlayout.addSpacing(10)
		hlayout = QHBoxLayout()
		self._okButton = QPushButton("OK")
		self._okButton.clicked.connect(self.accept)
		hlayout.addWidget(self._okButton)
		self._cancelButton = QPushButton("Cancel")
		self._cancelButton.clicked.connect(self.reject)
		hlayout.addWidget(self._cancelButton)
		vlayout.addLayout(hlayout)
		self.setLayout(vlayout)

	def selectedIndices(self):
		return [index for index in range(self._list.count()) if self._list.item(index).checkState() == Qt.Checked]

	def _onOk(self):
		pass

	def _onCancel(self):
		pass



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
	obstacleLayersSelected = QtCore.pyqtSignal(list)
	attractionLayersSelected = QtCore.pyqtSignal(list)

	def __init__(self, parent):
		QWidget.__init__(self, parent, Qt.Tool)
		self.setWindowTitle("PST - Isovist Tool")
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
		self._obstacleLayers = []
		self._attractionLayers = []

		vlayout = QVBoxLayout()

		fieldsLayout = self._createFields()
		vlayout.addLayout(fieldsLayout)

		vlayout.addSpacing(10)

		buttonsLayout = self._createButtons()
		vlayout.addLayout(buttonsLayout)

		self.setLayout(vlayout)

	def reset(self):
		pass

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

	def setAttractionCount(self, value):
		self.editAttractionCount.setText(str(value))

	def setObstacleCount(self, value):
		self.editObstacleCount.setText(str(value))

	def setColor(self, color):
		self._color = color
		self._colorPicker.setColor(color)

	def setOpacity(self, value):
		self._opacity = clamp(value, 0, 255)
		self._opacitySlider.setValue(self._opacity)

	def setObstacleLayers(self, layers):
		self._obstacleLayers = list(layers)  # Clone
		log("setObstacleLayers [%s]" % ', '.join([layer.name() for layer in self._obstacleLayers]))
		self._updateObstacleLayersText()

	def setAttractionLayers(self, layers):
		self._attractionLayers = list(layers)  # Clone
		log("setAttractionLayers [%s]" % ', '.join([layer.name() for layer in self._attractionLayers]))
		self._updateAttractionLayersText()

	def _updateObstacleLayersText(self):
		self._updateLayerSelectionLabel(self._obstaclesLabel, self._obstacleLayers)

	def _updateAttractionLayersText(self):
		self._updateLayerSelectionLabel(self._attractionLabel, self._attractionLayers)

	def _updateLayerSelectionLabel(self, label, layers):
		layer_count = len(layers)
		if 0 == layer_count:
			text = 'None'
		elif 1 == layer_count:
			text = layers[0].name()
		else:
			text = '%d layers' % layer_count
		label.setText(text)

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
		self.editAttractionCount = self._createEditField("Attractions", None, glayout, readOnly = True)
		self.editObstacleCount = self._createEditField("Obstacles", None, glayout, readOnly = True)

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

		self._obstaclesLabel = QLabel()
		self._obstaclesButton = QToolButton()
		self._obstaclesButton.setText("...")
		self._obstaclesButton.clicked.connect(self._onObstaclesClick)		
		obstacleFieldLayout = QHBoxLayout()
		obstacleFieldLayout.addWidget(self._obstaclesLabel)
		obstacleFieldLayout.addStretch()
		obstacleFieldLayout.addWidget(self._obstaclesButton)
		self._addField("Obstacles", obstacleFieldLayout, None, glayout)
		self._updateObstacleLayersText()

		self._attractionLabel = QLabel()
		self._attractionButton = QToolButton()
		self._attractionButton.setText("...")
		self._attractionButton.clicked.connect(self._onAttractionsClick)		
		attractionFieldLayout = QHBoxLayout()
		attractionFieldLayout.addWidget(self._attractionLabel)
		attractionFieldLayout.addStretch()
		attractionFieldLayout.addWidget(self._attractionButton)
		self._addField("Attractions", attractionFieldLayout, None, glayout)
		self._updateAttractionLayersText()

		return glayout

	def _createEditField(self, name, unit, glayout, changedSlot = None, readOnly = False):
		edit = self._createLineEdit(0, changedSlot = changedSlot, readOnly = readOnly)
		self._addField(name, edit, unit, glayout)
		return edit

	def _addField(self, name, widgetOrLayout, unit, glayout):
		row = glayout.rowCount()
		glayout.addWidget(QLabel(name), row, 0)
		if isinstance(widgetOrLayout, QLayout):
			glayout.addLayout(widgetOrLayout, row, 1)
		else:
			glayout.addWidget(widgetOrLayout, row, 1)
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

	def _onObstaclesClick(self):
		selectedLayers = self._selectLayers("Please select obstacles", allPolygonLayers(), self._obstacleLayers)
		if selectedLayers is None:
			return
		self.setObstacleLayers(selectedLayers)
		self.obstacleLayersSelected.emit(selectedLayers)

	def _onAttractionsClick(self):
		selectedLayers = self._selectLayers("Please select attractions", allPointLayers(), self._attractionLayers)
		if selectedLayers is None:
			return
		self.setAttractionLayers(selectedLayers)
		self.attractionLayersSelected.emit(selectedLayers)

	def _selectLayers(self, text, availableLayers, selectedLayers):
		items = ([(layer.name(), layer in selectedLayers) for layer in availableLayers])
		dlg = MultiSelListDialog(self, text, items)
		if QDialog.Accepted != dlg.exec():
			return None
		selectedIndices = dlg.selectedIndices()
		selectedLayers = [availableLayers[index] for index in selectedIndices]
		return selectedLayers

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
			action.triggered.connect(lambda checked, layer=layer: self.addToPointLayer.emit(layer))
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
			action.triggered.connect(lambda checked, layer=layer: self.addToPolygonLayer.emit(layer))
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