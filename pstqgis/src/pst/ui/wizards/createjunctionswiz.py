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

from qgis.PyQt.QtWidgets import QComboBox, QGridLayout, QLabel, QRadioButton
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import ReadyPage, ProgressPage, FinishPage
from ..widgets import WidgetEnableCheckBox, WidgetEnableRadioButton


class CreateJunctionsWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Create Junctions")
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
		self.setTitle("Input Tables")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()

		glayout.setColumnStretch(0, 0)
		glayout.setColumnStretch(1, 1)
		y = 0;

		glayout.addWidget(QLabel("Find crossings between lines from:"), y, 0, 1, 2)
		y = y + 1

		self._lines1Combo = QComboBox()
		self.regProp("in_lines1", WizProp(self._lines1Combo, ""))
		self._lines1Check = QRadioButton("One table")
		self._lines1Check.setChecked(True)
		glayout.addWidget(self._lines1Check, y, 0)
		glayout.addWidget(self._lines1Combo, y, 1)
		y = y + 1

		self._lines2Combo = QComboBox()
		self.regProp("in_lines2", WizProp(self._lines2Combo, ""))
		self._lines2Check = WidgetEnableRadioButton("Two tables", [self._lines2Combo])
		self.regProp("in_lines2_enabled", WizProp(self._lines2Check, False))
		glayout.addWidget(self._lines2Check, y, 0)
		glayout.addWidget(self._lines2Combo, y, 1)
		y = y + 1

		glayout.setRowMinimumHeight(y, 20)
		y = y + 1

		self._unlinksCombo = QComboBox()
		self.regProp("in_unlinks", WizProp(self._unlinksCombo, ""))
		self._unlinksCheck = WidgetEnableCheckBox("Use unlinks", [self._unlinksCombo])
		self.regProp("in_unlinks_enabled", WizProp(self._unlinksCheck, False))
		glayout.addWidget(self._unlinksCheck, y, 0)
		glayout.addWidget(self._unlinksCombo, y, 1)
		y = y + 1

		glayout.setRowStretch(y, 1)

		self.setLayout(glayout)

	def initializePage(self):
		self._lines1Combo.clear()
		self._lines2Combo.clear()
		self._unlinksCombo.clear()
		for name in self.model().tableNames():
			self._lines1Combo.addItem(name)
			self._lines2Combo.addItem(name)
			self._unlinksCombo.addItem(name)