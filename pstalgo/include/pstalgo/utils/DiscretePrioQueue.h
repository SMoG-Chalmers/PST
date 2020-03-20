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

#include <pstalgo/Debug.h>

#include <vector>
#include <cstring>


// This is a very specialized priority queue that has been specifically optimized for
// graph traversal. Although its functionality is a bit restricted it has insert and 
// pop operations with time complexity O(1).
//
// At a given time it can only contain priorities that has a max-min priority range that 
// is less than the given 'prio_range' on construction. Also, once an item with priority 
// N has ben popped it is not allowed to insert a new item with priority < N. Finally, 
// prio order is inverted - if prio X < Y then X has higher priority than Y.

template <typename TPrio, typename TValue> 
class TDiscretePrioQueue
{
public:
	TDiscretePrioQueue(size_t prio_range = 0)
	{
		Init(prio_range);
	}

	void Init(size_t prio_range)
	{
		m_Tops.clear();
		m_Tops.resize(prio_range, (unsigned int)-1);
		m_Items.clear();
		Reset(0);
	}
		
	void Reset(TPrio prio)
	{
		m_AtPrio = prio;
		m_AtIndex = 0;
		if (!m_Items.empty())
		{
			if (!m_Tops.empty())
				memset(&m_Tops.front(), -1, m_Tops.size() * sizeof(m_Tops.front()));
			m_Items.clear();
		}
	}

	bool Empty() const { return m_Items.empty(); }

	void Insert(TPrio prio, const TValue& value)
	{
		ASSERT(prio - m_AtPrio < m_Tops.size());
		TPrio at_index = (TPrio)(m_AtIndex + (prio - m_AtPrio));
		if (at_index >= m_Tops.size())
			at_index -= (unsigned int)m_Tops.size();
		const unsigned int my_index = (unsigned int)m_Items.size();
		if (-1 != m_Tops[at_index])
			m_Items[m_Tops[at_index]].m_Prev = my_index;
		m_Items.resize(m_Items.size() + 1);
		SItem& new_item = m_Items.back();
		new_item.m_Next = m_Tops[at_index];
		new_item.m_Prev = -1 - at_index;
		new_item.m_Value = value;
		m_Tops[at_index] = my_index;
	}

	TValue& Top()
	{
		StepToTop();
		return m_Items[m_Tops[m_AtIndex]].m_Value;
	}

	void Pop()
	{
		ASSERT(!Empty());
		StepToTop();
		const unsigned int index_to_pop = m_Tops[m_AtIndex];
		const unsigned int next = m_Items[index_to_pop].m_Next;
		m_Tops[m_AtIndex] = next;
		if (next != -1)
		{
			m_Items[next].m_Prev = -1 - (int)m_AtIndex;
		}
		if (index_to_pop != m_Items.size()-1)
		{
			const SItem& back_item = m_Items.back();
			if (back_item.m_Prev < 0)
				m_Tops[-1 - back_item.m_Prev] = index_to_pop;
			else
				m_Items[back_item.m_Prev].m_Next = index_to_pop;
			if (-1 != back_item.m_Next)
				m_Items[back_item.m_Next].m_Prev = index_to_pop;
			m_Items[index_to_pop] = back_item;
		}
		m_Items.pop_back();
	}

private:
	void StepToTop()
	{
		ASSERT( !Empty() );
		while (-1 == m_Tops[m_AtIndex])
		{
			++m_AtPrio;
			++m_AtIndex;
			if (m_Tops.size() == m_AtIndex)
				m_AtIndex = 0;
		}
	}

	size_t m_AtIndex;  // = m_AtPrio % m_PrioRange
	TPrio  m_AtPrio;

	std::vector<unsigned int> m_Tops;  // Index to m_Items, or -1 if empty

	struct SItem
	{
		int          m_Prev;   // If top item: negative index in m_Tops, else positive index in m_Items
		unsigned int m_Next;   // Index to next item in m_Items, or -1 if no next item
		TValue       m_Value;
	};
	std::vector<SItem> m_Items;				
};
