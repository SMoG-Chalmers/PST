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

from builtins import range
from builtins import object
import array, ctypes
from ..model import GeometryType
from .base import BaseAnalysis
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate


class Tasks(object):
	READ_LINES = 1
	ANALYSIS = 2
	WRITE_RESULTS = 3


class CreateSegmentMapAnalysis(BaseAnalysis):

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
		progress.addTask(Tasks.READ_LINES, 5,    "Reading polylines")
		progress.addTask(Tasks.ANALYSIS, 1,      None)
		progress.addTask(Tasks.WRITE_RESULTS, 5, "Writing results")

		# --- READ_LINES ---
		progress.setCurrentTask(Tasks.READ_LINES)
		(coords, polys) = model.readPolylines(props['in_network'], progress)

		initial_alloc_state = stack_allocator.state()
		algo = None

		try:
			# Unlinks
			unlinks = None
			if props['in_unlinks_enabled']:
				unlinks_table = props['in_unlinks']
				max_count = model.rowCount(unlinks_table)
				unlinks = Vector(ctypes.c_double, max_count*2, stack_allocator)
				model.readPoints(unlinks_table, unlinks, None, progress)

			# --- ANALYSIS ---
			progress.setCurrentTask(Tasks.ANALYSIS)
			(res, algo) = pstalgo.CreateSegmentMap(
				poly_coords = coords,
				poly_sections = polys,
				unlinks = unlinks,
				progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(progress),
				snap = props['trim_snap'],
				tail = props['trim_tail'],
				deviation = props['trim_coldev'],
				extrude = props['trim_snap'])

			def id_gen(count):
				i = 1
				while i <= count:
					yield i
					i = i + 1

			columns = [('id', 'integer', id_gen(res.m_SegmentCount))]

			if props['copy_column_enabled']:
				copy_column_name = props['copy_column_in']
				extra_column_name = props['copy_column_out']
				extra_column_type = model.columnType(props['in_network'], copy_column_name)
				if extra_column_type is None:
					raise Exception("Unsupported copy column data type")

				# Create copy-column repeat counts
				segments = res.m_Segments
				poly_count = len(polys)
				repeat_count = array.array('I', [0])*poly_count
				for i in range(res.m_SegmentCount):
					poly_index = segments[i*3+2]
					repeat_count[poly_index] = repeat_count[poly_index] + 1

				def repeat_iter(value_iter, repeat_counts):
					for reps in repeat_counts:
						value = next(value_iter)
						for i in range(reps):
							yield value

				columns.append((extra_column_name, extra_column_type, repeat_iter(model.values(props['in_network'], copy_column_name), repeat_count)))

			def line_gen(coords, segments, count):
				for i in range(count):
					p0 = segments[i*3]
					p1 = segments[i*3+1]
					yield model.createLine(coords[p0*2], coords[p0*2+1], coords[p1*2], coords[p1*2+1])

			# --- WRITE_RESULTS ---
			progress.setCurrentTask(Tasks.WRITE_RESULTS)
			model.createTable(
				props['in_network'] + '_segments',
				model.coordinateReferenceSystem(props['in_network']),
				columns,
				line_gen(res.m_SegmentCoords, res.m_Segments, res.m_SegmentCount),
				res.m_SegmentCount,
				progress,
				geo_type=GeometryType.LINE)

		finally:
			stack_allocator.restore(initial_alloc_state)
			if algo is not None:
				pstalgo.Free(algo)