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

#include <pstalgo/Debug.h>
#include <pstalgo/maths.h>
#include <pstalgo/graph/SegmentGraph.h>
#include <pstalgo/graph/SegmentGroupGraph.h>
#include <pstalgo/utils/BitVector.h>
#include <pstalgo/utils/Macros.h>

uint32 GroupSegmentsByAngularThreshold(const CSegmentGraph& graph, float threshold_degrees, bool split_groups_at_junctions, uint32* ret_group_id_per_line)
{
	if (split_groups_at_junctions)
	{
		const uint32 NO_GROUP = (uint32)-1;

		uint32 group_count = 0;

		// Initially segments have no group
		for (uint32 i = 0; i < graph.GetSegmentCount(); ++i)
			ret_group_id_per_line[i] = NO_GROUP;

		for (uint32 segment_index = 0; segment_index < graph.GetSegmentCount(); ++segment_index)
		{
			if (NO_GROUP != ret_group_id_per_line[segment_index])
				continue;

			ret_group_id_per_line[segment_index] = group_count;

			const auto& start_segment = graph.GetSegment(segment_index);

			for (const auto* intersection : start_segment.m_Intersections)
			{
				for (uint32 seg_idx = segment_index; intersection && 2 == intersection->m_NumSegments;)
				{
					const uint32 next_seg_idx = (intersection->m_Segments[0] == seg_idx) ? intersection->m_Segments[1] : intersection->m_Segments[0];
					if (next_seg_idx == segment_index)
						break;  // Loop
					if (NO_GROUP != ret_group_id_per_line[next_seg_idx])
						break;
					const auto& this_seg = graph.GetSegment(seg_idx);
					const auto& next_seg = graph.GetSegment(next_seg_idx);
					const auto d = 180.f - angleDiff(
						(this_seg.m_Intersections[0] == intersection) ? this_seg.m_Orientation : reverseAngle(this_seg.m_Orientation),
						(next_seg.m_Intersections[0] == intersection) ? next_seg.m_Orientation : reverseAngle(next_seg.m_Orientation));
					if (d > threshold_degrees)
						break;
					ret_group_id_per_line[next_seg_idx] = group_count;
					seg_idx = next_seg_idx;
					intersection = (next_seg.m_Intersections[0] == intersection) ? next_seg.m_Intersections[1] : next_seg.m_Intersections[0];
				}
			}

			++group_count;
		}

		return group_count;
	}

	// We initially assign a unique group for each line
	for (uint32 i = 0; i < graph.GetSegmentCount(); ++i)
		ret_group_id_per_line[i] = i;

	struct SSeg
	{
		uint32 m_Index;  // € [0..lines at intersection - 1]
		float  m_Orientation;  // 0 - 360
	};
	std::vector<SSeg> tmp;

	for (uint32 segment_index = 0; segment_index < graph.GetSegmentCount(); ++segment_index)
	{
		const auto& segment = graph.GetSegment(segment_index);
		for (const auto* intersection : segment.m_Intersections)
		{
			if (nullptr == intersection || intersection->m_NumSegments < 2)
				continue;

			// Create list of (index, angle) pairs for each line at intersection
			tmp.clear();
			for (uint32 i = 0; i < intersection->m_NumSegments; ++i)
			{
				SSeg s;
				s.m_Index = intersection->m_Segments[i];
				const auto& seg = graph.GetSegment(s.m_Index);
				s.m_Orientation = (seg.m_Intersections[0] == intersection) ? seg.m_Orientation : reverseAngle(seg.m_Orientation);
				tmp.push_back(s);
			}

			while (tmp.size() > 1)
			{
				// Find the pair of lines with lowest deviation
				uint32 s0 = 0;
				uint32 s1 = 0;
				float lowest_deviation = std::numeric_limits<float>::infinity();
				for (uint32 i = 0; i < tmp.size() - 1; ++i)
				{
					for (uint32 ii = i + 1; ii < tmp.size(); ++ii)
					{
						const auto d = 180.f - angleDiff(tmp[i].m_Orientation, tmp[ii].m_Orientation);
						if (d < lowest_deviation)
						{
							s0 = i;
							s1 = ii;
							lowest_deviation = d;
						}
					}
				}

				ASSERT(lowest_deviation >= 0 && lowest_deviation <= 180);

				if (lowest_deviation > threshold_degrees)
					break;  // No more pairs of lines with deviation lower than threshold at this intersection

				// Find root groups of both lines
				uint32 g0, g1;
				for (g0 = tmp[s0].m_Index; ret_group_id_per_line[g0] != g0; g0 = ret_group_id_per_line[g0]);
				for (g1 = tmp[s1].m_Index; ret_group_id_per_line[g1] != g1; g1 = ret_group_id_per_line[g1]);

				// Make the group with lowest index be the root of the other group
				const auto g = std::min(g0, g1);
				ret_group_id_per_line[g0] = g;
				ret_group_id_per_line[g1] = g;

				// Make both lines point directly to root group to decrease future lookup time for them
				ret_group_id_per_line[tmp[s0].m_Index] = g;
				ret_group_id_per_line[tmp[s1].m_Index] = g;

				// Remove these lines from the lines to be processed for this intersection
				tmp.erase(tmp.begin() + s1);
				tmp.erase(tmp.begin() + s0);
			}
		}
	}

	// Lookup root groups
	for (uint32 i = 0; i < graph.GetSegmentCount(); ++i)
	{
		uint32 g;
		for (g = i; ret_group_id_per_line[g] != g; g = ret_group_id_per_line[g]);
		ret_group_id_per_line[i] = g;
	}

	// Pack group numbers
	uint32 group_count = 0;
	for (uint32 i = 0; i < graph.GetSegmentCount(); ++i)
		ret_group_id_per_line[i] = (ret_group_id_per_line[i] == i) ? group_count++ : ret_group_id_per_line[ret_group_id_per_line[i]];

	return group_count;
}

///////////////////////////////////////////////////////////////////////////////

CSegmentGroupGraph::CSegmentGroupGraph()
	: m_GroupCount(0)
{
}

void CSegmentGroupGraph::Create(const CSegmentGraph& segment_graph, const uint32* group_id_per_segment, uint32 group_count)
{
	std::vector<uint32> segment_end_to_node(segment_graph.GetSegmentCount() * 2, (uint32)-1);
	
	// Create nodes
	for (uint32 segment_index = 0; segment_index < segment_graph.GetSegmentCount(); ++segment_index)
	{
		const auto& segment = segment_graph.GetSegment(segment_index);
		const auto group_id = group_id_per_segment[segment_index];
		for (uint8 intersection_index = 0; intersection_index < 2; ++intersection_index)
		{
			if ((uint32)-1 != segment_end_to_node[(segment_index << 1) + intersection_index])
				continue;  // Already processed
			auto* intersection = segment.m_Intersections[intersection_index];
			if (nullptr == intersection || intersection->m_NumSegments < 2)
				continue;  // Dead end
			if (2 == intersection->m_NumSegments)
			{
				// Path intersection (two connected segments)
				const auto other_segment_index = (intersection->m_Segments[0] == segment_index) ? intersection->m_Segments[1] : intersection->m_Segments[0];
				if (group_id == group_id_per_segment[other_segment_index])
					continue;  // Both segments belong to same group
			}
			// Create nodes for all paths in this intersection
			for (uint32 path_index = 0; path_index < intersection->m_NumSegments; ++path_index)
			{
				const auto path_seg_idx = intersection->m_Segments[path_index];
				const auto& path_seg = segment_graph.GetSegment(path_seg_idx);
				const auto seg_end_idx = (path_seg_idx << 1) + (path_seg.m_Intersections[0] == intersection ? 0 : 1);
				ASSERT((uint32)-1 == segment_end_to_node[seg_end_idx]);
				segment_end_to_node[seg_end_idx] = (uint32)m_Nodes.size();
				m_Nodes.resize(m_Nodes.size() + 1);
				auto& node = m_Nodes.back();
				node.m_GroupId = group_id_per_segment[path_seg_idx];
				node.m_MyIndexAtIntersection = path_index;
				node.m_Edge.m_Length = 0;
				node.m_Edge.m_TargetNode = (uint32)-1;
			}
		}
	}

	// Connect nodes
	for (uint32 seg_end_idx = 0; seg_end_idx < segment_end_to_node.size(); ++seg_end_idx)
	{
		const auto start_node_index = segment_end_to_node[seg_end_idx];
		if ((uint32)-1 == start_node_index)
			continue;
		auto& start_node = m_Nodes[start_node_index];
		if ((uint32)-1 != start_node.m_Edge.m_TargetNode)
			continue;  // Already connected
		auto segment_index = seg_end_idx >> 1;
		auto* start_intersection = segment_graph.GetSegment(segment_index).m_Intersections[seg_end_idx & 1];
		auto* intersection = start_intersection;
		start_node.m_Edge.m_Length = 0;
		INFINITE_LOOP	
		{
			const auto& segment = segment_graph.GetSegment(segment_index);
			start_node.m_Edge.m_Length += segment.m_Length;
			const uint8 next_intersection_index = (segment.m_Intersections[0] == intersection) ? 1 : 0;
			auto next_node_idx = segment_end_to_node[(segment_index << 1) + next_intersection_index];
			if ((uint32)-1 != next_node_idx)
			{
				// Found target node
				start_node.m_Edge.m_TargetNode = next_node_idx;
				auto& target_node = m_Nodes[next_node_idx];
				ASSERT((uint32)-1 == target_node.m_Edge.m_TargetNode);
				target_node.m_Edge.m_TargetNode = start_node_index;
				target_node.m_Edge.m_Length = start_node.m_Edge.m_Length;
				break;
			}
			intersection = segment.m_Intersections[next_intersection_index];
			if (nullptr == intersection || intersection->m_NumSegments < 2)
				break;  // Dead end
			ASSERT(2 == intersection->m_NumSegments);
			segment_index = (intersection->m_Segments[0] == segment_index) ? intersection->m_Segments[1] : intersection->m_Segments[0];
		}
	}

	m_GroupCount = group_count;
}

CSegmentGroupGraph::dist_t CSegmentGroupGraph::GetDistance(const edge_t& edge) const
{
	const auto& node = m_Nodes[edge.m_NodeIndex];
	dist_t dist;
	if (edge.m_PathIndex == node.m_MyIndexAtIntersection)
	{
		// Following the edge of this node
		dist.m_Walking = node.m_Edge.m_Length;
		dist.m_Steps = 0;
	}
	else
	{
		// Stepping to another path at this intersection
		const auto first_path_index = edge.m_NodeIndex - node.m_MyIndexAtIntersection;
		const auto& target_node = m_Nodes[first_path_index + edge.m_PathIndex];
		dist.m_Walking = 0;
		dist.m_Steps = (node.m_GroupId == target_node.m_GroupId) ? 0 : 1;
	}
	return dist;
}

CSegmentGroupGraph::node_index_t CSegmentGroupGraph::GetTargetNode(const edge_t& edge) const
{
	const auto& src_node = m_Nodes[edge.m_NodeIndex];
	if (src_node.m_MyIndexAtIntersection == edge.m_PathIndex)
		return src_node.m_Edge.m_TargetNode;  // We're following the edge of this node, travelling to a node of another intersection
	// we're stepping to another node within same intersection
	return edge.m_NodeIndex - src_node.m_MyIndexAtIntersection + edge.m_PathIndex;
}
