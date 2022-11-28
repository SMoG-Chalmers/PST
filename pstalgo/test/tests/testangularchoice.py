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

class TestAngularChoice(unittest.TestCase):

	def test_ach_five_chain(self):
		line_count = 5
		line_length = 3
		graph = CreateSegmentChainGraph(line_count, line_length)
		self.doTest(graph, line_count, Radii(), False, [0, 6, 8, 6, 0], [line_count]*line_count, [0, 0, 0, 0, 0], None)
		self.doTest(graph, line_count, Radii(straight=0), False, None, [1]*line_count, None, None)
		self.doTest(graph, line_count, Radii(straight=1), False, None, [1]*line_count, None, None)
		self.doTest(graph, line_count, Radii(straight=line_length), False, None, [2, 3, 3, 3, 2], None, None)
		self.doTest(graph, line_count, Radii(walking=0), False, None, [1]*line_count, None, None)
		self.doTest(graph, line_count, Radii(walking=1), False, None, [1]*line_count, None, None)
		self.doTest(graph, line_count, Radii(walking=3), False, None, [2, 3, 3, 3, 2], None, None)
		self.doTest(graph, line_count, Radii(steps=0), False, None, [1]*line_count, None, None)
		self.doTest(graph, line_count, Radii(steps=1), False, None, [2, 3, 3, 3, 2], None, None)
		self.doTest(graph, line_count, Radii(steps=2), False, None, [3, 4, 5, 4, 3], None, None)
		self.doTest(graph, line_count, Radii(angular=1), False, None, [line_count]*line_count, None, None)
		self.doTest(graph, line_count, Radii(), True, [36.0, 90.0, 108.0, 90.0, 36.0], [line_count]*line_count, [0, 0, 0, 0, 0], [0, 0, 0, 0, 0])
		pstalgo.FreeSegmentGraph(graph)

	def test_ach_square(self):
		line_count = 4
		line_length = 3
		graph = CreateSegmentSquareGraph(line_length)
		self.doTest(graph, line_count, Radii(), False, [1,1,1,1], [line_count]*line_count, [4]*line_count, None)
		self.doTest(graph, line_count, Radii(angular=80), False, None, [1]*line_count, [0]*line_count, None)
		self.doTest(graph, line_count, Radii(angular=100), False, None, [3]*line_count, [2]*line_count, None)
		self.doTest(graph, line_count, Radii(), True, [36,36,36,36], [line_count]*line_count, [4,4,4,4], [12,12,12,12])
		pstalgo.FreeSegmentGraph(graph)

	def test_ach_line_weight(self):
		line_count = 5
		line_length = 3
		graph = CreateSegmentChainGraph(line_count, line_length)
		choice = array.array('f', [0])*line_count
		pstalgo.AngularChoice(
			graph_handle = graph,
			radius = Radii(), 
			weigh_by_length = True,
			angle_threshold = 0,
			angle_precision = 1, 
			out_choice = choice)
		self.assertEqual(choice, array.array('f', [36, 90, 108, 90, 36]))
		pstalgo.FreeSegmentGraph(graph)

	def test_ach_normalize(self):
		values = array.array('f', [1, 2, 3, 4, 5])
		normalized = array.array('f', [0])*5
		
		pstalgo.StandardNormalize(values, len(values), normalized)
		self.assertEqual(normalized, array.array('f', [0, 0.25, 0.5, 0.75, 1]), "Standard Normalization")
		
		pstalgo.AngularChoiceNormalize(values, array.array('I', [1, 2, 3, 4, 5]), len(values), normalized)
		self.assertTrue(IsArrayRoughlyEqual(normalized, [1, 2, 1.5, 4.0/6, 5.0/12]), "Normalization " + str(normalized))
		
		TD = array.array('f', [5, 4, 3, 2, 1])
		pstalgo.AngularChoiceSyntaxNormalize(values, TD, len(values), normalized)
		check = [(math.log10(values[i] + 1)/math.log10(TD[i] + 2)) for i in range(len(values))]
		self.assertTrue(IsArrayRoughlyEqual(normalized, check), "Syntax Normalization " + str(normalized) + " != " + str(check))

	def runTests(self, graph, test_tuples, line_count):
		for t in test_tuples:
			self.doTest(graph, line_count, t[0], False, t[1], t[2], t[3], None)

	def doTest(self, graph, count, radii, weigh_by_length, C, N, TD, TDW):
		choice = array.array('f', [0])*count if C is not None else None
		node_count = array.array('I', [0])*count if N is not None else None
		total_depth = array.array('f', [0])*count if TD is not None else None
		total_depth_weight = array.array('f', [0])*count if TDW is not None else None
		pstalgo.AngularChoice(
			graph_handle = graph,
			radius = radii,
			weigh_by_length = weigh_by_length,
			angle_threshold = 0,
			angle_precision = 1, 
			out_choice = choice if C is not None else None,
			out_node_count = node_count if N is not None else None,
			out_total_depth = total_depth if TD is not None else None,
			out_total_depth_weight = total_depth_weight if TDW is not None else None)
		if C is not None:
			self.assertTrue(IsArrayRoughlyEqual(choice, C), str(choice) + " != " + str(C))
		if N is not None:
			self.assertEqual(node_count, array.array('I', N))
		if TD is not None:
			self.assertTrue(IsArrayRoughlyEqual(total_depth, TD), str(total_depth) + " != " + str(TD))
		if TDW is not None:
			self.assertTrue(IsArrayRoughlyEqual(total_depth_weight, TDW), str(total_depth_weight) + " != " + str(TDW))