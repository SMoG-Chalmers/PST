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
#include <queue>
#include <vector>

#include <pstalgo/Debug.h>
#include <pstalgo/maths.h>
#include <pstalgo/analyses/SegmentGrouping.h>
#include <pstalgo/graph/GraphColoring.h>
#include <pstalgo/graph/SegmentGraph.h>
#include <pstalgo/graph/SegmentGroupGraph.h>
#include <pstalgo/graph/SimpleGraph.h>
#include <pstalgo/utils/BitVector.h>

#include "../ProgressUtil.h"

CSimpleGraph CreateSegmentGroupConnectionGraph(const CSegmentGraph& segment_graph, const uint32* group_id_per_segment, const uint32 group_count)
{
	CBitVector segment_bitmask;
	segment_bitmask.resize(segment_graph.GetSegmentCount());
	segment_bitmask.clearAll();
		
	std::vector<uint32> group_to_segment(group_count, (uint32)-1);
	for (uint32 i = segment_graph.GetSegmentCount() - 1; (uint32)-1 != i; --i)
		group_to_segment[group_id_per_segment[i]] = i;

	CSimpleGraph graph;
	graph.Reserve(
		segment_graph.GetSegmentCount(), 
		segment_graph.GetSegmentCount() * 3);  // Estimation

	std::queue<uint32> bfs_queue;
	std::vector<uint32> processed_segments;
	std::vector<uint32> neighbour_groups;
	for (uint32 group_index = 0; group_index < group_count; ++group_index)
	{
		const uint32 start_segment_index = group_to_segment[group_index];
		
		bfs_queue.push(start_segment_index);
		segment_bitmask.set(start_segment_index);
		processed_segments.push_back(start_segment_index);
		
		// Do BFS search and find neighbour groups
		neighbour_groups.clear();
		while (!bfs_queue.empty())
		{
			const uint32 segment_index = bfs_queue.front();
			bfs_queue.pop();
			const auto& segment = segment_graph.GetSegment(segment_index);
			for (auto* intersection : segment.m_Intersections)
			{
				if (nullptr == intersection)
					continue;
				for (unsigned int neighbour_index = 0; neighbour_index < intersection->m_NumSegments; ++neighbour_index)
				{
					const auto neighbour_segment_index = intersection->m_Segments[neighbour_index];
					if (segment_bitmask.get(neighbour_segment_index))
						continue;  // Already visited
					segment_bitmask.set(neighbour_segment_index);
					processed_segments.push_back(neighbour_segment_index);
					if (group_id_per_segment[neighbour_segment_index] == group_index)
						bfs_queue.push(neighbour_segment_index);
					else
						neighbour_groups.push_back(group_id_per_segment[neighbour_segment_index]);
				}
			}
		}

		// Clear segment_bitmask and processed_segments
		for (uint32 seg_index : processed_segments)
			segment_bitmask.clear(seg_index);
		processed_segments.clear();

		// Sort neighbour_groups and remove duplicates
		std::sort(neighbour_groups.begin(), neighbour_groups.end());
		uint32 n = std::min((uint32)neighbour_groups.size(), (uint32)1);
		for (uint32 i = 1; i < neighbour_groups.size(); ++i)
		{
			if (neighbour_groups[i - 1] == neighbour_groups[i])
				continue;
			neighbour_groups[n++] = neighbour_groups[i];
		}
		neighbour_groups.resize(n);

		// Add node
		graph.AddNode(neighbour_groups.data(), (uint32)neighbour_groups.size());
	}

	return graph;
}

SPSTASegmentGroupingDesc::SPSTASegmentGroupingDesc()
	: m_Version(VERSION)
	, m_SegmentGraph(nullptr)
	, m_AngleThresholdDegrees(0)
	, m_SplitGroupsAtJunctions(false)
	, m_ProgressCallback(nullptr)
	, m_ProgressCallbackUser(nullptr)
	, m_LineCount(0)
	, m_OutGroupIdPerLine(nullptr)
	, m_OutGroupCount(0)
	, m_OutColorPerLine(nullptr)
	, m_OutColorCount(0)
{
}

PSTADllExport bool PSTASegmentGrouping(SPSTASegmentGroupingDesc* desc)
{
	ASSERT(desc->m_SegmentGraph);
	const auto& graph = *static_cast<const CSegmentGraph*>(desc->m_SegmentGraph);

	if (desc->m_LineCount != graph.GetSegmentCount())
	{
		LOG_ERROR("Output array doesn't match graph line count!");
		return false;
	}

	uint32* group_id_per_line = desc->m_OutGroupIdPerLine;

	std::vector<uint32> temp_ids;
	if (nullptr == group_id_per_line)
	{
		temp_ids.resize(graph.GetSegmentCount());
		group_id_per_line = temp_ids.data();
	}

	ASSERT(desc->m_OutGroupIdPerLine);
	desc->m_OutGroupCount = GroupSegmentsByAngularThreshold(graph, desc->m_AngleThresholdDegrees, desc->m_SplitGroupsAtJunctions, group_id_per_line);

	if (desc->m_OutColorPerLine)
	{
		auto group_graph = CreateSegmentGroupConnectionGraph(graph, group_id_per_line, desc->m_OutGroupCount);
		std::vector<uint32> color_per_group(desc->m_OutGroupCount);
		desc->m_OutColorCount = ColorGraph(group_graph, color_per_group.data());
		for (uint32 i = 0; i < graph.GetSegmentCount(); ++i)
			desc->m_OutColorPerLine[i] = color_per_group[group_id_per_line[i]];
	}

	return true;
}