"""
Copyright 2019 Meta Berghauser Pont

This file is part of PST.

PST is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. The GNU General Public License
is intended to guarantee your freedom to share and change all versions
of a program--to make sure it remains free software for all its users.

PST is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PST. If not, see <http://www.gnu.org/licenses/>.
"""

from qgis.PyQt.QtWidgets import QGridLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import FinishPage, NetworkInputPage, ProgressPage, ReadyPage, RadiusPage
from ..widgets import MultiSelectionListWidget, PropertySheetWidget

class NetworkBetweennessWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Network Betweenness")
		self._task_factory = task_factory
		pages = [
			NetworkInputPage(point_src_available=False),
			CalcOptionsPage(),
			WeightPage(),
			RadiusPage(),
			OutputPage(),
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
		("Walking distance (meters)",   True,  "dist_walking"),
		("Axial/segment lines (steps)", False, "dist_steps"),
		("Axialmeter (steps*meters)",   False, "dist_axmeter"),
	]
	NORM_MODES = [
		("No Normalization",             True,  "norm_none"),
		("Standard normalization (0-1)", False, "norm_standard"),
	]
	WEIGHT_MODES = [
		("No weight",               True,  "weight_none"),
		("Weigh by segment length", False, "weight_length"),
		("Weigh by segment data",   False, "weight_data"),
	]

	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Calculation Options")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()

		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Distance modes")
		for m in self.DIST_MODES:
			prop_sheet.addBoolProp(m[0], m[1], m[2])
		prop_sheet.newSection("Weight modes")
		for m in self.WEIGHT_MODES:
			prop_sheet.addBoolProp(m[0], m[1], m[2])
		glayout.addWidget(prop_sheet, 0, 0)

		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Normalization modes")
		for m in self.NORM_MODES:
			prop_sheet.addBoolProp(m[0], m[1], m[2])
		prop_sheet.addStretch(1)
		glayout.addWidget(prop_sheet, 0, 1)

		glayout.setRowStretch(1,1)
		self.setLayout(glayout)

	def nextId(self):
		if not self.wizard().properties().get("weight_data"):
			return self.wizard().currentId() + 2  # Skip next page
		return BasePage.nextId(self)

	def validatePage(self):
		if not [True for m in self.DIST_MODES if self.wizard().prop(m[2])]:
			QMessageBox.information(self, "Incomplete input", "Please select at least one distance mode.")
		elif not [True for m in self.NORM_MODES if self.wizard().prop(m[2])]:
			QMessageBox.information(self, "Incomplete input", "Please select at least one normalization mode.")
		elif not [True for m in self.WEIGHT_MODES if self.wizard().prop(m[2])]:
			QMessageBox.information(self, "Incomplete input", "Please select at least one wight mode.")
		else:
			return True
		return False


class TableColumnListWidget(MultiSelectionListWidget):
	def __init__(self):
		MultiSelectionListWidget.__init__(self)

	def updateContents(self, model, table_name):
		self.setItems(model.columnNames(table_name))


class WeightPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Segment Weight Data")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()

		glayout.addWidget(QLabel("Available data"), 0, 0)
		self._list = TableColumnListWidget()
		self.regProp("weight_data_cols", WizProp(self._list, []))
		glayout.addWidget(self._list, 1, 0, 2, 1)

		glayout.addWidget(QLabel("Data name (to be used in output column)"), 0, 1)
		edit = QLineEdit()
		self.regProp("weight_data_name", WizProp(edit, ""))
		glayout.addWidget(edit, 1, 1)
		glayout.setRowStretch(2, 1)

		self.setLayout(glayout)

	def initializePage(self):
		self._list.updateContents(self.model(), self.wizard().prop("in_network"))

	def validatePage(self):
		if not self.wizard().prop("weight_data_cols"):
			QMessageBox.information(self, "Incomplete input", "Please select at least one data colum.")
		elif not self.wizard().prop("weight_data_name"):
			QMessageBox.information(self, "Incomplete input", "Please enter a valid data name.")
		else:
			return True
		return False


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