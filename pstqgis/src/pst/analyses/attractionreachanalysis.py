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
from ..model import GeometryType
from .base import BaseAnalysis
from .columnnaming import ColName, GenColName
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildAxialGraph, DistanceTypesFromSettings, RadiiFromSettings, PointGen
from .attractiondistanceanalysis import AttractionValueGen, GenerateAttractionDataName, OriginTypeFromProps, ReadAttractionPoints


class AttractionReachAnalysis(BaseAnalysis):
	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):
		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props
		model = self._model

		# Origin type
		origin_type = OriginTypeFromProps(pstalgo, props)

		# Weight mode enabled
		weight_enabled = props['weight_enabled']

		radii_list = RadiiFromSettings(pstalgo, props).split()  # Only applicable in non-weight mode

		# Distance modes - pairs of (distance type, radii), only applicable in weight mode
		distance_modes = []
		if props['dist_straight_enabled']:
			distance_modes.append((pstalgo.DistanceType.STRAIGHT, pstalgo.Radii(straight=props['dist_straight'])))
		if props['dist_walking_enabled']:
			distance_modes.append((pstalgo.DistanceType.WALKING, pstalgo.Radii(walking=props['dist_walking'])))
		if props['dist_steps_enabled']:
			distance_modes.append((pstalgo.DistanceType.STEPS, pstalgo.Radii(steps=props['dist_steps'])))
		if props['dist_angular_enabled']:
			distance_modes.append((pstalgo.DistanceType.ANGULAR, pstalgo.Radii(angular=props['dist_angular'])))
		if props['dist_axmeter_enabled']:
			distance_modes.append((pstalgo.DistanceType.AXMETER, pstalgo.Radii(axmeter=props['dist_axmeter'])))

		# Weight function
		weight_func = {
			'constant' : pstalgo.AttractionWeightFunction.CONSTANT,
			'pow'      : pstalgo.AttractionWeightFunction.POW,
			'curve'    : pstalgo.AttractionWeightFunction.CURVE,
			'divide'   : pstalgo.AttractionWeightFunction.DIVIDE,
		}[props['weight_func']]

		# Distribution function
		attraction_distribution_func = {
			'copy'   : pstalgo.AttractionDistributionFunc.COPY,
			'divide' : pstalgo.AttractionDistributionFunc.DIVIDE,
		}[props['dest_distribution_function']]

		# Collection function
		attraction_collection_func = {
			'avarage' : pstalgo.AttractionCollectionFunc.AVARAGE,
			'sum'     : pstalgo.AttractionCollectionFunc.SUM,
			'min'     : pstalgo.AttractionCollectionFunc.MIN,
			'max'     : pstalgo.AttractionCollectionFunc.MAX,
		}[props['origin_collection_function']]

		# Attraction columns (None = use value 1 for every attraction)
		attraction_columns = props['dest_data'] if props['dest_data_enabled'] else [None]

		# Number of analyses
		analysis_count = len(attraction_columns) * (len(distance_modes) if weight_enabled else len(radii_list))

		def GenerateColumnName(dest_name, radii, weight_func):
			# NOTE: Distance mode will be implicit since it will always be the same as radius type
			return GenColName(
				ColName.ATTRACTION_REACH,
				weight = dest_name,
				radii  = radii,
				decay  = ColName.DECAY_NONE if weight_func is None or weight_func == pstalgo.AttractionWeightFunction.CONSTANT else ColName.DECAY_FUNCTION)

		# Tasks
		class Tasks(object):
			READ_ATTRACTIONS = 1
			BUILD_GRAPH = 2
			ANALYSIS = 3
			WRITE_RESULTS = 4
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.READ_ATTRACTIONS, 1, None)
		progress.addTask(Tasks.BUILD_GRAPH, 1, None)
		progress.addTask(Tasks.ANALYSIS, 5*analysis_count, None)
		progress.addTask(Tasks.WRITE_RESULTS, 1, None)

		initial_alloc_state = stack_allocator.state()

		graph = None

		try:
			# Attraction points
			progress.setCurrentTask(Tasks.READ_ATTRACTIONS)
			(attr_table, attr_rows, attr_points, attr_points_per_polygon) = ReadAttractionPoints(model, pstalgo, stack_allocator, props, progress)

			# Graph
			progress.setCurrentTask(Tasks.BUILD_GRAPH)
			(graph, line_rows, origin_rows) = BuildAxialGraph(
				model,
				pstalgo,
				stack_allocator,
				self._props['in_network'],
				self._props['in_unlinks'] if self._props['in_unlinks_enabled'] else None,
				self._props['in_origin_points'] if origin_type in [pstalgo.OriginType.POINTS, pstalgo.OriginType.POINT_GROUPS] else None,
				progress,
				poly_edge_point_interval = props['origin_poly_edge_point_interval'] if (origin_type == pstalgo.OriginType.POINT_GROUPS) else 0)

			# Output count
			output_count = 0
			junction_coords = None
			if origin_type in [pstalgo.OriginType.POINTS, pstalgo.OriginType.POINT_GROUPS]:
				output_count = origin_rows.size()
			elif origin_type == pstalgo.OriginType.LINES:
				output_count = line_rows.size()
			elif origin_type == pstalgo.OriginType.JUNCTIONS:
				output_count = pstalgo.GetGraphInfo(graph).m_CrossingCount
				junction_coords = Vector(ctypes.c_double, output_count*2, stack_allocator, output_count*2)
				pstalgo.GetGraphCrossingCoords(graph, junction_coords)
			else:
				assert(False)

			attr_values = None
			columns = []

			# Analyses
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
				if weight_enabled:
					for distance_type, radii in distance_modes:
						# Allocate output array
						scores = Vector(ctypes.c_float, output_count, stack_allocator, output_count)
						# Analysis
						pstalgo.AttractionReach(
							graph_handle = graph,
							origin_type = origin_type,
							distance_type = distance_type,
							radius = radii,
							weight_func = weight_func,
							weight_func_constant = props['weight_func_constant'],
							attraction_points = attr_points,
							points_per_attraction_polygon = attr_points_per_polygon,
							attraction_polygon_point_interval = props['dest_poly_edge_point_interval'],
							attraction_values = None if attr_col is None else attr_values,
							attraction_distribution_func = attraction_distribution_func,
							attraction_collection_func = attraction_collection_func,
							progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_progress),
							out_scores = scores)
						# Output column
						columns.append((GenerateColumnName(attr_title, radii, weight_func), 'float', scores.values()))
						# Progress
						analysis_progress.nextTask()
				else:
					for radii in radii_list:
						# Allocate output array
						scores = Vector(ctypes.c_float, output_count, stack_allocator, output_count)
						# Analysis
						pstalgo.AttractionReach(
							graph_handle = graph,
							origin_type = origin_type,
							distance_type = pstalgo.DistanceType.UNDEFINED,
							radius = radii,
							attraction_points = attr_points,
							points_per_attraction_polygon = attr_points_per_polygon,
							attraction_polygon_point_interval = props['dest_poly_edge_point_interval'],
							attraction_values = attr_values,
							attraction_distribution_func = attraction_distribution_func,
							attraction_collection_func = attraction_collection_func,
							progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_progress),
							out_scores = scores)
						# Output column
						columns.append((GenerateColumnName(attr_title, radii, None), 'float', scores.values()))
						# Progress
						analysis_progress.nextTask()

			# Write
			progress.setCurrentTask(Tasks.WRITE_RESULTS)
			if origin_type in [pstalgo.OriginType.POINTS, pstalgo.OriginType.POINT_GROUPS]:
				model.writeColumns(self._props['in_origin_points'], origin_rows, columns, progress)
			elif origin_type == pstalgo.OriginType.LINES:
				model.writeColumns(self._props['in_network'], line_rows, columns, progress)
			elif origin_type == pstalgo.OriginType.JUNCTIONS:
				model.createTable(
					props['in_network'] + '_junctions',
					model.coordinateReferenceSystem(self._props['in_network']),
					columns,
					PointGen(junction_coords, model),
					int(junction_coords.size()/2),
					progress,
					geo_type=GeometryType.POINT)
				pass
			else:
				assert(False)

		finally:
			stack_allocator.restore(initial_alloc_state)
			if graph:
				pstalgo.FreeGraph(graph)

		delegate.setStatus("Attraction Reach done")
		delegate.setProgress(1)