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

#include <cmath>

template <typename T>
struct TVec2 {

public:
	T x;
	T y;

public:
	TVec2() {}
	TVec2(T _x, T _y) : x(_x), y(_y) {}

	template <typename TOther>
	inline explicit operator TVec2<TOther>() const { return TVec2<TOther>((TOther)x, (TOther)y); }

public:
	inline T getLength() const { return sqrt(getLengthSqr()); }
	inline T getLengthSqr() const { return x*x + y*y; }
	inline void normalize() { const T s = (T)1 / getLength(); x *= s; y *= s; }
	inline TVec2 normalized() const { const float s = 1.f / getLength(); return TVec2(x * s, y * s); }
	inline unsigned char getMajorAxis() const { return (abs(y) > abs(x)) & 1; }

public:
	inline T     operator[](int idx) const       { return (&x)[idx]; }
	inline T&    operator[](int idx)             { return (&x)[idx]; }
	inline TVec2  operator-() const               { return TVec2(-x, -y); }
	inline TVec2  operator-(const TVec2& v) const  { return TVec2(x - v.x, y - v.y); }
	inline TVec2  operator+(const TVec2& v) const  { return TVec2(x + v.x, y + v.y); }
	inline TVec2  operator*(const T t)  const     { return TVec2(x * t, y * t); }
	inline TVec2  operator/(const T t)  const     { return TVec2(x / t, y / t); }
	inline void  operator+=(const TVec2& t)       { x += t.x; y += t.y; }
	inline const TVec2& operator*=(T s)           { x *= s; y *= s; return *this; }
	inline const TVec2& operator/=(T s)           { const auto s_inv = (T)1 / s; x *= s_inv; y *= s_inv; return *this; }
	inline bool  operator==(const TVec2& v) const { return (x == v.x) && (y == v.y); }
	inline bool  operator!=(const TVec2& v) const { return (x != v.x) || (y != v.y); }
	inline bool  operator<(const TVec2& v)  const { return (x == v.x) ? (y < v.y) : (x < v.x); }
};

typedef TVec2<int> int2;
typedef TVec2<float> float2;
typedef TVec2<double> double2;

template <typename T>
inline T dot(const TVec2<T>& a, const TVec2<T>& b) { return (a.x * b.x) + (a.y * b.y); }

template <typename T>
inline T crp(const TVec2<T>& a, const TVec2<T>& b) { return (a.x * b.y) - (a.y * b.x); }