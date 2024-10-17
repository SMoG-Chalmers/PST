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

from qgis.PyQt.QtWidgets import QComboBox, QGridLayout, QLabel
from ..wizard import BasePage, WizProp, WizPropFloat
from ..widgets import WidgetEnableCheckBox


class NetworkTypeFlags(object):
	AXIAL = 1
	SEGMENT = 2
	AXIAL_AND_SEGMENT = 3


def NetworkTypeTextFromFlags(networkTypeFlags):
	if networkTypeFlags == NetworkTypeFlags.AXIAL:
		return "Axial"
	if networkTypeFlags == NetworkTypeFlags.SEGMENT:
		return "Segment"
	if networkTypeFlags == NetworkTypeFlags.AXIAL_AND_SEGMENT:
		return "Axial/Segment"
	raise Exception("Unsupported network type flags")


class NetworkInputPage(BasePage):
	def __init__(self, point_src_available=False, networkTypeFlags=NetworkTypeFlags.AXIAL_AND_SEGMENT):
		BasePage.__init__(self)
		self.setTitle("Input Tables")
		self.setSubTitle(" ")
		self.createWidgets(point_src_available, networkTypeFlags)

	def createWidgets(self, point_src_available, networkTypeFlags):
		glayout = QGridLayout()

		glayout.setColumnStretch(0, 0)
		glayout.setColumnStretch(1, 1)

		y = 0

		if point_src_available:
			self._pointsCombo = QComboBox()
			self.regProp("in_origins", WizProp(self._pointsCombo, ""))
			chk = WidgetEnableCheckBox("Origin points", [self._pointsCombo])
			self.regProp("in_origins_enabled", WizProp(chk, False))
			glayout.addWidget(chk, y, 0)
			glayout.addWidget(self._pointsCombo, y, 1)
			y = y + 1
		else:
			self._pointsCombo = None

		glayout.addWidget(QLabel(NetworkTypeTextFromFlags(networkTypeFlags) + " lines"), y, 0)
		self._linesCombo = QComboBox()
		self.regProp("in_network", WizProp(self._linesCombo, ""))
		glayout.addWidget(self._linesCombo, y, 1)
		y = y + 1

		if (networkTypeFlags & NetworkTypeFlags.AXIAL) != 0:
			self._unlinksCombo = QComboBox()
			self.regProp("in_unlinks", WizProp(self._unlinksCombo, ""))
			self._unlinksCheck = WidgetEnableCheckBox("Unlink points", [self._unlinksCombo])
			self.regProp("in_unlinks_enabled", WizProp(self._unlinksCheck, False))
			glayout.addWidget(self._unlinksCheck, y, 0)
			glayout.addWidget(self._unlinksCombo, y, 1)
			y = y + 1
		else:
			self._unlinksCombo = None

		glayout.setRowStretch(y, 1)

		self.setLayout(glayout)

	def initializePage(self):
		combos = [self._linesCombo]
		if self._pointsCombo is not None:
			combos.append(self._pointsCombo)
		if self._unlinksCombo is not None:
			combos.append(self._unlinksCombo)
		for combo in combos:
			combo.clear()
		for name in self.model().tableNames():
			for combo in combos:
				combo.addItem(name)