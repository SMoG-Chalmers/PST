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

#include <pstalgo/Types.h>
#include <pstalgo/Vec2.h>

double2 PolygonCentroid(const double2* points, uint32 point_count, double& ret_area);

template <class T>
bool TestPointInRing(const TVec2<T>& point, const TVec2<T>* ring, size_t ring_size)
{
	if (ring_size < 3)
	{
		return false;
	}
	int winding_count = 0;
	auto p0 = ring[ring_size - 1];
	for (size_t i = 0; i < ring_size; ++i)
	{
		const auto& p1 = ring[i];
		const int crossing_vertical_mask = (int)((p1.x - point.x) * (p0.x - point.x) >= (T)0) - 1;
		const auto cross_prod = crp(p0 - point, p1 - p0);
		const int direction = (cross_prod > 0) - (cross_prod < 0);
		winding_count += (int)(direction & crossing_vertical_mask);
		p0 = p1;
	}
	return winding_count != 0;
}

template <class T>
bool TestPointInPolygon(const TVec2<T>& point, const TVec2<T>* perimeter, size_t perimeter_size, const TVec2<T>* const* holes, const size_t* hole_sizes, size_t hole_count)
{
	if (!TestPointInRing(point, perimeter, perimeter_size))
	{
		return false;
	}

	for (size_t hole_index = 0; hole_index < hole_count; ++hole_index)
	{
		if (TestPointInRing(point, holes[hole_index], hole_sizes[hole_index]))
		{
			return false;
		}
	}

	return true;
}