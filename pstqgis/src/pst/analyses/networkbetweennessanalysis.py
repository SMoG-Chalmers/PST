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

from __future__ import print_function
from builtins import object
import ctypes
from .base import BaseAnalysis
from .columnnaming import ColName, GenColName
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildAxialGraph, DistanceTypesFromSettings, RadiiFromSettings, MeanDepthGen


class NetworkBetweennessAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):

		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props

		radii_list = RadiiFromSettings(pstalgo, self._props).split()

		# Distance modes
		distance_modes = DistanceTypesFromSettings(pstalgo, props)

		# Weight modes
		class WeightMode(object):
			NONE = 0
			LENGTH = 1
		weight_modes = []
		if props['weight_none']:
			weight_modes.append(WeightMode.NONE)
		if props['weight_length']:
			weight_modes.append(WeightMode.LENGTH)
		if props['weight_data']:
			for name in props['weight_data_cols']:
				weight_modes.append(name)

		def GenerateScoreColumnName(distance_mode, weight, radii, norm):
			if weight == WeightMode.NONE:
				weight = ColName.WEIGHT_NONE
			elif weight == WeightMode.LENGTH:
				weight = ColName.WEIGHT_LENGTH
			return GenColName(ColName.NETWORK_BETWEENNESS, pst_distance_type=distance_mode, weight=weight, radii=radii, normalization=norm)

		def GenerateStatColumnName(stat, distance_mode, radii):
			name = GenColName(ColName.NETWORK_BETWEENNESS, pst_distance_type=distance_mode, radii=radii, extra=stat)
			print(name)
			return name

		# Number of analyses
		analysis_count = len(radii_list) * len(distance_modes) * len(weight_modes)

		# Tasks
		class Tasks(object):
			BUILD_GRAPH = 1
			ANALYSIS = 2
			WRITE_RESULTS = 3
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.BUILD_GRAPH, 1, None)
		progress.addTask(Tasks.ANALYSIS, 5*analysis_count, None)

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
			weights        = None
			scores         = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
			scores_norm    = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if props['norm_normalization'] else None
			scores_std     = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if props['norm_standard'] else None
			scores_syntax  = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if props['norm_syntax'] else None
			total_counts   = Vector(ctypes.c_uint,  line_count, stack_allocator, line_count)
			total_depths   = Vector(ctypes.c_float, line_count, stack_allocator, line_count)

			output_N  = (False != props['output_N'])
			output_TD = (False != props['output_TD'])
			output_MD = (False != props['output_MD'])

			progress.setCurrentTask(Tasks.ANALYSIS)
			analysis_progress = TaskSplitProgressDelegate(analysis_count, "Performing analysis", progress)
			for weight_mode in weight_modes:

				# Get weights
				if weight_mode == WeightMode.NONE:
					pass
				elif weight_mode == WeightMode.LENGTH:
					if weights is  None:
						weights = Vector(ctypes.c_float, line_count, stack_allocator)
					weights.resize(line_count)
					pstalgo.GetGraphLineLengths(graph, weights)
				else:
					if weights is  None:
						weights = Vector(ctypes.c_float, line_count, stack_allocator)
					column_name = weight_mode
					analysis_progress.setStatus("Reading weight data '%s'"%column_name)
					weights.resize(0)
					self._model.readValues(self._props['in_network'], column_name, line_rows, weights)

				# These metrics are independent of weight mode, and should therefore only be outputted for first weight mode
				if weight_mode != weight_modes[0]:
					output_N  = False
					output_TD = False
					output_MD = False

				for radii in radii_list:

					for distance_mode in distance_modes:

						# Analysis sub progress
						analysis_sub_progress = MultiTaskProgressDelegate(analysis_progress)
						analysis_sub_progress.addTask(Tasks.ANALYSIS, 3, "Calculating")
						analysis_sub_progress.addTask(Tasks.WRITE_RESULTS, 1, "Writing line results")

						# Analysis
						analysis_sub_progress.setCurrentTask(Tasks.ANALYSIS)
						pstalgo.SegmentBetweenness(
							graph_handle = graph,
							distance_type = distance_mode,
							radius = radii,
							weights = None if weight_mode == WeightMode.NONE else weights,
							attraction_points = None,
							progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_sub_progress),
							out_betweenness = scores,
							out_node_count = total_counts,
							out_total_depth = total_depths)

						# Output
						analysis_sub_progress.setCurrentTask(Tasks.WRITE_RESULTS)
						columns = []
						# No normalization
						if props['norm_none']:
							columns.append((GenerateScoreColumnName(distance_mode, weight_mode, radii, ColName.NORM_NONE), 'float', scores.values()))
						# Normalization
						if scores_norm is not None:
							pstalgo.BetweennessNormalize(scores, total_counts, scores.size(), scores_norm)
							columns.append((GenerateScoreColumnName(distance_mode, weight_mode, radii, ColName.NORM_TURNER), 'float', scores_norm.values()))
						# Standard normalization
						if scores_std is not None:
							pstalgo.StandardNormalize(scores, scores.size(), scores_std)
							columns.append((GenerateScoreColumnName(distance_mode, weight_mode, radii, ColName.NORM_STANDARD), 'float', scores_std.values()))
						# Syntax normalization
						if scores_syntax is not None:
							pstalgo.BetweennessSyntaxNormalize(scores, total_depths, scores.size(), scores_syntax)
							columns.append((GenerateScoreColumnName(distance_mode, weight_mode, radii, ColName.NORM_SYNTAX_NACH), 'float', scores_syntax.values()))
						# Node counts
						if output_N:
							columns.append((GenerateStatColumnName(ColName.EXTRA_NODE_COUNT,  distance_mode, radii), 'integer',  total_counts.values()))
						# Total depths
						if output_TD:
							columns.append((GenerateStatColumnName(ColName.EXTRA_TOTAL_DEPTH, distance_mode, radii), 'float', total_depths.values()))
						# Mean depths
						if output_MD:
							columns.append((GenerateStatColumnName(ColName.EXTRA_MEAN_DEPTH,  distance_mode, radii), 'float', MeanDepthGen(total_depths, total_counts)))

						# Write
						self._model.writeColumns(self._props['in_network'], line_rows, columns, analysis_sub_progress)

						analysis_progress.nextTask()

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph:
				pstalgo.FreeGraph(graph)

		delegate.setStatus("Network Betweenness done")
		delegate.setProgress(1)