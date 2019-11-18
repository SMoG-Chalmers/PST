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

from qgis.PyQt.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat, WizPropCombo
from ..pages import FinishPage, NetworkInputPage, ProgressPage, ReadyPage, RadiusPage
from ..widgets import WidgetEnableCheckBox


class ReachWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Reach")
		self._task_factory = task_factory
		self.addPage(NetworkInputPage(point_src_available=True))
		self.addPage(CalcPage())
		self.addPage(RadiusPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class CalcPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Reach calculation options")
		self.setSubTitle("Please specify calculation options for the analysys")
		self.createWidgets()

	def createWidgets(self):

		vlayout = QVBoxLayout()

		widget = QCheckBox("Calculate number of reached lines")
		vlayout.addWidget(widget)
		self.regProp("calc_count", WizProp(widget, True))

		vlayout.addSpacing(5)

		widget = QCheckBox("Calculate total length of reached lines")
		vlayout.addWidget(widget)
		self.regProp("calc_length", WizProp(widget, True))

		vlayout.addSpacing(5)

		area_unit_combo = QComboBox()
		for item in [('square meter','m2'), ('square kilometer','km2'), ('hectare','ha')]:
			area_unit_combo.addItem(item[0], item[1])
		hlayout = QHBoxLayout()
		hlayout.addSpacing(20)
		unit_label = QLabel("Area unit")
		hlayout.addWidget(unit_label)
		hlayout.addWidget(area_unit_combo)
		hlayout.addStretch(1)
		widget = WidgetEnableCheckBox("Calculate reached area", [unit_label, area_unit_combo])
		vlayout.addWidget(widget)
		vlayout.addLayout(hlayout)
		self.regProp("calc_area", WizProp(widget, True))
		self.regProp("area_unit", WizPropCombo(area_unit_combo, 'm2'))

		vlayout.addStretch(1)

		self.setLayout(vlayout)