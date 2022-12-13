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
#include <pstalgo/geometry/IsovistCalculator.h>
#include <pstalgo/maths.h>


// GENERILIZED VISIBILITY - BASED DESIGN EVALUATION USING GPU
// http://papers.cumincad.org/data/works/att/caadria2018_056.pdf


static const float EPSILON = 0.0001f;

inline static float AngleFromDirection(const float2& dir)
{
	return atan2f(dir.y, dir.x);
}

CIsovistCalculator::CIsovistCalculator()
	: m_EdgeHeap(HeapIndexUpdater(m_HeapIndexFromEdgeIndex))
{
}

void CIsovistCalculator::CalculateIsovist(const float2& origin, const std::pair<float2, float2>* edges, size_t edge_count, std::vector<float2>& ret_isovist)
{
	std::vector<Edge> myedges;
	myedges.reserve(edge_count);

	m_EdgeEndPoints.clear();
	m_EdgeEndPoints.reserve(edge_count * 2);

	m_Edges.clear();
	m_HeapIndexFromEdgeIndex.clear();

	m_EdgeHeap.clear();

	for (size_t i = 0; i < edge_count; ++i)
	{
		const auto& e = edges[i];
		if ((e.second - e.first).getLengthSqr() < EPSILON)
		{
			continue;
		}
		const auto p0 = e.first - origin;
		const auto p1 = e.second - origin;
		if (crp(p0, p1) < EPSILON)
		{
			continue;  // Not facing origin (assumes polygon is cartesian clockwise)
		}
		const auto a0 = AngleFromDirection(p0);
		const auto a1 = AngleFromDirection(p1);
		if (a0 == a1)
		{
			continue;
		}
		Edge edge;
		edge.p0 = p0;
		edge.p1 = p1;
		edge.tangent = (p1 - p0).normalized();
		if (dot(edge.normal(), p0) > -EPSILON)
		{
			continue;  // Origin is too close to edge
		}
		edge.p0_angle = a0;
		edge.index = (uint32_t)m_Edges.size();
		m_EdgeEndPoints.push_back(EdgeEndPoint(edge.index, a0, false));
		m_EdgeEndPoints.push_back(EdgeEndPoint(edge.index, a1, true));
		m_HeapIndexFromEdgeIndex.push_back((uint32_t)-1);
		m_Edges.push_back(edge);
		if (a0 > 0 && a1 < 0)
		{
			m_EdgeHeap.push(edge);
		}
	}

	std::sort(m_EdgeEndPoints.begin(), m_EdgeEndPoints.end());

	auto try_add_to_isovist = [&ret_isovist, origin](const float2& pt_local)
	{
		const auto pt_world = pt_local + origin;
		if (ret_isovist.empty() || (pt_world - ret_isovist.back()).getLengthSqr() > 0.01f)
		{
			ret_isovist.push_back(pt_world);
		}
	};

	for (const auto& pt : m_EdgeEndPoints)
	{
		if (pt.IsEndPoint())
		{
			const auto edge_index = pt.EdgeIndex();
			const auto heap_index = m_HeapIndexFromEdgeIndex[edge_index];
			ASSERT(heap_index != (uint32_t)-1 && "Maybe edge is tangent to direction from origin and end point got added before start point?");
			if (0 == heap_index)
			{
				const auto prev_p1 = m_EdgeHeap.top().p1;
				try_add_to_isovist(prev_p1);
				m_EdgeHeap.pop();
				if (!m_EdgeHeap.empty())
				{
					const auto& next_edge = m_EdgeHeap.top();
					if (next_edge.p0 != prev_p1)
					{
						// Find intersection of next edge and vector from origin towwards p1 of previous edge
						const auto normal = next_edge.normal();
						const auto dist_from_next_along_normal = dot(normal, prev_p1 - next_edge.p0);
						const auto p1_normalized = prev_p1.normalized();
						const auto p = prev_p1 - (p1_normalized * (dist_from_next_along_normal / dot(p1_normalized, normal)));
						try_add_to_isovist(p);
					}
				}
			}
			else
			{
				m_EdgeHeap.removeAt(heap_index);
			}
		}
		else
		{
			const auto& edge = m_Edges[pt.EdgeIndex()];
			if (m_EdgeHeap.empty())
			{
				try_add_to_isovist(edge.p0);
				m_EdgeHeap.push(edge);
			}
			else
			{
				const auto prev_edge = m_EdgeHeap.top();
				m_EdgeHeap.push(edge);
				if (m_EdgeHeap.top().index == edge.index)
				{
					if (prev_edge.p1 != edge.p0)
					{
						// Find intersection of previous edge and vector from origin towwards p0 of new edge
						const auto normal = prev_edge.normal();
						const auto dist_from_prev_along_normal = dot(normal, edge.p0 - prev_edge.p0);
						const auto p0_normalized = edge.p0.normalized();
						const auto p = edge.p0 - (p0_normalized * (dist_from_prev_along_normal / dot(p0_normalized, normal)));
						try_add_to_isovist(p);
					}
					// Add p0 of new edge to isovist
					try_add_to_isovist(edge.p0);
				}
			}
		}

	}

	m_EdgeHeap.clear();
	m_HeapIndexFromEdgeIndex.clear();
	m_EdgeEndPoints.clear();
	m_Edges.clear();
}