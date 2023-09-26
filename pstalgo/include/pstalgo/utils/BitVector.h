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

#include <pstalgo/utils/Bit.h>
#include <vector>


///////////////////////////////////////////////////////////////////////////////
//
//  CBitVector
//

template <typename TWord = size_t>
class bit_vector {

// Data Members
protected:
	std::vector<TWord> m_bits;
	size_t m_Size = 0;
	const unsigned int WORD_BIT_COUNT = sizeof(TWord) * 8;

// Operations
public:
	inline bool   empty() const       { return 0 == m_Size; }
	inline size_t size() const        { return m_Size; }
	inline void   resize(size_t size) { m_Size = size;  m_bits.resize((size + WORD_BIT_COUNT - 1) / WORD_BIT_COUNT); }
	inline void   clearAll()          { if (!m_bits.empty()) memset(&m_bits.front(), 0x00, m_bits.size() * sizeof(TWord)); }
	inline void   setAll()            { if (!m_bits.empty()) memset(&m_bits.front(), 0xFF, m_bits.size() * sizeof(TWord)); }
	inline bool   get(size_t index) const { return (m_bits[index / WORD_BIT_COUNT] & ((TWord)1 << (index & (WORD_BIT_COUNT - 1)))) != 0; }
	inline void   set(size_t index)   { m_bits[index / WORD_BIT_COUNT] |= ((TWord)1 << (index & (WORD_BIT_COUNT - 1))); }
	inline void   clear(size_t index) { m_bits[index / WORD_BIT_COUNT] &= ~((TWord)1 << (index & (WORD_BIT_COUNT - 1))); }
	
	template <class TFunc>
	inline void forEachSetBit(TFunc&& fn) const
	{
		if (empty())
		{
			return;
		}
		auto* at = m_bits.data();
		auto* end = at + m_bits.size();
		for (size_t base_index = 0; at < end; at++, base_index += WORD_BIT_COUNT)
		{
			auto w = *at;
			while (w)
			{
				const auto bit_index = psta::bit_scan_reverse(w);
				const auto index = base_index + bit_index;
				if (index >= m_Size)
				{
					return;
				}
				w ^= (TWord)1 << bit_index;
				fn(index);
			}
		}
	}
};

typedef bit_vector<unsigned int> CBitVector;