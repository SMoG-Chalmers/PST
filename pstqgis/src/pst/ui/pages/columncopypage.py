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

from qgis.PyQt.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QVBoxLayout
from ..wizard import BasePage, WizProp
from ..widgets import WidgetEnableCheckBox


class ColumnCopyPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Column Copy")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):

		vlayout = QVBoxLayout()

		lbl = QLabel(
			"A column labeled 'ID' with unique increasing numbers for every row will be "\
			"added to the output table automatically. In addition to this column it is also "\
			"possible to copy one of the columns of the source table to the output table "\
			"(tip: if a row identifying column is copied this can later be used for transferring "\
			"more data from source table to the new table if necessary).")
		lbl.setWordWrap(True);
		vlayout.addWidget(lbl)

		vlayout.addSpacing(20)

		self._copyCheck = WidgetEnableCheckBox("Copy column from source table")
		self.regProp("copy_column_enabled", WizProp(self._copyCheck, False))
		vlayout.addWidget(self._copyCheck)

		glayout = QGridLayout()
		glayout.setColumnMinimumWidth(0, 20)

		lbl = QLabel(
			"The selected column of the source table will be added to the output table "\
			"(possibly with a new name). For every object in the output table the value of "\
			"its source object will be copied to this column.")
		lbl.setWordWrap(True);
		self._copyCheck.addWidget(lbl)
		glayout.addWidget(lbl, 0, 1, 1, 3)

		lbl = QLabel("Column in source table")
		self._copyCheck.addWidget(lbl)
		glayout.addWidget(lbl, 1, 1)
		self._sourceCombo = QComboBox()
		self.regProp("copy_column_in", WizProp(self._sourceCombo, ""))
		self._copyCheck.addWidget(self._sourceCombo)
		glayout.addWidget(self._sourceCombo, 1, 2)

		lbl = QLabel("Column in output table")
		self._copyCheck.addWidget(lbl)
		glayout.addWidget(lbl, 2, 1)
		self._outputEdit = QLineEdit()
		self.regProp("copy_column_out", WizProp(self._outputEdit, ""))
		self._copyCheck.addWidget(self._outputEdit)
		glayout.addWidget(self._outputEdit, 2, 2)

		vlayout.addLayout(glayout)

		vlayout.addStretch(1)

		self.setLayout(vlayout)

	def initializePage(self):
		table = self.wizard().prop("in_network")
		self._sourceCombo.clear()
		for column in self.model().columnNames(table):
			self._sourceCombo.addItem(column)