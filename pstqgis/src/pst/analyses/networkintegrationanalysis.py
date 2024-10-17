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
import ctypes
from ..model import GeometryType
from .base import BaseAnalysis
from .columnnaming import ColName, GenColName
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildAxialGraph, RadiiFromSettings, MeanDepthGen, PointGen


class NetworkIntegrationAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):

		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector

		junctions_enabled = self._props['output_at_junctions']

		#radii_list = RadiiFromSettings(pstalgo, self._props).split()
		radii_list = [
			pstalgo.Radii(steps = self._props['rad_steps'] if self._props.get('rad_steps_enabled') else None)
		]

		# Tasks
		class Tasks(object):
			BUILD_GRAPH = 1
			ANALYSIS = 2
			WRITE_LINE_RESULTS = 3
			WRITE_JUNCTION_RESULTS = 4

		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.BUILD_GRAPH, 1, None)
		progress.addTask(Tasks.ANALYSIS, 2*len(radii_list), None)

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

			# Allocate output arrays
			scores =       Vector(ctypes.c_float, line_count, stack_allocator, line_count)
			total_counts = Vector(ctypes.c_uint,  line_count, stack_allocator, line_count) if self._props['output_N'] or self._props['output_MD'] else None
			total_depths = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if self._props['output_TD'] or self._props['output_MD'] else None

			# Junction output
			junction_count = pstalgo.GetGraphInfo(graph).m_CrossingCount if junctions_enabled else 0
			junction_coords = Vector(ctypes.c_double, junction_count*2, stack_allocator, junction_count*2) if junctions_enabled else None
			junction_scores = Vector(ctypes.c_float, junction_count, stack_allocator, junction_count) if junctions_enabled else None

			progress.setCurrentTask(Tasks.ANALYSIS)

			radii_progress = TaskSplitProgressDelegate(len(radii_list), "Performing analysis", progress)
			for radii in radii_list:

				radii_sub_progress = MultiTaskProgressDelegate(radii_progress)
				radii_sub_progress.addTask(Tasks.ANALYSIS, 3, "Calculating")
				radii_sub_progress.addTask(Tasks.WRITE_LINE_RESULTS, 1, "Writing line results")
				if junctions_enabled:
					radii_sub_progress.addTask(Tasks.WRITE_JUNCTION_RESULTS, 1, "Writing junction results")

				# Analysis
				radii_sub_progress.setCurrentTask(Tasks.ANALYSIS)
				pstalgo.NetworkIntegration(
					graph_handle = graph,
					radius = radii,
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(radii_sub_progress),
					out_junction_coords = junction_coords,
					out_junction_scores = junction_scores,
					out_line_integration = scores,
					out_line_node_count = total_counts,
					out_line_total_depth = total_depths)

				# Line outputs
				radii_sub_progress.setCurrentTask(Tasks.WRITE_LINE_RESULTS)
				columns = []
				if scores is not None:
					columns.append((GenColName(ColName.NETWORK_INTEGRATION, radii=radii), 'float', scores.values()))
				if total_counts is not None:
					columns.append((GenColName(ColName.NETWORK_INTEGRATION, radii=radii, extra=ColName.EXTRA_NODE_COUNT), 'integer', total_counts.values()))
				if total_depths is not None:
					columns.append((GenColName(ColName.NETWORK_INTEGRATION, radii=radii, extra=ColName.EXTRA_TOTAL_DEPTH), 'float', total_depths.values()))
				if self._props['output_MD']:
					columns.append((GenColName(ColName.NETWORK_INTEGRATION, radii=radii, extra=ColName.EXTRA_MEAN_DEPTH), 'float', MeanDepthGen(total_depths, total_counts)))
				self._model.writeColumns(self._props['in_network'], line_rows, columns, radii_sub_progress)

				# Junction output
				if junctions_enabled:
					radii_sub_progress.setCurrentTask(Tasks.WRITE_JUNCTION_RESULTS)
					columns = []
					columns.append((column_base_name, 'float', junction_scores.values()))
					self._model.createTable(
						self._props['in_network'] + '_junctions',
						self._model.coordinateReferenceSystem(self._props['in_network']),
						columns,
						PointGen(junction_coords, self._model),
						junction_count,
						radii_sub_progress,
						geo_type=GeometryType.POINT)

				radii_progress.nextTask()

			# Free graph
			pstalgo.FreeGraph(graph)
			graph = None

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph:
				pstalgo.FreeGraph(graph)
				graph = None

		delegate.setStatus("Network Integration done")
		delegate.setProgress(1)