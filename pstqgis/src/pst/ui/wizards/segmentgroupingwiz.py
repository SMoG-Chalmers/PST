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

from qgis.PyQt.QtWidgets import QCheckBox, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizProp
from ..pages import FinishPage, NetworkInputPage, ProgressPage, ReadyPage
from ..widgets import PropertySheetWidget, WidgetEnableCheckBox


class SegmentGroupingWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Segment Grouping")
		self._task_factory = task_factory
		self.addPage(NetworkInputPage(point_src_available=False, axial=False))
		self.addPage(OptionsPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class OptionsPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Options")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Grouping")
		prop_sheet.addNumberProp("Angle threshold", 1, 2, "degrees", "angle_threshold")
		prop_sheet.addBoolProp("Split at junctions", False, "split_at_junctions")
		prop_sheet.newSection("Coloring")
		checkbox2 = QCheckBox("Apply generated colors to map")
		checkbox1 = WidgetEnableCheckBox("Generate minimal disjunct colors", [checkbox2])
		prop_sheet.add(checkbox1)
		prop_sheet.add(checkbox2)
		self.regProp("generate_colors", WizProp(checkbox1, False))
		self.regProp("apply_colors", WizProp(checkbox2, False))
		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)