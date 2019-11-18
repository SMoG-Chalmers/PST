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

from builtins import str
from builtins import range
from builtins import object
import array, ctypes
from .base import BaseAnalysis
from .memory import stack_allocator
from .utils import BuildSegmentGraph, MultiTaskProgressDelegate

PALETTE = [(114,120,203),(211,82,56),(97,182,94),(188,174,66),(184,89,190),(76,179,192),(191,123,68),(205,70,110),(98,124,59),(191,110,148)]

class SegmentGroupingAnalysis(BaseAnalysis):
	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):
		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props
		model = self._model

		def GenerateName(what, angle_threshold, split):
			title = 'seggrp_' + what + '_' + str(int(angle_threshold))
			if split:
				title += "_split"
			return title

		# Tasks
		class Tasks(object):
			GRAPH = 1
			ANALYSIS = 2
			WRITE = 3
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.GRAPH, 5, None)
		progress.addTask(Tasks.ANALYSIS, 1, "Creating segment groups")
		progress.addTask(Tasks.WRITE, 5, "Writing results")

		initial_alloc_state = stack_allocator.state()
		graph = None

		try:
			# Graph
			progress.setCurrentTask(Tasks.GRAPH)
			(graph, line_rows) = BuildSegmentGraph(self._model, pstalgo, stack_allocator, props['in_network'], progress)
			line_count = line_rows.size()

			# Allocate output arrays
			group_ids = Vector(ctypes.c_uint,  line_count, stack_allocator, line_count)
			colors = Vector(ctypes.c_uint, line_count, stack_allocator, line_count) if props['generate_colors'] else None

			# --- ANALYSIS ---
			progress.setCurrentTask(Tasks.ANALYSIS)
			(group_count, color_count) = pstalgo.SegmentGrouping(
				segment_graph = graph,
				angle_threshold = props['angle_threshold'],
				split_at_junctions = props['split_at_junctions'],
				out_group_id_per_line = group_ids,
				out_color_per_line = colors,
				progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(progress))

			columns = []
			if group_ids is not None:
				columns.append((GenerateName("id", props['angle_threshold'], props['split_at_junctions']), 'integer', group_ids.values()))
			if colors is not None:
				color_column_name = GenerateName("color", props['angle_threshold'], props['split_at_junctions'])
				columns.append((color_column_name, 'integer', colors.values()))

			# --- WRITE_RESULTS ---
			progress.setCurrentTask(Tasks.WRITE)
			self._model.writeColumns(props['in_network'], line_rows, columns, progress)

			# Color layer
			if props['apply_colors']:
				assert(colors is not None)
				progress.setStatus('Coloring')
				ranges = []
				for color_index in range(color_count):
					ranges.append((str(color_index), PALETTE[color_index%len(PALETTE)], color_index))
				model.makeThematic(props['in_network'], color_column_name, ranges)

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph:
				pstalgo.FreeSegmentGraph(graph)
				graph = None

		delegate.setStatus("Segment grouping done")
		delegate.setProgress(1)