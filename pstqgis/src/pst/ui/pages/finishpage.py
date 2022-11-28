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

from qgis.PyQt.QtWidgets import QLabel, QVBoxLayout, QWizard, QWizardPage

class FinishPage(QWizardPage):
	def __init__(self, title = "Analysis finished", sub_title = " "):
		QWizardPage.__init__(self)

		self.setTitle(title)
		self.setSubTitle(sub_title)

		self.createWidgets()

		self.setButtonText(QWizard.FinishButton, "Restart")
		self.setButtonText(QWizard.CancelButton, "Close")

	def createWidgets(self):
		vlayout = QVBoxLayout()
		vlayout.addWidget(QLabel("The analysis was performed successfully."))
		vlayout.addStretch(1)
		vlayout.addWidget(QLabel("Click 'Restart' to do new analysis or 'Close' to close."))
		self.setLayout(vlayout)