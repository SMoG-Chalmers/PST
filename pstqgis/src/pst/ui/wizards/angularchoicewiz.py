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

from qgis.PyQt.QtWidgets import QGridLayout, QMessageBox, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import FinishPage, NetworkInputPage, ProgressPage, ReadyPage, RadiusPage
from ..widgets import PropertySheetWidget

class AngularChoiceWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Angular Choice")
		self._task_factory = task_factory
		pages = [
			NetworkInputPage(point_src_available=False, axial=False),
			CalcOptionsPage(),
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
	NORM_MODES = [
		("No Normalization",             True,  "norm_none"),
		("Normalization (Turner 2007)",  False, "norm_normalization"),
		("Standard normalization (0-1)", False, "norm_standard"),
		("Syntax normalization (NACH)",  False, "norm_syntax"),
	]
	WEIGHT_MODES = [
		("No weight",               True,  "weight_none"),
		("Weigh by segment length", False, "weight_length"),
	]

	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Calculation Options")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()

		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Normalization modes")
		for m in self.NORM_MODES:
			prop_sheet.addBoolProp(m[0], m[1], m[2])
		prop_sheet.newSection("Angle options")
		prop_sheet.addNumberProp("Angle precision", 1, 0, "degrees", "angle_precision")
		prop_sheet.addNumberProp("Angle threshold", 0, 2, "degrees", "angle_threshold")
		glayout.addWidget(prop_sheet, 0, 0)

		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Weight modes")
		for m in self.WEIGHT_MODES:
			prop_sheet.addBoolProp(m[0], m[1], m[2])
		prop_sheet.addStretch(1)
		glayout.addWidget(prop_sheet, 0, 1)

		glayout.setRowStretch(1,1)
		self.setLayout(glayout)

	def validatePage(self):
		if not [True for m in self.NORM_MODES if self.wizard().prop(m[2])]:
			QMessageBox.information(self, "Incomplete input", "Please select at least one normalization mode.")
		elif not [True for m in self.WEIGHT_MODES if self.wizard().prop(m[2])]:
			QMessageBox.information(self, "Incomplete input", "Please select at least one wight mode.")
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