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

namespace psta
{
	template <class T>
	class Arr2dView
	{
	public:
		Arr2dView(T* elements, uint32_t width, uint32_t height, uint32_t element_stride)
			: m_Elements(elements), m_Width(width), m_Height(height), m_ElementStride(element_stride)
		{}

		inline const uint32_t Width() const
		{
			return m_Width;
		}

		inline const uint32_t Height() const
		{
			return m_Height;
		}

		inline size_t size() const
		{
			return m_Width * m_Height;
		}

		inline void Clear(T value = T())
		{
			for (size_t i = 0; i < m_ElementStride * m_Height; ++i)
			{
				m_Elements[i] = value;
			}
		}

		inline uint32_t StrideBytes() const
		{
			return m_ElementStride * sizeof(T);
		}

		T& at(uint32_t x, uint32_t y)
		{
			return m_Elements[y * m_ElementStride + x];
		}

		const T& at(uint32_t x, uint32_t y) const
		{
			return m_Elements[y * m_ElementStride + x];
		}

		template <class TLambda>
		inline void for_each(TLambda&& fn)
		{
			for (size_t i = 0; i < m_Width * m_Height; ++i)
			{
				fn(m_Elements[i]);
			}
		}

		template <class TLambda>
		inline void for_each_coords(TLambda&& fn)
		{
			auto* row = m_Elements;
			for (uint32_t y = 0; y < m_Height; ++y)
			{
				for (uint32_t x = 0; x < m_Width; ++x)
				{
					fn(x, y, *(row + x));
				}
				row += m_ElementStride;
			}
		}

		template <class TLambda>
		inline void for_each_coords(TLambda&& fn) const
		{
			const auto* row = m_Elements;
			for (uint32_t y = 0; y < m_Height; ++y)
			{
				for (uint32_t x = 0; x < m_Width; ++x)
				{
					fn(x, y, *(row + x));
				}
				row += m_ElementStride;
			}
		}

		inline void FlipY()
		{
			const uint32_t strideBytes = StrideBytes();
			const uint32_t half_row_count = (m_Height >> 1);
			char* a = (char*)m_Elements;
			char* b = a + ((m_Height - 1) * strideBytes);
			void* rowBuffer = malloc(strideBytes);
			for (uint32_t i = 0; i < half_row_count; ++i)
			{
				memcpy(rowBuffer, a, strideBytes);
				memcpy(a, b, strideBytes);
				memcpy(b, rowBuffer, strideBytes);
				a += strideBytes;
				b -= strideBytes;
			}
			free(rowBuffer);
		}

		inline Arr2dView<T> sub_view(uint32_t x, uint32_t y, uint32_t width, uint32_t height)
		{
			return Arr2dView<T>(&at(x, y), width, height, m_ElementStride);
		}

	protected:
		T* m_Elements;
		uint32_t m_Width;
		uint32_t m_Height;
		uint32_t m_ElementStride;
	};

	template <typename T>
	inline Arr2dView<T> MakeArr2dView(T* elements, uint32_t width, uint32_t height, uint32_t element_stride)
	{
		return Arr2dView<T>(elements, width, height, element_stride);
	}

	template <class T>
	class Arr2d : public Arr2dView<T>
	{
	public:
		Arr2d(uint32_t width, uint32_t height)
			: Arr2dView<T>(nullptr, width, height, width)
			, m_Vec(width * height)
		{
			Arr2dView<T>::m_Elements = m_Vec.data();
		}

	private:
		std::vector<T> m_Vec;
	};
}