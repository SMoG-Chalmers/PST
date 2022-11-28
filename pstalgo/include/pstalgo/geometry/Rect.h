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

template <typename T, typename TVec> struct TRect 
{
public:
	TRect() {}
	TRect(T left, T top, T right, T bottom)
	: m_Left(left), m_Top(top), m_Right(right), m_Bottom(bottom) {}

public:
	inline bool operator==(const TRect& other) const { return other.m_Left == m_Left && other.m_Top == m_Top &&other.m_Right == m_Right &&other.m_Bottom == m_Bottom; }
	inline T Width() const { return m_Right - m_Left; }
	inline T Height() const { return m_Bottom - m_Top; }
	inline T MinSize() const { using namespace std; return min(Width(), Height()); }
	inline T CenterX() const { return (m_Left + m_Right) / 2; }
	inline T CenterY() const { return (m_Top + m_Bottom) / 2; }
	inline T Area() const { return Width() * Height(); }
	inline void Set(T left, T top, T right, T bottom) { m_Left = left; m_Top = top; m_Right = right; m_Bottom = bottom; }
	inline void SetMax();
	inline void SetEmpty() { m_Left = m_Top = m_Right = m_Bottom = 0; }
	inline bool Contains(T x, T y) const { return (x >= m_Left) && (y >= m_Top) && (x < m_Right) && (y < m_Bottom); }
	inline void GrowToIncludePoint(T x, T y) { if (x < m_Left) m_Left = x; if (y < m_Top) m_Top = y; if (x > m_Right) m_Right = x; if (y > m_Bottom) m_Bottom = y; }
	inline bool Overlaps(const TRect& other) const { return m_Left < other.m_Right && m_Top < other.m_Bottom && m_Right > other.m_Left && m_Bottom > other.m_Top; }
	inline TRect Inflated(T amount) const { return TRect(m_Left - amount, m_Top - amount, m_Right + amount, m_Bottom + amount); }
	inline TRect Inflated(T left, T top, T right, T bottom) const { return TRect(m_Left - left, m_Top - top, m_Right + right, m_Bottom + bottom); }
	inline TRect Offsetted(T x, T y) const { return TRect(m_Left + x, m_Top + y, m_Right + x, m_Bottom + y); }
	inline bool IsEmpty() const { return m_Right <= m_Left || m_Bottom <= m_Top; }
	
	inline static TRect BBFromPoints(const TVec* coords, unsigned int count)
	{
		if (0 == count)
			return EMPTY;
		TRect rc(coords->x, coords->y, coords->x, coords->y);
		for (unsigned int i = 1; i < count; ++i)
			rc.GrowToIncludePoint(coords[i].x, coords[i].y);
		return rc;
	}

	static TRect Intersection(const TRect& a, const TRect& b) 
	{ 
		using namespace std;
		return TRect(
			max(a.m_Left, b.m_Left),
			max(a.m_Top, b.m_Top),
			min(a.m_Right, b.m_Right),
			min(a.m_Bottom, b.m_Bottom));
	}
	
	inline T PerpendicularDistanceToPoint(int x, int y) const
	{
		using namespace std;
		int d = m_Left - x;
		d = max(d, x - m_Right);
		d = max(d, m_Top - y);
		d = max(d, y - m_Bottom);
		return d;
	}

	T m_Left;
	T m_Top;
	T m_Right;
	T m_Bottom;

	static const TRect EMPTY;
};

template <typename T, typename TVec> const TRect<T, TVec> TRect<T, TVec>::EMPTY(0, 0, 0, 0);

typedef TRect<int, int2> CRecti;
typedef TRect<float, float2> CRectf;
typedef TRect<double, double2> CRectd;

inline CRectf CRectfFromCRecti(const CRecti& rc)
{
	return CRectf((float)rc.m_Left, (float)rc.m_Top, (float)rc.m_Right, (float)rc.m_Bottom);
}

template<> inline void TRect<int,int2>::SetMax()
{
	m_Left = m_Top = 0x80000000;
	m_Right = m_Bottom = 0x7FFFFFFF;
}