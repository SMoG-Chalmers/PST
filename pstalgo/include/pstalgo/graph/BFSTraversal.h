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
#include <pstalgo/utils/BitVector.h>
#include <pstalgo/Debug.h>

template <class TGraph, class TQueue>
class TBFSTraversal
{
public:
	typedef typename TGraph::node_index_t node_index_t;
	typedef typename TGraph::edge_t edge_t;
	typedef typename TGraph::dist_t dist_t;

	TBFSTraversal(const TGraph& graph)
		: m_Graph(graph)
	{
		m_VisitedNodesMask.resize(graph.NodeCount());
		m_VisitedNodesMask.clearAll();
	}

	void operator=(const TBFSTraversal& other) = delete;

	template <class TDelegate>
	void TSearch(node_index_t origin, const dist_t& initial_dist, const dist_t& radius, TDelegate& dlgt)
	{
		TSearchMulti(&origin, 1, initial_dist, radius, dlgt);
	}

	template <class TDelegate>
	void TSearchMulti(const uint32* origins, uint32 origin_count, const dist_t& initial_dist, const dist_t& radius, TDelegate& dlgt)
	{
		ASSERT(m_Queue.empty());
		for (uint32 origin_index = 0; origin_index < origin_count; ++origin_index)
		{
			const auto node = origins[origin_index];
			m_Queue.push(std::make_pair(node, initial_dist));
		}
		TSearchInternal(radius, dlgt);
		ClearNodeVisitingInfo();
	}

private:
	template <class TDelegate>
	void TSearchInternal(const dist_t& radius, TDelegate& dlgt)
	{
		while (!m_Queue.empty())
		{
			const auto node = m_Queue.front().first;
			const auto dist = m_Queue.front().second;
			m_Queue.pop();

			if (m_VisitedNodesMask.get(node))
				continue;

			MarkNodeAsVisited(node);

			dlgt.Visit(node, dist);

			m_Graph.ForEachEdge(node, [&](edge_t edge)
			{
				if (m_VisitedNodesMask.get(m_Graph.GetTargetNode(edge)))
					return;  // Early out check
				const auto accumulated_dist = dist + m_Graph.GetDistance(edge);
				if (dlgt.TestRadius(accumulated_dist, radius))
					m_Queue.push(std::make_pair(m_Graph.GetTargetNode(edge), accumulated_dist));
			});
		}
	}

	void MarkNodeAsVisited(node_index_t node)
	{
		m_VisitedNodesMask.set(node);
		m_VisitedNodes.push_back(node);
	}

	void ClearNodeVisitingInfo()
	{
		for (auto node : m_VisitedNodes)
			m_VisitedNodesMask.clear(node);
		m_VisitedNodes.clear();
	}

	const TGraph& m_Graph;
	TQueue m_Queue;
	CBitVector m_VisitedNodesMask;
	std::vector<node_index_t> m_VisitedNodes;
};