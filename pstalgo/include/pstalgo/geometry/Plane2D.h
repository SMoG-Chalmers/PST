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

template <class TType>
struct TPlane2D
{
	TVec2<TType> Normal;
	TType T;

	inline bool IsInFront(const TVec2<TType>& point) const;
	inline bool IsBehind(const TVec2<TType>& point) const;

	inline bool IsInFront(const TRect<TType>& rect) const;
	inline bool IsBehind(const TRect<TType>& rect) const;
};

template <class TType>
inline bool TPlane2D<TType>::IsInFront(const TVec2<TType>& point) const
{
	return dot(this->Normal, point) >= this->T;
}

template <class TType>
inline bool TPlane2D<TType>::IsBehind(const TVec2<TType>& point) const
{
	return dot(this->Normal, point) <= this->T;
}

template <class TType>
inline bool TPlane2D<TType>::IsInFront(const TRect<TType>& rect) const
{
	return IsInFront(TVec2<TType>(
		rect.m_Min.x * (Normal.x > 0) + rect.m_Max.x * (Normal.x <= 0),
		rect.m_Min.y * (Normal.y > 0) + rect.m_Max.y * (Normal.y <= 0)
	));
}

template <class TType>
inline bool TPlane2D<TType>::IsBehind(const TRect<TType>& rect) const
{
	return IsBehind(TVec2<TType>(
		rect.m_Min.x * (Normal.x < 0) + rect.m_Max.x * (Normal.x > 0),
		rect.m_Min.y * (Normal.y < 0) + rect.m_Max.y * (Normal.y > 0)
	));
}


typedef TPlane2D<float> Plane2Df;

// Returns: False if entire line segment is behind plane. True otherwise.
template <class TType>
bool ClipLineSegment(TVec2<TType>& p0, TVec2<TType>& p1, const TPlane2D<TType>& plane)
{
	static const TType EPSILON = 0.001f;
	const auto t0 = dot(plane.Normal, p0) - plane.T;
	const auto t1 = dot(plane.Normal, p1) - plane.T;
	if (t0 < 0)
	{
		const auto len = t1 - t0;
		if (len + t0 < EPSILON)
		{
			return false;
		}
		const auto t = t0 / len;
		p0.x -= (p1.x - p0.x) * t;
		p0.y -= (p1.y - p0.y) * t;
	}
	else if (t1 < 0)
	{
		const auto len = t0 - t1;
		if (len + t1 < EPSILON)
		{
			return false;
		}
		const auto t = t1 / len;
		p1.x -= (p0.x - p1.x) * t;
		p1.y -= (p0.y - p1.y) * t;
	}
	return true;
}