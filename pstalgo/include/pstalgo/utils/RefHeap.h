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

#include <memory>
#include <vector>
#include <pstalgo/Debug.h>

/**
 * A heap that keeps track of indices of its items, and supports
 * removal of items at any give index in O(log(N)) time.
 */
template <class T, class TUpdateHeapIndex>
class CRefHeap
{
public:
	typedef size_t index_t;

	static const index_t INVALID_INDEX = std::numeric_limits<index_t>::max();

	CRefHeap(TUpdateHeapIndex&& update_heap_index)
		: m_UpdateHeapIndex(std::forward<TUpdateHeapIndex>(update_heap_index))
	{}

	CRefHeap(const TUpdateHeapIndex&) = delete;

	inline void clear() { m_Items.clear(); }

	inline void reserve(index_t size) { m_Items.reserve(size); }

	inline bool empty() const { return m_Items.empty(); }

	inline index_t size() const { return (index_t)m_Items.size(); }
	
	inline const T& top() const
	{
		return m_Items.front();
	}

	void push(const T& item)
	{
		index_t at = (index_t)m_Items.size();
		m_Items.resize(m_Items.size() + 1);
		at = swim(item, at);
		set(at, T(item));
	}

	void push(T&& item)
	{
		index_t at = m_Items.size();
		m_Items.resize(m_Items.size() + 1);
		at = swim(item, at);
		set(at, std::forward<T>(item));
	}

	void pop()
	{
		ASSERT(!empty());
		m_UpdateHeapIndex(m_Items.front(), INVALID_INDEX);
		if (m_Items.size() > 1)
		{
			auto at = sift(m_Items.back(), 0, (index_t)m_Items.size() - 1);
			auto& item_at = m_Items[at];
			set(at, std::move(m_Items.back()));
		}
		m_Items.pop_back();
	}

	void removeAt(index_t index)
	{
		ASSERT(index < (index_t)size());
		m_UpdateHeapIndex(m_Items[index], INVALID_INDEX);
		if (index < m_Items.size() - 1)
		{
			auto& last_item = m_Items.back();
			index_t at = swim(last_item, index);
			if (at == index)
			{
				at = sift(last_item, index, (index_t)m_Items.size() - 1);
			}
			set(at, std::move(last_item));
		}
		m_Items.pop_back();
	}

private:
	TUpdateHeapIndex m_UpdateHeapIndex;
	std::vector<T> m_Items;

	index_t swim(const T& item, index_t at)
	{
		while (at > 0)
		{
			const index_t parent_index = parent_from_child(at);
			auto& parent = m_Items[parent_index];
			if (!(item < parent))
			{
				break;
			}
			set(at, std::move(parent));
			at = parent_index;
		}
		return at;
	}

	index_t sift(const T& item, index_t at, index_t item_count)
	{
		for (;;)
		{
			const auto first_child_index = first_child_from_parent(at);
			if (first_child_index >= item_count)
			{
				break;
			}
			const auto second_child_index = first_child_index + 1;
			const auto smallest_child_index = (second_child_index >= item_count || m_Items[first_child_index] < m_Items[second_child_index]) ? first_child_index : second_child_index;
			auto& smallest_child = m_Items[smallest_child_index];
			if (!(smallest_child < item))
			{
				break;
			}
			set(at, std::move(smallest_child));
			at = smallest_child_index;
		}
		return at;
	}

	inline void set(index_t index, T&& item)
	{
		auto& item_at = m_Items[index];
		item_at = std::forward<T>(item);
		m_UpdateHeapIndex(item_at, index);
	}

	inline static index_t parent_from_child(index_t index)
	{
		ASSERT(index > 0);
		return (index - 1) / 2; 
	}

	inline static index_t first_child_from_parent(index_t index)
	{
		return index * 2 + 1;
	}
};


template <class T, class TUpdateHeapIndex>
inline CRefHeap<T, TUpdateHeapIndex> make_ref_heap(TUpdateHeapIndex&& update_heap_index)
{
	return CRefHeap<T, TUpdateHeapIndex>(std::forward<TUpdateHeapIndex>(update_heap_index));
}