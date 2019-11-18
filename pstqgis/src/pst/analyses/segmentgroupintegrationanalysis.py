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
import ctypes
from .base import BaseAnalysis
from .columnnaming import ColName, GenColName
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildSegmentGraph, RadiiFromSettings, MeanDepthGen


class SegmentGroupIntegrationAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):

		import pstalgo  # Do it here when it is needed instead of on plugin load
		props = self._props
		Vector = pstalgo.Vector

		radii_list = RadiiFromSettings(pstalgo, self._props).split()

		# Tasks
		class Tasks(object):
			BUILD_SEGMENT_GRAPH = 1
			ANALYSIS = 2
			WRITE_RESULTS = 3

		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.BUILD_SEGMENT_GRAPH, 1, None)
		progress.addTask(Tasks.ANALYSIS, 10*len(radii_list), None)

		initial_alloc_state = stack_allocator.state()

		segment_graph = None
		group_graph = None

		try:
			# Segment Graph
			progress.setCurrentTask(Tasks.BUILD_SEGMENT_GRAPH)
			(segment_graph, segment_rows) = BuildSegmentGraph(self._model, pstalgo, stack_allocator, self._props['in_network'], progress)
			segment_count = segment_rows.size()

			# Generate groups
			progress.setStatus("Generating groups")
			group_per_segment = Vector(ctypes.c_uint, segment_count, stack_allocator, segment_count)
			group_count = pstalgo.SegmentGrouping(
				segment_graph = segment_graph,
				angle_threshold = props['angle_threshold'],
				split_at_junctions = props['split_at_junctions'],
				out_group_id_per_line = group_per_segment)[0]

			# Create group graph
			progress.setStatus("Creating segment group graph")
			group_graph = pstalgo.CreateSegmentGroupGraph(segment_graph, group_per_segment, group_count)

			# Allocate output arrays
			scores_grp =       Vector(ctypes.c_float, group_count, stack_allocator, group_count)
			total_counts_grp = Vector(ctypes.c_uint,  group_count, stack_allocator, group_count) if self._props['output_N'] or self._props['output_MD'] else None
			total_depths_grp = Vector(ctypes.c_float, group_count, stack_allocator, group_count) if self._props['output_TD'] or self._props['output_MD'] else None
			scores_seg =       Vector(ctypes.c_float, segment_count, stack_allocator, segment_count)
			total_counts_seg = Vector(ctypes.c_uint,  segment_count, stack_allocator, segment_count) if self._props['output_N'] or self._props['output_MD'] else None
			total_depths_seg = Vector(ctypes.c_float, segment_count, stack_allocator, segment_count) if self._props['output_TD'] or self._props['output_MD'] else None

			progress.setCurrentTask(Tasks.ANALYSIS)

			radii_progress = TaskSplitProgressDelegate(len(radii_list), "Performing analysis", progress)
			for radii in radii_list:

				radii_sub_progress = MultiTaskProgressDelegate(radii_progress)
				radii_sub_progress.addTask(Tasks.ANALYSIS, 5, "Calculating")
				radii_sub_progress.addTask(Tasks.WRITE_RESULTS, 1, "Writing results")

				# Analysis
				radii_sub_progress.setCurrentTask(Tasks.ANALYSIS)
				pstalgo.SegmentGroupIntegration(
					group_graph = group_graph,
					radii = radii,
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(radii_sub_progress),
					out_integration = scores_grp,
					out_node_counts = total_counts_grp,
					out_total_depths = total_depths_grp)

				# Map outputs from group to segments
				if scores_grp is not None:
					MapGroupValues(scores_grp, group_per_segment, scores_seg)
				if total_counts_grp is not None:
					MapGroupValues(total_counts_grp, group_per_segment, total_counts_seg)
				if total_depths_grp is not None:
					MapGroupValues(total_depths_grp, group_per_segment, total_depths_seg)

				# Line outputs
				radii_sub_progress.setCurrentTask(Tasks.WRITE_RESULTS)
				base_name = '%s_%d%s' % (ColName.SEGMENT_GROUP_INTEGRATION, int(round(props['angle_threshold'])), '_sp' if props['split_at_junctions'] else '')
				columns = []
				if scores_seg is not None:
					columns.append((GenColName(base_name, radii=radii), 'float', scores_seg.values()))
				if total_counts_seg is not None:
					columns.append((GenColName(base_name, radii=radii, extra=ColName.EXTRA_NODE_COUNT), 'integer', total_counts_seg.values()))
				if total_depths_seg is not None:
					columns.append((GenColName(base_name, radii=radii, extra=ColName.EXTRA_TOTAL_DEPTH), 'float', total_depths_seg.values()))
				if self._props['output_MD']:
					columns.append((GenColName(base_name, radii=radii, extra=ColName.EXTRA_MEAN_DEPTH), 'float', MeanDepthGen(total_depths_seg, total_counts_seg)))
				self._model.writeColumns(self._props['in_network'], segment_rows, columns, radii_sub_progress)

				radii_progress.nextTask()

		finally:
			stack_allocator.restore(initial_alloc_state)
			if group_graph:
				pstalgo.FreeSegmentGroupGraph(group_graph)
				group_graph = None
			if segment_graph:
				pstalgo.FreeSegmentGraph(segment_graph)
				segment_graph = None

		delegate.setStatus("Segment Group Integration done")
		delegate.setProgress(1)


def MapGroupValues(group_values, group_per_segment, segment_values):
	assert(group_per_segment.size() == segment_values.size())
	for i in range(segment_values.size()):
		segment_values.set(i, group_values.at(group_per_segment.at(i)))