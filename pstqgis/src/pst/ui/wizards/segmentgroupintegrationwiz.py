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

from qgis.PyQt.QtWidgets import QComboBox, QLabel, QMessageBox, QVBoxLayout
from ..widgets import PropertySheetWidget, WidgetEnableCheckBox
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import FinishPage, NetworkInputPage, ProgressPage, ReadyPage, RadiusPage, RadiusType, RadiusTypePropName


class SegmentGroupIntegrationWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Segment Group Integration")
		self._task_factory = task_factory
		self.addPage(InputPage())
		self.addPage(MyRadiusPage())
		self.addPage(OutputPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class OutputPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Output Settings")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		prop_sheet = PropertySheetWidget(self)
		prop_sheet.setIndent(0)
		prop_sheet.addBoolProp("Output node count (N)",   True, "output_N")
		prop_sheet.addBoolProp("Output total depth (TD)", True, "output_TD")
		prop_sheet.addBoolProp("Output mean depth (MD)",  True, "output_MD")
		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)


class InputPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Graph")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		prop_sheet = PropertySheetWidget(self)

		prop_sheet.newSection("Map")
		self._linesCombo = QComboBox()
		prop_sheet.add(QLabel("Segment lines"), self._linesCombo)
		self.regProp("in_network", WizProp(self._linesCombo, ""))

		prop_sheet.newSection("Grouping")
		prop_sheet.addNumberProp("Angle threshold", 1, 2, "degrees", "angle_threshold")
		prop_sheet.addBoolProp("Split at junctions", False, "split_at_junctions")

		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)

	def initializePage(self):
		combos = [self._linesCombo]
		for combo in combos:
			combo.clear()
		for name in self.model().tableNames():
			for combo in combos:
				combo.addItem(name)


class MyRadiusPage(RadiusPage):
	RADIUS_TYPES = [RadiusType.WALKING, RadiusType.STEPS]
	
	def __init__(self):
		RadiusPage.__init__(self, radius_types=self.RADIUS_TYPES)
		self.setTitle("Distance type")
		self.setSubTitle("Please select distance type and radius")

	def validatePage(self):
		selected_radius_types = [radius_type for radius_type in self.RADIUS_TYPES if self.wizard().prop(RadiusTypePropName(radius_type) + "_enabled")]
		if not selected_radius_types:
			QMessageBox.information(self, "Incomplete input", "Please select at least one distance type.")
			return False
		return RadiusPage.validatePage(self)