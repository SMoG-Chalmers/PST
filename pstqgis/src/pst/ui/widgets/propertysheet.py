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
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QCheckBox, QComboBox, QGridLayout, QLabel, QLineEdit, QRadioButton, QWidget
from .widgetenablecheckbox import WidgetEnableCheckBox
from .widgetenableradiobutton import WidgetEnableRadioButton
from ..wizard import WizProp, WizPropFloat, WizPropCombo

class PropertyStyle(object):
	LABEL = 0
	CHECK = 1
	RADIO = 2

class PropertyState(object):
	UNCHECKED = False
	CHECKED = True

class PropertySheetWidget(QWidget):
	def __init__(self, wizard_page):
		QWidget.__init__(self)
		self._page = wizard_page
		self._glayout = QGridLayout()
		self._glayout.setContentsMargins(0,0,0,0)
		self._glayout.setVerticalSpacing(4)
		self._glayout.setColumnStretch(4, 1)
		self._row_count = 0
		self.setDefaultIndent()
		self.setLayout(self._glayout)

	def setDefaultIndent(self):
		self.setIndent(10)

	def setIndent(self, indent):
		self._glayout.setColumnMinimumWidth(0, indent)

	def newSection(self, title=None):
		if self._row_count > 0:
			self._glayout.setRowMinimumHeight(self._row_count, 10)
			self._row_count = self._row_count + 1
		if title is not None:
			self._glayout.addWidget(QLabel(title), self._row_count, 0, 1, 4)
			self._row_count = self._row_count + 1

	def add(self, label, ctrl=None, unit=None):
		label_col_span = 1
		if ctrl is None:
			label_col_span = 3 if unit is None else 2
		self._glayout.addWidget(label, self._row_count, 1, 1, label_col_span)
		if ctrl is not None:
			self._glayout.addWidget(ctrl,  self._row_count, 2)
		if unit is not None:
			self._glayout.addWidget(unit,  self._row_count, 3)
		self._row_count = self._row_count + 1

	def addBoolProp(self, title, default_value, prop_name, style=PropertyStyle.CHECK):
		widget = None
		if style == PropertyStyle.CHECK:
			widget = QCheckBox(title)
		elif style == PropertyStyle.RADIO:
			widget = QRadioButton(title)
		else:
			raise Exception("Unsupported bool property style (#%d)!" % (style))
		self._page.regProp(prop_name, WizProp(widget, default_value))
		self.add(widget)
		return widget

	def addTextProp(self, title, default_value, prop_name):
		label = QLabel(title)
		edit = QLineEdit()
		self._page.regProp(prop_name, WizProp(edit, default_value))
		self.add(label, edit)
		return edit

	def addNumberProp(self, title, default_value, decimals, unit, prop_name, style=PropertyStyle.LABEL, default_state=PropertyState.CHECKED):
		edit = QLineEdit()
		edit.setAlignment(Qt.AlignRight)
		unit_label = QLabel(unit)
		self._page.regProp(prop_name, WizPropFloat(edit, default_value, decimals))
		widget = None
		if PropertyStyle.LABEL == style:
			widget = QLabel(title)
		elif PropertyStyle.CHECK == style:
			widget = WidgetEnableCheckBox(title, [edit, unit_label])
			self._page.regProp(prop_name + "_enabled", WizProp(widget, default_state))
		elif PropertyStyle.RADIO == style:
			widget = WidgetEnableRadioButton(title, [edit, unit_label])
			self._page.regProp(prop_name + "_enabled", WizProp(widget, default_state))
		else:
			raise Exception("Unsupported number property style (#%d)!" % (style))
		self.add(widget, edit, unit_label)
		return (widget, edit, unit_label)

	def addComboProp(self, title, options, default_value, prop_name):
		combo = QComboBox()
		for text, value in options:
			combo.addItem(text, value)
		self._page.regProp(prop_name, WizPropCombo(combo, default_value))
		label = QLabel(title)
		self.add(label, combo)
		return (label, combo)

	def addStretch(self, amount):
		self._glayout.setRowStretch(self._row_count, amount)
		self._row_count = self._row_count + 1