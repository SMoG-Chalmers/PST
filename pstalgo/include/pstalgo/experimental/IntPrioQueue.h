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
	template <class T>
	class int_prio_queue
	{
	public:
		typedef unsigned int prio_t;

		void reserve(size_t size);

		bool empty() const;

		const T& top() const;

		void push(const T& data);

		void pop();

		size_t size() const;

	private:
		enum { INVALID_ELEMENT_INDEX = (unsigned int)-1 };

		struct SElement
		{
			T m_Data;
			unsigned int m_Next;
		};

		unsigned int min_prio() const;

		unsigned int new_element();

		void free_element(unsigned int);

		mutable prio_t m_MinPrio = 0;

		unsigned int m_Size = 0;

		std::vector<unsigned int> m_Buckets;
		std::vector<SElement> m_Elements;
		std::vector<unsigned int> m_FreeElements;
	};

	template <class T> void int_prio_queue<T>::reserve(size_t size)
	{
		m_Elements.reserve(size);
		m_FreeElements.reserve(size);
	}

	template <class T> bool int_prio_queue<T>::empty() const
	{
		return 0 == m_Size;
	}
	
	template <class T> const T& int_prio_queue<T>::top() const
	{
		return m_Elements[m_Buckets[min_prio()]].m_Data;
	}

	template <class T> void int_prio_queue<T>::push(const T& data)
	{
		const auto prio = (prio_t)data;
		m_MinPrio = std::min(m_MinPrio, prio);
		if (prio >= m_Buckets.size())
			m_Buckets.resize(prio + 1, INVALID_ELEMENT_INDEX);
		auto& bucket = m_Buckets[prio];
		const auto element_index = new_element();
		auto& e = m_Elements[element_index];
		e.m_Data = data;
		e.m_Next = bucket;
		bucket = element_index;
		++m_Size;
	}

	template <class T> void int_prio_queue<T>::pop()
	{
		auto& bucket = m_Buckets[min_prio()];
		const auto next = m_Elements[bucket].m_Next;
		free_element(bucket);
		bucket = next;
		--m_Size;
		if (empty())
		{
			m_Elements.clear();
			m_FreeElements.clear();
		}
	}

	template <class T> size_t int_prio_queue<T>::size() const
	{
		return m_Size;
	}

	template <class T> unsigned int int_prio_queue<T>::min_prio() const
	{
		for (; m_MinPrio < m_Buckets.size() && INVALID_ELEMENT_INDEX == m_Buckets[m_MinPrio]; ++m_MinPrio);
		return m_MinPrio;
	}

	template <class T> unsigned int int_prio_queue<T>::new_element()
	{
		if (m_FreeElements.empty())
		{
			m_Elements.resize(m_Elements.size() + 1);
			return (unsigned int)(m_Elements.size() - 1);
		}
		const auto index = m_FreeElements.back();
		m_FreeElements.pop_back();
		return index;
	}

	template <class T> void int_prio_queue<T>::free_element(unsigned int index)
	{
		m_FreeElements.push_back(index);
	}
}


// Test

//psta::int_prio_queue<unsigned int> q;
//q.push(7);
//q.push(3);
//q.push(10);
//q.push(4);
//q.push(3);
//q.push(3);
//q.push(1);
//q.push(5);

//std::vector<unsigned int> v;
//while (!q.empty())
//{
//	v.push_back(q.top());
//	q.pop();
//}
