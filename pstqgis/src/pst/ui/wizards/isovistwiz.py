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

from qgis.PyQt.QtWidgets import QCheckBox, QGridLayout, QVBoxLayout, QLabel, QComboBox, QLineEdit
from qgis.PyQt.QtCore import Qt
from ...model import GeometryType
from ...maptools.isovist.layerselection import LayerSelectionView, LayerSelectionItem
from ...maptools.isovist.common import allLayers, isPointLayer, isPolygonLayer
from ..wizard import BaseWiz, BasePage, WizPropBase, WizProp, WizPropFloat
from ..pages import FinishPage, NetworkInputPage, ProgressPage, ReadyPage
from ..widgets import PropertySheetWidget


class IsovistWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Calculate Isovists")
		self._task_factory = task_factory
		self.addPage(OriginsPage())
		self.addPage(MetricsPage())
		self.addPage(LayersPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class OriginsPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Input")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()
		glayout.setColumnStretch(3, 1)

		y = 0

		glayout.addWidget(QLabel("Origins (points)"), y, 0)
		self._originsCombo = QComboBox()
		self.regProp("in_origins", WizProp(self._originsCombo, ""))
		glayout.addWidget(self._originsCombo, y, 1)
		y = y + 1

		"""
		glayout.addWidget(QLabel("Obstacles (polygons)"), y, 0)
		self._obstaclesCombo = QComboBox()
		self.regProp("in_obstacles", WizProp(self._obstaclesCombo, ""))
		glayout.addWidget(self._obstaclesCombo, y, 1)
		y = y + 1

		glayout.addWidget(QLabel("Max viewing distance"), y, 0)
		self._maxRadiusEdit = QLineEdit()
		self._maxRadiusEdit.setAlignment(Qt.AlignRight)
		self.regProp("max_viewing_distance", WizPropFloat(self._maxRadiusEdit, 500, 0))
		glayout.addWidget(self._maxRadiusEdit, y, 1)
		glayout.addWidget(QLabel("meters"), y, 2)
		y = y + 1

		glayout.addWidget(QLabel("Perimeter resolution"), y, 0)
		self._perimeterResolutionEdit = QLineEdit()
		self._perimeterResolutionEdit.setAlignment(Qt.AlignRight)
		self.regProp("perimeter_resolution", WizPropFloat(self._perimeterResolutionEdit, 64, 0))
		glayout.addWidget(self._perimeterResolutionEdit, y, 1)
		glayout.addWidget(QLabel("segments"), y, 2)
		y = y + 1
		"""

		glayout.setRowStretch(y, 1)

		self.setLayout(glayout)

	def initializePage(self):
		for table_name in self.model().tableNames():
			geo_type = self.model().geometryType(table_name)
			if geo_type == GeometryType.POINT:
				self._originsCombo.addItem(table_name)
			#elif geo_type == GeometryType.POLYGON:
			#	self._obstaclesCombo.addItem(table_name)


class MetricsPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Metrics")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()
		glayout.setColumnStretch(3, 1)

		y = 0

		glayout.addWidget(QLabel("Max view distance"), y, 0)
		self._maxRadiusEdit = QLineEdit()
		self._maxRadiusEdit.setAlignment(Qt.AlignRight)
		self.regProp("max_view_distance", WizPropFloat(self._maxRadiusEdit, 500, 0))
		glayout.addWidget(self._maxRadiusEdit, y, 1)
		glayout.addWidget(QLabel("meters"), y, 2)
		y = y + 1

		glayout.setRowStretch(y, 1)

		self.setLayout(glayout)


class AttractionsProp(WizPropBase):
	def __init__(self, layerSelectionItemModel):
		self._layerSelectionItemModel = layerSelectionItemModel
	def value(self):
		return [item.qgisLayer.name() for item in self._layerSelectionItemModel.items() if item.selected and not item.obstacle]
	def default(self):
		return []
	def setValue(self, value):
		pass


class ObstaclesProp(WizPropBase):
	def __init__(self, layerSelectionItemModel):
		self._layerSelectionItemModel = layerSelectionItemModel
	def value(self):
		return [item.qgisLayer.name() for item in self._layerSelectionItemModel.items() if item.selected and item.obstacle]
	def default(self):
		return []
	def setValue(self, value):
		pass


class LayersPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self._layerSelectionItems = []
		self.setTitle("Layers")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		vlayout = QVBoxLayout()
		self._layerSelectionView = LayerSelectionView(self, self._layerSelectionItems)
		self.regProp("attractions", AttractionsProp(self._layerSelectionView.model()))
		self.regProp("obstacles", ObstaclesProp(self._layerSelectionView.model()))
		vlayout.addWidget(self._layerSelectionView)
		self.setLayout(vlayout)

	def initializePage(self):
		attractions = self.wizard().prop("attractions")
		obstacles = self.wizard().prop("obstacles")
		layerSelectionItems = []
		for layer in allLayers():
			if isPointLayer(layer) or isPolygonLayer(layer):
				layerName = layer.name()
				is_attraction = attractions and layerName in attractions
				is_obstacle = obstacles and layerName in obstacles
				selected = is_attraction or is_obstacle
				layerSelectionItems.append(LayerSelectionItem(layer, selected = selected, obstacle = is_obstacle))
		self._layerSelectionView.model().setItems(layerSelectionItems)