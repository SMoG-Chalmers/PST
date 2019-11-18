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
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildAxialGraph, RadiiFromSettings
from .attractiondistanceanalysis import AttractionValueGen

class ODBetweennessAnalysis(BaseAnalysis):
	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):
		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props
		model = self._model

		origin_weights_column = props['in_origin_weights']
		network_table = props['in_network']
		destination_weights_column = props['in_destination_weights'] if props['in_destination_weights_enabled'] else None

		destination_mode = {
			"all"     : pstalgo.ODBDestinationMode.ALL_REACHABLE_DESTINATIONS,
			"closest" : pstalgo.ODBDestinationMode.CLOSEST_DESTINATION_ONLY,
		}[props["destination_mode"]]

		distance_type = {
			"walking" : pstalgo.DistanceType.WALKING,
			"angular" : pstalgo.DistanceType.ANGULAR,
		}[props["route_choice"]]

		# Radii
		radii_list = RadiiFromSettings(pstalgo, props).split()  # Only applicable in non-weight mode

		column_suffix =  props['column_suffix'] if props['column_suffix_enabled'] else None

		def GenerateColumnName(distance_type, radii, suffix=None):
			# NOTE: Distance mode will be implicit since it will always be the same as radius type
			name = GenColName(
				analysis = ColName.ODBETWEENNESS,
				pst_distance_type = distance_type,
				radii  = radii)
			if suffix is not None:
				name += '_' + suffix
			return name

		# Number of analyses
		analysis_count = len(radii_list)

		# Tasks
		class Tasks(object):
			READ_ORIGIN_POINTS = 1
			READ_ORIGIN_WEIGHTS = 2
			BUILD_GRAPH = 3
			READ_DESTINATION_WEIGHTS = 4
			ANALYSIS = 5
			WRITE_RESULTS = 6
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.READ_ORIGIN_POINTS, 1, None)
		progress.addTask(Tasks.READ_ORIGIN_WEIGHTS, 1, None)
		progress.addTask(Tasks.BUILD_GRAPH, 3, None)
		progress.addTask(Tasks.READ_DESTINATION_WEIGHTS, 1, None)
		progress.addTask(Tasks.ANALYSIS, 10*analysis_count, None)
		progress.addTask(Tasks.WRITE_RESULTS, 1, None)

		initial_alloc_state = stack_allocator.state()

		graph_handle = None

		try:
			# Origins
			progress.setCurrentTask(Tasks.READ_ORIGIN_POINTS)
			origins_table = props['in_origins']
			origin_max_count = model.rowCount(origins_table)
			origin_ids = Vector(ctypes.c_longlong, origin_max_count, stack_allocator)
			origin_points = Vector(ctypes.c_double, origin_max_count*2, stack_allocator)
			model.readPoints(origins_table, origin_points, origin_ids, progress)
			progress.setCurrentTask(Tasks.READ_ORIGIN_WEIGHTS)
			origin_weights = Vector(ctypes.c_float, origin_ids.size(), stack_allocator)
			for value in AttractionValueGen(model, origins_table, origin_ids, [origin_weights_column], progress):
				origin_weights.append(value)

			# Graph
			progress.setCurrentTask(Tasks.BUILD_GRAPH)
			destinations_table = props['in_destinations']
			(graph_handle, line_rows, destination_rows) = BuildAxialGraph(
				model,
				pstalgo,
				stack_allocator,
				network_table,
				self._props['in_unlinks'] if self._props['in_unlinks_enabled'] else None,
				destinations_table,
				progress)

			# Destination weights
			if destination_weights_column:
				progress.setCurrentTask(Tasks.READ_DESTINATION_WEIGHTS)
				destination_weights = Vector(ctypes.c_float, destination_rows.size(), stack_allocator)
				for value in AttractionValueGen(model, destinations_table, destination_rows, [destination_weights_column], progress):
					destination_weights.append(value)
			else:
				destination_weights = None

			output_count = line_rows.size()
			output_columns = []

			# Analyses
			progress.setCurrentTask(Tasks.ANALYSIS)
			analysis_progress = TaskSplitProgressDelegate(analysis_count, "Performing analysis", progress)
			for radii in radii_list:
				# Allocate output array
				scores = Vector(ctypes.c_float, output_count, stack_allocator, output_count)
				# Analysis
				pstalgo.ODBetweenness(
					graph_handle = graph_handle, 
					origin_points = origin_points,
					origin_weights = origin_weights,
					destination_weights = destination_weights,
					destination_mode = destination_mode, 
					distance_type = distance_type, 
					radius = radii, 
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_progress), 
					out_scores = scores)
				output_columns.append((GenerateColumnName(distance_type=distance_type, radii=radii, suffix=column_suffix), 'float', scores.values()))
				analysis_progress.nextTask()

			# Write
			progress.setCurrentTask(Tasks.WRITE_RESULTS)
			model.writeColumns(network_table, line_rows, output_columns, progress)

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph_handle:
				pstalgo.FreeGraph(graph_handle)

		delegate.setStatus("Origin-Destination Betweenness done")
		delegate.setProgress(1)