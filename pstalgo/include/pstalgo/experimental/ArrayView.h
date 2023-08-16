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

#include "../Debug.h"

namespace psta
{
	template <class TCollection, class TLambda>
	void enumerate(TCollection& collection, TLambda&& lambda)
	{
		size_t idx = 0;
		for (auto& element : collection)
			lambda(idx++, element);
	}

	template <typename T>
	class array_view
	{
	public:
		array_view(T* arr, size_t size) : m_Begin(arr), m_End(arr + size) {}

		size_t size() const { return m_End - m_Begin; }

		T& operator[](size_t idx) { ASSERT(idx < size());  return m_Begin[idx]; }
		const T& operator[](size_t idx) const { ASSERT(idx < size());  return m_Begin[idx]; }

		T* data() { return m_Begin; }
		const T* data() const { return m_Begin; }

		T* begin() { return m_Begin; }
		const T* begin() const { return m_Begin; }

		T* end() { return m_End; }
		const T* end() const { return m_End; }

		array_view sub_view(size_t first, size_t size) { return array_view(m_Begin + first, size); }
		const array_view sub_view(size_t first, size_t size) const { return array_view(m_Begin + first, size); }

	private:
		T* m_Begin;
		T* m_End;
	};

	template <typename T>
	array_view<T> make_array_view(T* arr, size_t size) { return array_view<T>(arr, size); }

	template <typename T, size_t TSize>
	array_view<T> make_array_view(T (&arr)[TSize]) { return array_view<T>(arr, TSize); }
}