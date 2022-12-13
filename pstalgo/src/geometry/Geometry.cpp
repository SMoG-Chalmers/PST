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

#include <algorithm>
#include <cmath>
#include <pstalgo/Maths.h>
#include <pstalgo/geometry/Rect.h>

bool TestAABBCircleOverlap(const float2& bb_half_size, const float2& circle_center, float circle_radius)
{
	using namespace std;
	const float2 d(abs(circle_center.x) - bb_half_size.x, abs(circle_center.y) - bb_half_size.y);
	if (d.x > circle_radius || d.y > circle_radius)
		return false;
	if (d.x <= 0 && d.y <= 0)
		return true;
	return d.x*d.x + d.y*d.y <= circle_radius*circle_radius;
}

bool TestAABBCircleOverlap(const float2& bb_center, const float2& bb_half_size, const float2& circle_center, float radius)
{
	const float dx = fabs(circle_center.x - bb_center.x);
	if (dx >= bb_half_size.x + radius)
		return false;
	const float dy = fabs(circle_center.y - bb_center.y);
	if (dy >= bb_half_size.y + radius)
		return false;
	if (dx < bb_half_size.x || dy < bb_half_size.y)
		return true;
	return sqr(dx - bb_half_size.x) + sqr(dy - bb_half_size.y) < sqr(radius);
}

bool TestAABBProjectionOverlap(const CRectf& aabb, const float2& v, float range_min, float range_max)
{
	float bb_min, bb_max;
	if (same_sign(v.x, v.y))
	{
		bb_min = aabb.m_Left * v.x + aabb.m_Top * v.y;
		bb_max = aabb.m_Right * v.x + aabb.m_Bottom * v.y;
	}
	else
	{
		bb_min = aabb.m_Right * v.x + aabb.m_Top * v.y;
		bb_max = aabb.m_Left * v.x + aabb.m_Bottom * v.y;
	}
	if (bb_min > bb_max)
		std::swap(bb_min, bb_max);
	return bb_max >= range_min && bb_min <= range_max;
}

bool TestAABBOBBOverlap(const CRectf& aabb, const float2& center, const float2& half_size, const float2& orientation)
{
	const CRectf bb0 = aabb.Offsetted(-center.x, -center.y);

	if (!TestAABBProjectionOverlap(bb0, orientation, -half_size.x, half_size.x) ||
		!TestAABBProjectionOverlap(bb0, float2(orientation.y, -orientation.x), -half_size.y, half_size.y))
		return false;
	
	float2 corners[4];
	const float2 vx = orientation * half_size.x;
	const float2 vy = float2(orientation.y, -orientation.x) * half_size.y;
	corners[0] = vy + vx;
	corners[1] = vy - vx;
	corners[2] = -corners[0];
	corners[3] = -corners[1];
	CRectf bb1(corners->x, corners->y, corners->x, corners->y);
	for (unsigned char i = 1; i < 4; ++i)
		bb1.GrowToIncludePoint(corners[i].x, corners[i].y);
	return bb0.Overlaps(bb1);
}

bool TestAABBCapsuleOverlap(const CRectf& aabb, const float2& p0, const float2 p1, float radius)
{
	const float2 bb_center(aabb.CenterX(), aabb.CenterY());
	const float2 bb_half_size(.5f * aabb.Width(), .5f * aabb.Height());

	if (TestAABBCircleOverlap(bb_half_size, p0 - bb_center, radius))
		return true;

	if (p1 == p0)
		return false;

	if (TestAABBCircleOverlap(bb_half_size, p1 - bb_center, radius))
		return true;
	
	const float2 center = (p0 + p1) *.5f;
	const float2 v = p1 - p0;
	const float length = v.getLength();
	const float2 orientation = v * (1.0f / length);
	return TestAABBOBBOverlap(aabb, center, float2(.5f * length, radius), orientation);
}
