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
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/utils/Macros.h>
#include <pstalgo/Vec2.h>
#include <pstalgo/experimental/ArrayView.h>

namespace psta
{
	template <class T, class TItemIterator>
	class LooseBspTree
	{
	public:
		typedef float real_t;
		typedef TRect<real_t> bb_t;
		typedef void* node_handle_t;

		LooseBspTree() {}

		LooseBspTree(const LooseBspTree&) = delete;

		LooseBspTree(LooseBspTree&& other)
			: m_Nodes(std::move(other.m_Nodes))
			, m_ItemsBegin(std::move(other.m_ItemsBegin))
		{
		}

		LooseBspTree& operator=(LooseBspTree&& rhs)
		{
			m_Nodes = std::move(rhs.m_Nodes);
			m_ItemsBegin = std::move(rhs.m_ItemsBegin);
			return *this;
		}

		inline void Clear();

		inline node_handle_t Root() const { return &m_Nodes.front(); }

		inline bool IsLeaf(node_handle_t node_handle) const;

		inline const bb_t& NodeBB(node_handle_t node_handle) const;

		inline node_handle_t Child0(node_handle_t node_handle) const;
		inline node_handle_t Child1(node_handle_t node_handle) const;

		inline TItemIterator NodeItemsBegin(node_handle_t node_handle) const;
		inline TItemIterator NodeItemsEnd(node_handle_t node_handle) const;

		template <class TBBFromItem>
		inline void Recreate(TItemIterator begin, TItemIterator end, size_t max_depth, size_t max_objects_per_leaf, TBBFromItem&& bbFromItem);

		template <class TBBFromItem>
		inline static LooseBspTree FromObjects(TItemIterator begin, TItemIterator end, size_t max_depth, size_t max_objects_per_leaf, TBBFromItem&& bbFromItem);

		template <class TBBTest, class TItemVisitor>
		inline void VisitItems(TBBTest&& bb_test, TItemVisitor&& item_visitor);

		template <class TFunc>
		inline void ForEachRangeInBB(const bb_t& bb, TFunc&& fn);

	private:
		struct Node
		{
			bb_t     BB;
			uint32_t ItemIndexBeg;
			uint32_t ItemIndexEnd;
			uint32_t Child0;
			uint32_t Child1;

			static const uint32_t INVALID_NODE_INDEX = (uint32_t)-1;

			inline bool IsLeaf() const { return INVALID_NODE_INDEX == Child0; }
		};

		template <class TFunc>
		inline void ForEachSubRangeInBB(uint32_t node_index, const bb_t& bb, TFunc&& fn, std::pair<uint32_t, uint32_t>& pending_range);

		inline static Node& NodeFromHandle(node_handle_t node_handle) { return *(Node*)node_handle; }

		template <class TBBFromItem>
		inline void CreateSubtree(uint32_t base_item_index, TItemIterator begin, TItemIterator end, size_t max_depth, size_t max_objects_per_leaf, TBBFromItem&& bbFromItem);

		template <class BBTest, class ItemVisitor>
		inline void VisitItems(size_t node_index, BBTest&& bb_test, ItemVisitor&& item_visitor);

		std::vector<Node> m_Nodes;
		TItemIterator m_ItemsBegin;
	};

	// In-place binary ordering of sequence. Returns iterator to beginning of first right item.
	template <class TItemIterator, class TTestLeft>
	TItemIterator binary_partition(TItemIterator begin, TItemIterator end, TTestLeft&& testLeft)
	{
		--end;
		for (;;)
		{
			for (; begin <= end && testLeft(*begin); ++begin);
			for (; begin <= end && !testLeft(*end); --end);
			if (begin > end)
			{
				return begin;
			}
			std::swap(*begin, *end);
			++begin;
			--end;
		}
	}

	template <class T, class TItemIterator>
	template <class TBBFromItem>
	inline void LooseBspTree<T, TItemIterator>::Recreate(TItemIterator begin, TItemIterator end, size_t max_depth, size_t max_objects_per_leaf, TBBFromItem&& bbFromItem)
	{
		m_Nodes.clear();
		if (end > begin)
		{
			m_ItemsBegin = begin;
			CreateSubtree(0, begin, end, max_depth, max_objects_per_leaf, std::forward<TBBFromItem>(bbFromItem));
		}
	}

	template <class T, class TItemIterator>
	template <class TBBFromItem>
	inline LooseBspTree<T, TItemIterator> LooseBspTree<T, TItemIterator>::FromObjects(TItemIterator begin, TItemIterator end, size_t max_depth, size_t max_objects_per_leaf, TBBFromItem&& bbFromItem)
	{
		LooseBspTree tree;
		tree.Recreate(begin, end, max_depth, max_objects_per_leaf, std::forward<TBBFromItem>(bbFromItem));
		return tree;
	}

	template <class T, class TItemIterator>
	inline void LooseBspTree<T, TItemIterator>::Clear()
	{
		m_Nodes.clear();
	}

	template <class T, class TItemIterator>
	inline bool LooseBspTree<T, TItemIterator>::IsLeaf(node_handle_t node_handle) const
	{
		return NodeFromHandle(node_handle).IsLeaf();
	}

	template <class T, class TItemIterator>
	inline const typename LooseBspTree<T, TItemIterator>::bb_t& LooseBspTree<T, TItemIterator>::NodeBB(node_handle_t node_handle) const
	{
		return NodeFromHandle(node_handle).BB;
	}

	template <class T, class TItemIterator>
	inline typename LooseBspTree<T, TItemIterator>::node_handle_t LooseBspTree<T, TItemIterator>::Child0(node_handle_t node_handle) const
	{
		return &m_Nodes[NodeFromHandle(node_handle).Child0];
	}

	template <class T, class TItemIterator>
	inline typename LooseBspTree<T, TItemIterator>::node_handle_t LooseBspTree<T, TItemIterator>::Child1(node_handle_t node_handle) const
	{
		return &m_Nodes[NodeFromHandle(node_handle).Child1];
	}

	template <class T, class TItemIterator>
	inline TItemIterator LooseBspTree<T, TItemIterator>::NodeItemsBegin(node_handle_t node_handle) const
	{
		return m_ItemsBegin + NodeFromHandle(node_handle).ItemIndexBeg;
	}

	template <class T, class TItemIterator>
	inline TItemIterator LooseBspTree<T, TItemIterator>::NodeItemsEnd(node_handle_t node_handle) const
	{
		return m_ItemsBegin + NodeFromHandle(node_handle).ItemIndexEnd;
	}

	template <class T, class TItemIterator>
	template <class TBBTest, class TItemVisitor>
	void LooseBspTree<T, TItemIterator>::VisitItems(TBBTest&& bb_test, TItemVisitor&& item_visitor)
	{
		if (!m_Nodes.empty())
		{
			VisitItems(0, std::forward<TBBTest>(bb_test), std::forward<TItemVisitor>(item_visitor));
		}
	}

	template <class T, class TItemIterator>
	template <class TBBFromItem>
	inline void LooseBspTree<T, TItemIterator>::CreateSubtree(uint32_t base_item_index, TItemIterator begin, TItemIterator end, size_t max_depth, size_t max_objects_per_leaf, TBBFromItem&& bbFromItem)
	{
		const size_t item_count = end - begin;

		// Bounding box
		bb_t bb;
		if (item_count > 0)
		{
			bb = bbFromItem(*begin);
			for (auto it = begin + 1; it < end; ++it)
			{
				bb.GrowToIncludeRect(bbFromItem(*it));
			}
		}
		else
		{
			bb.SetEmpty();
		}

		// Leaf?
		if (item_count <= max_objects_per_leaf || max_depth <= 1)
		{
			Node node;
			node.BB = bb;
			node.ItemIndexBeg = base_item_index;
			node.ItemIndexEnd = base_item_index + (uint32_t)item_count;
			node.Child0 = Node::INVALID_NODE_INDEX;
			node.Child1 = Node::INVALID_NODE_INDEX;
			m_Nodes.push_back(node);
			return;
		}

		// Partition children
		const auto bbSize = bb.Size();
		TItemIterator partitionAt;
		if (bbSize.x > bbSize.y) {
			const auto centerX = bb.CenterX();
			partitionAt = binary_partition(begin, end, [&](auto& item) { return bbFromItem(item).CenterX() < centerX; });
		}
		else
		{
			const auto centerY = bb.CenterY();
			partitionAt = binary_partition(begin, end, [&](auto& item) { return bbFromItem(item).CenterY() < centerY; });
		}

		const size_t node_index = m_Nodes.size();
		m_Nodes.resize(node_index + 1);

		m_Nodes[node_index].BB = bb;
		m_Nodes[node_index].ItemIndexBeg = base_item_index;
		m_Nodes[node_index].ItemIndexEnd = base_item_index + (uint32_t)item_count;

		m_Nodes[node_index].Child0 = (unsigned int)m_Nodes.size();
		CreateSubtree(base_item_index, begin, partitionAt, max_depth - 1, max_objects_per_leaf, std::forward<TBBFromItem>(bbFromItem));

		m_Nodes[node_index].Child1 = (unsigned int)m_Nodes.size();
		CreateSubtree(base_item_index + (uint32_t)(partitionAt - begin), partitionAt, end, max_depth - 1, max_objects_per_leaf, std::forward<TBBFromItem>(bbFromItem));
	}

	template <class T, class TItemIterator>
	template <class TBBTest, class TItemVisitor>
	void LooseBspTree<T, TItemIterator>::VisitItems(size_t node_index, TBBTest&& bb_test, TItemVisitor&& item_visitor)
	{
		const auto& node = m_Nodes[node_index];
		if (!bb_test(node.BB))
		{
			return;
		}

		if (node.IsLeaf())
		{
			for (uint32_t item_index = node.ItemIndexBeg; item_index < node.ItemIndexEnd; ++item_index) {
				item_visitor(*(m_ItemsBegin + item_index));
			}
		}
		else
		{
			VisitItems(node.Child0, std::forward<TBBTest>(bb_test), std::forward<TItemVisitor>(item_visitor));
			VisitItems(node.Child1, std::forward<TBBTest>(bb_test), std::forward<TItemVisitor>(item_visitor));
		}
	}

	template <class T, class TItemIterator>
	template <class TFunc>
	inline void LooseBspTree<T, TItemIterator>::ForEachRangeInBB(const bb_t& bb, TFunc&& fn)
	{
		if (m_Nodes.empty())
		{
			return;
		}

		std::pair<uint32_t, uint32_t> pending_range(0, 0);
		ForEachSubRangeInBB(0, bb, std::forward<TFunc>(fn), pending_range);

		if (pending_range.second > pending_range.first)
		{
			fn(m_ItemsBegin + pending_range.first, m_ItemsBegin + pending_range.second);
		}
	}

	template <class T, class TItemIterator>
	template <class TFunc>
	inline void LooseBspTree<T, TItemIterator>::ForEachSubRangeInBB(uint32_t node_index, const bb_t& bb, TFunc&& fn, std::pair<uint32_t, uint32_t>& pending_range)
	{
		const auto& node = m_Nodes[node_index];

		if (!bb.Overlaps(node.BB))
		{
			return;
		}

		if (node.IsLeaf() || node.BB.IsFullyInside(bb))
		{
			if (pending_range.second != node.ItemIndexBeg)
			{
				if (pending_range.second > pending_range.first)
				{
					fn(m_ItemsBegin + pending_range.first, m_ItemsBegin + pending_range.second);
				}
				pending_range.first = node.ItemIndexBeg;
			}
			pending_range.second = node.ItemIndexEnd;
			return;
		}

		ForEachSubRangeInBB(node.Child0, bb, std::forward<TFunc>(fn), pending_range);
		ForEachSubRangeInBB(node.Child1, bb, std::forward<TFunc>(fn), pending_range);
	}
}