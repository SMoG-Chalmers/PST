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
import ctypes
from .base import BaseAnalysis
from .columnnaming import ColName, GenColName
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildAxialGraph, RadiiFromSettings

class ReachAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):

		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector

		origins_enabled = self._props['in_origins_enabled']

		radii_list = RadiiFromSettings(pstalgo, self._props).split()

		analysis_count = len(radii_list)

		# Tasks
		class Tasks(object):
			BUILD_GRAPH = 1
			READ_POINTS = 2
			ANALYSIS = 3
			WRITE_RESULTS = 4
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.BUILD_GRAPH, 1, None)
		if origins_enabled:
			progress.addTask(Tasks.READ_POINTS, 1, "Reading points")
		progress.addTask(Tasks.ANALYSIS, 10*analysis_count, None)

		initial_alloc_state = stack_allocator.state()

		graph = None

		try:
			# Graph
			progress.setCurrentTask(Tasks.BUILD_GRAPH)
			(graph, line_rows, _) = BuildAxialGraph(
				self._model,
				pstalgo,
				stack_allocator,
				self._props['in_network'],
				self._props['in_unlinks'] if self._props['in_unlinks_enabled'] else None,
				None,
				progress)
			line_count = line_rows.size()

			# Origins
			origins = None
			origin_rows = None
			if origins_enabled:
				progress.setCurrentTask(Tasks.READ_POINTS)
				max_origin_count = self._model.rowCount(self._props['in_origins'])
				origin_rows = Vector(ctypes.c_uint, max_origin_count, stack_allocator)
				origins = Vector(ctypes.c_double, max_origin_count*2, stack_allocator)
				self._model.readPoints(self._props['in_origins'], origins, origin_rows, progress)

			# Allocate output arrays
			output_count = origin_rows.size() if origins_enabled else line_count
			reached_count =  Vector(ctypes.c_uint,  output_count, stack_allocator, output_count) if self._props['calc_count']  else None
			reached_length = Vector(ctypes.c_float, output_count, stack_allocator, output_count) if self._props['calc_length'] else None
			reached_area =   Vector(ctypes.c_float, output_count, stack_allocator, output_count) if self._props['calc_area']   else None

			# Radius
			progress.setCurrentTask(Tasks.ANALYSIS)
			analysis_progress = TaskSplitProgressDelegate(analysis_count, "Performing analysis", progress)
			for radii in radii_list:
				# Analysis sub progress
				analysis_sub_progress = MultiTaskProgressDelegate(analysis_progress)
				analysis_sub_progress.addTask(Tasks.ANALYSIS, 1, "Calculating")
				analysis_sub_progress.addTask(Tasks.WRITE_RESULTS, 0, "Writing line results")
				# Analysis
				analysis_sub_progress.setCurrentTask(Tasks.ANALYSIS)
				pstalgo.Reach(
					graph_handle = graph,
					radius = radii,
					origin_points = origins,
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_sub_progress),
					out_reached_count = reached_count,
					out_reached_length = reached_length,
					out_reached_area = reached_area)
				# Area unit conversion
				area_unit = self._props['area_unit']
				if reached_area is not None:
					if area_unit != 'm2':
						factor = {'km2' : 0.000001, 'ha' : 0.0001}[area_unit]
						ptr = reached_area.ptr()
						for i in range(reached_area.size()):
							ptr[i] = ptr[i] * factor

				# Output columns
				columns = []
				if reached_count is not None:
					columns.append((GenColName(ColName.REACH, radii=radii, extra=ColName.EXTRA_NODE_COUNT), 'integer', reached_count.values()))
				if reached_length is not None:
					columns.append((GenColName(ColName.REACH, radii=radii, extra=ColName.EXTRA_LENGTH), 'float', reached_length.values()))
				if reached_area is not None:
					columns.append((GenColName(ColName.REACH, radii=radii, extra=ColName.EXTRA_AREA_CONVEX_HULL, unit=ColNameUnitFromPropAreaUnit(area_unit)), 'float', reached_area.values()))
				# Write
				analysis_sub_progress.setCurrentTask(Tasks.WRITE_RESULTS)
				self._model.writeColumns(
					self._props['in_origins'] if origins_enabled else self._props['in_network'],
					origin_rows if origins_enabled else line_rows,
					columns,
					analysis_sub_progress)
				# Progress
				analysis_progress.nextTask()

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph:
				pstalgo.FreeGraph(graph)
				graph = None

		delegate.setStatus("Reach done")
		delegate.setProgress(1)


def ColNameUnitFromPropAreaUnit(unit):
	if 'm2' == unit:
		return ColName.UNIT_SQUARE_METER
	if 'km2' == unit:
		return ColName.UNIT_SQUARE_KILOMETER
	if 'ha' == unit:
		return ColName.UNIT_HECTARE
	raise Exception("Unsupported area unit '%s'" % unit)