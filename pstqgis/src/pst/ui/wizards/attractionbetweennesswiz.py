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

from qgis.PyQt.QtWidgets import QGridLayout, QLabel, QLineEdit, QMessageBox, QRadioButton, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import FinishPage, GraphInputPage, ProgressPage, RadiusPage, ReadyPage
from ..widgets import PropertySheetWidget, TableDataSelectionWidget, WidgetEnableRadioButton
from .attractiondistancewiz import ValidateNonCollidingAttractionDataOutputColumns, CUSTOM_COLUMN_NAME_CHAR_LIMIT

class AttractionBetweennessWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Attraction Betweenness")
		self._task_factory = task_factory
		pages = [
			GraphInputPage(origins_available=False),
			CalcOptionsPage(),
			RadiusPage(),
			WeightPage(),
			ReadyPage(),
			ProgressPage(),
			FinishPage(),
		]
		for index, page in enumerate(pages):
			self.setPage(index, page)

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class CalcOptionsPage(BasePage):
	DIST_MODES = [
		("Walking distance (meters)",       True,  "dist_walking"),
		("Axial/segment lines (steps)",     False, "dist_steps"),
		("Angle (degrees)",                 False, "dist_angular"),
		("Axialmeter (steps*meters)",       False, "dist_axmeter"),
	]
	NORM_MODES = [
		("No Normalization",             True,  "norm_none"),
		("Standard normalization (0-1)", False, "norm_standard"),
	]
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Calculation Options")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Distance modes")
		for m in self.DIST_MODES:
			prop_sheet.addBoolProp(m[0], m[1], m[2])
		prop_sheet.newSection("Normalization modes")
		for m in self.NORM_MODES:
			prop_sheet.addBoolProp(m[0], m[1], m[2])
		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)

	def validatePage(self):
		if not [True for m in self.DIST_MODES if self.wizard().prop(m[2])]:
			QMessageBox.information(self, "Incomplete input", "Please select at least one distance mode.")
		elif not [True for m in self.NORM_MODES if self.wizard().prop(m[2])]:
			QMessageBox.information(self, "Incomplete input", "Please select at least one normalization mode.")
		else:
			return True
		return False


class WeightPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Weights")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()

		vlayout = QVBoxLayout()
		self._list = TableDataSelectionWidget()
		self.regProp("dest_data", WizProp(self._list, []))
		radio = QRadioButton("Points are weighed equally")
		radio.setChecked(True)
		vlayout.addWidget(radio)
		radio = WidgetEnableRadioButton("Points are weighed by data", [self._list])
		self.regProp("dest_data_enabled", WizProp(radio, False))
		vlayout.addWidget(radio)
		vlayout.addWidget(self._list)
		glayout.addLayout(vlayout, 0, 0)

		vlayout = QVBoxLayout()
		vlayout.addWidget(QLabel("Attraction name (for output column)"))
		edit = QLineEdit()
		edit.setMaxLength(CUSTOM_COLUMN_NAME_CHAR_LIMIT)  # Charcter count limit, to avoid column names being too long (limitation in table file format)
		self.regProp("dest_name", WizProp(edit, ""))
		vlayout.addWidget(edit)
		vlayout.addStretch()
		glayout.addLayout(vlayout, 0, 1)

		self.setLayout(glayout)

	def initializePage(self):
		self._list.updateContents(self.model(), self.wizard().prop("in_destinations"))

	def validatePage(self):
		if self.wizard().prop("dest_data_enabled") and not self.wizard().prop("dest_data"):
			QMessageBox.information(self, "Incomplete input", "Please select at least one data colum.")
			return False
		if not ValidateNonCollidingAttractionDataOutputColumns(self, self.wizard().prop("dest_data_enabled"), self.wizard().prop("dest_data"), self.wizard().prop("dest_name")):
			return False
		return True

