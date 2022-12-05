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
from qgis.PyQt.QtCore import QVariant
from ..model import GeometryType
from .base import BaseAnalysis
from .columnnaming import ColName, GenColName
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, TaskSplitProgressDelegate, BuildAxialGraph, DistanceTypesFromSettings, RadiiFromSettings, PointGen


class AttractionDistanceAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):
		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props
		model = self._model

		# Radius
		radii = RadiiFromSettings(pstalgo, self._props)

		# Origin type
		origin_type = OriginTypeFromProps(pstalgo, props)

		# Distance types
		distance_types = DistanceTypesFromSettings(pstalgo, props)

		# Attraction columns (None = use value 1 for every attraction)
		attraction_columns = props['dest_data'] if props['dest_data_enabled'] else [None]

		# Number of analyses
		analysis_count = len(attraction_columns) * len(distance_types)

		def GenerateColumnName(dest_name, distance_type, radii):
			return GenColName(ColName.ATTRACTION_DISTANCE, weight=dest_name, pst_distance_type=distance_type, radii=radii)

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

			columns = []

			attr_points_temp = None
			attr_points_per_polygon_temp = None

			progress.setCurrentTask(Tasks.ANALYSIS)
			analysis_progress = TaskSplitProgressDelegate(analysis_count, "Performing analysis", progress)
			for attr_col in attraction_columns:
				# Attraction values
				if attr_col is None:
					attr_points_filtered = attr_points
					attr_points_per_polygon_filtered = attr_points_per_polygon
				else:
					attr_values = AttractionValueGen(model, attr_table, attr_rows, [attr_col], progress)
					(attr_points_temp, attr_points_per_polygon_temp) = FilterZeroAttractions(attr_points, attr_points_per_polygon, attr_values, stack_allocator, attr_points_temp, attr_points_per_polygon_temp)
					attr_points_filtered = attr_points_temp
					attr_points_per_polygon_filtered = attr_points_per_polygon_temp
				# Distance types
				for distance_type in distance_types:
					# Allocate output array
					scores = Vector(ctypes.c_float, output_count, stack_allocator, output_count)
					# Analysis
					pstalgo.AttractionDistance(
						graph_handle = graph,
						origin_type = origin_type,
						distance_type = distance_type,
						radius = radii,
						attraction_points = attr_points_filtered,
						points_per_polygon = attr_points_per_polygon_filtered,
						polygon_point_interval = props['dest_poly_edge_point_interval'],
						progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(analysis_progress),
						out_min_distances = scores)
					# Output column
					attr_title = GenerateAttractionDataName(props['in_destinations'], attr_col, props['dest_name'])
					columns.append((GenerateColumnName(attr_title, distance_type, radii), 'float', scores.values()))
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

		delegate.setStatus("Attraction Distance done")
		delegate.setProgress(1)

def GenerateAttractionDataName(table_name, column_name, custom_name):
	name = custom_name
	if not name:
		name = column_name
	if not name:
		name = table_name
	name = name.lower()
	if len(name) > 2:
		name = name[:2]
	return name
	""" Old naming logic
	if table_name and len(table_name) > 4:
		table_name = table_name[:4]
	if column_name and len(column_name) > 4:
		column_name = column_name[:4]
	return '_'.join([name for name in [table_name, column_name, custom_name] if name])
	"""

def OriginTypeFromProps(pstalgo, props):
	origin_type_name = props['in_origin_type']
	if 'points' == origin_type_name:
		if props['origin_is_regions'] and props.get('origin_poly_edge_point_interval_enabled'):
			return pstalgo.OriginType.POINT_GROUPS
		return pstalgo.OriginType.POINTS
	elif 'lines' == origin_type_name:
		return pstalgo.OriginType.LINES
	elif 'junctions' == origin_type_name:
		return pstalgo.OriginType.JUNCTIONS
	raise Exception("Unsupported origin type '%s'!" % origin_type_name)

def ReadAttractionPoints(model, pstalgo, stack_allocator, props, progress):
	attr_table = props['in_destinations']
	max_attr_count = model.rowCount(attr_table)
	attr_rows = pstalgo.Vector(ctypes.c_longlong, max_attr_count, stack_allocator) if props['dest_data_enabled'] else None
	attr_points = None
	attr_points_per_polygon = None
	if props['dest_is_regions'] and props.get('dest_poly_edge_point_interval_enabled'):
		attr_points_per_polygon = pstalgo.Vector(ctypes.c_uint, max_attr_count, stack_allocator)
		attr_points = model.readPolygons(attr_table, attr_points_per_polygon, attr_rows, progress)
		if attr_rows is not None:
			assert(attr_points_per_polygon.size() == attr_rows.size())
	else:
		attr_points = pstalgo.Vector(ctypes.c_double, max_attr_count*2, stack_allocator)
		model.readPoints(attr_table, attr_points, attr_rows, progress)
	return (attr_table, attr_rows, attr_points, attr_points_per_polygon)

def AttractionValueGen(model, table, rowids, column_names, progress):
	row_count = rowids.size()
	if len(column_names)==1:
		for i, value in enumerate(model.values(table, column_names, rowids)):
			if isinstance(value, QVariant) and value.isNull():
				value = 0
			yield value
			if (i % 1000) == 0:
				progress.setProgress(float(i) / row_count)
	else:
		for i, values in enumerate(model.values(table, column_names, rowids)):
			yield sum(values)
			if (i % 1000) == 0:
				progress.setProgress(float(i) / row_count)

def FilterZeroAttractions(points, points_per_polygon, attr_values, allocator, points_out=None, points_per_polygon_out=None):
	from pstalgo import Vector # Do it here when it is needed instead of on plugin load
	if points_out is None:
		points_out = Vector(ctypes.c_double, len(points), allocator)
	points_out.clear()
	if points_per_polygon:
		if points_per_polygon_out is None:
			points_per_polygon_out = Vector(points_per_polygon.elemtype(), points_per_polygon.size(), allocator)
		points_per_polygon_out.clear()
	pcount = 0
	total_poly_point_count = 0
	attr_count = 0
	for i, val in enumerate(attr_values):
		count = points_per_polygon[i] if points_per_polygon else 1
		if val > 0:
			if points_per_polygon:
				points_per_polygon_out.append(count)
			for ii in range(pcount*2, (pcount+count)*2):
				points_out.append(points[ii])
		pcount += count
		attr_count += 1
	if points_per_polygon_out is None:
		assert(len(points) == attr_count*2)
	else:
		assert(len(points_per_polygon) == attr_count)
	return (points_out, points_per_polygon_out)