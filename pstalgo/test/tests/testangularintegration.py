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

class TestAngularIntegration(unittest.TestCase):

	def test_aint_five_chain(self):
		count = 5
		length = 3
		g = CreateSegmentChainGraph(count, length)
		self.doTest(g, count, False, Radii(), [count]*count, [0]*count, None, [4]*count, [math.pow(count,1.2)]*count, [count*count]*count)
		self.doTest(g, count, True,  Radii(), [count]*count, [0]*count, None, None, None, None)
		self.doTest(g, count, False, Radii(straight=0), [1]*count, None, None, None, None, None)
		self.doTest(g, count, False, Radii(straight=1), [1]*count, None, None, None, None, None)
		self.doTest(g, count, False, Radii(straight=length), [2, 3, 3, 3, 2], None, None, None, None, None)
		self.doTest(g, count, False, Radii(walking=0), [1]*count, None, None, None, None, None)
		self.doTest(g, count, False, Radii(walking=1), [1]*count, None, None, None, None, None)
		self.doTest(g, count, False, Radii(walking=3), [2, 3, 3, 3, 2], None, None, None, None, None)
		self.doTest(g, count, False, Radii(steps=0), [1]*count, None, None, None, None, None)
		self.doTest(g, count, False, Radii(steps=1), [2, 3, 3, 3, 2], None, None, None, None, None)
		self.doTest(g, count, False, Radii(steps=2), [3, 4, 5, 4, 3], None, None, None, None, None)
		self.doTest(g, count, False, Radii(angular=1), [count]*count, None, None, None, None, None)
		pstalgo.FreeSegmentGraph(g)

	def test_aint_square(self):
		count = 4
		length = 3
		g = CreateSegmentSquareGraph(length)
		self.doTest(g, count, False, Radii(), [count]*count, [4]*count, None, [float(count-1)/5]*count, [math.pow(count,1.2)/5]*count, None)
		self.doTest(g, count, True,  Radii(), [count]*count, [4]*count, None, [9.0/13.0]*count, [math.pow(9,1.2)/13.0]*count, None)
		self.doTest(g, count, False, Radii(angular=80), [1]*count, [0]*count, None, None, None, None)
		self.doTest(g, count, False, Radii(angular=100), [3]*count, [2]*count, None, None, None, None)
		pstalgo.FreeSegmentGraph(g)

	def doTest(self, graph, line_count, weigh_by_length, radius, N, TD, TDW, aint_norm, aint_syntax_norm, aint_hillier_norm):
		node_counts = array.array('I', [0])*line_count
		total_depths = array.array('f', [0])*line_count
		total_lengths = array.array('f', [0])*line_count
		total_depth_lengths = array.array('f', [0])*line_count
		text = "limits=%s"%str(radius.toString())
		pstalgo.AngularIntegration(
			graph_handle = graph,
			radius = radius,
			weigh_by_length = weigh_by_length,
			angle_threshold = 0,
			angle_precision = 1, 
			out_node_counts = node_counts,
			out_total_depths = total_depths,
			out_total_weights = total_lengths,
			out_total_depth_weights = total_depth_lengths)
		if N is not None:
			self.assertEqual(node_counts, array.array('I', N), text)
		if TD is not None:
			self.assertTrue(IsArrayRoughlyEqual(total_depths, TD), text + " " + str(total_depths) + " != " + str(TD))
		if aint_norm is not None:
			scores = array.array('f', [0])*line_count
			if weigh_by_length:
				pstalgo.AngularIntegrationNormalizeLengthWeight(total_lengths, total_depth_lengths, line_count, scores)
			else:
				pstalgo.AngularIntegrationNormalize(node_counts, total_depths, line_count, scores)
			self.assertTrue(IsArrayRoughlyEqual(scores, aint_norm), text + " " + str(scores) + " != " + str(aint_norm))
		if aint_syntax_norm is not None:
			scores = array.array('f', [0])*line_count
			if weigh_by_length:
				pstalgo.AngularIntegrationSyntaxNormalizeLengthWeight(total_lengths, total_depth_lengths, line_count, scores)
			else:
				pstalgo.AngularIntegrationSyntaxNormalize(node_counts, total_depths, line_count, scores)
			self.assertTrue(IsArrayRoughlyEqual(scores, aint_syntax_norm), text + " " + str(scores) + " != " + str(aint_syntax_norm))
		if aint_hillier_norm is not None:
			scores = array.array('f', [0])*line_count
			if weigh_by_length:
				pstalgo.AngularIntegrationHillierNormalizeLengthWeight(total_lengths, total_depth_lengths, line_count, scores)
			else:
				pstalgo.AngularIntegrationHillierNormalize(node_counts, total_depths, line_count, scores)
			self.assertTrue(IsArrayRoughlyEqual(scores, aint_hillier_norm), text + " " + str(scores) + " != " + str(aint_hillier_norm))