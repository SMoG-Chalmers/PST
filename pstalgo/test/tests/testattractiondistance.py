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

import array, math, unittest
import pstalgo
from pstalgo import DistanceType, Radii, OriginType
from .common import *
from .graphs import *

class TestAttractionDistance(unittest.TestCase):

	def test_adi_five_chain(self):
		count = 5
		length = 3
		g = CreateTestGraph(count, length)
		attraction_points = array.array('d', [-1, 0])
		self.doTest(g, OriginType.POINTS, DistanceType.WALKING, Radii(), attraction_points, [3.5, 6.5, 9.5, 12.5, 15.5])
		self.doTest(g, OriginType.POINTS, DistanceType.WALKING, Radii(walking=10), attraction_points, [3.5, 6.5, 9.5, -1, -1])
		self.doTest(g, OriginType.POINTS, DistanceType.WALKING, Radii(steps=3), attraction_points, [3.5, 6.5, 9.5, 12.5, -1])
		self.doTest(g, OriginType.LINES,  DistanceType.WALKING, Radii(), attraction_points, [2.5, 5.5, 8.5, 11.5, 14.5])
		self.doTest(g, OriginType.JUNCTIONS, DistanceType.WALKING, Radii(), attraction_points, [4, 7, 10, 13])
		self.doTest(g, OriginType.LINES,  DistanceType.STRAIGHT, Radii(), attraction_points, [2.5, 5.5, 8.5, 11.5, 14.5])
		self.doTest(g, OriginType.LINES,  DistanceType.STRAIGHT, Radii(straight = 7), attraction_points, [2.5, 5.5, -1, -1, -1])
		self.doTest(g, OriginType.POINTS, DistanceType.STRAIGHT, Radii(), attraction_points, [math.sqrt(x*x+1) for x in [2.5, 5.5, 8.5, 11.5, 14.5]])
		pstalgo.FreeGraph(g)

	def test_adi_weights(self):
		count = 5
		length = 3
		g = CreateTestGraph(count, length)
		attraction_points = array.array('d', [-1, 0])
		line_weights = array.array('f', [1,2,3,4,5])
		self.doTest(g, OriginType.POINTS, DistanceType.WEIGHTS, Radii(), attraction_points, [0.5, 2, 4.5, 8, 12.5], line_weights=line_weights)
		pstalgo.FreeGraph(g)

	def test_adi_polygon(self):
		count = 3
		length = 3
		g = CreateTestGraph(count, length)
		attraction_points      = array.array('d', [-1.1, 0.5, -0.1, 0.5, -0.1, -0.5, -1.1, -0.5])
		points_per_polygon     = array.array('I', [4])
		polygon_point_interval = 0.5
		self.doTest(g, OriginType.POINTS, DistanceType.WALKING, Radii(), attraction_points, [2.6, 5.6, 8.6], points_per_polygon, polygon_point_interval)
		pstalgo.FreeGraph(g)

	def test_adi_wave(self):
		g = CreateWaveGraph()
		attraction_points = array.array('d', [-1, 0])
		self.doTest(g, OriginType.POINTS,    DistanceType.WALKING, Radii(), attraction_points, [7])
		self.doTest(g, OriginType.LINES,     DistanceType.WALKING, Radii(), attraction_points, [1.5, 2.5, 3.5, 4.5, 5.5])
		self.doTest(g, OriginType.JUNCTIONS, DistanceType.WALKING, Radii(), attraction_points, [2,3,4,5])
		self.doTest(g, OriginType.POINTS,    DistanceType.WALKING, Radii(angular=121), attraction_points, [7])
		self.doTest(g, OriginType.POINTS,    DistanceType.WALKING, Radii(angular=90), attraction_points, [-1])
		self.doTest(g, OriginType.POINTS,    DistanceType.ANGULAR, Radii(), attraction_points, [120])
		self.doTest(g, OriginType.LINES,     DistanceType.ANGULAR, Radii(), attraction_points, [0,30,60,90,120])
		self.doTest(g, OriginType.JUNCTIONS, DistanceType.ANGULAR, Radii(), attraction_points, [0,30,60,90])
		self.doTest(g, OriginType.POINTS,    DistanceType.ANGULAR, Radii(steps=4), attraction_points, [120])
		self.doTest(g, OriginType.POINTS,    DistanceType.ANGULAR, Radii(steps=3), attraction_points, [-1])
		self.doTest(g, OriginType.POINTS,    DistanceType.ANGULAR, Radii(steps=4,angular=121), attraction_points, [120])
		self.doTest(g, OriginType.POINTS,    DistanceType.ANGULAR, Radii(steps=4,angular=119), attraction_points, [-1])
		self.doTest(g, OriginType.POINTS,    DistanceType.ANGULAR, Radii(steps=3,angular=121), attraction_points, [-1])
		self.doTest(g, OriginType.POINTS,    DistanceType.ANGULAR, Radii(steps=4,angular=121,walking=7.1), attraction_points, [120])
		self.doTest(g, OriginType.POINTS,    DistanceType.ANGULAR, Radii(steps=4,angular=121,walking=6.9), attraction_points, [-1])
		pstalgo.FreeGraph(g)

	def doTest(self, graph, origin_type, distance_type, radius, attraction_points, min_dists_check, points_per_polygon=None, polygon_point_interval=0, line_weights=None):
		min_dists = array.array('f', [0])*len(min_dists_check)
		pstalgo.AttractionDistance(
			graph_handle = graph,
			origin_type = origin_type,
			distance_type = distance_type,
			radius = radius,
			attraction_points = attraction_points,
			out_min_distances = min_dists,
			points_per_polygon = points_per_polygon,
			polygon_point_interval = polygon_point_interval,
			line_weights = line_weights)
		self.assertTrue(IsArrayRoughlyEqual(min_dists, min_dists_check), str(min_dists) + " != " + str(min_dists_check))

def CreateTestGraph(line_count, line_length):
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
	graph_handle = pstalgo.CreateGraph(line_coords, line_indices, None, points, None)
	return graph_handle

def CreateWaveGraph():
	#     ___
	# ___/   \___
	#
	# 5 lines, line length = 1, intersection angle = 30
	line_coords = []	
	x = 0
	line_coords.append(0)
	line_coords.append(0)
	x += 1
	line_coords.append(x)
	line_coords.append(0)
	x += math.sqrt(0.75)
	line_coords.append(x)
	line_coords.append(0.5)
	x += 1
	line_coords.append(x)
	line_coords.append(0.5)
	x += math.sqrt(0.75)
	line_coords.append(x)
	line_coords.append(0)
	x += 1
	line_coords.append(x)
	line_coords.append(0)
	line_indices = [0,1,2,1,3,2,3,4,4,5]  # reversing the order of some pairs
	points = [x + 1, 0]
	line_coords = array.array('d', line_coords)
	line_indices = array.array('I', line_indices)
	points = array.array('d', points)
	graph_handle = pstalgo.CreateGraph(line_coords, line_indices, None, points, None)
	return graph_handle
