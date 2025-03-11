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

from builtins import object
from qgis.PyQt.QtWidgets import QGridLayout
from ..wizard import BasePage, WizProp, WizPropFloat
from ..widgets import PropertySheetWidget, PropertyStyle, PropertyState
from .networkinputpage import NetworkTypeFlags

class RadiusType(object):
	STRAIGHT=0
	WALKING=1
	STEPS=2
	ANGULAR=3
	AXMETER=4
	WEIGHTS=5

RADIUS_PROP_NAMES = {
	RadiusType.STRAIGHT : "rad_straight",
	RadiusType.WALKING  : "rad_walking",
	RadiusType.STEPS    : "rad_steps",
	RadiusType.ANGULAR  : "rad_angular",
	RadiusType.AXMETER  : "rad_axmeter",
	RadiusType.WEIGHTS  : "rad_weights"
}

def RadiusTypePropName(radius_type):
	return RADIUS_PROP_NAMES[radius_type]

def StepsTextFromNetworkTypeFlags(network_type_flags):
	if network_type_flags == NetworkTypeFlags.AXIAL:
		return "Axial (topological) steps"
	return "Axial/segment steps"

def AddRadiusProperties(prop_sheet, radius_types, network_type_flags=NetworkTypeFlags.AXIAL_AND_SEGMENT):
	if RadiusType.STRAIGHT in radius_types:
		prop_sheet.addNumberProp("Straight line distance", 1000, 0, "meters",  RadiusTypePropName(RadiusType.STRAIGHT), style=PropertyStyle.CHECK, default_state=PropertyState.UNCHECKED)
	if RadiusType.WALKING in radius_types:
		prop_sheet.addNumberProp("Walking distance",       1000, 0, "meters",  RadiusTypePropName(RadiusType.WALKING),  style=PropertyStyle.CHECK, default_state=PropertyState.UNCHECKED)
	if RadiusType.STEPS in radius_types:
		prop_sheet.addNumberProp(StepsTextFromNetworkTypeFlags(network_type_flags), 2, 0, "steps",   RadiusTypePropName(RadiusType.STEPS),    style=PropertyStyle.CHECK, default_state=PropertyState.UNCHECKED)
	if RadiusType.ANGULAR in radius_types:
		prop_sheet.addNumberProp("Angular",                 180, 0, "degrees", RadiusTypePropName(RadiusType.ANGULAR),  style=PropertyStyle.CHECK, default_state=PropertyState.UNCHECKED)
	if RadiusType.AXMETER in radius_types:
		prop_sheet.addNumberProp("Axialmeter",             2000, 0, "steps*m", RadiusTypePropName(RadiusType.AXMETER),  style=PropertyStyle.CHECK, default_state=PropertyState.UNCHECKED)
	if RadiusType.WEIGHTS in radius_types:
		prop_sheet.addNumberProp("Other weight (custom)",     0, 0, "varies", RadiusTypePropName(RadiusType.WEIGHTS),  style=PropertyStyle.CHECK, default_state=PropertyState.UNCHECKED)

class RadiusWidget(PropertySheetWidget):
	def __init__(self, wizard_page, radius_types, network_type_flags=NetworkTypeFlags.AXIAL_AND_SEGMENT):
		PropertySheetWidget.__init__(self, wizard_page)
		self.setIndent(0)
		AddRadiusProperties(self, radius_types, network_type_flags)

class RadiusPage(BasePage):
	def __init__(self, radius_types=[RadiusType.STRAIGHT, RadiusType.WALKING, RadiusType.STEPS, RadiusType.ANGULAR, RadiusType.AXMETER, RadiusType.WEIGHTS], network_type_flags=NetworkTypeFlags.AXIAL_AND_SEGMENT):
		BasePage.__init__(self)
		self.setTitle("Radius")
		self.setSubTitle("Please select radius type and range")
		self.createWidgets(radius_types, network_type_flags)

	def createWidgets(self, radius_types, network_type_flags):
		# Make radius widget vertically and horizontally centered
		glayout = QGridLayout()
		glayout.setRowStretch(0, 1)
		glayout.setRowStretch(2, 1)
		glayout.setColumnStretch(0, 1)
		glayout.setColumnStretch(2, 1)
		glayout.addWidget(RadiusWidget(self, radius_types, network_type_flags), 1, 1)
		self.setLayout(glayout)