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
from .base import BaseAnalysis
from .columnnaming import ColName, GenColName
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, BuildSegmentGraph, RadiiFromSettings, MeanDepthGen

class AngularIntegrationAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):

		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector

		props = self._props

		need_no_weight_analysis     = props['calc_no_weight']
		need_length_weight_analysis = props['calc_length_weight']

		def ScoreColName(radii, weight, norm):
			return GenColName(ColName.ANGULAR_INTEGRATION, radii=radii, weight=weight, normalization=norm)

		def ExtraColName(radii, extra):
			return GenColName(ColName.ANGULAR_INTEGRATION, radii=radii, extra=extra)

		# Tasks
		class Tasks(object):
			BUILD_GRAPH = 1
			LENGTH_WEIGHT_ANALYSIS = 2
			NO_WEIGHT_ANALYSIS = 3
			WRITE_RESULTS = 4
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.BUILD_GRAPH, 1, None)
		if need_length_weight_analysis:
			progress.addTask(Tasks.LENGTH_WEIGHT_ANALYSIS, 5, "Calculating length-weighted angular integration")
		if need_no_weight_analysis:
			progress.addTask(Tasks.NO_WEIGHT_ANALYSIS, 5, "Calculating angular integration")
		progress.addTask(Tasks.WRITE_RESULTS, 1, "Writing results")

		initial_alloc_state = stack_allocator.state()

		graph = None

		try:
			# Graph
			progress.setCurrentTask(Tasks.BUILD_GRAPH)
			(graph, line_rows) = BuildSegmentGraph(self._model, pstalgo, stack_allocator, self._props['in_network'], progress)
			line_count = line_rows.size()

			# Allocate output arrays
			total_counts = Vector(ctypes.c_uint,  line_count, stack_allocator, line_count)
			total_depths = Vector(ctypes.c_float, line_count, stack_allocator, line_count)

			# Radius
			radii = RadiiFromSettings(pstalgo, self._props)

			columns = []

			N_TD_MD_outputted = False

			# Length-weighted analysis
			if need_length_weight_analysis:
				progress.setCurrentTask(Tasks.LENGTH_WEIGHT_ANALYSIS)
				total_weights = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
				total_depth_weights = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
				pstalgo.AngularIntegration(
					graph_handle = graph,
					radius = radii,
					weigh_by_length = True,
					angle_threshold = props['angle_threshold'],
					angle_precision = props['angle_precision'],
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(progress),
					out_node_counts = total_counts,
					out_total_depths = total_depths,
					out_total_weights = total_weights,
					out_total_depth_weights = total_depth_weights)
				if props['norm_normalization']:
					scores_weighted = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
					pstalgo.AngularIntegrationNormalizeLengthWeight(total_weights, total_depth_weights, line_count, scores_weighted)
					columns.append((ScoreColName(radii, ColName.WEIGHT_LENGTH, ColName.NORM_NONE), 'float', scores_weighted.values()))
				if props['norm_syntax']:
					scores_weighted = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
					pstalgo.AngularIntegrationSyntaxNormalizeLengthWeight(total_weights, total_depth_weights, line_count, scores_weighted)
					columns.append((ScoreColName(radii, ColName.WEIGHT_LENGTH, ColName.NORM_SYNTAX_NAIN), 'float', scores_weighted.values()))
				if props['norm_hillier']:
					scores_weighted = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
					pstalgo.AngularIntegrationHillierNormalizeLengthWeight(total_weights, total_depth_weights, line_count, scores_weighted)
					columns.append((ScoreColName(radii, ColName.WEIGHT_LENGTH, ColName.NORM_HILLIER), 'float', scores_weighted.values()))
				if not N_TD_MD_outputted:
					if props['output_N']:
						columns.append((ExtraColName(radii, ColName.EXTRA_NODE_COUNT), 'integer', total_counts.values()))
					if props['output_TD']:
						columns.append((ExtraColName(radii, ColName.EXTRA_TOTAL_DEPTH), 'float', total_depths.values()))
					if props['output_MD']:
						columns.append((ExtraColName(radii, ColName.EXTRA_MEAN_DEPTH), 'float', MeanDepthGen(total_depths, total_counts)))
					N_TD_MD_outputted = True

			# Non-weighted analysis
			if need_no_weight_analysis:
				progress.setCurrentTask(Tasks.NO_WEIGHT_ANALYSIS)
				pstalgo.AngularIntegration(
					graph_handle = graph,
					radius = radii,
					weigh_by_length = False,
					angle_threshold = props['angle_threshold'],
					angle_precision = props['angle_precision'],
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(progress),
					out_node_counts = total_counts,
					out_total_depths = total_depths,
					out_total_weights = None,
					out_total_depth_weights = None)
				if props['norm_normalization']:
					scores = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
					pstalgo.AngularIntegrationNormalize(total_counts, total_depths, line_count, scores)
					columns.append((ScoreColName(radii, ColName.WEIGHT_NONE, ColName.NORM_NONE), 'float', scores.values()))
				if props['norm_syntax']:
					scores = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
					pstalgo.AngularIntegrationSyntaxNormalize(total_counts, total_depths, line_count, scores)
					columns.append((ScoreColName(radii, ColName.WEIGHT_NONE, ColName.NORM_SYNTAX_NAIN), 'float', scores.values()))
				if props['norm_hillier']:
					scores = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
					pstalgo.AngularIntegrationHillierNormalize(total_counts, total_depths, line_count, scores)
					columns.append((ScoreColName(radii, ColName.WEIGHT_NONE, ColName.NORM_HILLIER), 'float', scores.values()))
				if not N_TD_MD_outputted:
					if props['output_N']:
						columns.append((ExtraColName(radii, ColName.EXTRA_NODE_COUNT), 'integer', total_counts.values()))
					if props['output_TD']:
						columns.append((ExtraColName(radii, ColName.EXTRA_TOTAL_DEPTH), 'float', total_depths.values()))
					if props['output_MD']:
						columns.append((ExtraColName(radii, ColName.EXTRA_MEAN_DEPTH), 'float', MeanDepthGen(total_depths, total_counts)))
					N_TD_MD_outputted = True

			# Free graph
			pstalgo.FreeSegmentGraph(graph)
			graph = None

			# --- WRITE_RESULTS ---
			progress.setCurrentTask(Tasks.WRITE_RESULTS)
			self._model.writeColumns(
				self._props['in_network'],
				line_rows,
				columns,
				progress)

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph:
				pstalgo.FreeSegmentGraph(graph)
				graph = None

		delegate.setStatus("Reach done")
		delegate.setProgress(1)