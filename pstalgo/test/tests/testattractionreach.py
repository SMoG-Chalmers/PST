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

import array, math, unittest
import pstalgo
from pstalgo import DistanceType, Radii, OriginType, AttractionWeightFunction
from .common import *
from .graphs import *

class TestAttractionReach(unittest.TestCase):

	def test_arch_point_origin(self):
		count = 5
		length = 3
		g = CreatePointOriginChainGraph(count, length)
		attraction_points = array.array('d', [-1, 0, length*count+1, 0])  # One point left of and another right of graph
		attraction_values = array.array('f', [4, 3])
		collect_func = pstalgo.AttractionCollectionFunc.AVARAGE  # Redundant here
		distr_func   = pstalgo.AttractionDistributionFunc.DIVIDE  # Redundant here
		self.doTest(g, count, OriginType.POINTS,    DistanceType.UNDEFINED, Radii(),        AttractionWeightFunction.CONSTANT, 0, attraction_points, None, 0, attraction_values, distr_func, collect_func, [4+3]*count)
		self.doTest(g, count, OriginType.LINES,     DistanceType.UNDEFINED, Radii(),        AttractionWeightFunction.CONSTANT, 0, attraction_points, None, 0, attraction_values, distr_func, collect_func, [4+3]*count)
		self.doTest(g, count, OriginType.JUNCTIONS, DistanceType.UNDEFINED, Radii(),        AttractionWeightFunction.CONSTANT, 0, attraction_points, None, 0, attraction_values, distr_func, collect_func, [4+3]*(count-1))
		self.doTest(g, count, OriginType.POINTS,    DistanceType.UNDEFINED, Radii(steps=2), AttractionWeightFunction.CONSTANT, 0, attraction_points, None, 0, attraction_values, distr_func, collect_func, [4,4,4+3,3,3])
		self.doTest(g, count, OriginType.POINTS,    DistanceType.STEPS,     Radii(steps=2), AttractionWeightFunction.DIVIDE,   1, attraction_points, None, 0, attraction_values, distr_func, collect_func, [4,2,4.0/3+1,1.5,3])
		pstalgo.FreeGraph(g)

	def test_arch_region_origin(self):
		count = 5
		length = 3
		g = CreateRegionOriginChainGraph(count, length)
		attraction_points = array.array('d', [-1, 0, length*count+1, 0])  # One point left of and another right of graph
		attraction_values = array.array('f', [4, 3])
		collect_func = pstalgo.AttractionCollectionFunc.AVARAGE
		distr_func   = pstalgo.AttractionDistributionFunc.DIVIDE  # Redundant here
		self.doTest(g, count, OriginType.POINT_GROUPS, DistanceType.UNDEFINED, Radii(), AttractionWeightFunction.CONSTANT, 0, attraction_points, None, 0, attraction_values, distr_func, collect_func, [4+3]*count)
		pstalgo.FreeGraph(g)

	def test_arch_region_attr(self):
		count = 5
		length = 3
		g = CreateRegionOriginChainGraph(count, length)
		attraction_points = array.array('d', [-2, 0, -1, 0, -1, -1, -2, -1, length*count+1, 0, length*count+2, 0, length*count+2, -1, length*count+1, -1])  # One region left of and another right of graph
		points_per_attraction_polygon = array.array('I', [4, 4])
		attraction_polygon_point_interval = 0.5
		attraction_values = array.array('f', [4, 3])
		collect_func = pstalgo.AttractionCollectionFunc.AVARAGE
		distr_func   = pstalgo.AttractionDistributionFunc.DIVIDE
		self.doTest(g, count, OriginType.POINT_GROUPS, DistanceType.UNDEFINED, Radii(), AttractionWeightFunction.CONSTANT, 0, attraction_points, points_per_attraction_polygon, attraction_polygon_point_interval, attraction_values, distr_func, collect_func, [4+3]*count)
		distr_func   = pstalgo.AttractionDistributionFunc.COPY
		self.doTest(g, count, OriginType.POINT_GROUPS, DistanceType.UNDEFINED, Radii(), AttractionWeightFunction.CONSTANT, 0, attraction_points, points_per_attraction_polygon, attraction_polygon_point_interval, attraction_values, distr_func, collect_func, [4+3]*count)
		pstalgo.FreeGraph(g)

	def doTest(self, graph, line_count, origin_type, distance_type, radius, weight_func, weight_func_constant, attraction_points, points_per_attraction_polygon, attraction_polygon_point_interval, attraction_values, distr_func, collect_func, scores_check):
		scores = array.array('f', [0])*len(scores_check)
		pstalgo.AttractionReach(
			graph_handle = graph,
			origin_type = origin_type,
			distance_type = distance_type,
			radius = radius,
			weight_func = weight_func,
			weight_func_constant = weight_func_constant,
			attraction_points = attraction_points,
			points_per_attraction_polygon = points_per_attraction_polygon, 
			attraction_polygon_point_interval = attraction_polygon_point_interval,
			attraction_values = attraction_values,
			attraction_distribution_func=distr_func,
			attraction_collection_func=collect_func,
			out_scores = scores)
		self.assertTrue(IsArrayRoughlyEqual(scores, scores_check), str(scores) + " != " + str(scores_check))


def CreatePointOriginChainGraph(line_count, line_length):
	line_coords = []	
	for x in range(line_count+1): 
		line_coords.append(x*line_length)
		line_coords.append(0)
	line_indices = []	
	for i in range(line_count): 
		line_indices.append(i)
		line_indices.append(i+1)
	points = []
	for i in range(line_count): 
		points.append((0.5 + i)*line_length)
		points.append(1)
	line_coords = array.array('d', line_coords)
	line_indices = array.array('I', line_indices)
	points = array.array('d', points)
	graph_handle = pstalgo.CreateGraph(
		line_coords = line_coords,
		line_indices = line_indices,
		points = points)
	return graph_handle

def CreateRegionOriginChainGraph(line_count, line_length):
	line_coords = []	
	for x in range(line_count+1): 
		line_coords.append(x*line_length)
		line_coords.append(0)
	line_indices = []	
	for i in range(line_count): 
		line_indices.append(i)
		line_indices.append(i+1)
	points = []
	for i in range(line_count): 
		center = (0.5 + i)*line_length
		half_size = line_length / 4
		points += [center-half_size, 1+half_size*2, center+half_size, 1+half_size*2, center+half_size, 1, center-half_size, 1]
	line_coords = array.array('d', line_coords)
	line_indices = array.array('I', line_indices)
	points = array.array('d', points)
	points_per_polygon = array.array('I', [4]*line_count)
	graph_handle = pstalgo.CreateGraph(
		line_coords = line_coords,
		line_indices = line_indices,
		points = points,
		points_per_polygon = points_per_polygon, 
		polygon_point_interval = half_size/2)
	return graph_handle