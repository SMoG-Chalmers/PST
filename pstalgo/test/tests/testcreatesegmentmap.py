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

class TestCreateSegmentMap(unittest.TestCase):

    def test_createsegmentmap(self):
        coords = array.array('d', [
            0, 0,
            1, 0,
        ])
        polys = array.array('i', [
            2,
        ])
        (res, algo) = pstalgo.CreateSegmentMap(pstalgo.common.RoadNetworkType.AXIAL_OR_SEGMENT, coords, polys)  # , tail=50, progress_callback=self._pstalgo.CreateAnalysisDelegateCallbackWrapper(delegate))
        pstalgo.Free(algo)

    T_COUNT = 20

    def _t_junctions(self, duplicate_end_vertex, lines_per_junction=1):
        """ A slanted line with T_COUNT junctions on it, where lines_per_junction lines end exactly
            on it at the same point, in SWEREF-like coordinates far from the data centre so that
            coordinates are rounded when converted to float. """
        x0, y0, dx, dy = 146000.0, 6398000.0, 103.0, 47.0
        coords = array.array('d', [x0, y0, x0 + dx, y0 + dy])
        polys = array.array('i', [2])
        for i in range(self.T_COUNT):
            t = (i + 0.37) / self.T_COUNT
            px, py = x0 + dx*t, y0 + dy*t
            for k in range(lines_per_junction):
                ox = -3.0 if lines_per_junction == 1 else -1.0 + 2.0*k  # Steep enough not to cross the neighbours
                coords.extend([px + ox, py + 20.0, px, py])
                if duplicate_end_vertex:
                    coords.extend([px, py])
                polys.append(3 if duplicate_end_vertex else 2)
        coords.extend([156000.0, 6410000.0, 156010.0, 6410000.0])  # Far away line, moves the data centre
        polys.append(2)
        return coords, polys

    def _segments_and_junctions(self, coords, polys, snap, degree_of_junction=3):
        """ Returns (segment count, number of points shared by degree_of_junction segments) """
        (res, algo) = pstalgo.CreateSegmentMap(pstalgo.common.RoadNetworkType.AXIAL_OR_SEGMENT, coords, polys, snap=snap, tail=0, deviation=0, extrude=snap)
        count = res.m_SegmentCount
        degree = {}
        for i in range(count):
            for p in (res.m_Segments[i*3], res.m_Segments[i*3+1]):
                degree[p] = degree.get(p, 0) + 1
        pstalgo.Free(algo)
        return count, sum(1 for d in degree.values() if d == degree_of_junction)

    def test_t_junctions_zero_snap(self):
        # Each T cuts the slanted line and connects to it: (T_COUNT + 1) pieces + T_COUNT T lines + far line
        coords, polys = self._t_junctions(duplicate_end_vertex=False)
        self.assertEqual(self._segments_and_junctions(coords, polys, snap=0), (2*self.T_COUNT + 2, self.T_COUNT))

    def test_t_junctions_duplicate_end_vertex(self):
        # A duplicated end vertex must not make the end count as connected
        coords, polys = self._t_junctions(duplicate_end_vertex=True)
        self.assertEqual(self._segments_and_junctions(coords, polys, snap=1), (2*self.T_COUNT + 2, self.T_COUNT))
        self.assertEqual(self._segments_and_junctions(coords, polys, snap=0), (2*self.T_COUNT + 2, self.T_COUNT))

    def test_t_junctions_shared_end_point(self):
        # Two lines ending at the same point on the slanted line: their shared end counts as
        # connected, but must still cut the slanted line (T_COUNT + 1 pieces + 2*T_COUNT lines + far line)
        coords, polys = self._t_junctions(duplicate_end_vertex=False, lines_per_junction=2)
        for snap in (0, 1):
            self.assertEqual(self._segments_and_junctions(coords, polys, snap=snap, degree_of_junction=4), (3*self.T_COUNT + 2, self.T_COUNT))

    def test_multipart_base_index(self):
        # Negative section = part of the same object as the next section
        coords = array.array('d', [
            0, 0, 10, 0,      # Object 0, part 1
            0, 50, 10, 50,    # Object 0, part 2
            0, 100, 10, 100,  # Object 1
        ])
        polys = array.array('i', [-1 - 2, 2, 2])
        (res, algo) = pstalgo.CreateSegmentMap(pstalgo.common.RoadNetworkType.AXIAL_OR_SEGMENT, coords, polys, snap=0, tail=0, deviation=0, extrude=0)
        bases = sorted(res.m_Segments[i*3+2] for i in range(res.m_SegmentCount))
        pstalgo.Free(algo)
        self.assertEqual(bases, [0, 0, 1])