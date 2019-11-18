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

from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWizard, QWizardPage
import json

class ReadyPage(QWizardPage):
	def __init__(self, title = "Ready", sub_title = " "):
		QWizardPage.__init__(self)
		self.setTitle(title)
		self.setSubTitle(sub_title)
		self.setCommitPage(True)
		self.createWidgets()
		self.setButtonText(QWizard.CommitButton, "Start")

	def createWidgets(self):
		vlayout = QVBoxLayout()
		vlayout.addWidget(QLabel("PST now has all information necessary to start the analysis."))
		vlayout.addStretch(1)
		self._propView = QPlainTextEdit()
		self._propView.setReadOnly(True)
		self._propView.setVisible(False)
		vlayout.addWidget(self._propView, 30)
		hlayout = QHBoxLayout()
		hlayout.addWidget(QLabel("Click 'Start' to start the analysis."), 1)
		self._toggleSettingsButton = QPushButton("Show settings")
		self._toggleSettingsButton.clicked.connect(self.onToggleShowSettings)
		hlayout.addWidget(self._toggleSettingsButton)
		vlayout.addLayout(hlayout)
		self.setLayout(vlayout)

	def initializePage(self):
		self.wizard().removeDeprecatedProperties()
		props = self.wizard().properties()
		text = json.dumps(props, sort_keys=True, indent=4, separators=(',', ': '))
		self._propView.setPlainText(text)

	def validatePage(self):
		if not QWizardPage.validatePage(self):
			return False
		self.wizard().saveProperties()
		return True

	def onToggleShowSettings(self):
		visible = not self._propView.isVisible()
		self._propView.setVisible(visible)
		self._toggleSettingsButton.setText("Hide settings" if visible else "Show settings")