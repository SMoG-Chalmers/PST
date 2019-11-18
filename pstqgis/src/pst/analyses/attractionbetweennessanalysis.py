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

from builtins import object
import ctypes
from .base import BaseAnalysis
from .columnnaming import ColName, GenColName
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildAxialGraph, DistanceTypesFromSettings, RadiiFromSettings, MeanDepthGen
from .attractiondistanceanalysis import AttractionValueGen, GenerateAttractionDataName, ReadAttractionPoints


class AttractionBetweennessAnalysis(BaseAnalysis):
	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):

		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props
		model = self._model

		radii_list = RadiiFromSettings(pstalgo, self._props).split()

		# Distance modes
		distance_modes = DistanceTypesFromSettings(pstalgo, props)

		def GenerateColumnName(attr_name, distance_mode, radii, norm):
			return GenColName(ColName.ATTRACTION_BETWEENNESS, weight=attr_name, pst_distance_type=distance_mode, radii=radii, normalization=norm)

		# Attraction columns (None = use value 1 for every attraction)
		attraction_columns = props['dest_data'] if props['dest_data_enabled'] else [None]

		# Number of analyses
		analysis_count = len(attraction_columns) * len(radii_list) * len(distance_modes)

		# Tasks
		class Tasks(object):
			READ_ATTRACTIONS = 1
			BUILD_GRAPH = 2
			ANALYSIS = 3
			WRITE_RESULTS = 4
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.READ_ATTRACTIONS, 1, None)
		progress.addTask(Tasks.BUILD_GRAPH, 1, None)
		progress.addTask(Tasks.ANALYSIS, 10*analysis_count, None)

		initial_alloc_state = stack_allocator.state()

		graph = None

		try:
			# Attraction points
			progress.setCurrentTask(Tasks.READ_ATTRACTIONS)
			(attr_table, attr_rows, attr_points, attr_points_per_polygon) = ReadAttractionPoints(model, pstalgo, stack_allocator, props, progress)

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
			scores = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
			scores_std = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if props['norm_standard'] else None

			# Analyses
			attr_values = None
			progress.setCurrentTask(Tasks.ANALYSIS)
			analysis_progress = TaskSplitProgressDelegate(analysis_count, "Performing analysis", progress)
			for attr_col in attraction_columns:
				# Attraction values
				if attr_col is not None:
					if attr_values is None:
						attr_values = Vector(ctypes.c_float, attr_rows.size(), stack_allocator)
					attr_values.clear()
					for value in AttractionValueGen(model, attr_table, attr_rows, [attr_col], progress):
						attr_values.append(value)
				attr_title = GenerateAttractionDataName(props['in_destinations'], attr_col, props['dest_name'])
				for radii in radii_list:
					for distance_mode in distance_modes:
						# Analysis sub progress
						analysis_sub_progress = MultiTaskProgressDelegate(analysis_progress)
						analysis_sub_progress.addTask(Tasks.ANALYSIS, 1, "Calculating")
						analysis_sub_progress.addTask(Tasks.WRITE_RESULTS, 0, "Writing line results")
						# Analysis
						analysis_sub_progress.setCurrentTask(Tasks.ANALYSIS)
						pstalgo.SegmentBetweenness(
							graph_handle = graph,
							distance_type = distance_mode,
							radius = radii,
							weights = None if attr_col is None else attr_values,
							attraction_points = attr_points,
							progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_sub_progress),
							out_betweenness = scores)
						# Write
						analysis_sub_progress.setCurrentTask(Tasks.WRITE_RESULTS)
						columns = []
						if props['norm_none']:
							columns.append((GenerateColumnName(attr_title, distance_mode, radii, ColName.NORM_NONE), 'float', scores.values()))
						if props['norm_standard']:
							pstalgo.StandardNormalize(scores, scores.size(), scores_std)
							columns.append((GenerateColumnName(attr_title, distance_mode, radii, ColName.NORM_STANDARD), 'float', scores_std.values()))
						self._model.writeColumns(self._props['in_network'], line_rows, columns, analysis_sub_progress)
						# Progress
						analysis_progress.nextTask()

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph:
				pstalgo.FreeGraph(graph)

		delegate.setStatus("Attraction Betweenness done")
		delegate.setProgress(1)