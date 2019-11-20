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

import array
import math
import unittest
import pstalgo
from pstalgo import DistanceType, Radii
from .graphs import CreateChainGraph, CreateSquareGraph

class TestReach(unittest.TestCase):

	def test_reach_chain(self):
		line_count = 3
		line_length = 3
		graph = CreateChainGraph(line_count, line_length)

		tests = [
			(Radii(), [3, 3, 3], [9, 9, 9], [0, 0, 0]),
			(Radii(straight=0), [1, 1, 1], [3, 3, 3], [0, 0, 0]),
			(Radii(straight=1), [1, 1, 1], [3, 3, 3], [math.pi]*3),
			(Radii(straight=3), [2, 3, 2], [6, 9, 6], [3*3*math.pi]*3),
			(Radii(walking=0), [1, 1, 1], [3, 3, 3], [0, 0, 0]),
			(Radii(walking=1), [1, 1, 1], [3, 3, 3], [0, 0, 0]),
			(Radii(walking=3), [2, 3, 2], [6, 9, 6], [0, 0, 0]),
			(Radii(steps=0), [1, 1, 1], [3, 3, 3], [0, 0, 0]),
			(Radii(steps=1), [2, 3, 2], [6, 9, 6], [0, 0, 0]),
			(Radii(steps=2), [3, 3, 3], [9, 9, 9], [0, 0, 0]),
			(Radii(angular=1), [3, 3, 3], [9, 9, 9], [0, 0, 0]),
		]

		self.runTests(graph, tests, line_count)

		pstalgo.FreeGraph(graph)

	def test_reach_square(self):
		line_count = 4
		line_length = 3
		graph = CreateSquareGraph(line_length)

		tests = [
			(Radii(), [4, 4, 4, 4], [line_length*line_count]*line_count, [line_length*line_length]*line_count),
			(Radii(angular=80), [1, 1, 1, 1], [line_length*1]*line_count, [0]*line_count),
			(Radii(angular=100), [3, 3, 3, 3], [line_length*3]*line_count, [line_length*line_length]*line_count),
			(Radii(angular=190), [4, 4, 4, 4], [line_length*line_count]*line_count, [line_length*line_length]*line_count),
		]

		self.runTests(graph, tests, line_count)

		pstalgo.FreeGraph(graph)

	def runTests(self, graph, test_tuples, line_count):
		reached_count = array.array('I', [0])*line_count
		reached_length = array.array('f', [0])*line_count
		reached_area = array.array('f', [0])*line_count
		for t in test_tuples:
			text = "limits=%s"%str(t[0].toString())
			pstalgo.Reach(
				graph_handle = graph,
				radius = t[0],
				out_reached_count = reached_count if t[1] is not None else None,
				out_reached_length = reached_length if t[2] is not None else None,
				out_reached_area = reached_area if t[3] is not None else None)
			if t[1] is not None:
				self.assertEqual(reached_count, array.array('I', t[1]), text)
			if t[2] is not None:
				self.assertEqual(reached_length, array.array('f', t[2]), text)
			if t[3] is not None:
				self.assertTrue(IsArrayRoughlyEqual(reached_area, t[3]), text + " " + str(reached_area) + " != " + str(t[3]))


def IsRoughlyEqual(v0, v1, max_rel_diff=0.0001):
	if 0 == v0: 
		return 0 == v1
	return abs((v1-v0)/v0) <= max_rel_diff

def IsArrayRoughlyEqual(a0, a1, max_rel_diff=0.0001):
	if len(a0) != len(a1):
		return False
	for i in range(len(a0)):
		if not IsRoughlyEqual(a0[i], a1[i], max_rel_diff):
			return False
	return True