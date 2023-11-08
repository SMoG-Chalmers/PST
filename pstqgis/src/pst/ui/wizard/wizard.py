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

from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QCheckBox, QComboBox, QLineEdit, QListWidget, QRadioButton, QWizard, QWizardPage
from ... import APP_TITLE

BASE_TITLE = APP_TITLE

class WizPropBase(object):
	def value(self):
		return None
	def default(self):
		return None
	def setValue(self, value):
		raise NotImplementedError("The method 'setValue' is not implemented!")
	def toString(self):
		return str(self.value())


class WizProp(object):
	def __init__(self, widget, default):
		self._widget = widget
		self._default = default

	def value(self):
		return WizProp.ValueFromWidget(self._widget)

	def default(self):
		return self._default

	def setValue(self, value):
		widget = self._widget
		if isinstance(widget, QLineEdit):
			widget.setText(self.toString(value))
		elif isinstance(widget, QCheckBox):
			widget.setCheckState(Qt.Checked if bool(value) else Qt.Unchecked)
		elif isinstance(widget, QRadioButton):
			widget.setChecked(bool(value))
		elif isinstance(widget, QComboBox):
			widget.setCurrentIndex(max(0, widget.findText(self.toString(value))))
		elif isinstance(widget, QListWidget):
			for i in range(widget.count()):
				if widget.item(i).text() in value:
					widget.item(i).setCheckState(Qt.Checked)
		else:
			assert(False)

	def toString(self, value):
		return value if type(value) is str else str(value)

	@staticmethod
	def ValueFromWidget(widget):
		if isinstance(widget, QLineEdit):
			return widget.text()
		if isinstance(widget, QCheckBox):
			return (widget.checkState() == Qt.Checked)
		if isinstance(widget, QRadioButton):
			return widget.isChecked()
		if isinstance(widget, QComboBox):
			return widget.currentText()
		if isinstance(widget, QListWidget):
			return [widget.item(i).text() for i in range(widget.count()) if widget.item(i).checkState() == Qt.Checked]
		return widget.value()


class WizPropManual(object):
	def __init__(self, default):
		self._default = default
		self._value = default

	def value(self):
		return self._value

	def default(self):
		return self._default

	def setValue(self, value):
		self._value = value

	def toString(self, value):
		return str(value)


class WizPropFloat(WizProp):
	def __init__(self, widget, default, decimals):
		WizProp.__init__(self, widget, default)
		self._decimals = decimals

	def value(self):
		return float(WizProp.value(self))

	def toString(self, value):
		return ("%%.%df" % self._decimals) % value


class WizPropRadio(object):
	def __init__(self, radio_value_pairs, default):
		self._radio_value_pairs = radio_value_pairs
		self._default = default

	def value(self):
		for radio, value in self._radio_value_pairs:
			if radio.isChecked():
				return value
		return self.default()

	def default(self):
		return self._default

	def setValue(self, value):
		for radio, v in self._radio_value_pairs:
			if v == value:
				radio.setChecked(True)
				return
		for radio, v in self._radio_value_pairs:
			if v == self._default:
				radio.setChecked(True)
		raise Exception("Default value not found!")

	def toString(self, value):
		return str(value)


class WizPropCombo(object):
	def __init__(self, combobox, default):
		self._combobox = combobox
		self._default = default

	def value(self):
		return self._combobox.itemData(self._combobox.currentIndex())

	def default(self):
		return self._default

	def setValue(self, value):
		for i in range(self._combobox.count()):
			if self._combobox.itemData(i) == value:
				self._combobox.setCurrentIndex(i)
				return
		for i in range(self._combobox.count()):
			if self._combobox.itemData(i) == self._default:
				self._combobox.setCurrentIndex(i)
				return
		raise Exception("Default value not found in combo box!")

	def toString(self, value):
		return str(value)


class BaseWiz(QWizard):
	def __init__(self, parent, settings, model, title):
		QWizard.__init__(self, parent)
		self._settings = settings
		self._model = model  # TODO: Remove?
		self._title = title
		self._props = {}
		self.setWizardStyle(QWizard.ModernStyle)
		self.setTitle(title)
		self.setOption(QWizard.NoBackButtonOnLastPage, True)
		self.loadProperties()

	def setTitle(self, title):
		self.setWindowTitle(BASE_TITLE + ' - ' + title)

	def model(self):  # TODO: Remove?
		return self._model

	def properties(self):
		return self._props

	def setProperties(self, props):
		self._props = props

	def accept(self):
		""" 'Finish' is clicked. """
		self.restart()

	def reject(self):
		""" 'Cancel' is clicked. """
		return QWizard.reject(self)

	def prop(self, name):
		return self._props[name]

	def addPage(self, page):
		QWizard.addPage(self, page)
		self._onPageAdded(page)

	def setPage(self, index, page):
		QWizard.setPage(self, index, page)
		self._onPageAdded(page)

	def _onPageAdded(self, page):
		# Register all properties that we don't already have values for, to make sure
		# all properties of all pages are in the property set. This makes it safe for
		# analysis to ask for any property, even if the page of that property was never
		# visited and hence the property never collected.
		if isinstance(page, BasePage):
			for key, value in page.getPropertyDefaults().items():
				if key not in self._props:
					self._props[key] = value

	def initializePage(self, id):
		QWizard.initializePage(self, id)
		page = self.page(id)
		if isinstance(page, BasePage):
			self.restorePageProperties(page)

	def validateCurrentPage(self):
		page = self.currentPage()
		if isinstance(page, BasePage):
			self.collectPageProperties(page)
		return QWizard.validateCurrentPage(self)

	def cleanupPage(self, id):
		page = self.page(id)
		if isinstance(page, BasePage):
			self.collectPageProperties(page)
		QWizard.cleanupPage(self, id)

	def restorePageProperties(self, page):
		for name, prop in page._props.items():
			value = self._props.get(name)
			if value is None:
				value = prop.default()
			prop.setValue(value)

	def collectPageProperties(self, page):
		page.collectProperties(self._props)

	def saveProperties(self):
		self.removeDeprecatedProperties()
		self._settings.set(self.settingsKey(), self._props)
		self._settings.save()

	def loadProperties(self):
		p = self._settings.get(self.settingsKey())
		self._props = {} if p is None else p

	def removeDeprecatedProperties(self):
		available = self._availableProperties()
		deprecated_props = [name for name in self._props if name not in available]
		for name in deprecated_props:
			del self._props[name]

	def _availableProperties(self):
		""" Returns a Set of names of all properties of all pages """
		names = set()
		for page_id in self.pageIds():
			page = self.page(page_id)
			if isinstance(page, BasePage):
				for name in page._props:
					if name in names:
						raise Exception("Duplicate wizard property '%s'" % name)
					names.add(name)
		return names

	def settingsKey(self):
		return "analyses/" + self._title

	@staticmethod
	def ValueFromWidget(widget):
		if isinstance(widget, QLineEdit):
			return widget.text()
		if isinstance(widget, QCheckBox):
			return (widget.checkState() == Qt.Checked)
		if isinstance(widget, QComboBox):
			return widget.currentText()
		return widget.value()


class BasePage(QWizardPage):
	def __init__(self):
		QWizardPage.__init__(self)
		self._props = {}

	def model(self):
		return self.wizard().model()

	def regProp(self, name, prop):
		self._props[name] = prop

	def prop(self, name):
		return self._props[name].value()

	def setProp(self, name, value):
		self._props[name].setValue(value)

	def resetProps(self):
		for name, prop in self._props.items():
			prop.setValue(prop.default())

	def collectProperties(self, out_props):
		for name, prop in self._props.items():
			out_props[name] = prop.value()

	def getPropertyDefaults(self):
		p = {}
		for name, prop in self._props.items():
			p[name] = prop.default()
		return p