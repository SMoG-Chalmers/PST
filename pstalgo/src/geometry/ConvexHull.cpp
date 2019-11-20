/*
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
*/

#include <algorithm>
#include <pstalgo/Debug.h>
#include <pstalgo/geometry/ConvexHull.h>

// LinePointTest(): tests if a point is Left|On|Right of an infinite line.
//    Input:  three points P0, P1, and P
//    Return: <0 for P left of the line through P0 and P1
//            =0 for P on the line
//            >0 for P right of the line
inline float LinePointTest(const float2& P0, const float2& P1, const float2& P)
{
	return (P.x - P0.x)*(P1.y - P0.y) - (P1.x - P0.x)*(P.y - P0.y);
}

int ConvexHull(const float2* sorted_points, int count, float2* ret_hull)
{
#ifdef _DEBUG
	for (int i = 1; i < count; ++i)
	{
		if (sorted_points[i - 1] == sorted_points[i])
		{
			ASSERT(false && "point array contains duplicates");
			return -1;
		}

		if (sorted_points[i - 1].x > sorted_points[i].x)
		{
			ASSERT(false && "point array is not sorted");
			return -1;
		}

		if (sorted_points[i - 1].x < sorted_points[i].x)
			continue;

		if (sorted_points[i - 1].y > sorted_points[i].y)
		{
			ASSERT(false && "point array is not sorted");
			return -1;
		}
	}
#endif

	if (count < 3)
	{
		if (count > 0)
			memcpy(ret_hull, sorted_points, count * sizeof(float2));
		return count;
	}

	int num_hull_points = 0;


	// LOWER-Y HULL

	// Find index of point with lowest Y-value among those with maximum X-value
	int p_max_min = count - 1;
	for (; p_max_min > 0 && sorted_points[p_max_min].x == sorted_points[p_max_min - 1].x; --p_max_min);

	ret_hull[num_hull_points++] = sorted_points[0];
	for (int i = 1; i <= p_max_min; ++i)
	{
		if ((i == p_max_min) || LinePointTest(sorted_points[0], sorted_points[p_max_min], sorted_points[i]) > 0.0f)
		{
			for (; (num_hull_points > 1) && (LinePointTest(ret_hull[num_hull_points - 2], ret_hull[num_hull_points - 1], sorted_points[i]) >= 0.0f); --num_hull_points);
			ret_hull[num_hull_points++] = sorted_points[i];
		}
	}


	// Transition point
	if (count - 1 != p_max_min)
		ret_hull[num_hull_points++] = sorted_points[count - 1];


	// HIGHER-Y HULL

	const auto min_len = num_hull_points;

	// Find index of point with highest Y-value among those with minimum X-value
	int p_min_max = 0;
	for (; p_min_max < count - 1 && sorted_points[p_min_max].x == sorted_points[p_min_max + 1].x; ++p_min_max);

	for (int i = count - 2; i >= p_min_max; --i)
	{
		if ((i == p_min_max) || LinePointTest(sorted_points[count - 1], sorted_points[p_min_max], sorted_points[i]) > 0.0f)
		{
			for (; (num_hull_points > min_len) && (LinePointTest(ret_hull[num_hull_points - 2], ret_hull[num_hull_points - 1], sorted_points[i]) >= 0.0f); --num_hull_points);
			if (0 != i)
				ret_hull[num_hull_points++] = sorted_points[i];
		}
	}

	ASSERT(num_hull_points <= count);

	return num_hull_points;
}

float ConvexPolyArea(const float2* points, unsigned int count)
{
	float area = 0;
	for (int i = 1; i < (int)count - 1; ++i)
		area += fabs(crp(points[i] - points[0], points[i + 1] - points[0]));
	return 0.5f * area;
}