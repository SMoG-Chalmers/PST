/*
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
*/


#pragma once

#include <pstalgo/Vec2.h>

/**
*  Calculates convex hull of a set of points.
*  The supplied point array must not contain duplicates and must
*  be sorted by increasing x and increasing y.
*/
int ConvexHull(const float2* sorted_points, int count, float2* ret_hull);

/**
*  Calculates area of a convex polygon.
*/
float ConvexPolyArea(const float2* points, unsigned int count);
