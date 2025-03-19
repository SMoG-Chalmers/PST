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

#include <pstalgo/analyses/Common.h>
#include <pstalgo/graph/AxialGraph.h>
#include <pstalgo/utils/Span.h>
#include <pstalgo/Debug.h>
#include <pstalgo/Vec2.h>
#include "SparseDirectedGraph.h"

namespace psta
{
	/**
	 *  Sparse directed graph with multiple distance weights per edge.
	 *  A subset of the nodes are marked as origin nodes (upper part 
	 *  of node indices). The graph also has a set of destinations. 
	 *  Destinations are NOT part of the node set - they are merely 
	 *  referred to by index on edges leading out from the graph.
	 *  The graph can OPTIONALLY store node positions. If node positions
	 *  are enabled then positions are also stored for destinations.
	 */
	class CDirectedMultiDistanceGraph: public CSparseDirectedGraph
	{
	public:
		CDirectedMultiDistanceGraph(const EPSTADistanceType* distance_types, size_t distance_type_count, bool enable_node_positions);

		void SetFirstOriginNodeIndex(size_t index);

		size_t NetworkNodeCount() const;

		size_t OriginNodeCount() const;

		size_t OriginNodeIndex(size_t origin_index) const;

		const SNode& OriginNode(size_t index) const;

		bool EdgePointsToDestination(const SEdge& e) const;

		void SetDestinationCount(size_t count);

		void SetDestinationPosition(size_t index, const float2& pos);

		const float2& DestinationPosition(size_t index) const;

		size_t DestinationCount() const;

		int DestinationIndexFromEdge(const SEdge& e) const;

		inline EPSTADistanceType PrimaryDistanceType() const { return DistanceType(0); }

		inline unsigned int DistanceTypeCount() const { return m_DistanceTypeCount; }

		inline EPSTADistanceType DistanceType(unsigned int index) const { return m_DistanceTypes[index]; }

		inline float EdgePrimaryDistance(const SEdge& edge) const { return EdgeDistance(edge, 0); }

		inline float EdgeDistance(const SEdge& edge, unsigned int distance_index) const { return EdgeDistances(edge)[distance_index]; }

		inline float*       EdgeDistances(const SEdge& edge) { return (float*)edge.Data(); }
		inline const float* EdgeDistances(const SEdge& edge) const { return (const float*)edge.Data(); }

		bool NodePositionsEnabled() const { return m_HasNodePositions; }

		void SetNodePosition(SNode& node, const float2& pos) const { ASSERT(m_HasNodePositions); *(float2*)node.Data() = pos; }

		const float2& NodePosition(const SNode& node) const { ASSERT(m_HasNodePositions); return *(const float2*)node.Data(); }

		const float2& TargetPosition(const SEdge& edge) const { return EdgePointsToDestination(edge) ? DestinationPosition(edge.TargetIndex()) : NodePosition(Node(edge.TargetHandle())); }

	private:
		static const unsigned int MAX_DISTANCE_TYPES = 4;
		
		const bool m_HasNodePositions;
		unsigned int m_DistanceTypeCount = 0;
		size_t m_DestinationCount = 0;
		size_t m_FirstOriginNodeIndex = 0;
		EPSTADistanceType m_DistanceTypes[MAX_DISTANCE_TYPES];
		std::vector<float2> m_DestinationPositions;  // Only used if m_HasNodePositions is true
	};

	CDirectedMultiDistanceGraph BuildDirectedMultiDistanceGraph(
		const CAxialGraph& axial_graph,
		psta::span<const EPSTADistanceType> distance_types,
		psta::span<const float> line_weights,
		float weight_per_meter_for_point_edges,
		bool store_node_positions,
		const float2* origins,
		size_t origin_count,
		EPSTANetworkElement destination_type);
}