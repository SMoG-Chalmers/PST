/*
Copyright 2019 Meta Berghauser Pont

This file is part of PST.

PST is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. The GNU General Public License
is intended to guarantee your freedom to share and change all versions
of a program--to make sure it remains free software for all its users.

PST is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PST. If not, see <http://www.gnu.org/licenses/>.
*/


#pragma once

#include <vector>


///////////////////////////////////////////////////////////////////////////////
//
//  CBitVector
//

class CBitVector {

protected:
	typedef unsigned long TWord;

// Data Members
protected:
	std::vector<TWord> m_bits;

// Operations
public:
	inline size_t size() const        { return m_bits.size() << 5; }
	inline void   resize(size_t size) { m_bits.resize((size + 31) >> 5); }
	inline void   clearAll()          { if (!m_bits.empty()) memset(&m_bits.front(), 0x00, m_bits.size() * sizeof(TWord)); }
	inline void   setAll()            { if (!m_bits.empty()) memset(&m_bits.front(), 0xFF, m_bits.size() * sizeof(TWord)); }
	inline bool   get(size_t index) const { return (m_bits[index >> 5] & ((TWord)1 << (index & 31))) != 0; }
	inline void   set(size_t index)   { m_bits[index >> 5] |= ((TWord)1 << (index & 31)); }
	inline void   clear(size_t index) { m_bits[index >> 5] &= ~((TWord)1 << (index & 31)); }

};