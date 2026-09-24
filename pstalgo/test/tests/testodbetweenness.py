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
from pstalgo import DistanceType, Radii
from pstalgo import ODBetweenness, ODBDestinationMode, LineCostFactorsFromValues
from .common import *
from .graphs import *

class TestODBetweenness(unittest.TestCase):

	def test_odb_closest(self):
		g = CreateTestGraph()
		self.doTest(
			graph_handle = g, 
			origin_points = array.array('d', [-0.5, 0]), 
			origin_weights = None,
			destination_weights = None,
			destination_mode = ODBDestinationMode.CLOSEST_DESTINATION_ONLY, 
			distance_type = DistanceType.WALKING, 
			radius=Radii(), 
			scores_check = [1, 1, 0])
		pstalgo.FreeGraph(g)

	def test_odb_all(self):
		g = CreateTestGraph()
		self.doTest(
			graph_handle = g, 
			origin_points = array.array('d', [-0.5, 0]), 
			origin_weights = None,
			destination_weights = None,
			destination_mode = ODBDestinationMode.ALL_REACHABLE_DESTINATIONS, 
			distance_type = DistanceType.WALKING, 
			radius=Radii(), 
			scores_check = [1, 1, .5])
		pstalgo.FreeGraph(g)

	def test_odb_radius(self):
		g = CreateTestGraph()
		self.doTest(
			graph_handle = g, 
			origin_points = array.array('d', [-0.5, 0]), 
			origin_weights = None,
			destination_weights = None,
			destination_mode = ODBDestinationMode.ALL_REACHABLE_DESTINATIONS, 
			distance_type = DistanceType.WALKING, 
			radius=Radii(walking=3.9), 
			scores_check = [1, 1, 0])
		self.doTest(
			graph_handle = g, 
			origin_points = array.array('d', [-0.5, 0]), 
			origin_weights = None,
			destination_weights = None,
			destination_mode = ODBDestinationMode.ALL_REACHABLE_DESTINATIONS, 
			distance_type = DistanceType.WALKING, 
			radius=Radii(walking=4.1), 
			scores_check = [1, 1, .5])
		pstalgo.FreeGraph(g)

	def test_odb_origin_weights(self):
		g = CreateTestGraph()
		self.doTest(
			graph_handle = g, 
			origin_points = array.array('d', [-0.5, 0]), 
			origin_weights = array.array('f', [10]),
			destination_weights = None,
			destination_mode = ODBDestinationMode.ALL_REACHABLE_DESTINATIONS, 
			distance_type = DistanceType.WALKING, 
			radius=Radii(), 
			scores_check = [10, 10, 5])
		pstalgo.FreeGraph(g)

	def test_odb_dest_weights(self):
		g = CreateTestGraph()
		self.doTest(
			graph_handle = g, 
			origin_points = array.array('d', [-0.5, 0]), 
			origin_weights = array.array('f', [10]),
			destination_weights = array.array('f', [4, 1]),
			destination_mode = ODBDestinationMode.ALL_REACHABLE_DESTINATIONS, 
			distance_type = DistanceType.WALKING, 
			radius=Radii(), 
			scores_check = [10, 10, 2])
		pstalgo.FreeGraph(g)

	def test_odb_weights_neutral_matches_walking(self):
		# With every factor at 1 the weighted route must be the walking route
		g = CreateTwoRouteTestGraph()
		self.doTwoRouteTest(g, DistanceType.WALKING, None, Radii(), TWO_ROUTE_SCORES_TOP)
		self.doTwoRouteTest(g, DistanceType.WEIGHTS, array.array('f', [1]*6), Radii(), TWO_ROUTE_SCORES_TOP)
		pstalgo.FreeGraph(g)

	def test_odb_weights_reroute(self):
		# Doubling the cost of the shorter top route makes the longer bottom route cheaper
		g = CreateTwoRouteTestGraph()
		self.doTwoRouteTest(g, DistanceType.WEIGHTS, array.array('f', [1, 2, 2, 1, 1, 1]), Radii(), TWO_ROUTE_SCORES_BOTTOM)
		# A small increase is not enough to outweigh the extra length of the bottom route
		self.doTwoRouteTest(g, DistanceType.WEIGHTS, array.array('f', [1, 1.05, 1.05, 1, 1, 1]), Radii(), TWO_ROUTE_SCORES_TOP)
		pstalgo.FreeGraph(g)

	def test_odb_weights_radius_in_meters(self):
		# Walking radius is still measured in meters: the cheaper bottom route is
		# 4.92 m long and falls outside a 4.8 m radius, the top route (4.63 m) does not
		g = CreateTwoRouteTestGraph()
		factors = array.array('f', [1, 2, 2, 1, 1, 1])
		self.doTwoRouteTest(g, DistanceType.WEIGHTS, factors, Radii(walking=4.8), TWO_ROUTE_SCORES_TOP)
		self.doTwoRouteTest(g, DistanceType.WEIGHTS, factors, Radii(walking=4.5), [0]*6)
		pstalgo.FreeGraph(g)

	def test_odb_weights_invalid_factors(self):
		g = CreateTwoRouteTestGraph()
		for factors in [None, array.array('f', [1]*5), array.array('f', [1, 1, -1, 1, 1, 1])]:
			with self.assertRaises(Exception):
				self.doTwoRouteTest(g, DistanceType.WEIGHTS, factors, Radii(), [0]*6)
		pstalgo.FreeGraph(g)

	def test_line_cost_factors_from_values(self):
		(f, missing) = LineCostFactorsFromValues([30, 50, 70], increases_cost=True, max_factor=3)
		self.assertTrue(IsArrayRoughlyEqual(f, [1, 2, 3]))
		self.assertEqual(missing, 0)
		(f, missing) = LineCostFactorsFromValues([30, 50, 70], increases_cost=False, max_factor=3)
		self.assertTrue(IsArrayRoughlyEqual(f, [3, 2, 1]))
		(f, missing) = LineCostFactorsFromValues([0, None, 1], increases_cost=False, max_factor=2)
		self.assertTrue(IsArrayRoughlyEqual(f, [2, 1, 1]))
		self.assertEqual(missing, 1)
		(f, missing) = LineCostFactorsFromValues([5, 5, 5], max_factor=2)
		self.assertTrue(IsArrayRoughlyEqual(f, [1, 1, 1]))
		(f, missing) = LineCostFactorsFromValues([None, None], max_factor=2)
		self.assertTrue(IsArrayRoughlyEqual(f, [1, 1]))
		self.assertEqual(missing, 2)
		with self.assertRaises(ValueError):
			LineCostFactorsFromValues([1, 2], max_factor=0.5)

	def doTwoRouteTest(self, graph_handle, distance_type, line_cost_factors, radius, scores_check):
		self.doTest(
			graph_handle = graph_handle,
			origin_points = array.array('d', [0.1, 0]),
			origin_weights = None,
			destination_weights = None,
			destination_mode = ODBDestinationMode.ALL_REACHABLE_DESTINATIONS,
			distance_type = distance_type,
			radius = radius,
			scores_check = scores_check,
			line_cost_factors = line_cost_factors)

	def doTest(self, graph_handle, origin_points, origin_weights, destination_weights, destination_mode, distance_type, radius, scores_check, line_cost_factors=None):
		scores = array.array('f', [0])*len(scores_check)
		ODBetweenness(
			graph_handle = graph_handle,
			origin_points = origin_points,
			origin_weights = origin_weights,
			destination_weights = destination_weights,
			destination_mode = destination_mode,
			distance_type = distance_type,
			radius = radius,
			progress_callback = None,
			out_scores = scores,
			line_cost_factors = line_cost_factors)
		self.assertTrue(IsArrayRoughlyEqual(scores, scores_check), str(scores) + " != " + str(scores_check))

# Line order in CreateTwoRouteTestGraph: start, top-left, top-right, bottom-left, bottom-right, end
TWO_ROUTE_SCORES_TOP    = [1, 1, 1, 0, 0, 1]
TWO_ROUTE_SCORES_BOTTOM = [1, 0, 0, 1, 1, 1]

def CreateTwoRouteTestGraph():
	"""
	Two routes between an origin at (0.1, 0) and a destination at (3.9, 0):
	a shorter one over (2, 1) and a longer one under (2, -1.2).
	"""
	line_coords = array.array('d', [
		0, 0,     # 0
		1, 0,     # 1
		2, 1,     # 2
		3, 0,     # 3
		2, -1.2,  # 4
		4, 0,     # 5
	])
	line_indices = array.array('I', [
		0, 1,  # start
		1, 2,  # top-left
		2, 3,  # top-right
		1, 4,  # bottom-left
		4, 3,  # bottom-right
		3, 5,  # end
	])
	points = array.array('d', [3.9, 0])
	return pstalgo.CreateGraph(
		line_coords = line_coords,
		line_indices = line_indices,
		points = points)

def CreateTestGraph():
	line_count = 3
	line_coords = []	
	for x in range(line_count+1): 
		line_coords.append(x)
		line_coords.append(0)
	line_indices = []	
	for i in range(line_count): 
		line_indices.append(i)
		line_indices.append(i+1)
	points = [1.5, 0.5, 3.5, 0]
	line_coords = array.array('d', line_coords)
	line_indices = array.array('I', line_indices)
	points = array.array('d', points)
	graph_handle = pstalgo.CreateGraph(
		line_coords = line_coords,
		line_indices = line_indices,
		points = points)
	return graph_handle