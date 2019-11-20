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
from pstalgo import DistanceType, Radii
from pstalgo import ODBetweenness, ODBDestinationMode
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

	def doTest(self, graph_handle, origin_points, origin_weights, destination_weights, destination_mode, distance_type, radius, scores_check):
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
			out_scores = scores)
		self.assertTrue(IsArrayRoughlyEqual(scores, scores_check), str(scores) + " != " + str(scores_check))

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