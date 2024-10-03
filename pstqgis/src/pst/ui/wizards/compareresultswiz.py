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
from qgis.PyQt.QtWidgets import QComboBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QCheckBox, QRadioButton, QButtonGroup
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import ReadyPage, ProgressPage, FinishPage


class CompareResultsWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Compare Results")
		self._task_factory = task_factory
		self.addPage(InputPage())
		self.addPage(OutputPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class InputPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Calculation Settings")
		self.setSubTitle(" ")
		self._lineLayers = [layer for layer in QgsProject.instance().mapLayers().values() if type(layer) == QgsVectorLayer and layer.geometryType() == QgsWkbTypes.LineGeometry]
		self._tableCombos = []
		self._columnCombos = []
		self.createWidgets()

	def createWidgets(self):
		SEPARATOR_HEIGHT = 20

		vlayout = QVBoxLayout()
	
		glayout = QGridLayout()
		glayout.setColumnStretch(0, 0)
		glayout.setColumnStretch(1, 3)
		glayout.setColumnStretch(2, 1)
		y = 0
	
		glayout.addWidget(QLabel("Table"), y, 1)
		glayout.addWidget(QLabel("Field"), y, 2)
		y += 1

		for i in range(2):
			n = i + 1
			glayout.addWidget(QLabel(f"Value {'A' if i == 0 else 'B'}:") , y, 0)

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
		
		vlayout.addLayout(glayout)

		vlayout.addSpacing(SEPARATOR_HEIGHT)

		# vlayout.addWidget(QLabel("Calculate difference as:"))
		# button_group = QButtonGroup(self)
		
		# self._absoluteDifferenceRadio = QRadioButton("Absolute difference: B - A")
		# button_group.addButton(self._absoluteDifferenceRadio)
		# vlayout.addWidget(self._absoluteDifferenceRadio)
		
		# self._normalizedDifferenceRadio = QRadioButton("Normalized difference: (B - A) / MaxAbsDiff")
		# self.regProp("calc_normalized", WizProp(self._normalizedDifferenceRadio, True))
		# button_group.addButton(self._normalizedDifferenceRadio)
		# vlayout.addWidget(self._normalizedDifferenceRadio)

		# hlayout = QHBoxLayout()
		# hlayout.setSpacing(0)
		# self._relativeDifferenceRadio = QRadioButton("Relative difference percent: 100 * (max(B,M) / max(A,M) - 1), where M = ")
		# self.regProp("calc_relative_percent", WizProp(self._relativeDifferenceRadio, False))
		# button_group.addButton(self._relativeDifferenceRadio)
		# hlayout.addWidget(self._relativeDifferenceRadio)
		# edit = QLineEdit()
		# edit.setAlignment(Qt.AlignRight)
		# self.regProp("M", WizPropFloat(edit, 1, 2))
		# hlayout.addWidget(edit)
		# hlayout.addStretch()
		# vlayout.addLayout(hlayout)

		vlayout.addSpacing(SEPARATOR_HEIGHT)

		hlayout = QHBoxLayout()
		hlayout.addWidget(QLabel("Blur radius (std dev):"))
		edit = QLineEdit()
		edit.setAlignment(Qt.AlignRight)
		edit.setValidator(QIntValidator(0, 999999, self))
		self.regProp("radius", WizProp(edit, "50"))
		hlayout.addWidget(edit)
		hlayout.setStretch(1, 0)
		hlayout.addWidget(QLabel("meters"))
		hlayout.addStretch()
		hlayout.setStretch(3, 10)
		vlayout.addLayout(hlayout)

		vlayout.addSpacing(SEPARATOR_HEIGHT)

		vlayout.addStretch()

		self.setLayout(vlayout)

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


class OutputPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Output Settings")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		SEPARATOR_HEIGHT = 20

		vlayout = QVBoxLayout()
	
		vlayout.addWidget(QLabel("Output type:"))
		check_boxes = [
			("Ranges polygon layer",  "ranges_polygons"),
			#("Ranges raster layer",   "ranges_raster"),
			("Gradient raster layer", "gradient_raster"),
		]
		for title,var_name in check_boxes:
			checkBox = QRadioButton(title)
			self.regProp(var_name, WizProp(checkBox, True))
			vlayout.addWidget(checkBox)

		vlayout.addStretch()

		self.setLayout(vlayout)

	def initializePage(self):
		pass