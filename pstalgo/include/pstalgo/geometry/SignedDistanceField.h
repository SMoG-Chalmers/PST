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

#include <cstdint>
#include <vector>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/utils/Arr2d.h>
#include <pstalgo/Vec2.h>

namespace psta
{
	struct SPolygon
	{
		typedef std::vector<float2> ring_t;
		std::vector<ring_t> Rings;
	};
	
	std::vector<SPolygon> PolygonsFromSdfGrid(const Arr2dView<const float>& sdf, float range_min, float range_max = std::numeric_limits<float>::max());

	void AddLineSegmentToSdf(Arr2dView<float>& sdf, const float2& p0, const float2& p1, float maxDistance);

	void AddLineSegmentToSdf2(Arr2dView<float>& sdf, const float2& p0, const float2& p1, float maxDistance, float resolution, float strength);
}