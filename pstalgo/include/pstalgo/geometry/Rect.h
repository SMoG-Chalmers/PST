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

#include <pstalgo/utils/Macros.h>
#include <pstalgo/Vec2.h>

// Defined in 'pstalgo/geometry/Geometry.h'
template <class T> inline bool TestAABBFullyInsideCircle(const TVec2<T>& bb_center, const TVec2<T>& bb_half_size, const TVec2<T>& circle_center, T radius);


template <typename T> struct TRect 
{
public:
	TRect() {}
	TRect(const TVec2<T>& _min, const TVec2<T>& _max)
		: m_Min(_min), m_Max(_max) {}
	TRect(T left, T top, T right, T bottom)
	: m_Left(left), m_Top(top), m_Right(right), m_Bottom(bottom) {}
	template <class TIterator>
	TRect(TIterator beg, TIterator end);
		
public:
	template <typename TOther>
	inline explicit operator TRect<TOther>() const { return TRect<TOther>((TOther)m_Left, (TOther)m_Top, (TOther)m_Right, (TOther)m_Bottom); }

	inline bool operator==(const TRect& other) const { return other.m_Left == m_Left && other.m_Top == m_Top &&other.m_Right == m_Right &&other.m_Bottom == m_Bottom; }
	inline const TVec2<T>& Min() const { return m_Min; }
	inline const TVec2<T>& Max() const { return m_Max; }
	inline T Width() const { return m_Right - m_Left; }
	inline T Height() const { return m_Bottom - m_Top; }
	inline TVec2<T> Size() const { return TVec2<T>(Width(), Height()); }
	inline T MinSize() const { using namespace std; return min(Width(), Height()); }
	inline TVec2<T> Center() const { return TVec2<T>(CenterX(), CenterY()); }
	inline T CenterX() const { return (m_Left + m_Right) / 2; }
	inline T CenterY() const { return (m_Top + m_Bottom) / 2; }
	inline T Area() const { return Width() * Height(); }
	inline void Set(T left, T top, T right, T bottom) { m_Left = left; m_Top = top; m_Right = right; m_Bottom = bottom; }
	inline void SetMax();
	inline void SetEmpty() { m_Left = m_Top = m_Right = m_Bottom = 0; }
	inline bool Contains(T x, T y) const { return (x >= m_Left) && (y >= m_Top) && (x < m_Right) && (y < m_Bottom); }
	inline bool OverlapsCircle(const TVec2<T>& center, float radius) const { return TestAABBCircleOverlap(Center(), Size() * .5f, center, radius); }
	inline bool FullyInsideCircle(const TVec2<T>& center, float radius) const { return TestAABBFullyInsideCircle(Center(), Size() * .5f, center, radius); }
	inline bool IsFullyInside(const TRect& r) const { return m_Min.x >= r.m_Min.x && m_Min.y >= r.m_Min.y && m_Max.x <= r.m_Max.x && m_Max.y <= r.m_Max.y; }
	inline void GrowToIncludePoint(T x, T y) { if (x < m_Left) m_Left = x; if (y < m_Top) m_Top = y; if (x > m_Right) m_Right = x; if (y > m_Bottom) m_Bottom = y; }
	inline void GrowToIncludePoint(const TVec2<T>& pt) { GrowToIncludePoint(pt.x, pt.y); }
	inline void GrowToIncludeRect(const TRect& other) { GrowToIncludePoint(other.m_Min); GrowToIncludePoint(other.m_Max); }
	inline bool Overlaps(const TRect& other) const { return m_Left < other.m_Right && m_Top < other.m_Bottom && m_Right > other.m_Left && m_Bottom > other.m_Top; }
	inline void Inflate(T amount) { m_Min.x -= amount; m_Min.y -= amount; m_Max.x += amount; m_Max.y += amount; }
	inline TRect Translated(const TVec2<T>& v) const { return TRect(m_Min + v, m_Max + v); }
	inline TRect Inflated(T amount) const { return TRect(m_Left - amount, m_Top - amount, m_Right + amount, m_Bottom + amount); }
	inline TRect Inflated(T left, T top, T right, T bottom) const { return TRect(m_Left - left, m_Top - top, m_Right + right, m_Bottom + bottom); }
	inline TRect Offsetted(T x, T y) const { return TRect(m_Left + x, m_Top + y, m_Right + x, m_Bottom + y); }
	inline bool IsEmpty() const { return m_Right <= m_Left || m_Bottom <= m_Top; }
	inline bool Valid() const { return m_Right >= m_Left && m_Bottom >= m_Top; }
	inline bool Invalid() const { return !Valid(); }

	inline TRect operator-(const TVec2<T>& rhs) const { return TRect(m_Min - rhs, m_Max - rhs); }

	inline static TRect BBFromPoints(const TVec2<T>* coords, unsigned int count)
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
	
	static TRect Union(const TRect& a, const TRect& b)
	{
		using namespace std;
		return TRect(
			min(a.m_Left, b.m_Left),
			min(a.m_Top, b.m_Top),
			max(a.m_Right, b.m_Right),
			max(a.m_Bottom, b.m_Bottom));
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

	ALLOW_NAMELESS_STRUCT_BEGIN
	union
	{
		struct
		{
			T m_Left;
			T m_Top;
			T m_Right;
			T m_Bottom;
		};
		struct
		{
			TVec2<T> m_Min;
			TVec2<T> m_Max;
		};
	};
	ALLOW_NAMELESS_STRUCT_END

	static const TRect EMPTY;
	static const TRect INVALID;
};

template <typename T>
template <class TIterator>
TRect<T>::TRect(TIterator beg, TIterator end)
{
	if (beg < end)
	{
		*this = *beg;
		for (auto it = beg + 1; it < end; ++it)
		{
			GrowToIncludeRect(*it);
		}
	}
	else
	{
		SetEmpty();
	}
}

template <typename T> const TRect<T> TRect<T>::EMPTY(0, 0, 0, 0);
template <typename T> const TRect<T> TRect<T>::INVALID(std::numeric_limits<T>::max(), std::numeric_limits<T>::max(), std::numeric_limits<T>::lowest(), std::numeric_limits<T>::lowest());

typedef TRect<int> CRecti;
typedef TRect<float> CRectf;
typedef TRect<double> CRectd;

inline CRectf CRectfFromCRecti(const CRecti& rc)
{
	return CRectf((float)rc.m_Left, (float)rc.m_Top, (float)rc.m_Right, (float)rc.m_Bottom);
}

template<> inline void TRect<int>::SetMax()
{
	m_Left = m_Top = 0x80000000;
	m_Right = m_Bottom = 0x7FFFFFFF;
}