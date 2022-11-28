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
from qgis.PyQt.QtGui import QFontMetrics
from qgis.PyQt.QtWidgets import QApplication, QGridLayout, QLabel, QLineEdit, QMessageBox, QRadioButton, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import EntryPointsPage, FinishPage, GraphInputPage, ProgressPage, RadiusPage, ReadyPage
from ..widgets import PropertySheetWidget, TableDataSelectionWidget, WidgetEnableCheckBox, WidgetEnableRadioButton
from .attractiondistancewiz import ValidateNonCollidingAttractionDataOutputColumns, CUSTOM_COLUMN_NAME_CHAR_LIMIT


class AttractionReachWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Attraction Reach")
		self._task_factory = task_factory
		pages = [
			GraphInputPage(origins_available=True, skip_next_page_if_no_regions=True),
			EntryPointsPage(distribution_function_available=True),
			CalcOptionsPage(),
			RadiusPage(),
			AttractionPage(),
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
		("Straight line distance", 1000, "meters",  "dist_straight"),
		("Walking distance",       1000, "meters",  "dist_walking"),
		("Axial/segment steps",       2, "steps",   "dist_steps"),
		("Angular",                 180, "degrees", "dist_angular"),
		("Axialmeter",             2000, "steps*m", "dist_axmeter"),
	]

	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Calculation Options")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		dist_type_sheet = PropertySheetWidget(self)
		dist_type_sheet.newSection("Distance modes and radii")
		radius_edit_max_width = QFontMetrics(QApplication.font()).width("8888888888")
		for dt in self.DIST_MODES:
			edit = QLineEdit()
			edit.setAlignment(Qt.AlignRight)
			edit.setFixedWidth(radius_edit_max_width)
			unit = QLabel(dt[2])
			checkbox = WidgetEnableCheckBox(dt[0], [edit, unit])
			self.regProp(dt[3]+"_enabled", WizProp(checkbox, False))
			self.regProp(dt[3], WizPropFloat(edit, dt[1], 0))
			dist_type_sheet.add(checkbox, edit, unit)

		func_sheet = PropertySheetWidget(self)
		func_sheet.newSection("Weight function")
		func_sheet.addComboProp("f(x)", [("1-x^C", "pow"),("1-(4x^C)/2 <0.5< ((2-2x)^C)/2", "curve"),("(x+1)^-C", "divide")], "pow", "weight_func")
		func_sheet.addNumberProp("C", 1, 2, None, "weight_func_constant")

		enable_checkbox = WidgetEnableCheckBox("Enable distance weight mode", [dist_type_sheet, func_sheet])
		self.regProp("weight_enabled", WizProp(enable_checkbox, False))
		#prop_sheet = PropertySheetWidget(self)
		#prop_sheet.newSection("Weight mode")
		#radio = QRadioButton("No weight")
		#radio.setChecked(True)
		#prop_sheet.add(radio)
		#weight_mode_radio = WidgetEnableRadioButton("Weigh by distance", [dist_type_sheet, func_sheet])
		#self.regProp("weight_enabled", WizProp(weight_mode_radio, False))
		#prop_sheet.add(weight_mode_radio)

		glayout = QGridLayout()
		#glayout.addWidget(prop_sheet, 0, 0)
		glayout.addWidget(enable_checkbox, 0, 0)
		glayout.setRowMinimumHeight(1, 10)
		glayout.addWidget(dist_type_sheet, 2, 0, 2, 1)
		glayout.addWidget(func_sheet, 2, 1)
		glayout.setRowStretch(4, 1)

		self.setLayout(glayout)

	def validatePage(self):
		if self.wizard().prop("weight_enabled") and not [True for m in self.DIST_MODES if self.wizard().prop(m[3])]:
			QMessageBox.information(self, "Incomplete input", "Please select at least one distance mode.")
		else:
			return True
		return False

	def nextId(self):
		if self.wizard().properties().get("weight_enabled"):
			return self.wizard().currentId() + 2  # Skip next page
		return BasePage.nextId(self)


class AttractionPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Attractions")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()

		vlayout = QVBoxLayout()
		self._list = TableDataSelectionWidget()
		self.regProp("dest_data", WizProp(self._list, []))
		radio = QRadioButton("Weigh attractions equally")
		radio.setChecked(True)
		vlayout.addWidget(radio)
		radio = WidgetEnableRadioButton("Weigh attractions by data", [self._list])
		self.regProp("dest_data_enabled", WizProp(radio, False))
		vlayout.addWidget(radio)
		vlayout.addWidget(self._list)
		glayout.addLayout(vlayout, 0, 0)

		vlayout = QVBoxLayout()
		vlayout.addWidget(QLabel("Attraction name (for output column)"))
		edit = QLineEdit()
		edit.setMaxLength(2)  # Maximum 2 charcters, to avoid column names being too long (limitation in table file format)
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