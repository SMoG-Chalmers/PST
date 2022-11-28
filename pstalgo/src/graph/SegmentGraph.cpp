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

#include <pstalgo/Debug.h>
#include <pstalgo/graph/AxialGraph.h>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/graph/SegmentGraph.h>

CSegmentGraph::CSegmentGraph()
	: m_IntersectionAllocator(0x1000, 4)
	, m_WorldOrigin(0, 0)
{
}

CSegmentGraph::~CSegmentGraph()
{
}

bool CSegmentGraph::Create(const double2* line_coords, unsigned int line_coord_count, unsigned int* line_indices, unsigned int line_count)
{
	if (!line_indices && 0 == line_coord_count)
		line_coord_count = line_count * 2;

	// Bounding Box
	const auto bb = CRectd::BBFromPoints(line_coords, line_coord_count);

	// Origin in world space for local coordinate system
	const double2 world_origin(bb.CenterX(), bb.CenterY());
	m_WorldOrigin = world_origin;

	// Create intersections and a mapping from line coordinate index to intersections
	std::vector<SIntersection*> coord_to_intersection(line_coord_count);  // nullptr for coordinates with no intersection (dead ends)
	{
		memset(coord_to_intersection.data(), 0, coord_to_intersection.size() * sizeof(SIntersection*));
		// This here is ugly, but it saves us from allocating more memory. We calculate 
		// number of occurances of every coord index in line_indices, and store that in
		// the data of coord_to_intersection, temporarily.
		if (line_indices)
		{
			for (unsigned int i = 0; i < line_count * 2; ++i)
			{
				auto& at = coord_to_intersection[line_indices[i]];
				at = (SIntersection*)((size_t)at + 1);
			}
		}
		// Create an ordering of line coordinates
		std::vector<unsigned int> order(line_coord_count);
		for (unsigned int i = 0; i < order.size(); ++i)
			order[i] = i;
		std::sort(order.begin(), order.end(), [&](unsigned int a, unsigned int b) -> bool
		{
			const auto& p0 = line_coords[a];
			const auto& p1 = line_coords[b];
			return (p0.x == p1.x) ? (p0.y < p1.y) : (p0.x < p1.x);
		});
		// Fill in mappings
		for (unsigned int i = 0; i < order.size();)
		{
			const unsigned int start_coord_index = order[i];
			const unsigned int start = i;
			// Look how many identical coordinates we have
			unsigned int seg_count = 0;
			if (line_indices)
			{
				for (; i < order.size() && line_coords[order[i]] == line_coords[start_coord_index]; ++i)
					seg_count += (unsigned int)(size_t)coord_to_intersection[order[i]];  // This is ugly. See explanataion above!
			}
			else
			{
				for (++i; i < order.size() && line_coords[order[i]] == line_coords[start_coord_index]; ++i);
				seg_count = i - start;
			}
			if (1 == seg_count)
			{
				// Only one instance of this coordinate. Then it is a dead end.
				coord_to_intersection[start_coord_index] = nullptr;
				continue;
			}
			// We have multiple identical coordinates, create an intersection.
			SIntersection* intersection = NewIntersection(seg_count);
			intersection->m_Pos = (float2)(line_coords[start_coord_index] - world_origin);
			intersection->m_NumSegments = 0;
			for (unsigned int ii = start; ii < i; ++ii)
				coord_to_intersection[order[ii]] = intersection;
		}
	}

	// Create segments
	m_Segments.resize(line_count);
	for (unsigned int line_index = 0; line_index < line_count; ++line_index)
	{
		auto& segment = m_Segments[line_index];
		const unsigned int coord0_index = line_indices ? line_indices[line_index << 1] : (line_index << 1);
		const unsigned int coord1_index = line_indices ? line_indices[(line_index << 1) + 1] : ((line_index << 1) + 1);
		const auto& p0 = line_coords[coord0_index];
		const auto& p1 = line_coords[coord1_index];
		const auto v = p1 - p0;
		segment.m_Length = (float)v.getLength();
		segment.m_Orientation = (float)OrientationAngleFromVector(v);
		segment.m_Center = (float2)((p0 + p1) * 0.5 - world_origin);

		segment.m_Intersections[0] = coord_to_intersection[coord0_index];
		if (segment.m_Intersections[0])
			segment.m_Intersections[0]->m_Segments[segment.m_Intersections[0]->m_NumSegments++] = line_index;

		segment.m_Intersections[1] = coord_to_intersection[coord1_index];
		if (segment.m_Intersections[1])
			segment.m_Intersections[1]->m_Segments[segment.m_Intersections[1]->m_NumSegments++] = line_index;

		ASSERT(!segment.m_Intersections[0] || (float2)(p0 - world_origin) == segment.m_Intersections[0]->m_Pos);
		ASSERT(!segment.m_Intersections[1] || (float2)(p1 - world_origin) == segment.m_Intersections[1]->m_Pos);
	}

	return true;
}

CSegmentGraph::SIntersection* CSegmentGraph::NewIntersection(unsigned int num_segments)
{
	SIntersection* intersection = (SIntersection*)m_IntersectionAllocator.Alloc(sizeof(SIntersection) + ((int)num_segments - 1) * sizeof(unsigned int));
	intersection->m_NumSegments = num_segments;
	memset(intersection->m_Segments, -1, num_segments * sizeof(unsigned int));
	return intersection;
}