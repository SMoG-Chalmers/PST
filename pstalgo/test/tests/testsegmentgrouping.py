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
from .common import *
from .graphs import *


class TestSegmentGrouping(unittest.TestCase):

	def test_sgrp_chain(self):
		count = 5
		length = 3
		g = CreateSegmentChainGraph(count, length)
		self.doTest(g, count, 1, False, [0]*count, [0]*count)
		self.doTest(g, count, 1, True, [0]*count, [0]*count)
		pstalgo.FreeSegmentGraph(g)

	def test_sgrp_square(self):
		count = 4
		length = 3
		g = CreateSegmentSquareGraph(length)
		self.doTest(g, count, 89, False, [0,1,2,3], [0,1,0,1])
		self.doTest(g, count, 89, True, [0,1,2,3], [0,1,0,1])
		self.doTest(g, count, 90, False, [0]*count, [0]*count)
		self.doTest(g, count, 90, True, [0]*count, [0]*count)
		pstalgo.FreeSegmentGraph(g)

	def test_sgrp_crshr(self):
		count = 12
		g = CreateCrosshairSegmentGraph()
		self.doTest(g, count, 89, False, [0,0,1,1,2,2,3,3,4,4,5,5],   [0,0,1,1,0,0,1,1,0,0,1,1])
		self.doTest(g, count, 89, True,  [0,1,2,3,4,5,6,7,8,9,10,11], [0,1,2,1,0,1,0,2,0,1,2,3])
		self.doTest(g, count, 90, False, [0,0,0,0,0,0,0,0,1,1,2,2],   [0,0,0,0,0,0,0,0,1,1,2,2])
		pstalgo.FreeSegmentGraph(g)

	def test_sgrp_90plus(self):
		line_coords = array.array('d', [0, 0, -1, 0, -1, 0.01])
		line_indices = array.array('I', [0, 1, 2, 0])
		g = pstalgo.CreateSegmentGraph(line_coords, line_indices, None)
		self.doTest(g, 2, 100, False, [0,1], [0,1])
		self.doTest(g, 2, 180, False, [0,0], [0,0])
		self.doTest(g, 2, 100, True, [0,1], [0,1])
		self.doTest(g, 2, 180, True, [0,0], [0,0])
		pstalgo.FreeSegmentGraph(g)

		line_coords = array.array('d', [0, 0, -1, 0, -1, 0.01, 1, 1])
		line_indices = array.array('I', [0, 1, 2, 0, 0, 3])
		g = pstalgo.CreateSegmentGraph(line_coords, line_indices, None)
		self.doTest(g, 3, 90, False, [0,1,0], [0,1,0])
		pstalgo.FreeSegmentGraph(g)

	def doTest(self, graph, line_count, angle_threshold, split_at_junctions, groups, colors):
		group_arr = array.array('I', [0])*line_count
		color_arr = array.array('I', [0])*line_count
		pstalgo.SegmentGrouping(
			segment_graph = graph, 
			angle_threshold = angle_threshold, 
			split_at_junctions = split_at_junctions,
			out_group_id_per_line = group_arr,
			out_color_per_line = color_arr)
		self.assertTrue(IsArrayRoughlyEqual(group_arr, groups), str(group_arr) + " != " + str(groups))
		self.assertTrue(IsArrayRoughlyEqual(color_arr, colors), str(color_arr) + " != " + str(colors))