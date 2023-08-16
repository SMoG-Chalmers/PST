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
        (polygonCount, polygonData, polygonCoords, rangesRaster, gradientRaster, handle) = pstalgo.CreateBufferPolygons(lineCoords, 1, 1)
        try:
            pointCount = polygonData[1]
            dataPos = 0
            coordPos = 0
            for polygonIndex in range(polygonCount):
                print("Polygon #%d:" % polygonIndex)
                ringCount = polygonData[dataPos]
                dataPos += 1
                for ringIndex in range(ringCount):
                    pointCount = polygonData[dataPos]
                    dataPos += 1
                    coords = ["(%.2f %.2f)" % (polygonCoords[coordPos + pointIndex * 2], polygonCoords[coordPos + pointIndex * 2 + 1]) for pointIndex in range(pointCount)]
                    coordPos += pointCount * 2
                    print("\t" + ' '.join(coords))
        finally:
            pstalgo.Free(handle)