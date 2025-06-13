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
		self.doTest(g, OriginType.POINTS, DistanceType.WEIGHTS, Radii(), attraction_points, [3.5, 5, 7.5, 11, 15.5], line_weights=line_weights, weight_per_meter_for_point_edges=1.5)
		pstalgo.FreeGraph(g)

	def test_adi_polygon(self):
		count = 3
		length = 3
		g = CreateTestGraph(count, length)
		attraction_points      = array.array('d', [-1.1, 0.5, -0.1, 0.5, -0.1, -0.5, -1.1, -0.5] + [10, 0.5, 11, 0.5, 11, -0.5, 10, -0.5])
		points_per_polygon     = array.array('I', [4, 4])
		polygon_point_interval = 0.5
		self.doTest(g, OriginType.POINTS, DistanceType.WALKING, Radii(), attraction_points, 
			min_dists_check=[2.6, 5.6, 3.5],
			dest_idx_check=[0,0,1],
			points_per_polygon=points_per_polygon, 
			polygon_point_interval=polygon_point_interval)
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

	def test_adi_grid(self):
		dim = 10
		g = CreateTestGraph(dim, 1)
		pts = [0] * (dim*dim*2)
		for x in range(dim):
			for y in range(dim):
				pts[((x*dim)+y) * 2] = x
				pts[((x*dim)+y) * 2 + 1] = y
		attraction_points = array.array('d', pts)
		self.doTest(g, OriginType.POINTS, DistanceType.WALKING,  Radii(), attraction_points, min_dists_check=[1.5]*10, dest_idx_check=[0,10,20,30,40,50,60,70,80,90])
		self.doTest(g, OriginType.POINTS, DistanceType.STRAIGHT, Radii(), attraction_points, min_dists_check=[0.5]*10, dest_idx_check=[1,11,21,31,41,51,61,71,81,91])
		pstalgo.FreeGraph(g)

	def test_adi_straight_grid(self):
		origin_coords = CreatePointGrid(10,10)
		line_coords = [0, 0, 1, 0]
		g = CreateGraph(origin_coords, line_coords)
		attraction_coords = [-1.5, 0]
		attraction_arr = array.array('d', attraction_coords)
		min_dists_check = [-1]*int(len(origin_coords)/2)
		dest_idx_check = [-1]*int(len(origin_coords)/2)
		straight_radius = 2.1
		for i in range(len(min_dists_check)):
			dx = attraction_coords[0] - origin_coords[i*2]
			dy = attraction_coords[1] - origin_coords[i*2+1]
			d = math.sqrt(dx*dx+dy*dy)
			if d <= straight_radius:
				min_dists_check[i] = d;
				dest_idx_check[i] = 0
		self.doTest(g, OriginType.POINTS, DistanceType.STRAIGHT, Radii(straight=straight_radius), attraction_arr, min_dists_check=min_dists_check, dest_idx_check=dest_idx_check)
		pstalgo.FreeGraph(g)

	def doTest(self, graph, origin_type, distance_type, radius, attraction_points, min_dists_check=None, dest_idx_check=None, points_per_polygon=None, polygon_point_interval=0, line_weights=None, weight_per_meter_for_point_edges=0):
		min_dists = array.array('f', [0])*len(min_dists_check)
		dest_indices = array.array('i', [0])*len(dest_idx_check) if dest_idx_check is not None else None
		pstalgo.AttractionDistance(
			graph_handle = graph,
			origin_type = origin_type,
			distance_type = distance_type,
			radius = radius,
			attraction_points = attraction_points,
			out_min_distances = min_dists,
			out_destination_indices = dest_indices,
			points_per_polygon = points_per_polygon,
			polygon_point_interval = polygon_point_interval,
			line_weights = line_weights,
			weight_per_meter_for_point_edges = weight_per_meter_for_point_edges)
		self.assertTrue(IsArrayRoughlyEqual(min_dists, min_dists_check), str(min_dists) + " != " + str(min_dists_check))
		if dest_idx_check is not None:
			self.assertTrue(IsArrayRoughlyEqual(dest_indices, dest_idx_check), str(dest_indices) + " != " + str(dest_idx_check))

# Creates a chain of segments starting at (0,0) and ending at(line_count*line_length, 0)
# and one point centered one unit above each line segment.
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

def CreatePointGrid(res_x, res_y):
	""" Create grid of points centered around (0,0) """
	pts = [0] * (res_x*res_y*2)
	for y in range(res_y):
		for x in range(res_x):
			pts[((y*res_x)+x) * 2]     = x - (res_x - 1) * 0.5
			pts[((y*res_x)+x) * 2 + 1] = y - (res_y - 1) * 0.5
	return pts;

def CreateGraph(point_coords, line_coords):
	line_indices = [0]*int(len(line_coords)/2)
	for i in range(len(line_indices)):
		line_indices[i] = i
	line_coords_arr  = array.array('d', line_coords)
	line_indices_arr = array.array('I', line_indices)
	points_arr       = array.array('d', point_coords)
	return pstalgo.CreateGraph(line_coords_arr, line_indices_arr, None, points_arr, None)
