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
import math
import unittest
import pstalgo
from pstalgo import DistanceType, Radii
from .common import *
from .graphs import CreateChainGraph, CreateSquareGraph

class TestNetowrkIntegration(unittest.TestCase):

	def test_NInt_single(self):
		line_count = 1
		line_length = 3
		graph = CreateChainGraph(line_count, line_length)
		tests = [
			(Radii(), [-1], [1], [0]),
		]
		self.runTests(graph, tests, line_count)
		pstalgo.FreeGraph(graph)

	def test_NInt_chain(self):
		line_count = 5
		line_length = 3
		graph = CreateChainGraph(line_count, line_length)
		tests = [
			(Radii(), [0.352, 0.704, 1.056, 0.704, 0.352], [line_count]*line_count, [10, 7, 6, 7, 10]),
			(Radii(straight=0), None, [1]*line_count, None),
			(Radii(straight=1), None, [1]*line_count, None),
			(Radii(straight=line_length), None, [2, 3, 3, 3, 2], None),
			(Radii(walking=0), None, [1]*line_count, None),
			(Radii(walking=1), None, [1]*line_count, None),
			(Radii(walking=3), None, [2, 3, 3, 3, 2], None),
			(Radii(steps=0), None, [1]*line_count, None),
			(Radii(steps=1), None, [2, 3, 3, 3, 2], None),
			(Radii(steps=2), None, [3, 4, 5, 4, 3], None),
			(Radii(angular=1), None, [line_count]*line_count, None),
		]
		self.runTests(graph, tests, line_count)
		pstalgo.FreeGraph(graph)

	def runTests(self, graph, test_tuples, line_count):
		integration = array.array('f', [0])*line_count
		node_count = array.array('I', [0])*line_count
		total_depth = array.array('f', [0])*line_count
		for t in test_tuples:
			text = "limits=%s"%str(t[0].toString())
			pstalgo.NetworkIntegration(
				graph_handle = graph,
				radius = t[0],
				out_line_integration = integration if t[1] is not None else None,
				out_line_node_count = node_count if t[2] is not None else None,
				out_line_total_depth = total_depth if t[3] is not None else None)
			if t[1] is not None:
				self.assertTrue(IsArrayRoughlyEqual(integration, t[1]), text + " " + str(integration) + " != " + str(t[1]))
			if t[2] is not None:
				self.assertEqual(node_count, array.array('I', t[2]), text)
			if t[3] is not None:
				self.assertEqual(total_depth, array.array('f', t[3]), text)