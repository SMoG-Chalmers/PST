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

#include <queue>
#include <pstalgo/experimental/ShortestPathTraversal.h>
#include <pstalgo/utils/BitVector.h>

namespace psta
{
	// TODO: Move
	class CVistedFlags
	{
	public:
		CVistedFlags(size_t size)
			: m_MaxIndexCount(size / 16)
		{
			m_Bits.resize(size);
			m_Bits.clearAll();
			m_Indices.reserve(m_MaxIndexCount);
		}

		void clear()
		{
			if (m_Indices.size() >= m_MaxIndexCount)
				m_Bits.clearAll();
			else for (auto index : m_Indices)
				m_Bits.clear(index);
			m_Indices.clear();
		}

		bool hasVisited(size_t index) const
		{
			return m_Bits.get(index);
		}

		void setVisited(size_t index)
		{
			if (m_Indices.size() < m_MaxIndexCount)
				m_Indices.push_back((unsigned int)index);
			m_Bits.set(index);
		}

	private:
		const size_t m_MaxIndexCount;
		CBitVector m_Bits;
		std::vector<unsigned int> m_Indices;
	};

	template <size_t TDistCount>
	class TShortestPathTraversal: public IShortestPathTraversal
	{
	public:
		TShortestPathTraversal(const graph_t& graph)
			: m_Graph(graph)
			, m_VisitedNodes(graph.NetworkNodeCount())
			, m_NodeStates(graph.NetworkNodeCount())
			, m_VisitedDestinations(graph.DestinationCount())
		{
			ASSERT(graph.DistanceTypeCount() == TDistCount);
		}

		void Search(size_t origin_index, dist_callback_t& cb, const float* limits, float straight_line_distance_limit) override
		{
			m_VisitedNodes.clear();
			SearchInternal(origin_index, cb, limits, straight_line_distance_limit);
		}

		void SearchAccumulative(size_t origin_index, dist_callback_t& cb, const float* limits, float straight_line_distance_limit) override
		{
			SearchInternal(origin_index, cb, limits, straight_line_distance_limit);
		}

	private:
		struct SState
		{
			unsigned int   m_NodeIndex;
			graph_t::HNode m_NodeHandle;
			float m_Distances[TDistCount];

			inline bool IsDestination() const { return graph_t::INVALID_HANDLE == m_NodeHandle; }

			inline bool operator<(const SState& rhs) const { return m_Distances[0] > rhs.m_Distances[0]; }
		};

		struct SNodeState
		{
			float m_ShortestDistances[TDistCount];

			void Init(const float(&distances)[TDistCount])
			{
				for (size_t i = 0; i < TDistCount; ++i)
					m_ShortestDistances[i] = distances[i];
			}

			bool HasImprovement(const float(&distances)[TDistCount]) const
			{
				for (size_t i = 0; i < TDistCount; ++i)
					if (distances[i] < m_ShortestDistances[i])
						return true;
				return false;
			}

			bool Update(const float (&distances)[TDistCount])
			{
				bool updated = false;
				for (size_t i = 0; i < TDistCount; ++i)
				{
					if (distances[i] >= m_ShortestDistances[i])
						continue;
					m_ShortestDistances[i] = distances[i];
					updated = true;
				}
				return updated;
			}
		};

		void SearchInternal(size_t origin_index, dist_callback_t& cb, const float* limits, float straight_line_distance_limit)
		{
			m_VisitedDestinations.clear();

			for (size_t i = 0; i < TDistCount; ++i)
				m_Limits[i] = limits[i];
			m_StraightLineDistanceLimitSqrd = straight_line_distance_limit;

			if (m_Graph.NodePositionsEnabled())
				m_OriginPosition = m_Graph.NodePosition(m_Graph.OriginNode(origin_index));

			SState s;
			s.m_NodeIndex = (unsigned int)m_Graph.OriginNodeIndex(origin_index);
			s.m_NodeHandle = m_Graph.NodeHandleFromIndex(s.m_NodeIndex);
			for (auto& d : s.m_Distances)
				d = 0;
			TraverseEdges(s);

			while (!m_StateQueue.empty())
			{
				const auto s = m_StateQueue.top();
				m_StateQueue.pop();
				if (!s.IsDestination())
					VisitNetworkNode(s);
				else if (!m_VisitedDestinations.hasVisited(s.m_NodeIndex))
				{
					m_VisitedDestinations.setVisited(s.m_NodeIndex);
					cb(s.m_NodeIndex, s.m_Distances[0]);
				}
			}
		}

		void TraverseEdges(const SState& s)
		{
			auto& node = m_Graph.Node(s.m_NodeHandle);
			m_Graph.ForEachEdge(node, [&](const graph_t::SEdge& e)
			{
				SState new_state;
				size_t i;
				for (i = 0; i < TDistCount; ++i)
				{
					new_state.m_Distances[i] = s.m_Distances[i] + m_Graph.EdgeDistance(e, (unsigned int)i);
					if (new_state.m_Distances[i] > m_Limits[i])
						break;
				}
				if (i < TDistCount)
					return;
				if (m_Graph.EdgePointsToDestination(e))
				{
					if (m_VisitedDestinations.hasVisited(e.TargetIndex()))
						return;
				}
				else if (m_VisitedNodes.hasVisited(e.TargetIndex()) && !m_NodeStates[e.TargetIndex()].HasImprovement(s.m_Distances))
					return;
				if (HasStraightLineLimit() && !TestStraightLineLimit(m_Graph.TargetPosition(e)))
					return;
				new_state.m_NodeIndex  = e.TargetIndex();
				new_state.m_NodeHandle = e.TargetHandle();
				m_StateQueue.push(new_state);
			});
		}

		void VisitNetworkNode(const SState& s)
		{
			if (!m_VisitedNodes.hasVisited(s.m_NodeIndex))
			{
				m_VisitedNodes.setVisited(s.m_NodeIndex);
				m_NodeStates[s.m_NodeIndex].Init(s.m_Distances);
			}
			else if (!m_NodeStates[s.m_NodeIndex].Update(s.m_Distances))
				return;
			TraverseEdges(s);
		}

		bool HasStraightLineLimit() const
		{
			return m_StraightLineDistanceLimitSqrd > 0 && m_StraightLineDistanceLimitSqrd < std::numeric_limits<float>::infinity();
		}

		bool TestStraightLineLimit(const float2& pos) const
		{
			return (pos - m_OriginPosition).getLengthSqr() <= m_StraightLineDistanceLimitSqrd;
		}

		const CDirectedMultiDistanceGraph& m_Graph;
		float m_StraightLineDistanceLimitSqrd;
		float m_Limits[TDistCount];
		float2 m_OriginPosition;
		std::priority_queue<SState> m_StateQueue;
		std::vector<SNodeState> m_NodeStates;
		CVistedFlags m_VisitedNodes;
		CVistedFlags m_VisitedDestinations;
	};

	std::unique_ptr<IShortestPathTraversal> CreateShortestPathTraversal(const CDirectedMultiDistanceGraph& graph)
	{
		switch (graph.DistanceTypeCount())
		{
		case 1: return std::make_unique<TShortestPathTraversal<1>>(graph);
		case 2: return std::make_unique<TShortestPathTraversal<2>>(graph);
		case 3: return std::make_unique<TShortestPathTraversal<3>>(graph);
		case 4: return std::make_unique<TShortestPathTraversal<4>>(graph);
		case 5: return std::make_unique<TShortestPathTraversal<5>>(graph);
		}
		throw std::runtime_error("Unsupported distance type count");
	}
}