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

#include <algorithm>
#include <cstdlib>
#include <stdexcept>
#include <cstring>

#include <pstalgo/experimental/SparseDirectedGraph.h>

namespace
{
	static const unsigned int ALLOC_ALIGN_BYTES  = 64;
	static const unsigned int MIN_CAPACITY_BYTES = 4096;
}

namespace psta
{
	void* aligned_alloc(size_t size, size_t alignment)
	{
		#ifdef WIN32
			return _aligned_malloc(size, alignment);
		#else
			void* ptr;
			if (posix_memalign(&ptr, alignment, size))
				throw std::bad_alloc();
			return ptr;
		#endif
	}

	void aligned_free(void* ptr)
	{
		#ifdef WIN32
			_aligned_free(ptr);
		#else
			free(ptr);
		#endif
	}


	// CSparseDirectedGraphBase

	CSparseDirectedGraphBase::CSparseDirectedGraphBase()
	{
	}

	CSparseDirectedGraphBase::CSparseDirectedGraphBase(CSparseDirectedGraphBase&& other)
		: m_Data(other.m_Data)
		, m_Size(other.m_Size)
		, m_Capacity(other.m_Capacity)
		, m_NodeCount(other.m_NodeCount)
		, m_NodeHandles(std::move(other.m_NodeHandles))
	{
		other.m_Data = nullptr;
		other.m_Size = 0;
		other.m_Capacity = 0;
		other.m_NodeCount = 0;
	}

	CSparseDirectedGraphBase::~CSparseDirectedGraphBase()
	{
		Clear();
	}

	void CSparseDirectedGraphBase::Clear()
	{
		aligned_free(m_Data);
		m_Data = nullptr;
		m_Size = 0;
		m_Capacity = 0;
		m_NodeCount = 0;
	}

	void CSparseDirectedGraphBase::ReserveNodeCount(size_t node_count)
	{
		m_NodeHandles.reserve(node_count);
	}

	void CSparseDirectedGraphBase::operator=(CSparseDirectedGraphBase&& rhs)
	{
		m_Data = rhs.m_Data;
		rhs.m_Data = nullptr;
		m_Size = rhs.m_Size;
		rhs.m_Size = 0;
		m_Capacity = rhs.m_Capacity;
		rhs.m_Capacity = 0;
		m_NodeCount = rhs.m_NodeCount;
		rhs.m_NodeCount = 0;
		m_NodeHandles = std::move(rhs.m_NodeHandles);
	}

	void CSparseDirectedGraphBase::Copy(const CSparseDirectedGraphBase& other)
	{
		Clear();
		m_Data = (char*)aligned_alloc(other.m_Capacity, ALLOC_ALIGN_BYTES);
		memcpy(m_Data, other.m_Data, other.m_Size);
		m_Capacity = other.m_Capacity;
		m_Size = other.m_Size;
		m_NodeCount = other.m_NodeCount;
		m_NodeHandles = other.m_NodeHandles;
	}

	char* CSparseDirectedGraphBase::Alloc(unsigned int size)
	{
		auto at = m_Size;
		if ((at & (ALLOC_ALIGN_BYTES - 1)) + size > ALLOC_ALIGN_BYTES)
			at = align_up(at, (unsigned int)ALLOC_ALIGN_BYTES);
		NeedCapacity(at + m_Size);
		m_Size = at + size;
		return m_Data + at;
	}

	void CSparseDirectedGraphBase::NeedCapacity(unsigned int capacity)
	{
		if (m_Capacity >= capacity)
			return;
		const auto new_capacity = std::max(MIN_CAPACITY_BYTES, round_up_to_closest_power_of_two(capacity));
		auto* new_data = (char*)aligned_alloc(new_capacity, ALLOC_ALIGN_BYTES);
		memcpy(new_data, m_Data, m_Size);
		aligned_free(m_Data);
		m_Data = new_data;
		m_Capacity = new_capacity;
	}


	// CSparseDirectedGraph

	void CSparseDirectedGraph::ReserveNodeCount(size_t node_count)
	{
		CSparseDirectedGraphBase::ReserveNodeCount(node_count);
		NeedCapacity(node_count * (m_NodeSize + m_EdgeSize));  // Assume on avarage one edge per node
	}
}