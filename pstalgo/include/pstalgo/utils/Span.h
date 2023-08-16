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

#include <vector>

namespace psta
{
	// TODO: Replace with std::span when available on all platforms

	template <class T>
	class span
	{
	public:
		span(T* elements, size_t size) : m_Data(elements), m_Size(size) {}
		span(T* begin, T* end) : m_Data(begin), m_Size(end - begin) {}

		inline size_t size() const { return m_Size; }

		inline T* data() { return m_Data; }
		inline const T* data() const { return m_Data; }

		inline T& back() { return m_Data[m_Size - 1]; }
		inline const T& back() const { return m_Data[m_Size - 1]; }

		inline T& operator[](size_t index) { return m_Data[index]; }
		inline const T& operator[](size_t index) const { return m_Data[index]; }

		T* begin() { return m_Data; }
		const T* begin() const { return m_Data; }

		T* end() { return m_Data + m_Size; }
		const T* end() const { return m_Data + m_Size; }

	protected:
		T* m_Data;
		size_t m_Size;
	};

	template <class T>
	span<T> make_span(T* data, size_t size) { return span<T>(data, size); }

	template <class T>
	const span<T> make_span(const T* data, size_t size) { return span<T>(const_cast<T*>(data), size); }

	template <class T>
	const span<T> make_span(const std::vector<T>& v) { return make_span(const_cast<T*>(v.data()), v.size()); }
}