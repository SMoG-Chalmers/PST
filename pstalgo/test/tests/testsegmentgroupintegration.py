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
from .common import *
from .graphs import *


class TestSegmentGroupIntegration(unittest.TestCase):

	def test_sgint_chain(self):
		count = 5
		length = 3
		seg_graph = CreateSegmentChainGraph(count, length)
		
		group_arr = array.array('I', [i for i in range(count)])
		group_graph = pstalgo.CreateSegmentGroupGraph(seg_graph, group_arr, count)
		self.doTest(group_graph, count, Radii(), [0.352, 0.704, 1.056, 0.704, 0.352], [count]*count, [10, 7, 6, 7, 10])
		self.doTest(group_graph, count, Radii(walking=0), None, [2, 3, 3, 3, 2], None)
		self.doTest(group_graph, count, Radii(walking=1), None, [2, 3, 3, 3, 2], None)
		self.doTest(group_graph, count, Radii(walking=3), None, [3, 4, 5, 4, 3], None)
		self.doTest(group_graph, count, Radii(steps=0),   None, [1, 1, 1, 1, 1], None)
		self.doTest(group_graph, count, Radii(steps=1),   None, [2, 3, 3, 3, 2], None)
		self.doTest(group_graph, count, Radii(steps=2),   None, [3, 4, 5, 4, 3], None)
		self.doTest(group_graph, count, Radii(walking=3,steps=0), None, [1]*count, None)
		self.doTest(group_graph, count, Radii(walking=0,steps=2), None, [2, 3, 3, 3, 2], None)
		pstalgo.FreeSegmentGroupGraph(group_graph)
		
		group_arr = array.array('I', [0, 1, 1, 1, 2])
		group_graph = pstalgo.CreateSegmentGroupGraph(seg_graph, group_arr, 3)
		self.doTest(group_graph, 3, Radii(),          None, [3, 3, 3], [3, 2, 3])
		self.doTest(group_graph, 3, Radii(steps=0),   None, [1, 1, 1], [0, 0, 0])
		self.doTest(group_graph, 3, Radii(steps=1),   None, [2, 3, 2], [1, 2, 1])
		self.doTest(group_graph, 3, Radii(walking=0), None, [2, 3, 2], [1, 2, 1])
		self.doTest(group_graph, 3, Radii(walking=5), None, [2, 3, 2], [1, 2, 1])
		self.doTest(group_graph, 3, Radii(walking=9), None, [3, 3, 3], [3, 2, 3])
		pstalgo.FreeSegmentGroupGraph(group_graph)

		pstalgo.FreeSegmentGraph(seg_graph)

	def test_sgint_crshr(self):
		count = 12
		gcount = 8
		seg_graph = CreateCrosshairSegmentGraph()
		group_arr = array.array('I', [0,0,1,1,2,2,3,3,4,5,6,7])
		group_graph = pstalgo.CreateSegmentGroupGraph(seg_graph, group_arr, gcount)
		self.doTest(group_graph, gcount, Radii(), None, [gcount]*gcount, [11,11,11,11,10,10,10,10])
		self.doTest(group_graph, gcount, Radii(steps=1), None, [4, 4, 4, 4, 5, 5, 5, 5], [3, 3, 3, 3, 4, 4, 4, 4])
		self.doTest(group_graph, gcount, Radii(walking=1), None, [7, 7, 7, 7, 8, 8, 8, 8], [9, 9, 9, 9, 10, 10, 10, 10])
		pstalgo.FreeSegmentGroupGraph(group_graph)
		pstalgo.FreeSegmentGraph(seg_graph)

	def doTest(self, graph, count, radii, integration_check, node_counts_check, total_depths_check):
		integration  = array.array('f', [0])*count
		node_counts  = array.array('I', [0])*count
		total_depths = array.array('f', [0])*count
		pstalgo.SegmentGroupIntegration(
			group_graph = graph, 
			radii = radii, 
			out_integration = integration,
			out_node_counts = node_counts,
			out_total_depths = total_depths)
		if integration_check is not None:
			self.assertTrue(IsArrayRoughlyEqual(integration, integration_check), str(integration) + " != " + str(integration_check))
		if node_counts_check is not None:
			self.assertTrue(IsArrayRoughlyEqual(node_counts, node_counts_check), str(node_counts) + " != " + str(node_counts_check))
		if total_depths_check is not None:
			self.assertTrue(IsArrayRoughlyEqual(total_depths, total_depths_check), str(total_depths) + " != " + str(total_depths_check))