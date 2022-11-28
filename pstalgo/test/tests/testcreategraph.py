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
from .common import IsArrayRoughlyEqual

class TestCreateGraph(unittest.TestCase):

    def test_creategraph(self):
        #   |
        # --|--
        #   |__
        line_coords = array.array('d', [0, 0, 2, 0, 1, 1, 1, -1, 2, -1])
        line_indices = array.array('I', [0, 1, 2, 3, 3, 4])
        unlinks = array.array('d', [1, 0])
        points = array.array('d', [-1, 0])

        graph_handle = pstalgo.CreateGraph(line_coords, line_indices, unlinks, points, None)
        self.assertIsNotNone(graph_handle)

        graph_info = pstalgo.GetGraphInfo(graph_handle)
        self.assertEqual(graph_info.m_LineCount, 3)
        self.assertEqual(graph_info.m_CrossingCount, 1)  # One of the 2 crossings was unlinked
        self.assertEqual(graph_info.m_PointCount, 1)

        lengths = array.array('f', [0]) * 3
        pstalgo.GetGraphLineLengths(graph_handle, lengths)
        IsArrayRoughlyEqual(lengths, [2, 2, 1])

        crossings = array.array('d', [0]) * 2
        pstalgo.GetGraphCrossingCoords(graph_handle, crossings)
        IsArrayRoughlyEqual(crossings, [1, -1])

        pstalgo.FreeGraph(graph_handle)

    def test_createsegmentgraph(self):
        line_coords = array.array('d', [0, 0, 1, 0])
        line_indices = array.array('I', [0, 1])
        segment_graph_handle = pstalgo.CreateSegmentGraph(line_coords, line_indices, None)
        self.assertIsNotNone(segment_graph_handle)
        pstalgo.FreeSegmentGraph(segment_graph_handle)