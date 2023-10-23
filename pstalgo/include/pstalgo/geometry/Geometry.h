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

# pragma once

#include <cmath>
#include <pstalgo/maths.h>
#include <pstalgo/geometry/Rect.h>

bool TestAABBCircleOverlap(const float2& bb_half_size, const float2& circle_center, float circle_radius);

bool TestAABBCircleOverlap(const float2& bb_center, const float2& bb_half_size, const float2& circle_center, float radius);

template <class T>
inline bool TestAABBFullyInsideCircle(const TVec2<T>& bb_center, const TVec2<T>& bb_half_size, const TVec2<T>& circle_center, T radius)
{
	const T x = std::abs(circle_center.x - bb_center.x) + bb_half_size.x;
	const T y = std::abs(circle_center.y - bb_center.y) + bb_half_size.y;
	return x * x + y * y <= radius * radius;
}

bool TestAABBOBBOverlap(const CRectf& aabb, const float2& center, const float2& half_size, const float2& orientation);

bool TestAABBCapsuleOverlap(const CRectf& aabb, const float2& p0, const float2 p1, float radius);

template <typename T>
T DistanceFromPointToLineSegmentSqrd(const TVec2<T>& pt, const std::pair<TVec2<T>, TVec2<T>>& line, float line_length, const TVec2<T>& line_tangent)
{
	const auto localPos = pt - line.first;
	const auto t = dot(line_tangent, localPos);
	auto d = localPos.x * line_tangent.y - localPos.y * line_tangent.x;
	d *= d;
	d += (float)((t < 0) | (t > line_length)) * std::numeric_limits<T>::max();
	d = std::min(d, localPos.getLengthSqr());
	return std::min(d, (pt - line.second).getLengthSqr());
}

template <class T>
inline bool TestLineSegmentAndCircleOverlap(const TVec2<T>& p0, const TVec2<T>& p1, T radius)
{
	const T radius_sqrd = radius * radius;

	if (p0.getLengthSqr() < radius_sqrd || p1.getLengthSqr() < radius_sqrd)
	{
		return true;
	}

	const auto line_v = p1 - p0;
	const auto line_length = line_v.getLength();
	if (line_length == 0)
	{
		return false;
	}
	const auto line_tangent = line_v * ((T)1 / line_length);
	const TVec2<T> line_normal(line_tangent.y, -line_tangent.x);

	const float dist = dot(p0, line_normal);
	if (dist*dist >= radius_sqrd)
	{
		return false;
	}

	const auto at = dot(line_tangent, p0);

	return at > -line_length && at < 0;
}

template <class T>
inline bool TestLineSegmentsIntersection(const TVec2<T>& a0, const TVec2<T>& a1, const TVec2<T>& b0, const TVec2<T>& b1)
{
	const auto aV = a1 - a0;
	if (crp(aV, b0 - a0) * crp(aV, b1 - a0) > 0)
		return false;
	const auto bV = b1 - b0;
	return crp(bV, a0 - b0) * crp(bV, a1 - b0) <= 0;
}