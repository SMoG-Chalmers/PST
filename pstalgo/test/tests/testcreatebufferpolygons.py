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
from .common import IsRoughlyEqual

class TestCreateBufferPolygons(unittest.TestCase):

    def test_create_buffer_polygons(self):
        lineCoords = array.array('d', [
            0, 0,
            2, 2,
            0, 2,
            2, 0,
        ])
        values1 = array.array('f', [
            1,
            2,
        ])
        values2 = array.array('f', [
            3,
            4,
        ])
        ranges = [
            (0, 1),
            (1, 2),
        ]
        (raster, handle1) = pstalgo.CompareResults(
            lineCoords1=lineCoords, 
            values1=values1, 
            lineCoords2=None, 
            values2=values2)
        (polygonCountPerRange, polygonData, polygonCoords, handle2) = pstalgo.RasterToPolygons(raster, ranges)
        try:
            pass
            # dataPos = 0
            # coordPos = 0
            # for rangeIndex in range(len(ranges)):
            #     print(f"Range #{rangeIndex}:")
            #     for polygonIndex in range(polygonCountPerRange[rangeIndex]):
            #         print(f"  Polygon #{polygonIndex}:")
            #         ringCount = polygonData[dataPos]
            #         dataPos += 1
            #         for ringIndex in range(ringCount):
            #             pointCount = polygonData[dataPos]
            #             dataPos += 1
            #             coords = ["(%.2f %.2f)" % (polygonCoords[coordPos + pointIndex * 2], polygonCoords[coordPos + pointIndex * 2 + 1]) for pointIndex in range(pointCount)]
            #             coordPos += pointCount * 2
            #             print(f"      Ring #{ringIndex}: " + ' '.join(coords))
        finally:
            pstalgo.Free(handle1)
            pstalgo.Free(handle2)