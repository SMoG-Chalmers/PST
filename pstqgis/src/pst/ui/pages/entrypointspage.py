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

from qgis.PyQt.QtWidgets import QVBoxLayout
from ..wizard import BasePage
from ..widgets import PropertySheetWidget, PropertyStyle, PropertyState

class EntryPointsPage(BasePage):
	def __init__(self, distribution_function_available=False):
		BasePage.__init__(self)
		self.setTitle("Entry Points")
		self.setSubTitle("Please specify entry point options for origin/destination regions")
		self.createWidgets(distribution_function_available)

	def createWidgets(self, distribution_function_available):
		vlayout = QVBoxLayout()

		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Origins")
		prop_sheet.addBoolProp("Center", True, 'origin_poly_center_enabled', style=PropertyStyle.RADIO)
		edge_points_radio = prop_sheet.addNumberProp("Create entry point at every", 10, 0, "meters along region edge", "origin_poly_edge_point_interval", style=PropertyStyle.RADIO, default_state=PropertyState.UNCHECKED)[0]
		if distribution_function_available:
			widgets = prop_sheet.addComboProp("Attraction collection function", [('Avarage','avarage'),('Sum','sum'),('Min','min'),('Max','max')], 'avarage', 'origin_collection_function')
			for widget in widgets:
				edge_points_radio.addWidget(widget)
		self._origins_widget = prop_sheet
		vlayout.addWidget(prop_sheet)

		prop_sheet = PropertySheetWidget(self)
		prop_sheet.newSection("Destinations")
		prop_sheet.addBoolProp("Center", True, 'dest_poly_center_enabled', style=PropertyStyle.RADIO)
		edge_points_radio = prop_sheet.addNumberProp("Create entry point at every", 10, 0, "meters along region edge", "dest_poly_edge_point_interval", style=PropertyStyle.RADIO, default_state=PropertyState.UNCHECKED)[0]
		if distribution_function_available:
			widgets = prop_sheet.addComboProp("Attraction distribution function", [('Copy','copy'),('Divide','divide')], 'divide', 'dest_distribution_function')
			for widget in widgets:
				edge_points_radio.addWidget(widget)
		self._destinations_widget = prop_sheet
		vlayout.addWidget(prop_sheet)

		vlayout.addStretch(1)
		self.setLayout(vlayout)

	def initializePage(self):
		p = self.wizard().prop
		self._origins_widget.setEnabled(p("origin_is_regions"))
		self._destinations_widget.setEnabled(p("dest_is_regions"))