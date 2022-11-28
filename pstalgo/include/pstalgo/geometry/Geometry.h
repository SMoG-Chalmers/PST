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

#include <pstalgo/maths.h>
#include <pstalgo/geometry/Rect.h>

bool TestAABBCircleOverlap(const float2& bb_half_size, const float2& circle_center, float circle_radius);

bool TestAABBOBBOverlap(const CRectf& aabb, const float2& center, const float2& half_size, const float2& orientation);

bool TestAABBCapsuleOverlap(const CRectf& aabb, const float2& p0, const float2 p1, float radius);