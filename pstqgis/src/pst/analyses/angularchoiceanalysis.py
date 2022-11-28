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
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildSegmentGraph, RadiiFromSettings, MeanDepthGen


class AngularChoiceAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):

		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props

		def GenerateScoreColumnName(length_weight_enabled, radii, norm):
			return GenColName(
				ColName.ANGULAR_CHOICE,
				radii = radii,
				weight = ColName.WEIGHT_LENGTH if length_weight_enabled else ColName.WEIGHT_NONE,
				normalization = norm)

		def GenerateStatColumnName(stat, radii):
			return GenColName(ColName.ANGULAR_CHOICE, radii = radii, extra = stat)

		# Number of analyses
		analysis_count = 0
		if props['weight_none']:
			analysis_count += 1
		if props['weight_length']:
			analysis_count += 1
		assert(analysis_count > 0)

		# Tasks
		class Tasks(object):
			BUILD_GRAPH = 1
			ANALYSIS = 2
			WRITE_RESULTS = 3
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.BUILD_GRAPH, 1, None)
		progress.addTask(Tasks.ANALYSIS, 5*analysis_count, None)

		radii = RadiiFromSettings(pstalgo, self._props)

		initial_alloc_state = stack_allocator.state()

		graph = None

		try:
			# Graph
			progress.setCurrentTask(Tasks.BUILD_GRAPH)
			(graph, line_rows) = BuildSegmentGraph(self._model, pstalgo, stack_allocator, self._props['in_network'], progress)
			line_count = line_rows.size()

			# Allocate output arrays
			scores         = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
			scores_norm    = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if props['norm_normalization'] else None
			scores_std     = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if props['norm_standard'] else None
			scores_syntax  = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if props['norm_syntax'] else None
			total_counts   = Vector(ctypes.c_uint,  line_count, stack_allocator, line_count)
			total_depths   = Vector(ctypes.c_float, line_count, stack_allocator, line_count)
			total_depth_weights = Vector(ctypes.c_float, line_count, stack_allocator, line_count) if props['weight_length'] else None

			progress.setCurrentTask(Tasks.ANALYSIS)
			analysis_progress = TaskSplitProgressDelegate(analysis_count, "Performing analysis", progress)

			N_TD_MD_outputted = False

			if props['weight_length']:
				# Analysis sub progress
				analysis_sub_progress = MultiTaskProgressDelegate(analysis_progress)
				analysis_sub_progress.addTask(Tasks.ANALYSIS, 3, "Calculating")
				analysis_sub_progress.addTask(Tasks.WRITE_RESULTS, 1, "Writing line results")
				# Analysis
				analysis_sub_progress.setCurrentTask(Tasks.ANALYSIS)
				pstalgo.AngularChoice(
					graph_handle = graph,
					radius = radii,
					weigh_by_length = True,
					angle_threshold = props['angle_threshold'],
					angle_precision = props['angle_precision'],
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_sub_progress),
					out_choice = scores,
					out_node_count = total_counts,
					out_total_depth = total_depths,
					out_total_depth_weight = total_depth_weights)
				# Output
				columns = []
				if props['norm_none']:
					columns.append((GenerateScoreColumnName(True, radii, ColName.NORM_NONE), 'float', scores.values()))
				# Normalization
				if scores_norm is not None:
					pstalgo.AngularChoiceNormalize(scores, total_counts, scores.size(), scores_norm)
					columns.append((GenerateScoreColumnName(True, radii, ColName.NORM_TURNER), 'float', scores_norm.values()))
				# Standard normalization
				if scores_std is not None:
					pstalgo.StandardNormalize(scores, scores.size(), scores_std)
					columns.append((GenerateScoreColumnName(True, radii, ColName.NORM_STANDARD), 'float', scores_std.values()))
				# Syntax normalization
				if scores_syntax is not None:
					pstalgo.AngularChoiceSyntaxNormalize(scores, total_depth_weights, scores.size(), scores_syntax)
					columns.append((GenerateScoreColumnName(True, radii, ColName.NORM_SYNTAX_NACH), 'float', scores_syntax.values()))
				if not N_TD_MD_outputted:
					# N
					if props['output_N']:
						columns.append((GenerateStatColumnName(ColName.EXTRA_NODE_COUNT, radii), 'integer',  total_counts.values()))
					# TD
					if props['output_TD']:
						columns.append((GenerateStatColumnName(ColName.EXTRA_TOTAL_DEPTH, radii), 'float', total_depths.values()))
					# MD
					if props['output_MD']:
						columns.append((GenerateStatColumnName(ColName.EXTRA_MEAN_DEPTH, radii), 'float', MeanDepthGen(total_depths, total_counts)))
					N_TD_MD_outputted = True
				# Write
				analysis_sub_progress.setCurrentTask(Tasks.WRITE_RESULTS)
				self._model.writeColumns(self._props['in_network'], line_rows, columns, analysis_sub_progress)
				# Next task progress
				analysis_progress.nextTask()

			if props['weight_none']:
				# Analysis sub progress
				analysis_sub_progress = MultiTaskProgressDelegate(analysis_progress)
				analysis_sub_progress.addTask(Tasks.ANALYSIS, 3, "Calculating")
				analysis_sub_progress.addTask(Tasks.WRITE_RESULTS, 1, "Writing line results")
				# Analysis
				analysis_sub_progress.setCurrentTask(Tasks.ANALYSIS)
				pstalgo.AngularChoice(
					graph_handle = graph,
					radius = RadiiFromSettings(pstalgo, self._props),
					weigh_by_length = False,
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_sub_progress),
					out_choice = scores,
					out_node_count = total_counts,
					out_total_depth = total_depths)
				# Output
				columns = []
				if props['weight_none']:
					if props['norm_none']:
						columns.append((GenerateScoreColumnName(False, radii, ColName.NORM_NONE), 'float', scores.values()))
					# Normalization
					if scores_norm is not None:
						pstalgo.AngularChoiceNormalize(scores, total_counts, scores.size(), scores_norm)
						columns.append((GenerateScoreColumnName(False, radii, ColName.NORM_TURNER), 'float', scores_norm.values()))
					# Standard normalization
					if scores_std is not None:
						pstalgo.StandardNormalize(scores, scores.size(), scores_std)
						columns.append((GenerateScoreColumnName(False, radii, ColName.NORM_STANDARD), 'float', scores_std.values()))
					# Syntax normalization
					if scores_syntax is not None:
						pstalgo.AngularChoiceSyntaxNormalize(scores, total_depths, scores.size(), scores_syntax)
						columns.append((GenerateScoreColumnName(False, radii, ColName.NORM_SYNTAX_NACH), 'float', scores_syntax.values()))
				if not N_TD_MD_outputted:
					# N
					if props['output_N']:
						columns.append((GenerateStatColumnName(ColName.EXTRA_NODE_COUNT, radii), 'integer',  total_counts.values()))
					# TD
					if props['output_TD']:
						columns.append((GenerateStatColumnName(ColName.EXTRA_TOTAL_DEPTH, radii), 'float', total_depths.values()))
					# MD
					if props['output_MD']:
						columns.append((GenerateStatColumnName(ColName.EXTRA_MEAN_DEPTH, radii), 'float', MeanDepthGen(total_depths, total_counts)))
					N_TD_MD_outputted = True
				# Write
				analysis_sub_progress.setCurrentTask(Tasks.WRITE_RESULTS)
				self._model.writeColumns(self._props['in_network'], line_rows, columns, analysis_sub_progress)
				# Next task progress
				analysis_progress.nextTask()

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph:
				pstalgo.FreeSegmentGraph(graph)

		delegate.setStatus("Angular Choice done")
		delegate.setProgress(1)