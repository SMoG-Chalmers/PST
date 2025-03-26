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
from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QMessageBox, QRadioButton, QVBoxLayout, QDoubleSpinBox
from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import EntryPointsPage, FinishPage, GraphInputPage, ProgressPage, RadiusPage, ReadyPage
from ..widgets import PropertySheetWidget, PropertyStyle, PropertyState, TableDataSelectionWidget, WidgetEnableRadioButton, WidgetEnableCheckBox

class AttractionDistanceWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Attraction Distance")
		self._task_factory = task_factory
		pages = [
			GraphInputPage(origins_available=True, skip_next_page_if_no_regions=True),
			EntryPointsPage(distribution_function_available=False),
			CalcOptionsPage(),
			WeightPage(),
			RadiusPage(),
			DestinationPage(),
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
		("Straight line distance (meters)", False, "dist_straight"),
		("Walking distance (meters)",       True,  "dist_walking"),
		("Axial/segment lines (steps)",     False, "dist_steps"),
		("Angle (degrees)",                 False, "dist_angular"),
		("Axialmeter (steps*meters)",       False, "dist_axmeter"),
		("Attribute-based weight (varies)", False, "dist_weights"),
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

		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)



	def nextId(self):
		if not self.wizard().properties().get("dist_weights"):
			return self.wizard().currentId() + 2  # Skip next page
		return BasePage.nextId(self)

	def validatePage(self):
		if not ([True for m in self.DIST_MODES if self.wizard().prop(m[2])]):
			QMessageBox.information(self, "Incomplete input", "Please select at least one distance mode.")
		else:
			return True
		return False


class WeightPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Custom weight settings")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Weights configuration")

		self._dist_weightsCombo = QComboBox()
		prop_sheet.add(QLabel("Line weight attribute"), self._dist_weightsCombo)
		self.regProp("dw_attribute", WizProp(self._dist_weightsCombo, ""))

		self._point_connection_weightSpinBox = QDoubleSpinBox()	
		self._point_connection_weightSpinBox.setRange(0, 99999)
		prop_sheet.add(QLabel("Point connection weight"), self._point_connection_weightSpinBox, QLabel("per meter"))
		self.regProp("point_connection_weight", WizProp(self._point_connection_weightSpinBox, ""))


		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)

	def initializePage(self):
		self._dist_weightsCombo.clear()
		for attr in self.model().columnNames(self.wizard().prop("in_network")):
			#weights can only be integers or doubles, not strings
			if self.model().columnType(self.wizard().prop("in_network"), attr) in ["integer", "double"]:
				self._dist_weightsCombo.addItem(attr)
	def validatePage(self):
		layer = QgsProject.instance().mapLayersByName(self.wizard().prop("in_network"))[0]
		field_name = self.wizard().prop("dw_attribute")

		idx = layer.fields().indexOf(field_name)
		min_value = layer.minimumValue(idx)

		if min_value < 0:
				QMessageBox.information(self, "Wrong input", "Selected attribute field must not contain negative values")
		else:
			return True
		return False
CUSTOM_COLUMN_NAME_CHAR_LIMIT = 2

class DestinationPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Destinations")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):
		glayout = QGridLayout()

		vlayout = QVBoxLayout()
		self._list = TableDataSelectionWidget()
		self.regProp("dest_data", WizProp(self._list, []))
		vlayout.addWidget(QLabel("Find minimum distance to:"))
		radio = QRadioButton("Any destination element")
		radio.setChecked(True)
		vlayout.addWidget(radio)
		radio = WidgetEnableRadioButton("Destination element with specific attractions", [self._list])
		self.regProp("dest_data_enabled", WizProp(radio, False))
		vlayout.addWidget(radio)
		vlayout.addWidget(self._list)
		glayout.addLayout(vlayout, 0, 0)

		vlayout = QVBoxLayout()
		vlayout.addWidget(QLabel("Destination name (for output column)"))
		edit = QLineEdit()
		edit.setMaxLength(CUSTOM_COLUMN_NAME_CHAR_LIMIT)  # Character count limit, to avoid column names being too long (limitation in table file format)
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

def ValidateNonCollidingAttractionDataOutputColumns(parent, dest_data_enabled, dest_data_columns, custom_name):
	if not dest_data_enabled or len(dest_data_columns) < 2:
		return True
	if custom_name:
		QMessageBox.information(parent, "Column name collision", "When specifying a custom name only one data column can be selected, since output columns would otherwise get the same name.")
		return False
	prefixes = []
	for name in dest_data_columns:
		prefix = name[:CUSTOM_COLUMN_NAME_CHAR_LIMIT].lower()
		if prefix in prefixes:
			QMessageBox.information(parent, "Column name collision", "Selected data columns have same prefix '%s', which will cause generated output column names to collide." % (prefix))
			return False
		prefixes.append(prefix)
	return True
