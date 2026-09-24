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

from qgis.PyQt.QtWidgets import QLabel, QComboBox, QDoubleSpinBox, QLineEdit, QMessageBox, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizProp, WizPropCombo
from ..pages import FinishPage, ProgressPage, ReadyPage, AddRadiusProperties, RadiusType
from ..widgets import PropertySheetWidget, WidgetEnableCheckBox

class ODBetweennessWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Origin-Destination Betweenness")
		self._task_factory = task_factory
		pages = [
			GraphInputPage(),
			DistanceSettingsPage(),
			#EntryPointsPage(distribution_function_available=True),
			#CalcOptionsPage(),
			#RadiusPage(),
			#AttractionPage(),
			ReadyPage(),
			ProgressPage(),
			FinishPage(),
		]
		for index, page in enumerate(pages):
			self.setPage(index, page)

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class GraphInputPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Input Tables")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):

		prop_sheet = PropertySheetWidget(self)

		# Origins
		prop_sheet.newSection("Origins")
		self._originPointsCombo = QComboBox()
		self._originPointsCombo.currentIndexChanged.connect(self.onOriginPointsComboChanged)
		prop_sheet.add(QLabel("Point table"), self._originPointsCombo)
		self.regProp("in_origins", WizProp(self._originPointsCombo, ""))
		self._originWeightsCombo = QComboBox()
		prop_sheet.add(QLabel("Data column"), self._originWeightsCombo)
		self.regProp("in_origin_weights", WizProp(self._originWeightsCombo, ""))

		# Network
		prop_sheet.newSection("Network")
		self._linesCombo = QComboBox()
		prop_sheet.add(QLabel("Axial/Segment lines"), self._linesCombo)
		self.regProp("in_network", WizProp(self._linesCombo, ""))
		self._unlinksCombo = QComboBox()
		self._unlinksCheck = WidgetEnableCheckBox("Unlink points", [self._unlinksCombo])
		prop_sheet.add(self._unlinksCheck, self._unlinksCombo)
		self.regProp("in_unlinks", WizProp(self._unlinksCombo, ""))
		self.regProp("in_unlinks_enabled", WizProp(self._unlinksCheck, False))

		# Destinations
		prop_sheet.newSection("Destinations")
		self._destinationPointsCombo = QComboBox()
		self._destinationPointsCombo.currentIndexChanged.connect(self.onDestinationPointsComboChanged)
		prop_sheet.add(QLabel("Point table"), self._destinationPointsCombo)
		self.regProp("in_destinations", WizProp(self._destinationPointsCombo, ""))
		self._destinationWeightsCombo = QComboBox()
		self._destinationWeightsCheck = WidgetEnableCheckBox("Data column", [self._destinationWeightsCombo])
		prop_sheet.add(self._destinationWeightsCheck, self._destinationWeightsCombo)
		self.regProp("in_destination_weights", WizProp(self._destinationWeightsCombo, ""))
		self.regProp("in_destination_weights_enabled", WizProp(self._destinationWeightsCheck, False))

		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)

	def initializePage(self):
		table_names = self.model().tableNames()
		for combo in [self._originPointsCombo, self._linesCombo, self._unlinksCombo, self._destinationPointsCombo]:
			combo.clear()
			for name in table_names:
				combo.addItem(name)
		self.initOriginWeightsCombo()
		self.initDestinationWeightsCombo()

	def initOriginWeightsCombo(self):
		self.initColumnsCombo(self._originWeightsCombo, self._originPointsCombo.currentText())

	def initDestinationWeightsCombo(self):
		self.initColumnsCombo(self._destinationWeightsCombo, self._destinationPointsCombo.currentText())

	def initColumnsCombo(self, combo, table):
		combo.clear()
		if table:
			for column_name in self.model().columnNames(table):
				combo.addItem(column_name)

	def onOriginPointsComboChanged(self, index):
		self.initOriginWeightsCombo()

	def onDestinationPointsComboChanged(self, index):
		self.initDestinationWeightsCombo()

DESTINATION_MODE_ITEMS = [
	("All reachable destinations", "all"),
	("Closest destination only",   "closest"),
]

ROUTE_CHOICE_ITEMS = [
	("Minimum walking distance", "walking"),
	("Least angular",            "angular"),
	("Minimum weighted distance (line attribute)", "weights"),
]

WEIGHT_DIRECTION_ITEMS = [
	("Higher value increases cost", "increase"),
	("Higher value decreases cost", "decrease"),
]

DEFAULT_WEIGHT_MAX_FACTOR = 2.0

RADIUS_TYPES = [RadiusType.STRAIGHT, RadiusType.WALKING, RadiusType.ANGULAR]

class DistanceSettingsPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Settings")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):

		prop_sheet = PropertySheetWidget(self)

		prop_sheet.newSection("Traversal")
		self._destinationModeCombo = QComboBox()
		for item in DESTINATION_MODE_ITEMS:
			self._destinationModeCombo.addItem(item[0], item[1])
		prop_sheet.add(QLabel("Destination mode"), self._destinationModeCombo)
		self.regProp("destination_mode", WizPropCombo(self._destinationModeCombo, DESTINATION_MODE_ITEMS[0][1]))
		self._routeChoiceCombo = QComboBox()
		for item in ROUTE_CHOICE_ITEMS:
			self._routeChoiceCombo.addItem(item[0], item[1])
		prop_sheet.add(QLabel("Route choice"), self._routeChoiceCombo)
		self.regProp("route_choice", WizPropCombo(self._routeChoiceCombo, ROUTE_CHOICE_ITEMS[0][1]))
		self._routeChoiceCombo.currentIndexChanged.connect(self.updateWeightWidgets)

		# Line attribute weighting (only used with weighted route choice)
		prop_sheet.newSection("Line attribute weighting")
		self._weightAttributeCombo = QComboBox()
		prop_sheet.add(QLabel("Line attribute"), self._weightAttributeCombo)
		self.regProp("dw_attribute", WizProp(self._weightAttributeCombo, ""))
		self._weightDirectionCombo = QComboBox()
		for item in WEIGHT_DIRECTION_ITEMS:
			self._weightDirectionCombo.addItem(item[0], item[1])
		prop_sheet.add(QLabel("Effect"), self._weightDirectionCombo)
		self.regProp("dw_direction", WizPropCombo(self._weightDirectionCombo, WEIGHT_DIRECTION_ITEMS[0][1]))
		self._weightMaxFactorSpin = QDoubleSpinBox()
		self._weightMaxFactorSpin.setRange(1, 1000)
		self._weightMaxFactorSpin.setDecimals(2)
		self._weightMaxFactorSpin.setSingleStep(0.1)
		self._weightMaxFactorSpin.setValue(DEFAULT_WEIGHT_MAX_FACTOR)
		prop_sheet.add(QLabel("Highest cost factor"), self._weightMaxFactorSpin, QLabel("x distance"))
		self.regProp("dw_max_factor", WizProp(self._weightMaxFactorSpin, DEFAULT_WEIGHT_MAX_FACTOR))
		self._weightWidgets = [self._weightAttributeCombo, self._weightDirectionCombo, self._weightMaxFactorSpin]

		# Radius
		prop_sheet.newSection("Radius")
		AddRadiusProperties(prop_sheet, RADIUS_TYPES)
		
		# Output
		prop_sheet.newSection("Output")
		suffix_edit = QLineEdit()
		suffix_check =  WidgetEnableCheckBox("Column suffix", [suffix_edit])
		prop_sheet.add(suffix_check, suffix_edit)
		self.regProp("column_suffix", WizProp(suffix_edit, ""))
		self.regProp("column_suffix_enabled", WizProp(suffix_check, False))

		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)

	def initializePage(self):
		network_table = self.wizard().prop("in_network")
		selected = self._weightAttributeCombo.currentText()
		self._weightAttributeCombo.clear()
		if network_table:
			for column_name in self.model().columnNames(network_table):
				try:
					column_type = self.model().columnType(network_table, column_name)
				except Exception:
					continue  # Unsupported column types (dates etc) can't be weights
				if column_type in ["integer", "double"]:
					self._weightAttributeCombo.addItem(column_name)
		index = self._weightAttributeCombo.findText(selected)
		if index >= 0:
			self._weightAttributeCombo.setCurrentIndex(index)
		self.updateWeightWidgets()

	def updateWeightWidgets(self, *args):
		enabled = (self._routeChoiceCombo.currentData() == "weights")
		for widget in self._weightWidgets:
			widget.setEnabled(enabled)

	def validatePage(self):
		p = self.wizard().prop
		if p("route_choice") == "weights" and not p("dw_attribute"):
			QMessageBox.information(self, "Missing line attribute", "Please select a numeric line attribute for weighted route choice.")
			return False
		if p("column_suffix_enabled"):
			column_suffix = p("column_suffix")
			if not column_suffix:
				QMessageBox.information(self, "Invalid column suffix", "Please enter a column suffix or uncheck the column suffix checkpox.")
				return False
			if ' ' in column_suffix:
				QMessageBox.information(self, "Invalid column suffix", "Spaces not allowed in column suffix.")
				return False
		return True