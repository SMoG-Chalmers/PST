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

#include <atomic>
#include <future>
#include <queue>

#include <pstalgo/analyses/NetworkIntegration.h>
#include <pstalgo/analyses/SegmentGroupIntegration.h>
#include <pstalgo/graph/SegmentGroupGraph.h>
#include <pstalgo/graph/BFSTraversal.h>
#include <pstalgo/Debug.h>
#include <pstalgo/maths.h>

#include "../ProgressUtil.h"

static const bool USE_MULTIPLE_CORES = true;

class CSegmentGroupIntegration
{
public:
	typedef CSegmentGroupGraph::dist_t dist_t;

	CSegmentGroupIntegration(const CSegmentGroupGraph& graph, const SPSTARadii& radius)
		: m_Graph(graph)
		, m_Traversal(graph)
	{
		m_Radius.m_Walking = radius.Walking();
		m_Radius.m_Steps   = radius.Steps();
		m_GroupsVisitedMask.resize(graph.GroupCount());
		m_GroupsVisitedMask.clearAll();
	}

	void CalculateIntegration(const uint32* nodes, uint32 node_count, uint32& out_N, float& out_TD)
	{
		m_N = 0;
		m_TD = 0;

		dist_t initial_dist;
		initial_dist.m_Steps = 0;
		initial_dist.m_Walking = 0;

		m_Traversal.TSearchMulti(nodes, node_count, initial_dist, m_Radius, *this);

		ClearGroupVisitingInfo();

		out_N = m_N;
		out_TD = (float)m_TD;
	}

	// TBFSTraversal delegate method
	void Visit(uint32 node_index, const dist_t& dist)
	{
		const auto group_index = m_Graph.GroupidFromNode(node_index);
		if (HasVisitedGroup(group_index))
			return;
		MarkGroupAsVisited(group_index);
		m_N++;
		m_TD += dist.m_Steps;
	}

	bool TestRadius(const dist_t& distance, const dist_t& radius) const
	{
		return distance.m_Walking <= radius.m_Walking && distance.m_Steps <= radius.m_Steps;
	}

private:
	bool HasVisitedGroup(uint32 group_index) const
	{
		return m_GroupsVisitedMask.get(group_index);
	}
	
	void MarkGroupAsVisited(uint32 group_index)
	{
		ASSERT(!m_GroupsVisitedMask.get(group_index));
		m_GroupsVisitedMask.set(group_index);
		m_GroupsVisited.push_back(group_index);
	}

	void ClearGroupVisitingInfo()
	{
		for (auto group_index : m_GroupsVisited)
			m_GroupsVisitedMask.clear(group_index);
		m_GroupsVisited.clear();
	}

	const CSegmentGroupGraph& m_Graph;
	TBFSTraversal<CSegmentGroupGraph, std::queue<std::pair<uint32, dist_t>>> m_Traversal;
	CBitVector  m_GroupsVisitedMask;
	std::vector<uint32> m_GroupsVisited;
	dist_t m_Radius;
	uint32 m_N;
	uint32 m_TD;
};

static void SegmentGroupIntegrationTask(
	const CSegmentGroupGraph& graph,
	const SPSTARadii& radii,
	const std::vector<uint32>& first_node_per_group,
	const std::vector<uint32>& nodes,
	uint32 first_group,
	uint32 group_count,
	uint32 node_count,  // Index of first node past the nodes of this group (used for calculating number of nodes for last group)
	float* out_Int, 
	uint32* out_N,
	float* out_TD, 
	std::atomic<unsigned int>& groups_processed_count)
{
	CSegmentGroupIntegration seg_int(graph, radii);
	for (uint32 group_index = first_group; group_index < first_group + group_count; ++group_index)
	{
		uint32 N = 0;
		float TD = 0;
		const auto first_node = first_node_per_group[group_index];
		const auto num_nodes = ((group_count - 1 == group_index - first_group) ? node_count : first_node_per_group[group_index + 1]) - first_node;
		if (node_count > 0)
			seg_int.CalculateIntegration(nodes.data() + first_node, num_nodes, N, TD);
		if (out_Int)
			out_Int[group_index] = CalculateIntegrationScore(N, TD);
		if (out_N)
			out_N[group_index] = N;
		if (out_TD)
			out_TD[group_index] = TD;
		++groups_processed_count;
	}
}

bool SegmentGroupIntegration(const CSegmentGroupGraph& graph, const SPSTARadii& radii, float* out_Int, uint32* out_N, float* out_TD, IProgressCallback& progress)
{
	using namespace std;

	if (0 == graph.NodeCount() || 0 == graph.GroupCount())
		return true;

	// Order nodes by group
	std::vector<uint32> first_node_per_group(graph.GroupCount(), 0);
	for (uint32 i = 0; i < graph.NodeCount(); ++i)
		first_node_per_group[graph.GroupidFromNode(i)]++;
	uint32 n = 0;
	for (uint32 i = 0; i < graph.GroupCount(); ++i)
	{
		const uint32 t = first_node_per_group[i];
		first_node_per_group[i] = n;
		n += t;
	}
	ASSERT(graph.NodeCount() == n);
	std::vector<uint32> nodes_by_group(graph.NodeCount());
	for (uint32 i = 0; i < graph.NodeCount(); ++i)
		nodes_by_group[first_node_per_group[graph.GroupidFromNode(i)]++] = i;
	for (uint32 i = graph.GroupCount() - 1; i > 0; --i)
		first_node_per_group[i] = first_node_per_group[i - 1];
	first_node_per_group[0] = 0;

	// Multi-threading capability metrics
	const uint32 max_threads = USE_MULTIPLE_CORES ? max(thread::hardware_concurrency(), 1u) : 1;
	const uint32 groups_per_thread = (uint32)(graph.GroupCount() + max_threads - 1) / max_threads;

	// Progress counter
	std::atomic<unsigned int> groups_processed_count(0);

	// Create tasks
	std::vector<std::future<void>> tasks;
	tasks.reserve(max_threads);
	for (unsigned int thread_index = 0; thread_index < max_threads; ++thread_index)
	{
		const unsigned int first_group_to_process = (groups_per_thread * thread_index);
		const int num_groups_to_process = min((int)graph.GroupCount() - (int)first_group_to_process, (int)groups_per_thread);
		if (num_groups_to_process <= 0)
			break;
		const auto end_group = first_group_to_process + num_groups_to_process;
		const auto node_count = ((end_group == graph.GroupCount()) ? (uint32)nodes_by_group.size() : first_node_per_group[end_group]);
		tasks.push_back(std::async(
			std::launch::async,
			SegmentGroupIntegrationTask,
			std::ref(graph),
			std::ref(radii),
			std::ref(first_node_per_group),
			std::ref(nodes_by_group),
			first_group_to_process,
			num_groups_to_process,
			node_count,
			out_Int,
			out_N,
			out_TD,
			std::ref(groups_processed_count)));
	}

	// Wait for tasks to finish, and update progress every 100ms
	for (size_t task_index = 0; task_index < tasks.size(); ++task_index)
	{
		auto& task = tasks[task_index];
		while (std::future_status::ready != task.wait_for(std::chrono::milliseconds(100)))
			progress.ReportProgress((float)groups_processed_count.load() / graph.GroupCount());
		progress.ReportProgress((float)groups_processed_count.load() / graph.GroupCount());
	}

	// Verify that all groups were processed
	if (groups_processed_count.load() != graph.GroupCount())
	{
		LOG_ERROR("Segment Group Integration algorithm failed (all groups were not processed!?).");
		return false;
	}

	progress.ReportProgress(1.f);

	return true;
}

SPSTASegmentGroupIntegrationDesc::SPSTASegmentGroupIntegrationDesc()
	: m_Version(VERSION)
	, m_Graph(nullptr)
	, m_ProgressCallback(nullptr)
	, m_ProgressCallbackUser(nullptr)
	, m_OutIntegration(nullptr)
	, m_OutNodeCount(nullptr)
	, m_OutTotalDepth(nullptr)
{}

PSTADllExport bool PSTASegmentGroupIntegration(const SPSTASegmentGroupIntegrationDesc* desc)
{
	if (desc->VERSION != desc->m_Version)
	{
		LOG_ERROR("Segment Group Integration version mismatch (%d != %d)", desc->m_Version, desc->VERSION);
		return false;
	}

	ASSERT(desc->m_Graph);

	CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

	SegmentGroupIntegration(*static_cast<CSegmentGroupGraph*>(desc->m_Graph), desc->m_Radius, desc->m_OutIntegration, desc->m_OutNodeCount, desc->m_OutTotalDepth, progress);

	return true;
}