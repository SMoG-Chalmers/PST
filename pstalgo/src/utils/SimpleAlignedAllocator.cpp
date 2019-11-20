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

#include <cstdlib>

#include <pstalgo/utils/SimpleAlignedAllocator.h>
#include <pstalgo/Debug.h>

// TODO: Move!
inline void* aligned_malloc(size_t size, size_t align) 
{
	void *result;
	#ifdef _MSC_VER 
		result = _aligned_malloc(size, align);
	#else 
		if (posix_memalign(&result, align, size)) result = 0;
	#endif
	return result;
}

// TODO: Move!
inline void aligned_free(void *ptr)
{
	#ifdef _MSC_VER 
		_aligned_free(ptr);
	#else 
		free(ptr);
	#endif
}

CSimpleAlignedAllocator::CSimpleAlignedAllocator(unsigned int block_size, unsigned int alignment_bits)
: m_CurrentUsage(0)
, m_BlockSize(block_size)
, m_AlignmentBits(alignment_bits)
{
}

CSimpleAlignedAllocator::~CSimpleAlignedAllocator()
{
	FreeAll();
}

void CSimpleAlignedAllocator::FreeAll()
{
	for (auto it = m_Blocks.begin(); m_Blocks.end() != it; ++it)
		aligned_free(*it);
}

void* CSimpleAlignedAllocator::Alloc(size_t size)
{
	if (size > m_BlockSize)
	{
		ASSERT(false);
		return 0x0;
	}

	if ((m_CurrentUsage >> m_AlignmentBits) != ((m_CurrentUsage + size - 1) >> m_AlignmentBits))
	{
		const unsigned int mask = (1 << m_AlignmentBits) - 1;
		m_CurrentUsage = (m_CurrentUsage + mask) & ~mask;
	}

	if (m_Blocks.empty() || (size > m_BlockSize - m_CurrentUsage))
	{
		m_Blocks.push_back(aligned_malloc(m_BlockSize, 1 << m_AlignmentBits));
		m_CurrentUsage = 0;
	}
	
	void* p = (char*)m_Blocks.back() + m_CurrentUsage;
	m_CurrentUsage += (unsigned int)size;
	
	return p;
}
