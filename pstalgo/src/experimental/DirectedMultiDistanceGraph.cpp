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
#include <cstring>

#include <pstalgo/experimental/DirectedMultiDistanceGraph.h>
#include <pstalgo/maths.h>

namespace psta
{
	CDirectedMultiDistanceGraph::CDirectedMultiDistanceGraph(const EPSTADistanceType* distance_types, size_t distance_type_count, bool enable_node_positions)
		: CSparseDirectedGraph(enable_node_positions ? sizeof(float2) : 0, (unsigned int)distance_type_count * sizeof(float))
		, m_HasNodePositions(enable_node_positions)
		, m_DistanceTypeCount((unsigned int)distance_type_count)
	{
		ASSERT(distance_type_count <= MAX_DISTANCE_TYPES);
		for (unsigned int i = 0; i < distance_type_count; ++i)
			m_DistanceTypes[i] = distance_types[i];
	}

	void CDirectedMultiDistanceGraph::SetFirstOriginNodeIndex(size_t index)
	{
		m_FirstOriginNodeIndex = index;
	}

	size_t CDirectedMultiDistanceGraph::NetworkNodeCount() const
	{
		return m_FirstOriginNodeIndex;
	}

	size_t CDirectedMultiDistanceGraph::OriginNodeCount() const
	{
		return NodeCount() - m_FirstOriginNodeIndex;
	}

	size_t CDirectedMultiDistanceGraph::OriginNodeIndex(size_t origin_index) const
	{
		return m_FirstOriginNodeIndex + origin_index;
	}

	const CDirectedMultiDistanceGraph::SNode& CDirectedMultiDistanceGraph::OriginNode(size_t index) const
	{
		return Node(NodeHandleFromIndex(OriginNodeIndex(index)));
	}

	bool CDirectedMultiDistanceGraph::EdgePointsToDestination(const SEdge& e) const
	{
		return INVALID_HANDLE == e.TargetHandle();
	}

	int CDirectedMultiDistanceGraph::DestinationIndexFromEdge(const SEdge& e) const
	{
		return EdgePointsToDestination(e) ? e.TargetIndex() : -1;
	}

	void CDirectedMultiDistanceGraph::SetDestinationCount(size_t count)
	{
		m_DestinationCount = count;
		if (m_HasNodePositions)
			m_DestinationPositions.resize(count);

	}

	size_t CDirectedMultiDistanceGraph::DestinationCount() const
	{
		return m_DestinationCount;
	}

	void CDirectedMultiDistanceGraph::SetDestinationPosition(size_t index, const float2& pos)
	{
		m_DestinationPositions[index] = pos;
	}

	const float2& CDirectedMultiDistanceGraph::DestinationPosition(size_t index) const
	{
		return m_DestinationPositions[index];
	}

	/**
	 *  TODO: OPTIMIZATION: Skip creating nodes with zero edges (should halve the nodes for segment graphs when has_angular_distance is true)
	 *
	 *  TODO: OPTIMIZATION: For each edge E0 that points to a node with one single edge E1: Merge E0 + E1
	 */
	CDirectedMultiDistanceGraph BuildDirectedMultiDistanceGraph(
		const CAxialGraph& axial_graph,
		const EPSTADistanceType* distance_types,
		size_t distance_type_count,
		bool store_node_positions,
		const float2* origins,
		size_t origin_count,
		EPSTANetworkElement destination_type)
	{
		const bool has_angular_distance = std::find(distance_types, distance_types + distance_type_count, EPSTADistanceType_Angular) != distance_types + distance_type_count;

		// Verify supported distance types
		const auto SUPPORTED_DISTANCE_TYPES_MASK = EPSTADistanceTypeMask_Walking | EPSTADistanceTypeMask_Steps | EPSTADistanceTypeMask_Angular;
		for (unsigned int i = 0; i < distance_type_count; ++i)
			if (!(EPSTADistanceMaskFromType(distance_types[i]) & SUPPORTED_DISTANCE_TYPES_MASK))
				throw std::runtime_error("Unsupported distance type specified for building directed multi-distance graph");

		CDirectedMultiDistanceGraph graph(distance_types, distance_type_count, store_node_positions);

		switch (destination_type)
		{
		case EPSTANetworkElement_Point:
			graph.SetDestinationCount(axial_graph.getPointCount());
			if (store_node_positions)
				for (int i = 0; i < axial_graph.getPointCount(); ++i)
					graph.SetDestinationPosition(i, axial_graph.getPoint(i).coords);
			break;
		case EPSTANetworkElement_Junction:
			graph.SetDestinationCount(axial_graph.getCrossingCount());
			if (store_node_positions)
				for (int i = 0; i < axial_graph.getCrossingCount(); ++i)
					graph.SetDestinationPosition(i, axial_graph.getCrossing(i).pt);
			break;
		case EPSTANetworkElement_Line:
			graph.SetDestinationCount(axial_graph.getLineCount());
			if (store_node_positions)
			{
				for (int i = 0; i < axial_graph.getLineCount(); ++i)
				{
					const auto& line = axial_graph.getLine(i);
					graph.SetDestinationPosition(i, (line.p1 + line.p2) * .5f);
				}
			}
			break;
		default:
			throw std::runtime_error("Unsupported destination type specified for building directed multi-distance graph");
		}
	
		graph.ReserveNodeCount(has_angular_distance ?
			axial_graph.getLineCrossingCount() * 2 + origin_count :
			axial_graph.getLineCrossingCount() + origin_count);

		struct SEdgeData
		{
			SEdgeData() { memset(m_Distances, 0, sizeof(m_Distances)); }
			unsigned int                       m_TargetIndex;
			CDirectedMultiDistanceGraph::HNode m_TargetHandle;
			float m_Distances[EPSTADistanceType__COUNT];
		};
		std::vector<SEdgeData> edges;

		std::vector<unsigned int> temp_vec;

		// Create network
		for (int pass = 0; pass < 2; ++pass)
		{
			for (int i = 0; i < axial_graph.getLineCrossingCount(); ++i)
			{
				const auto& lc = axial_graph.getLineCrossing(i);
				const auto& line = axial_graph.getLine(lc.iLine);

				if (has_angular_distance)
				{
					// First pass is forwards (0), second pass backwards (1)
					for (int direction = 0; direction < 2; ++direction)
					{
						edges.clear();

						const auto angle = direction ? reverseAngle(line.angle) : line.angle;

						// Edges to other line-crossings
						for (int c = 0; c < line.nCrossings; ++c)
						{
							const auto lc_idx = line.iFirstCrossing + c;
							const auto& lc_src = axial_graph.getLineCrossing(lc_idx);
							if ((0 == direction && (lc_src.linePos <= lc.linePos)) ||
								(1 == direction && (lc_src.linePos >= lc.linePos)))
								continue;
							const auto& lc_dst = axial_graph.getLineCrossing(lc_src.iOpposite);
							const auto& line_dst = axial_graph.getLine(lc_dst.iLine);
							const auto node_idx_fwd = lc_src.iOpposite * 2;
							const auto node_idx_bwd = node_idx_fwd + 1;
							SEdgeData edge_data;
							edge_data.m_Distances[EPSTADistanceType_Walking] = fabs(lc.linePos - lc_src.linePos);
							edge_data.m_Distances[EPSTADistanceType_Steps] = 1;
							if (pass)
							{
								edge_data.m_TargetIndex = node_idx_fwd;
								edge_data.m_TargetHandle = graph.NodeHandleFromIndex(node_idx_fwd);
								edge_data.m_Distances[EPSTADistanceType_Angular] = angleDiff(angle, line_dst.angle);
							}
							edges.push_back(edge_data);
							if (pass)
							{
								edge_data.m_TargetIndex = node_idx_bwd;
								edge_data.m_TargetHandle = graph.NodeHandleFromIndex(node_idx_bwd);
								edge_data.m_Distances[EPSTADistanceType_Angular] = angleDiff(angle, reverseAngle(line_dst.angle));
							}
							edges.push_back(edge_data);
						}

						// Edges to destinations
						switch (destination_type)
						{
						case EPSTANetworkElement_Point:
							for (int p = 0; p < line.nPoints; ++p)
							{
								const auto pt_idx = axial_graph.getLinePoint(line.iFirstPoint + p);
								const auto& pt = axial_graph.getPoint(pt_idx);
								if ((0 == direction && (pt.linePos < lc.linePos)) ||
									(1 == direction && (pt.linePos > lc.linePos)))
									continue;
								SEdgeData edge_data;
								if (pass)
								{
									edge_data.m_Distances[EPSTADistanceType_Walking] = fabs(lc.linePos - pt.linePos) + pt.distFromLine;
									edge_data.m_TargetIndex = pt_idx;
									edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
								}
								edges.push_back(edge_data);
							}
							break;
						case EPSTANetworkElement_Junction:
							temp_vec.clear();
							for (int c = 0; c < line.nCrossings; ++c)
							{
								const auto lc_idx = line.iFirstCrossing + c;
								const auto& lc_dst = axial_graph.getLineCrossing(lc_idx);
								if ((0 == direction && (lc_dst.linePos <= lc.linePos)) ||
									(1 == direction && (lc_dst.linePos >= lc.linePos)))
									continue;
								if (std::find(temp_vec.begin(), temp_vec.end(), (unsigned int)lc_dst.iCrossing) == temp_vec.end())
								{
									temp_vec.push_back(lc_dst.iCrossing);
									SEdgeData edge_data;
									if (pass)
									{
										edge_data.m_Distances[EPSTADistanceType_Walking] = fabs(lc_dst.linePos - lc.linePos);
										edge_data.m_TargetIndex = lc_dst.iCrossing;
										edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
									}
									edges.push_back(edge_data);
								}
							}
							break;
						case EPSTANetworkElement_Line:
							{
								const float center_pos = line.length * .5f;
								if ((0 == direction && (center_pos >= lc.linePos)) ||
									(1 == direction && (center_pos <= lc.linePos)))
								{
									SEdgeData edge_data;
									if (pass)
									{
										edge_data.m_Distances[EPSTADistanceType_Walking] = fabs(lc.linePos - center_pos);
										edge_data.m_TargetIndex = lc.iLine;
										edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
									}
									edges.push_back(edge_data);
								}
							}
							break;
						}

						// Create node or populate edges (depending on pass)
						if (0 == pass)
							graph.NewNode((unsigned int)edges.size());
						else
						{
							const auto node_index = i * 2 + direction;
							auto& node = graph.Node(graph.NodeHandleFromIndex(node_index));
							ASSERT(node.EdgeCount() == edges.size());
							size_t edge_index = 0;
							graph.ForEachEdge(node, [&](CDirectedMultiDistanceGraph::SEdge& e)
							{
								const auto& edge_data = edges[edge_index];
								e.SetTarget(edge_data.m_TargetHandle, edge_data.m_TargetIndex);
								auto* dists = graph.EdgeDistances(e);
								for (unsigned int d = 0; d < distance_type_count; ++d)
									dists[d] = edge_data.m_Distances[distance_types[d]];
								++edge_index;
							});
						}
					}
				}
				else
				{
					edges.clear();

					// Edges to other line-crossings
					for (int c = 0; c < line.nCrossings; ++c)
					{
						const auto lc_idx = line.iFirstCrossing + c;
						const auto& lc_src = axial_graph.getLineCrossing(lc_idx);
						if (lc_src.linePos == lc.linePos)
							continue;
						const auto& lc_dst = axial_graph.getLineCrossing(lc_src.iOpposite);
						const auto& line_dst = axial_graph.getLine(lc_dst.iLine);
						SEdgeData edge_data;
						if (pass)
						{
							edge_data.m_Distances[EPSTADistanceType_Walking] = fabs(lc.linePos - lc_src.linePos);
							edge_data.m_Distances[EPSTADistanceType_Steps] = 1;
							edge_data.m_TargetIndex = lc_src.iOpposite;
							edge_data.m_TargetHandle = graph.NodeHandleFromIndex(edge_data.m_TargetIndex);
						}
						edges.push_back(edge_data);
					}

					// Edges to destinations
					switch (destination_type)
					{
					case EPSTANetworkElement_Point:
						for (int p = 0; p < line.nPoints; ++p)
						{
							const auto pt_idx = axial_graph.getLinePoint(line.iFirstPoint + p);
							const auto& pt = axial_graph.getPoint(pt_idx);
							SEdgeData edge_data;
							if (pass)
							{
								edge_data.m_Distances[EPSTADistanceType_Walking] = fabs(lc.linePos - pt.linePos) + pt.distFromLine;
								edge_data.m_TargetIndex = pt_idx;
								edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
							}
							edges.push_back(edge_data);
						}
						break;
					case EPSTANetworkElement_Junction:
						temp_vec.clear();
						for (int c = 0; c < line.nCrossings; ++c)
						{
							const auto lc_idx = line.iFirstCrossing + c;
							const auto& lc_dst = axial_graph.getLineCrossing(lc_idx);
							if (lc_dst.linePos == lc.linePos)
								continue;
							if (std::find(temp_vec.begin(), temp_vec.end(), (unsigned int)lc_dst.iCrossing) == temp_vec.end())
							{
								temp_vec.push_back(lc_dst.iCrossing);
								SEdgeData edge_data;
								if (pass)
								{
									edge_data.m_Distances[EPSTADistanceType_Walking] = fabs(lc_dst.linePos - lc.linePos);
									edge_data.m_TargetIndex = lc_dst.iCrossing;
									edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
								}
								edges.push_back(edge_data);
							}
						}
						break;
					case EPSTANetworkElement_Line:
						{
							SEdgeData edge_data;
							if (pass)
							{
								const float center_pos = line.length * .5f;
								edge_data.m_Distances[EPSTADistanceType_Walking] = fabs(lc.linePos - center_pos);
								edge_data.m_TargetIndex = lc.iLine;
								edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
							}
							edges.push_back(edge_data);
						}
						break;
					}

					// Create node or populate edges (depending on pass)
					if (0 == pass)
						graph.NewNode((unsigned int)edges.size());
					else
					{
						auto& node = graph.Node(graph.NodeHandleFromIndex(i));
						ASSERT(node.EdgeCount() == edges.size());
						size_t edge_index = 0;
						graph.ForEachEdge(node, [&](CDirectedMultiDistanceGraph::SEdge& e)
						{
							const auto& edge_data = edges[edge_index];
							e.SetTarget(edge_data.m_TargetHandle, edge_data.m_TargetIndex);
							auto* dists = graph.EdgeDistances(e);
							for (unsigned int d = 0; d < distance_type_count; ++d)
								dists[d] = edge_data.m_Distances[distance_types[d]];
							++edge_index;
						});
					}
				}
			}
		}

		graph.SetFirstOriginNodeIndex(graph.NodeCount());

		// Create origin nodes with edges into the network
		for (size_t i = 0; i < origin_count; ++i)
		{
			float dist_from_origin_to_line, pos_on_line;
			const auto line_index = axial_graph.getClosestLine(origins[i], &dist_from_origin_to_line, &pos_on_line);
			const auto& line = axial_graph.getLine(line_index);
			
			edges.clear();
			
			// Edges to line-crossings
			for (int c_idx = 0; c_idx < line.nCrossings; ++c_idx)
			{
				const auto& lc_src = axial_graph.getLineCrossing(line.iFirstCrossing + c_idx);
				const auto& lc_dst = axial_graph.getLineCrossing(lc_src.iOpposite);
				const auto& line_dst = axial_graph.getLine(lc_dst.iLine);

				SEdgeData edge_data;
				edge_data.m_Distances[EPSTADistanceType_Walking] = dist_from_origin_to_line + fabs(pos_on_line - lc_src.linePos);
				edge_data.m_Distances[EPSTADistanceType_Steps]   = 1;

				if (has_angular_distance)
				{
					const auto angle = lc_src.linePos < pos_on_line ? reverseAngle(line.angle) : line.angle;
					const auto node_idx_fwd = lc_src.iOpposite * 2;
					const auto node_idx_bwd = node_idx_fwd + 1;
					edge_data.m_TargetIndex  = node_idx_fwd;
					edge_data.m_TargetHandle = graph.NodeHandleFromIndex(node_idx_fwd);
					edge_data.m_Distances[EPSTADistanceType_Angular] = angleDiff(angle, line_dst.angle);
					edges.push_back(edge_data);
					edge_data.m_TargetIndex = node_idx_bwd;
					edge_data.m_TargetHandle = graph.NodeHandleFromIndex(node_idx_bwd);
					edge_data.m_Distances[EPSTADistanceType_Angular] = angleDiff(angle, reverseAngle(line_dst.angle));
					edges.push_back(edge_data);
				}
				else
				{
					const auto node_idx = lc_src.iOpposite;
					edge_data.m_TargetIndex = node_idx;
					edge_data.m_TargetHandle = graph.NodeHandleFromIndex(node_idx);
					edges.push_back(edge_data);
				}
			}

			// Edges to destinations
			switch (destination_type)
			{
			case EPSTANetworkElement_Point:
				for (int p = 0; p < line.nPoints; ++p)
				{
					const auto pt_idx = axial_graph.getLinePoint(line.iFirstPoint + p);
					const auto& pt = axial_graph.getPoint(pt_idx);
					SEdgeData edge_data;
					edge_data.m_Distances[EPSTADistanceType_Walking] = dist_from_origin_to_line + fabs(pos_on_line - pt.linePos) + pt.distFromLine;
					edge_data.m_TargetIndex = pt_idx;
					edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
					edges.push_back(edge_data);
				}
				break;
			case EPSTANetworkElement_Junction:
				temp_vec.clear();
				for (int c = 0; c < line.nCrossings; ++c)
				{
					const auto lc_idx = line.iFirstCrossing + c;
					const auto& lc_dst = axial_graph.getLineCrossing(lc_idx);
					if (std::find(temp_vec.begin(), temp_vec.end(), (unsigned int)lc_dst.iCrossing) == temp_vec.end())
					{
						temp_vec.push_back(lc_dst.iCrossing);
						SEdgeData edge_data;
						edge_data.m_Distances[EPSTADistanceType_Walking] = dist_from_origin_to_line + fabs(lc_dst.linePos - pos_on_line);
						edge_data.m_TargetIndex = lc_dst.iCrossing;
						edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
						edges.push_back(edge_data);
					}
				}
				break;
			case EPSTANetworkElement_Line:
				{
					SEdgeData edge_data;
					const float center_pos = line.length * .5f;
					edge_data.m_Distances[EPSTADistanceType_Walking] = dist_from_origin_to_line + fabs(center_pos - pos_on_line);
					edge_data.m_TargetIndex = line_index;
					edge_data.m_TargetHandle = CDirectedMultiDistanceGraph::INVALID_HANDLE;
					edges.push_back(edge_data);
				}
				break;
			}

			// Create node
			const auto node_handle = graph.NewNode((unsigned int)edges.size());
			auto& node = graph.Node(node_handle);
			if (store_node_positions)
				graph.SetNodePosition(node, origins[i]);
			size_t edge_index = 0;
			graph.ForEachEdge(node, [&](CDirectedMultiDistanceGraph::SEdge& e)
			{
				const auto& edge_data = edges[edge_index];
				e.SetTarget(edge_data.m_TargetHandle, edge_data.m_TargetIndex);
				auto* dists = graph.EdgeDistances(e);
				for (unsigned int d = 0; d < distance_type_count; ++d)
					dists[d] = edge_data.m_Distances[distance_types[d]];
				++edge_index;
			});
		}

		return graph;
	}
}