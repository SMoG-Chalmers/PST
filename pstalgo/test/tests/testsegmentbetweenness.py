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

import array
import unittest
import pstalgo
from pstalgo import DistanceType

class TestSegmentBetweenness(unittest.TestCase):

	def test_five_chain(self):
		graph = self.create_chain_graph(5)
		betweenness = array.array('f', [0])*5  # Fastest way of allocating arrays of array.array-type
		pstalgo.SegmentBetweenness(
			graph_handle = graph,
			distance_type = DistanceType.STEPS, 
			radius = pstalgo.Radii(steps=4),
			out_betweenness = betweenness)
		pstalgo.FreeGraph(graph)
		self.assertEqual(betweenness, array.array('f', [0, 3, 4, 3, 0]))

	def test_split(self):
		graph = self.create_split_graph()
		betweenness = array.array('f', [0])*6  # Fastest way of allocating arrays of array.array-type
		pstalgo.SegmentBetweenness(
			graph_handle = graph,
			distance_type = DistanceType.ANGULAR, 
			radius = pstalgo.Radii(angular=45),
			out_betweenness = betweenness)
		pstalgo.FreeGraph(graph)
		self.assertEqual(betweenness, array.array('f', [0, 1.5, 1.5, 1.5, 1.5, 0]))

	def test_split2(self):
		graph = self.create_split_graph2()
		betweenness = array.array('f', [0])*6  # Fastest way of allocating arrays of array.array-type
		pstalgo.SegmentBetweenness(
			graph_handle = graph,
			distance_type = DistanceType.ANGULAR, 
			radius = pstalgo.Radii(angular=45),
			out_betweenness = betweenness)
		pstalgo.FreeGraph(graph)
		self.assertEqual(betweenness, array.array('f', [0, 1, 1, 2, 2, 0]))

	def create_chain_graph(self, line_count):
		# --...--
		line_coords = []	
		for x in range(line_count+1): 
			line_coords.append(x)
			line_coords.append(0)
		line_indices = []	
		for i in range(line_count): 
			line_indices.append(i)
			line_indices.append(i+1)
		line_coords = array.array('d', line_coords)
		line_indices = array.array('I', line_indices)
		graph_handle = pstalgo.CreateGraph(line_coords, line_indices, None, None, None)
		self.assertIsNotNone(graph_handle)
		return graph_handle

	def create_split_graph(self):
		# _/\_
		#  \/
		line_coords = array.array('d', [-2, 0, -1, 0, 0, 0.1, 0, -0.1, 1, 0, 2, 0])
		line_indices = array.array('I', [0, 1, 1, 2, 2, 4, 1, 3, 3, 4, 4, 5])
		graph_handle = pstalgo.CreateGraph(line_coords, line_indices, None, None, None)
		self.assertIsNotNone(graph_handle)
		return graph_handle

	def create_split_graph2(self):
		# _/\_ where bottom path is shorter
		#  \/
		line_coords = array.array('d', [-2, 0, -1, 0, 0, 0.1, 0, 0, 1, 0, 2, 0])
		line_indices = array.array('I', [0, 1, 1, 2, 2, 4, 1, 3, 3, 4, 4, 5])
		graph_handle = pstalgo.CreateGraph(line_coords, line_indices, None, None, None)
		self.assertIsNotNone(graph_handle)
		return graph_handle