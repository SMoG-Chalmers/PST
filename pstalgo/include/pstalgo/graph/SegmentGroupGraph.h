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
#include <pstalgo/Types.h>

class CSegmentGraph;

uint32 GroupSegmentsByAngularThreshold(const CSegmentGraph& graph, float threshold_degrees, bool split_groups_at_junctions, uint32* ret_group_id_per_line);

class CSegmentGroupGraph
{
public:
	struct SEdge
	{
		SEdge() {}
		SEdge(uint32 node_index, uint32 path_index) : m_NodeIndex(node_index), m_PathIndex(path_index) {}
		uint32 m_NodeIndex;
		uint32 m_PathIndex;
	};

	struct SDist
	{
		SDist() {}
		SDist(float walking, uint32 steps) : m_Walking(walking), m_Steps(steps) {}

		SDist operator+(const SDist& rhs) const { return SDist(m_Walking + rhs.m_Walking, m_Steps + rhs.m_Steps); }

		float  m_Walking;
		uint32 m_Steps;
	};
	
	typedef uint32 node_index_t;
	typedef SEdge  edge_t;
	typedef SDist  dist_t;
	typedef uint32 groupid_t;

	CSegmentGroupGraph();

	void Create(const CSegmentGraph& segment_graph, const uint32* group_id_per_segment, uint32 group_count);

	groupid_t GroupidFromNode(node_index_t node) const { return m_Nodes[node].m_GroupId; }

	uint32 NodeCount() const { return (uint32)m_Nodes.size(); }

	uint32 GroupCount() const { return m_GroupCount; }

	dist_t GetDistance(const edge_t& edge) const;

	node_index_t GetTargetNode(const edge_t& edge) const;

	template <class TCallback>
	void ForEachEdge(node_index_t node_index, TCallback&& callback) const
	{
		const auto& node = m_Nodes[node_index];
		const auto my_path_index = node.m_MyIndexAtIntersection;
		const auto first_node = node_index - my_path_index;
		for (uint32 i = first_node; i < m_Nodes.size(); ++i)
		{
			const auto path_index = i - first_node;
			if (path_index != m_Nodes[i].m_MyIndexAtIntersection)
				break;
			if (path_index == my_path_index && ((uint32)-1 == node.m_Edge.m_TargetNode))
				continue;  // Edge leads to dead-end
			callback(SEdge(node_index, path_index));
		}
	}

private:
	struct SNode
	{
		uint32    m_MyIndexAtIntersection;
		groupid_t m_GroupId;
		struct SEdge
		{
			float  m_Length;  // Walking distance in meters
			node_index_t m_TargetNode;
		};
		SEdge m_Edge;
	};

	std::vector<SNode> m_Nodes;
	uint32 m_GroupCount;
};