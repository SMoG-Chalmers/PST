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

from qgis.PyQt.QtWidgets import QComboBox, QLabel, QRadioButton, QVBoxLayout
from ..wizard import BasePage, WizProp, WizPropManual, WizPropRadio
from ..widgets import WidgetEnableCheckBox, WidgetEnableRadioButton, PropertySheetWidget

class GraphInputPage(BasePage):
	def __init__(self, origins_available=True, skip_next_page_if_no_regions=False):
		BasePage.__init__(self)
		self.setTitle("Input Tables")
		self.setSubTitle(" ")
		self._origins_available = origins_available
		self._skip_next_page_if_no_regions = skip_next_page_if_no_regions
		self.createWidgets(origins_available)

	def createWidgets(self, origins_available):

		prop_sheet = PropertySheetWidget(self)

		# Origins
		if origins_available:
			prop_sheet.newSection("Origins")
			self._pointsCombo = QComboBox()
			self.regProp("in_origin_points", WizProp(self._pointsCombo, ""))
			chk1 = WidgetEnableRadioButton("Points/Polygons", [self._pointsCombo])
			chk2 = QRadioButton("Network lines")
			chk3 = QRadioButton("Junctions")
			self.regProp("in_origin_type", WizPropRadio([(chk1,"points"),(chk2,"lines"),(chk3,"junctions")], "points"))
			prop_sheet.add(chk1, self._pointsCombo)
			prop_sheet.add(chk2)
			prop_sheet.add(chk3)
			self.regProp('origin_is_regions', WizPropManual(False))
		else:
			self._pointsCombo = None

		# Network
		prop_sheet.newSection("Network")
		self._linesCombo = QComboBox()
		prop_sheet.add(QLabel("Axial/Segment lines"), self._linesCombo)
		self.regProp("in_network", WizProp(self._linesCombo, ""))
		self._unlinksCombo = QComboBox()
		self.regProp("in_unlinks", WizProp(self._unlinksCombo, ""))
		self._unlinksCheck = WidgetEnableCheckBox("Unlink points", [self._unlinksCombo])
		self.regProp("in_unlinks_enabled", WizProp(self._unlinksCheck, False))
		prop_sheet.add(self._unlinksCheck, self._unlinksCombo)

		# Destinations
		prop_sheet.newSection("Destinations")
		self._targetsCombo = QComboBox()
		self.regProp("in_destinations", WizProp(self._targetsCombo, ""))
		prop_sheet.add(QLabel("Data objects"), self._targetsCombo)
		self.regProp('dest_is_regions', WizPropManual(False))

		vlayout = QVBoxLayout()
		vlayout.addWidget(prop_sheet)
		vlayout.addStretch(1)
		self.setLayout(vlayout)

	def initializePage(self):
		table_combos = [self._linesCombo, self._unlinksCombo, self._targetsCombo]
		if self._pointsCombo is not None:
			table_combos.append(self._pointsCombo)
		for combo in table_combos:
			combo.clear()
		for name in self.model().tableNames():
			for combo in table_combos:
				combo.addItem(name)

	def collectProperties(self, props):
		if self._origins_available:
			self.setProp('origin_is_regions', ('points' == self.prop('in_origin_type') and self.model().getFirstGeometryType(self.prop('in_origin_points')) == 'polygon'))
		self.setProp('dest_is_regions', self.model().getFirstGeometryType(self.prop('in_destinations')) == 'polygon')
		BasePage.collectProperties(self, props)

	def hasRegionInput(self):
		p = self.prop
		return (self._origins_available and p('origin_is_regions')) or p('dest_is_regions')

	def nextId(self):
		if self._skip_next_page_if_no_regions and not self.hasRegionInput():
			return self.wizard().currentId() + 2  # Skip next page
		return BasePage.nextId(self)