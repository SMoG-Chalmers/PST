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
#include <pstalgo/Vec2.h>
#include <pstalgo/utils/RefHeap.h>


class CIsovistCalculator
{
public:
	CIsovistCalculator();

	void CalculateIsovist(const float2& origin, const std::pair<float2, float2>* edges, size_t edge_count, std::vector<float2>& ret_points);

private:
	struct EdgeEndPoint
	{
		float Angle;

		EdgeEndPoint() {}
		EdgeEndPoint(uint32_t edge_index, float angle, bool is_end_point)
			: m_EdgeIndexAndEndBit(edge_index | ((uint32_t)is_end_point << 31)), Angle(angle) {}

		inline uint32_t EdgeIndex() const { return m_EdgeIndexAndEndBit & 0x7FFFFFFF; }

		inline bool IsEndPoint() const { return (bool)(m_EdgeIndexAndEndBit >> 31); }

		inline bool operator<(const EdgeEndPoint& rhs) const
		{
			if (Angle == rhs.Angle)
			{
				return !IsEndPoint() && rhs.IsEndPoint();
			}
			return Angle < rhs.Angle;
		}

	private:
		uint32_t m_EdgeIndexAndEndBit;
	};

	struct Edge
	{
		float2 p0;
		float2 p1;
		float2 tangent;
		float p0_angle;
		uint32_t index;

		inline float2 normal() const { return float2(-tangent.y, tangent.x); }

		inline bool operator<(const Edge& rhs) const
		{
			const float my_p0_is_last = (float)(crp(p0, rhs.p0) < 0);
			const auto mp0 = (p0 * my_p0_is_last) + (rhs.p0 * (1.0f - my_p0_is_last));

			const float my_p1_is_first = (float)(crp(p1, rhs.p1) > 0);
			const auto mp1 = (p1 * my_p1_is_first) + (rhs.p1 * (1.0f - my_p1_is_first));

			const auto mv = (mp0 + mp1); // .normalized();
			const auto n = float2(-mv.y, mv.x);

			const auto my_v = p1 - p0;
			const float my_t = dot(mv - p0, n) / dot(my_v, n);
			const float my_depth = dot(p0 + my_v * my_t, mv);

			const auto rhs_v = rhs.p1 - rhs.p0;
			const float rhs_t = dot(mv - rhs.p0, n) / dot(rhs_v, n);
			const float rhs_depth = dot(rhs.p0 + rhs_v * rhs_t, mv);

			return my_depth < rhs_depth;
		}
	};

	class HeapIndexUpdater
	{
	public:
		HeapIndexUpdater(std::vector<uint32_t>& indices) : m_Indices(&indices) {}
		inline void operator()(const Edge& edge, size_t index) { (*m_Indices)[edge.index] = (uint32_t)index; }
	private:
		std::vector<uint32_t>* m_Indices;
	};
	
	CRefHeap<Edge, HeapIndexUpdater> m_EdgeHeap;
	std::vector<uint32_t> m_HeapIndexFromEdgeIndex;
	std::vector<EdgeEndPoint> m_EdgeEndPoints;
	std::vector<Edge> m_Edges;
};