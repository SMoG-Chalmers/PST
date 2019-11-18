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

from qgis.PyQt.QtWidgets import QMessageBox, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import FinishPage, NetworkInputPage, ProgressPage, ReadyPage, RadiusPage
from ..widgets import PropertySheetWidget

class AngularIntegrationWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Angular Integration")
		self._task_factory = task_factory
		self.addPage(NetworkInputPage(point_src_available=False, axial=False))
		self.addPage(CalcOptionsPage())
		self.addPage(RadiusPage())
		self.addPage(OutputPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class CalcOptionsPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Calculation Options")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Weight modes")
		prop_sheet.addBoolProp("No weights",      True, "calc_no_weight")
		prop_sheet.addBoolProp("Weigh by length", True, "calc_length_weight")
		prop_sheet.newSection("Normalization modes")
		prop_sheet.addBoolProp("Normalization (Turner 2007)", True, "norm_normalization")
		prop_sheet.addBoolProp("Syntax normalization (NAIN)", True, "norm_syntax")
		prop_sheet.newSection("Angle options")
		prop_sheet.addNumberProp("Angle precision", 1, 0, "degrees", "angle_precision")
		prop_sheet.addNumberProp("Angle threshold", 0, 2, "degrees", "angle_threshold")
		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)

	def validatePage(self):
		p = self.wizard().prop
		if not p("calc_no_weight") and not p("calc_length_weight"):
			QMessageBox.information(self, "Incomplete input", "Please select at least one wight mode.")
		elif not p("norm_normalization") and not p("norm_syntax"):
			QMessageBox.information(self, "Incomplete input", "Please select at least one normalization mode.")
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