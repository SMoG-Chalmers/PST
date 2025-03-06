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

import math, unittest, pstalgo
from .common import IsRoughlyEqual


class TestCalculateIsovists(unittest.TestCase):

    def test_calculateisovists_perimeter(self):
        geometry = pstalgo.IsovistContextGeometry()
        isovist_context = pstalgo.CreateIsovistContext(isovistContextGeometry = geometry)

        try:
            r = 1
            segmentCount = 4
            rSegmented = r * self._calcRadForSegmentedCircle(segmentCount)
            expectedIsovistCoords = [(0,rSegmented), (rSegmented,0), (0, -rSegmented), (-rSegmented, 0)]
            (pointCount, points, isovistHandle, area, visibleObstacles, visibleAttractionPoints, visibleAttractionPolygons) = pstalgo.CalculateIsovist(
                isovist_context=isovist_context, 
                originX=0, 
                originY=0, 
                max_view_distance=r, 
                field_of_view_degrees=360, 
                direction_degrees=0, 
                perimeter_segment_count=4)

            try:
                isovistCoords = self._unpackIsovistCoords(points, pointCount)
                self._compareIsovists(expectedIsovistCoords, isovistCoords)
            finally:
                pstalgo.Free(isovistHandle)

        finally:
            pstalgo.Free(isovist_context)
 
    def _calcRadForSegmentedCircle(self, segmentCount):
        halfAngle = math.pi / segmentCount
        return math.sqrt(math.pi / (segmentCount * math.sin(halfAngle) * math.cos(halfAngle)))

    def _unpackIsovistCoords(self, points, pointCount):
        outCoords = []
        for i in range(pointCount):
            outCoords.append((points[i*2], points[i*2+1]))
        return outCoords

    def _compareIsovists(self, actual, expected):
        self.assertEqual(len(actual), len(expected), "Length of actual and expected isovists do not match")
        actual_start_index = -1
        for i in range(len(actual)):
            if IsRoughlyEqual(actual[i][0], expected[0][0]) and IsRoughlyEqual(actual[i][1], expected[0][1]):
                actual_start_index = i
                break
        self.assertFalse(-1 == actual_start_index, "No matching start index found between actual and expected isovists")

        for i in range(len(actual)):
            actual_index = (actual_start_index + i) % len(actual)
            self.assertTrue(IsRoughlyEqual(actual[actual_index][0], expected[i][0]), "Coordinates of actual and expected isovists do not match")
            self.assertTrue(IsRoughlyEqual(actual[actual_index][1], expected[i][1]), "Coordinates of actual and expected isovists do not match")