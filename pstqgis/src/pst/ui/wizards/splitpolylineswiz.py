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

from ..wizard import BaseWiz, BasePage, WizProp, WizPropFloat
from ..pages import NetworkInputPage, ColumnCopyPage, ReadyPage, ProgressPage, FinishPage


class SplitPolylinesWiz(BaseWiz):
	def __init__(self, parent, settings, model, task_factory):
		BaseWiz.__init__(self, parent, settings, model, "Split Polylines")
		self._task_factory = task_factory
		self.addPage(NetworkInputPage(point_src_available=False))
		self.addPage(ColumnCopyPage())
		self.addPage(ReadyPage())
		self.addPage(ProgressPage())
		self.addPage(FinishPage())

	def createTask(self, props):
		""" Creates, initializes and returns a task object. """
		return self._task_factory(props)