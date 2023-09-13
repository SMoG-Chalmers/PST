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
#include <pstalgo/geometry/Plane2D.h>
#include <pstalgo/maths.h>


// GENERILIZED VISIBILITY - BASED DESIGN EVALUATION USING GPU
// http://papers.cumincad.org/data/works/att/caadria2018_056.pdf


static const float EPSILON = 0.0001f;

inline static float AngleRadFromDirection(const float2& dir)
{
	return atan2f(dir.y, dir.x);
}

// Returns angle in range [0..2*PI)
// Assumes a € [-2*PI..2*PI)
template <typename T>
inline static T GetPositiveAngleRad(T a)
{
	return a + ((T)PI * 2) * (a < 0);
}

CIsovistCalculator::CIsovistCalculator()
	: m_EdgeHeap(HeapIndexUpdater(m_HeapIndexFromEdgeIndex))
{
}

void CIsovistCalculator::CalculateIsovist(
	const float2& origin, 
	float fov_deg, 
	float direction_deg, 
	const std::pair<float2, float2>* edges, 
	size_t edge_count, 
	const uint32_t* edge_count_per_obstacle,
	size_t obstacle_count,
	std::vector<float2>& ret_isovist, 
	size_t& ret_visible_obstacle_count,
	CBitVector& obstacle_visibility_mask)
{
	m_EdgeEndPoints.clear();
	m_EdgeEndPoints.reserve(edge_count * 2);

	m_Edges.clear();
	m_HeapIndexFromEdgeIndex.clear();

	m_EdgeHeap.clear();

	obstacle_visibility_mask.resize(obstacle_count);
	obstacle_visibility_mask.clearAll();

	const auto fov_rad = deg2rad(fov_deg);
	const auto direction_rad = normalizeAngleRad(deg2rad(direction_deg));
	const auto fov_min_rad = normalizeAngleRad(direction_rad - fov_rad * .5f);

	{
		size_t edge_index = 0;
		for (size_t obstacle_index = 0; obstacle_index < obstacle_count; ++obstacle_index)
		{
			const auto obstacle_edge_count = edge_count_per_obstacle[obstacle_index];
			for (uint32_t obstacle_edge_index = 0; obstacle_edge_index < obstacle_edge_count; ++obstacle_edge_index)
			{
				const auto& e = edges[edge_index++];
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
				// a0,a1 € [0..2*PI)
				const auto a0 = GetPositiveAngleRad(AngleRadFromDirection(p0) - fov_min_rad);
				const auto a1 = GetPositiveAngleRad(AngleRadFromDirection(p1) - fov_min_rad);
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
				edge.index = (uint32_t)m_Edges.size();
				edge.obstacle = (uint32_t)obstacle_index;
				m_EdgeEndPoints.push_back(EdgeEndPoint(edge.index, a0, false));
				m_EdgeEndPoints.push_back(EdgeEndPoint(edge.index, a1, true));
				m_HeapIndexFromEdgeIndex.push_back((uint32_t)-1);
				m_Edges.push_back(edge);
				if (a0 > a1)
				{
					m_EdgeHeap.push(edge);
				}
			}
		}
	}

	std::sort(m_EdgeEndPoints.begin(), m_EdgeEndPoints.end());

	size_t visible_obstacle_count = 0;

	auto try_add_to_isovist = [&obstacle_visibility_mask, &ret_isovist, origin, &visible_obstacle_count](const float2& pt_local, uint32_t obstacle_index)
	{
		const auto pt_world = pt_local + origin;
		if (ret_isovist.empty() || (pt_world - ret_isovist.back()).getLengthSqr() > 0.001f)
		{
			ret_isovist.push_back(pt_world);
			if (!obstacle_visibility_mask.get(obstacle_index))
			{
				++visible_obstacle_count;
				obstacle_visibility_mask.set(obstacle_index);
			}
		}
	};

	if (fov_deg < 360)
	{
		ret_isovist.push_back(origin);
		if (!m_EdgeHeap.empty())
		{
			const auto& edge = m_EdgeHeap.top();

			const auto vec_fov_min = directionVectorfromAngleRad(direction_rad - .5f * fov_rad + (float)PI * .5f);
			const Plane2Df plane_fov_min = { vec_fov_min, 0 };
			auto p0 = edge.p0;
			auto p1 = edge.p1;
			ClipLineSegment(p0, p1, plane_fov_min);
			try_add_to_isovist(p0, edge.obstacle);
		}
	}

	for (const auto& pt : m_EdgeEndPoints)
	{
		if (pt.IsEndPoint())
		{
			const auto edge_index = pt.EdgeIndex();
			const auto heap_index = m_HeapIndexFromEdgeIndex[edge_index];
			ASSERT(heap_index != (uint32_t)-1 && "Maybe edge is tangent to direction from origin and end point got added before start point?");
			if (0 != heap_index)
			{
				m_EdgeHeap.removeAt(heap_index);
				continue;
			}
			if (pt.Angle >= fov_rad)
			{
				break;
			}
			const auto& edge = m_EdgeHeap.top();
			const auto prev_p1 = edge.p1;
			try_add_to_isovist(prev_p1, edge.obstacle);
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
					try_add_to_isovist(p, next_edge.obstacle);
				}
			}
		}
		else
		{
			if (pt.Angle >= fov_rad) 
			{
				break;
			}
			const auto& edge = m_Edges[pt.EdgeIndex()];
			if (m_EdgeHeap.empty())
			{
				try_add_to_isovist(edge.p0, edge.obstacle);
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
						try_add_to_isovist(p, edge.obstacle);
					}
					// Add p0 of new edge to isovist
					try_add_to_isovist(edge.p0, edge.obstacle);
				}
			}
		}

	}

	if (fov_deg < 360 && !m_EdgeHeap.empty())
	{
		const auto& edge = m_EdgeHeap.top();
		const auto vec_fov_max = directionVectorfromAngleRad(direction_rad + .5f * fov_rad - .5f * (float)PI);
		const Plane2Df plane_fov_min = { vec_fov_max, 0 };
		auto p0 = edge.p0;
		auto p1 = edge.p1;
		ClipLineSegment(p0, p1, plane_fov_min);
		try_add_to_isovist(p1, edge.obstacle);
	}

	ret_visible_obstacle_count = visible_obstacle_count;

	m_EdgeHeap.clear();
	m_HeapIndexFromEdgeIndex.clear();
	m_EdgeEndPoints.clear();
	m_Edges.clear();
}