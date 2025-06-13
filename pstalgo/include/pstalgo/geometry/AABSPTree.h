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

class CAABSPTree
{
public:
	struct SObjectSet
	{
		unsigned int m_FirstObject;
		unsigned int m_Count;
	};

	CAABSPTree();
	CAABSPTree(CAABSPTree&& other);
	CAABSPTree(const CAABSPTree&) = delete;

	const CAABSPTree& operator=(CAABSPTree&& other);
	const CAABSPTree& operator=(const CAABSPTree&) = delete;

	const CRectf& GetBB() const { return m_BB; }

	void TestSphere(const float2& center, float radius, std::vector<SObjectSet>& ret_sets);

	void TestCapsule(const float2& p0, const float2 p1, float radius, std::vector<SObjectSet>& ret_sets);

protected:
	void TestSphere(const CRectf& bb, const float2& center, float radius, unsigned int node_index, std::vector<SObjectSet>& ret_sets);

	void TestCapsule(const CRectf& bb, const float2& p0, const float2 p1, float radius, unsigned int node_index, std::vector<SObjectSet>& ret_sets);

	struct SNode
	{
		// NOTE: vertical_split = True means child nodes/cells will span separate ranges of the Y-axis (i.e. the splitting line is a horizontal line)
		void MakeNode(float split_at, bool vertical_split, unsigned int right_node)
		{
			m_SplitAt = split_at;
			m_RightNode = right_node;
			if (vertical_split)
				m_RightNode |= 0x40000000;  // Set vertical bit
		}

		void MakeCell(unsigned int first_object, unsigned int object_count)
		{
			m_FirstObject = first_object;
			m_ObjectCount = object_count | 0x80000000;  // Set Cell-bit
		}

		inline bool IsCell() const { return 0 != (0x80000000 & m_ObjectCount); }

		inline bool          IsVerticalSplit() const { return 0 != (0x40000000 & m_RightNode); }
		inline unsigned char GetSplitAxis() const { return (unsigned char)(IsVerticalSplit() & 1); }
		inline float         GetSplitAt()   const { return m_SplitAt; }
		inline unsigned int  GetRightNode() const { return m_RightNode & 0x3FFFFFFF; }
		
		inline unsigned int GetFirstObject() const { return m_FirstObject; }
		inline unsigned int GetObjectCount() const { return m_ObjectCount & 0x3FFFFFFF; }
		
	private:
		ALLOW_NAMELESS_STRUCT_BEGIN
		union
		{
			struct 
			{
				float        m_SplitAt;
				unsigned int m_RightNode;
			};
			struct
			{
				unsigned int m_FirstObject;
				unsigned int m_ObjectCount;
			};
		};
		ALLOW_NAMELESS_STRUCT_END
	};

	CRectf m_BB;
	std::vector<SNode> m_Nodes;
};


class CPointAABSPTree : public CAABSPTree
{
public:
	CPointAABSPTree() {}
	CPointAABSPTree(CPointAABSPTree&& other) : CAABSPTree(std::move(other)) {}
	CPointAABSPTree(const CPointAABSPTree&) = delete;

	const CPointAABSPTree& operator=(const CPointAABSPTree&) = delete;
	const CPointAABSPTree& operator=(CPointAABSPTree&& other) { CAABSPTree::operator=(std::move(other)); return *this; }

	// NOTE: On return each element in 'ret_order' will contain the index that the corresponding point was given in the generated tree.
	//       In other words - this array can be used to look up bsp element index from original point index - not vice versa! The rationale
	//       here is that it is assumed that the caller likely will use this array to reorder the original point object to match the
	//       ordering of the bsp elements, so that elements for a particular node will be laid out closely in memory (for cache coherency).
	template <class TPointCollection, class TOrderCollection>
	inline static CPointAABSPTree Create(const TPointCollection& points, TOrderCollection& ret_order, unsigned int max_points_per_cell = 16);

protected:
	struct SPointAndIndex
	{
		float2 m_Point;
		unsigned int m_Index;
	};

	void CreateSubTree(const CRectf& bb, SPointAndIndex* points_by_x, SPointAndIndex* points_by_y, SPointAndIndex* points_tmp, unsigned int count, unsigned int max_points_per_cell, unsigned int start_index, unsigned int* ret_order);

	void MakeCell(const SPointAndIndex* points_by_x, unsigned int count, unsigned int start_index, unsigned int* ret_order);
};

template <class TPointCollection, class TOrderCollection>
inline CPointAABSPTree CPointAABSPTree::Create(const TPointCollection& points, TOrderCollection& ret_order, unsigned int max_points_per_cell)
{
	CPointAABSPTree tree;

	if (0 == points.size())
		return tree;

	if (max_points_per_cell < 2)
		max_points_per_cell = 2;

	tree.m_Nodes.reserve(((points.size() + max_points_per_cell - 1) / max_points_per_cell) * 3);  // Reserve space for estimated node count

	std::vector<SPointAndIndex> points_by_x(points.size()), points_by_y(points.size());
	tree.m_BB.Set(points.begin()->x, points.begin()->y, points.begin()->x, points.begin()->y);
	psta::enumerate(points, [&](size_t i, const float2& pt)
	{
		tree.m_BB.GrowToIncludePoint(pt.x, pt.y);
		points_by_x[i].m_Point = pt;
		points_by_x[i].m_Index = i;
		points_by_y[i].m_Point = pt;
		points_by_y[i].m_Index = i;
	});
	std::sort(points_by_x.begin(), points_by_x.end(), [&](const SPointAndIndex& a, const SPointAndIndex& b) -> bool { return a.m_Point.x < b.m_Point.x; });
	std::sort(points_by_y.begin(), points_by_y.end(), [&](const SPointAndIndex& a, const SPointAndIndex& b) -> bool { return a.m_Point.y < b.m_Point.y; });

	std::vector<SPointAndIndex> points_tmp(points.size());
	tree.CreateSubTree(tree.m_BB, points_by_x.data(), points_by_y.data(), points_tmp.data(), points.size(), max_points_per_cell, 0, ret_order.data());

	return tree;
}


class CLineAABSPTree: public CAABSPTree
{
public:
	struct SLineAndIndex
	{
		float2 m_P0;
		float2 m_P1;
		unsigned int m_Index;
	};

	CLineAABSPTree() {}
	CLineAABSPTree(CLineAABSPTree&& other);
	CLineAABSPTree(const CLineAABSPTree&) = delete;

	const CLineAABSPTree& operator=(CLineAABSPTree&& other);
	const CLineAABSPTree& operator=(const CLineAABSPTree&) = delete;

	static CLineAABSPTree Create(const float2* line_points, unsigned int count, unsigned int max_lines_per_cell);

	const unsigned int GetLineIndex(unsigned int index) const { return m_Lines[index]; }

protected:
	void CreateSubTree(const CRectf& bb, std::vector<SLineAndIndex>& lines_tmp, unsigned int count, unsigned int max_lines_per_cell, unsigned int max_depth);

	void MakeCell(const SLineAndIndex* lines, unsigned int count);

	std::vector<unsigned int> m_Lines;
};