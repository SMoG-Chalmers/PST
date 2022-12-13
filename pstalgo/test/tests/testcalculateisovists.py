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


class TestCalculateIsovists(unittest.TestCase):

    def test_calculateisovists_1(self):
        polygons = [
             [(-5, 5), (-5,-5), (5,-5), (5, 5)],
        ]
        origins = [
            (0,0),
        ]
        expected_isovists = [
             [(-5, 5), (5, 5), (5,-5), (-5,-5)],
        ]
        self._runTest(polygons, origins, 10, 64, expected_isovists)

    def test_calculateisovists_2(self):
        polygons = [
             [(-5, 5), (-5,-5), (5,-5), (5, 5)],
             [(-1,-2), (0,-2), (0,-3)],
        ]
        origins = [
            (0,0),
        ]
        expected_isovists = [
             [(-5, 5), (5, 5), (5,-5), (0,-5), (0,-2), (-1,-2), (-2.5,-5), (-5,-5)],
        ]
        self._runTest(polygons, origins, 10, 64, expected_isovists)

    def test_calculateisovists_clip(self):
        polygons = [
             [(-5, 5), (-5,-5), (5,-5), (5, 5)],
        ]
        origins = [
            (0,0),
        ]
        expected_isovists = [
             [(-5,2.5), (-2.5,5), (2.5,5), (5,2.5), (5,-2.5), (2.5,-5), (-2.5,-5), (-5,-2.5)],
        ]
        self._runTest(polygons, origins, 7.5, 4, expected_isovists)

    def test_calculateisovists_perimeter(self):
        polygons = [
        ]
        origins = [
            (1,2),
        ]
        expected_isovists = [
             [(6,2), (1,-3), (-4,2), (1,7)],
        ]
        self._runTest(polygons, origins, 5, 4, expected_isovists)
    
    def _runTest(self, polygons, origins, max_radius, perimeter_segment_count, expected_isovists):

        point_count_per_polygon = array.array('I', [len(polygon) for polygon in polygons])
        
        polygon_coords = []
        for polygon in polygons:
            for pt in polygon:
                polygon_coords.append(pt[0])
                polygon_coords.append(pt[1])
        polygon_coords = array.array('d', polygon_coords)

        origin_coords = []
        for pt in origins:
            origin_coords.append(pt[0])
            origin_coords.append(pt[1])
        origin_coords = array.array('d', origin_coords)

        (res, algo) = pstalgo.CalculateIsovists(point_count_per_polygon, polygon_coords, origin_coords, max_radius, perimeter_segment_count, None)
        try:
            self.assertEqual(len(expected_isovists), res.m_IsovistCount, "Unexpected isovist count")

            coordinate_element_index = 0
            for isovist_index in range(res.m_IsovistCount):
                point_count = res.m_PointCountPerIsovist[isovist_index]
                polygon = []
                for i in range(point_count):
                    polygon.append((res.m_IsovistPoints[coordinate_element_index], res.m_IsovistPoints[coordinate_element_index+1]))
                    coordinate_element_index += 2
                self._compareIsovists(expected_isovists[isovist_index], polygon)
        finally:        
            pstalgo.Free(algo)

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