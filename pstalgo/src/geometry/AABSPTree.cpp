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

#include <algorithm>
#include <cmath>

#include <pstalgo/geometry/AABSPTree.h>
#include <pstalgo/geometry/Geometry.h>

CAABSPTree::CAABSPTree()
{
	m_BB.SetEmpty();
}

CAABSPTree::CAABSPTree(CAABSPTree&& other)
	: m_Nodes(std::move(other.m_Nodes))
	, m_BB(other.m_BB)
{
}

const CAABSPTree& CAABSPTree::operator=(CAABSPTree&& other)
{
	m_Nodes = std::move(other.m_Nodes);
	m_BB = other.m_BB;
	return *this;
}

void CAABSPTree::TestSphere(const float2& center, float radius, std::vector<SObjectSet>& ret_sets)
{
	ret_sets.clear();

	const float2 bb_center(m_BB.CenterX(), m_BB.CenterY());
	const float2 bb_half_size(.5f * m_BB.Width(), .5f * m_BB.Height());

	if (m_Nodes.empty() || !TestAABBCircleOverlap(bb_half_size, center - bb_center, radius))
		return;

	TestSphere(m_BB, center, radius, 0, ret_sets);
}

void CAABSPTree::TestCapsule(const float2& p0, const float2 p1, float radius, std::vector<SObjectSet>& ret_sets)
{
	ret_sets.clear();

	if (m_Nodes.empty() || !TestAABBCapsuleOverlap(m_BB, p0, p1, radius))
		return;

	TestCapsule(m_BB, p0, p1, radius, 0, ret_sets);
}

void CAABSPTree::TestSphere(const CRectf& bb, const float2& center, float radius, unsigned int node_index, std::vector<SObjectSet>& ret_sets)
{
	using namespace std;

	const auto& node = m_Nodes[node_index];

	if (node.IsCell())
	{
		ret_sets.resize(ret_sets.size() + 1);
		auto& os = ret_sets.back();
		os.m_FirstObject = node.GetFirstObject();
		os.m_Count = node.GetObjectCount();
		return;
	}

	const unsigned char split_axis = node.GetSplitAxis();
	const float2* bb_pts = (const float2*)&bb;
	const float split_pos = node.GetSplitAt();
	
	const float d = center[split_axis] - split_pos;
	
	unsigned char child_bits = (d < 0) ? 1 : 2;

	if (abs(d) < radius)
	{
		const unsigned char non_split_axis = split_axis ^ 1;
		const float bb_half_size = .5f * (bb_pts[1][non_split_axis] - bb_pts[0][non_split_axis]);
		const float d2 = abs(center[non_split_axis] - bb_pts[0][non_split_axis] - bb_half_size);
		if (d2 <= bb_half_size || sqr(d2 - bb_half_size) + sqr(d) <= sqr(radius))
			child_bits = 3;
	}

	if (child_bits & 1)
	{
		CRectf bb_child(bb);
		(&bb_child.m_Right)[split_axis] = split_pos;
		TestSphere(bb_child, center, radius, node_index + 1, ret_sets);
	}

	if (child_bits & 2)
	{
		CRectf bb_child(bb);
		(&bb_child.m_Left)[split_axis] = split_pos;
		TestSphere(bb_child, center, radius, node.GetRightNode(), ret_sets);
	}
}

void CAABSPTree::TestCapsule(const CRectf& bb, const float2& p0, const float2 p1, float radius, unsigned int node_index, std::vector<SObjectSet>& ret_sets)
{
	using namespace std;

	const auto& node = m_Nodes[node_index];

	if (node.IsCell())
	{
		ret_sets.resize(ret_sets.size() + 1);
		auto& os = ret_sets.back();
		os.m_FirstObject = node.GetFirstObject();
		os.m_Count = node.GetObjectCount();
		return;
	}

	const unsigned char split_axis = node.GetSplitAxis();
	const float split_pos = node.GetSplitAt();

	const float d0 = p0[split_axis] - split_pos;
	const float d1 = p1[split_axis] - split_pos;
	const float ad0 = abs(d0);
	const float ad1 = abs(d1);

	unsigned char child_bits = 0;

	if (d0*d1 >= 0)
	{
		// End-points are on same side of splitter
		child_bits = (d0 < 0) ? 1 : 2;

		if (ad0 > radius && ad1 > radius)
			goto done; // The whole capsule is on one side of the splitter

		if (ad0 <= radius && ad1 <= radius)
		{
			child_bits = 3;
			goto done;
		}
	}

	if (!(child_bits & 1))
	{
		CRectf bb_child(bb);
		(&bb_child.m_Right)[split_axis] = split_pos;
		if (TestAABBCapsuleOverlap(bb_child, p0, p1, radius))
			child_bits |= 1;
	}

	if (!(child_bits & 2))
	{
		CRectf bb_child(bb);
		(&bb_child.m_Left)[split_axis] = split_pos;
		if (TestAABBCapsuleOverlap(bb_child, p0, p1, radius))
			child_bits |= 2;
	}

done:

	if (child_bits & 1)
	{
		CRectf bb_child(bb);
		(&bb_child.m_Right)[split_axis] = split_pos;
		TestCapsule(bb_child, p0, p1, radius, node_index + 1, ret_sets);
	}

	if (child_bits & 2)
	{
		CRectf bb_child(bb);
		(&bb_child.m_Left)[split_axis] = split_pos;
		TestCapsule(bb_child, p0, p1, radius, node.GetRightNode(), ret_sets);
	}
}

void CPointAABSPTree::CreateSubTree(const CRectf& bb, SPointAndIndex* points_by_x, SPointAndIndex* points_by_y, SPointAndIndex* points_tmp, unsigned int count, unsigned int max_points_per_cell, unsigned int start_index, unsigned int* ret_order)
{
	if (count <= max_points_per_cell)
	{
		MakeCell(points_by_x, count, start_index, ret_order);
		return;
	}

	const bool horiz_split_line = (bb.Height() > bb.Width());
	const unsigned char split_axis = horiz_split_line ? 1 : 0;

	const float split_pos = (horiz_split_line ? points_by_y : points_by_x)[count >> 1].m_Point[split_axis];

	auto non_split_order = horiz_split_line ? points_by_x : points_by_y;
	unsigned int child0_count = 0;
	for (unsigned int i = 0; i < count; ++i)
		if (non_split_order[i].m_Point[split_axis] < split_pos)
			points_tmp[child0_count++] = non_split_order[i];
	unsigned int child1_count = child0_count;
	for (unsigned int i = 0; i < count; ++i)
		if (non_split_order[i].m_Point[split_axis] >= split_pos)
			points_tmp[child1_count++] = non_split_order[i];
	child1_count -= child0_count;
	std::swap((non_split_order == points_by_x) ? points_by_x : points_by_y, points_tmp);

	// Avoid infinite loops for the odd case that lots of points are in the exact same coordinate
	if (0 == child0_count || count == child0_count)
	{
		MakeCell(points_by_x, count, start_index, ret_order);
		return;
	}

	const unsigned int node_index = (unsigned int)m_Nodes.size();
	m_Nodes.resize(m_Nodes.size() + 1);

	CRectf child_bb = bb;
	*(horiz_split_line ? &child_bb.m_Bottom : &child_bb.m_Right) = split_pos;
	CreateSubTree(child_bb, points_by_x, points_by_y, points_tmp, child0_count, max_points_per_cell, start_index, ret_order);

	m_Nodes[node_index].MakeNode(split_pos, horiz_split_line, (unsigned int)m_Nodes.size());

	child_bb = bb;
	*(horiz_split_line ? &child_bb.m_Top : &child_bb.m_Left) = split_pos;
	CreateSubTree(child_bb, points_by_x + child0_count, points_by_y + child0_count, points_tmp, child1_count, max_points_per_cell, start_index + child0_count, ret_order);
}

void CPointAABSPTree::MakeCell(const SPointAndIndex* points_by_x, unsigned int count, unsigned int start_index, unsigned int* ret_order)
{
	m_Nodes.resize(m_Nodes.size() + 1);
	m_Nodes.back().MakeCell(start_index, count);
	for (unsigned int i = 0; i < count; ++i)
		ret_order[points_by_x[i].m_Index] = start_index + i;
}

CLineAABSPTree::CLineAABSPTree(CLineAABSPTree&& other)
	: CAABSPTree(std::move(other)), 
	m_Lines(std::move(other.m_Lines)) 
{
}

const CLineAABSPTree& CLineAABSPTree::operator=(CLineAABSPTree&& other) 
{ 
	CAABSPTree::operator=(std::move(other));
	m_Lines = std::move(other.m_Lines); 
	return *this; 
}

CLineAABSPTree CLineAABSPTree::Create(const float2* line_points, unsigned int count, unsigned int max_lines_per_cell)
{
	CLineAABSPTree tree;

	if (0 == count)
		return tree;

	if (max_lines_per_cell < 2)
		max_lines_per_cell = 2;

	// Calculate bb
	tree.m_BB.Set(line_points->x, line_points->y, line_points->x, line_points->y);
	for (unsigned int i = 0; i < (count << 1); ++i)
		tree.m_BB.GrowToIncludePoint(line_points[i].x, line_points[i].y);

	// Reserve estimated space for nodes
	tree.m_Nodes.reserve(((count + max_lines_per_cell - 1) / max_lines_per_cell) * 3);

	// Reserve estimated space for lines
	tree.m_Lines.reserve(count * 3);

	std::vector<SLineAndIndex> lines_tmp;
	lines_tmp.reserve(count * 3);
	lines_tmp.resize(count);
	for (unsigned int i = 0; i < count; ++i)
	{
		lines_tmp[i].m_P0 = line_points[i << 1];
		lines_tmp[i].m_P1 = line_points[(i << 1) + 1];
		lines_tmp[i].m_Index = i;
	}

	tree.CreateSubTree(tree.m_BB, lines_tmp, count, max_lines_per_cell, 3 + (int)std::log2((count + max_lines_per_cell - 1) / max_lines_per_cell));

	return tree;
}

void CLineAABSPTree::CreateSubTree(const CRectf& bb, std::vector<SLineAndIndex>& lines_tmp, unsigned int count, unsigned int max_lines_per_cell, unsigned int max_depth)
{
	const unsigned int first = (unsigned int)lines_tmp.size() - count;

	if (count <= max_lines_per_cell || 0 == max_depth)
	{
		MakeCell(lines_tmp.data() + first, count);
		return;
	}

	const bool horiz_split_line = (bb.Height() > bb.Width());
	const unsigned char split_axis = horiz_split_line ? 1 : 0;

	const float split_pos = (horiz_split_line ? bb.CenterY() : bb.CenterX());

	const unsigned int node_index = (unsigned int)m_Nodes.size();
	m_Nodes.resize(m_Nodes.size() + 1);

	for (unsigned char child = 0; child < 2; ++child)
	{
		CRectf child_bb = bb;
		if (0 == child)
			*(horiz_split_line ? &child_bb.m_Bottom : &child_bb.m_Right) = split_pos;
		else
			*(horiz_split_line ? &child_bb.m_Top : &child_bb.m_Left) = split_pos;

		const float2 bb_center(child_bb.CenterX(), child_bb.CenterY());
		const float2 bb_half_size(child_bb.Width() * .5f, child_bb.Height() * .5f);

		if (0 == child)
		{
			for (unsigned int i = first; i < first + count; ++i)
			{
				const auto& line = lines_tmp[i];
				if (line.m_P0[split_axis] > split_pos && line.m_P1[split_axis] > split_pos)
					continue; // Both points on other side
				if (line.m_P0[split_axis] <= split_pos && line.m_P1[split_axis] <= split_pos)
				{
					// Both points on this side
					lines_tmp.push_back(SLineAndIndex(line));  // Need a copy here since reference might become invalid when vector grows
				}
				else
				{
					// Line is split
					auto piece = line;
					if (piece.m_P0[split_axis] > split_pos)
						std::swap(piece.m_P0, piece.m_P1);
					const float t = (split_pos - piece.m_P0[split_axis]) / (piece.m_P1[split_axis] - piece.m_P0[split_axis]);
					piece.m_P1[!split_axis] = piece.m_P0[!split_axis] + t * (piece.m_P1[!split_axis] - piece.m_P0[!split_axis]);
					piece.m_P1[split_axis] = split_pos;
					lines_tmp.push_back(piece);
				}
			}
		}
		else
		{
			for (unsigned int i = first; i < first + count; ++i)
			{
				const auto& line = lines_tmp[i];
				if (line.m_P0[split_axis] < split_pos && line.m_P1[split_axis] < split_pos)
					continue; // Both points on other side
				if (line.m_P0[split_axis] >= split_pos && line.m_P1[split_axis] >= split_pos)
				{
					// Both points on this side
					lines_tmp.push_back(SLineAndIndex(line));  // Need a copy here since reference might become invalid when vector grows
				}
				else
				{
					// Line is split
					auto piece = line;
					if (piece.m_P0[split_axis] < split_pos)
						std::swap(piece.m_P0, piece.m_P1);
					const float t = (split_pos - piece.m_P0[split_axis]) / (piece.m_P1[split_axis] - piece.m_P0[split_axis]);
					piece.m_P1[!split_axis] = piece.m_P0[!split_axis] + t * (piece.m_P1[!split_axis] - piece.m_P0[!split_axis]);
					piece.m_P1[split_axis] = split_pos;
					lines_tmp.push_back(piece);
				}
			}
		}

		CreateSubTree(child_bb, lines_tmp, (unsigned int)lines_tmp.size() - first - count, max_lines_per_cell, max_depth - 1);

		lines_tmp.resize(first + count);

		if (0 == child)
		{
			m_Nodes[node_index].MakeNode(split_pos, horiz_split_line, (unsigned int)m_Nodes.size());
		}
	}
}

void CLineAABSPTree::MakeCell(const SLineAndIndex* lines, unsigned int count)
{
	m_Nodes.resize(m_Nodes.size() + 1);
	m_Nodes.back().MakeCell((unsigned int)m_Lines.size(), count);
	for (unsigned int i = 0; i < count; ++i)
		m_Lines.push_back(lines[i].m_Index & 0x7FFFFFFF);
}
