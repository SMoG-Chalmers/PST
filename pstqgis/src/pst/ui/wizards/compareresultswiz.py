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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIntValidator
from qgis.PyQt.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QCheckBox
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes
from ..wizard import BaseWiz, BasePage, WizProp
from ..pages import ReadyPage, ProgressPage, FinishPage


class CompareResultsWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Compare Results")
		self._task_factory = task_factory
		self.addPage(InputPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class InputPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Compare Results")
		self.setSubTitle(" ")
		self._lineLayers = [layer for layer in QgsProject.instance().mapLayers().values() if type(layer) == QgsVectorLayer and layer.geometryType() == QgsWkbTypes.LineGeometry]
		self._tableCombos = []
		self._columnCombos = []
		self.createWidgets()

	def createWidgets(self):
		SEPARATOR_HEIGHT = 20

		glayout = QGridLayout()

		glayout.setColumnStretch(0, 0)
		glayout.setColumnStretch(1, 3)
		glayout.setColumnStretch(2, 1)
		y = 0

		for i in range(2):
			n = i + 1
			glayout.addWidget(QLabel("Result #%d:" % n), y, 0)

			combo = QComboBox()
			self.regProp("in_table%d" % n, WizProp(combo, ""))
			glayout.addWidget(combo, y, 1)
			self._tableCombos.append(combo)
			combo.currentIndexChanged.connect(lambda index, resultIndex=i: self._onTableSelected(resultIndex, index))

			combo = QComboBox()
			self.regProp("in_column%d" % n, WizProp(combo, ""))
			glayout.addWidget(combo, y, 2)
			self._columnCombos.append(combo)

			y += 1
		
		glayout.setRowMinimumHeight(y, SEPARATOR_HEIGHT)
		y += 1

		glayout.addWidget(QLabel("Radius (std dev):"), y, 0)
		edit = QLineEdit()
		edit.setAlignment(Qt.AlignRight)
		edit.setValidator(QIntValidator(0, 999999, self))
		self.regProp("radius", WizProp(edit, "50"))
		glayout.addWidget(edit, y, 1)
		glayout.addWidget(QLabel("meters"), y, 2)
		y += 1

		glayout.setRowMinimumHeight(y, SEPARATOR_HEIGHT)
		y += 1

		check_boxes = [
			("Create ranges polygon layer",  "ranges_polygons"),
			("Create ranges raster layer",   "ranges_raster"),
			("Create gradient raster layer", "gradient_raster"),
		]
		for title,var_name in check_boxes:
			checkBox = QCheckBox(title)
			self.regProp(var_name, WizProp(checkBox, True))
			glayout.addWidget(checkBox, y, 0, 1, 2)
			y += 1

		glayout.setRowStretch(y, 1)

		self.setLayout(glayout)

	@staticmethod
	def updateColumnCombo(combo, layer):
		combo.clear()
		for field in layer.fields():
			combo.addItem(field.name())

	def initializePage(self):
		for tableCombo in self._tableCombos:
			tableCombo.clear()
			for layer in self._lineLayers:
				tableCombo.addItem(layer.name())

	def _onTableSelected(self, resultIndex, layerIndex):
		InputPage.updateColumnCombo(self._columnCombos[resultIndex], self._lineLayers[layerIndex])