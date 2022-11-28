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

from builtins import range
from builtins import object
import array, ctypes
from ..model import GeometryType
from .base import BaseAnalysis
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate


class Tasks(object):
	READ1 = 1
	READ2 = 2
	ANALYSIS = 3
	WRITE = 4


class CreateJunctionsAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):
		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props
		model = self._model

		# Tasks
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.READ1, 5, "Reading lines from " + props['in_lines1'])
		if self._props['in_lines2_enabled']:
			progress.addTask(Tasks.READ2, 5, "Reading lines from " + props['in_lines2'])
		progress.addTask(Tasks.ANALYSIS, 1,      None)
		progress.addTask(Tasks.WRITE, 5, "Creating junction table")

		initial_alloc_state = stack_allocator.state()
		algo = None

		try:
			# --- READ1 ---
			progress.setCurrentTask(Tasks.READ1)
			max_line_count = model.rowCount(props['in_lines1'])
			lines1 = Vector(ctypes.c_double, max_line_count*4, stack_allocator)
			model.readLines(props['in_lines1'], lines1, None, progress)

			# --- READ2 ---
			lines2 = None
			if self._props['in_lines2_enabled']:
				progress.setCurrentTask(Tasks.READ2)
				max_line_count = model.rowCount(props['in_lines2'])
				lines2 = Vector(ctypes.c_double, max_line_count*4, stack_allocator)
				model.readLines(props['in_lines2'], lines2, None, progress)

			# Unlinks
			unlinks = None
			if self._props['in_unlinks_enabled']:
				unlinks_table = props['in_unlinks']
				max_count = model.rowCount(unlinks_table)
				unlinks = Vector(ctypes.c_double, max_count*2, stack_allocator)
				model.readPoints(point_table, unlinks, None, progress)

			# --- ANALYSIS ---
			progress.setCurrentTask(Tasks.ANALYSIS)
			(res, algo) = pstalgo.CreateJunctions(
				lines1, None,
				lines2, None,
				unlinks = unlinks,
				progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(progress))

			def id_gen(count):
				i = 1
				while i <= count:
					yield i
					i = i + 1

			columns = [('id', 'integer', id_gen(res.m_PointCount))]

			def point_gen(coords, count):
				for i in range(count):
					yield model.createPoint(coords[i*2], coords[i*2+1])

			# --- WRITE_---
			progress.setCurrentTask(Tasks.WRITE)
			self._model.createTable(
				props['in_lines1'] + '_junctions',
				model.coordinateReferenceSystem(props['in_lines1']),
				columns,
				point_gen(res.m_PointCoords, res.m_PointCount),
				res.m_PointCount,
				progress,
				geo_type=GeometryType.POINT)

		finally:
			stack_allocator.restore(initial_alloc_state)
			if algo is not None:
				pstalgo.Free(algo)