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