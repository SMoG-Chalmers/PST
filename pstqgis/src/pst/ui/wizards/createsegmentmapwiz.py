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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout
from ..wizard import BaseWiz, BasePage, WizPropFloat
from ..pages import NetworkInputPage, ColumnCopyPage, ReadyPage, ProgressPage, FinishPage


class CreateSegmentMapWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Create Segment Map")
		self._task_factory = task_factory
		self.addPage(NetworkInputPage(point_src_available=False))
		self.addPage(TrimmingPage())
		self.addPage(ColumnCopyPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)


class TrimmingPage(BasePage):
	def __init__(self):
		BasePage.__init__(self)
		self.setTitle("Trimming")
		self.setSubTitle(" ")
		self.createWidgets()

	def createWidgets(self):

		vlayout = QVBoxLayout()

		glayout = QGridLayout()
		glayout.setColumnStretch(3, 1)

		glayout.addWidget(QLabel("Snap points closer than"), 0, 0)
		self._snapEdit = QLineEdit()
		self._snapEdit.setAlignment(Qt.AlignRight)
		self.regProp("trim_snap", WizPropFloat(self._snapEdit, 1, 1))
		glayout.addWidget(self._snapEdit, 0, 1)
		glayout.addWidget(QLabel("meters"), 0, 2)

		glayout.addWidget(QLabel("Remove tail segments shorter than"), 1, 0)
		self._tailEdit = QLineEdit()
		self._tailEdit.setAlignment(Qt.AlignRight)
		self.regProp("trim_tail", WizPropFloat(self._tailEdit, 10, 1))
		glayout.addWidget(self._tailEdit, 1, 1)
		glayout.addWidget(QLabel("meters"), 1, 2)

		glayout.addWidget(QLabel("Merge segment-pairs with colinear deviation below"), 2, 0)
		self._mergeEdit = QLineEdit()
		self._mergeEdit.setAlignment(Qt.AlignRight)
		self.regProp("trim_coldev", WizPropFloat(self._mergeEdit, 1, 1))
		glayout.addWidget(self._mergeEdit, 2, 1)
		glayout.addWidget(QLabel("meters"), 2, 2)

		glayout.setRowMinimumHeight(3, 10)

		vlayout.addLayout(glayout)

		vlayout.addSpacing(10)

		hlayout = QHBoxLayout()
		btn = QPushButton("Restore default values")
		btn.clicked.connect(self.resetProps)
		hlayout.addWidget(btn)
		hlayout.addStretch(1)
		vlayout.addLayout(hlayout)

		vlayout.addStretch(1)

		self.setLayout(vlayout)