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
import unittest
import pstalgo

class TestCreateJunctions(unittest.TestCase):

    def test_two_layers(self):
        coords0 = array.array('d', [0, 0, 2, 0])
        lines0 = array.array('I', [0, 1])
        coords1 = array.array('d', [1, 1, 1, -1])
        lines1 = array.array('I', [0, 1])
        (res, algo) = pstalgo.CreateJunctions(coords0, lines0, coords1, lines1, None, None)
        self.assertEqual(res.m_PointCount, 1)
        pstalgo.Free(algo)
        unlinks = array.array('d', [1, 0])
        (res, algo) = pstalgo.CreateJunctions(coords0, lines0, coords1, lines1, unlinks, None)
        self.assertEqual(res.m_PointCount, 0)
        pstalgo.Free(algo)

    def test_one_layer_two_lines(self):
        coords0 = array.array('d', [-1, 0, 0, 0, 1, 0])
        lines0 = array.array('I', [0, 1, 1, 2])
        (res, algo) = pstalgo.CreateJunctions(coords0, lines0, None, None, None, None)
        self.assertEqual(res.m_PointCount, 0)  # Two intersecting lines within same layer shouldn't qualify as a junction
        pstalgo.Free(algo)

    def test_one_layer_three_lines(self):
        coords0 = array.array('d', [-1, 0, 0, 0, 1, 0, 0, 1])
        lines0 = array.array('I', [0, 1, 1, 2, 1, 3])
        (res, algo) = pstalgo.CreateJunctions(coords0, lines0, None, None, None, None)
        self.assertEqual(res.m_PointCount, 1) # Three (or more) intersecting lines in same point within same layer qualifies as a junction
        pstalgo.Free(algo)