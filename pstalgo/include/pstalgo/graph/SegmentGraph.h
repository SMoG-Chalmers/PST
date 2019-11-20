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

#pragma once

#include <vector>
#include <pstalgo/utils/SimpleAlignedAllocator.h>
#include <pstalgo/Vec2.h>

class CSegmentGraph
{
public:
	// Represents an intersection of network segments - the "Edges" of the graph
	struct SIntersection
	{
		float2       m_Pos;
		unsigned int m_NumSegments;
		unsigned int m_Segments[1];  // Size will vary 0-N depending on allocation size of each SIntersection object
	};

	// Represents a network segment - the "Nodes" of the graph
	struct SSegment
	{
		float2         m_Center;
		float          m_Orientation;
		float          m_Length;
		SIntersection* m_Intersections[2];
		char           m_Padding[8]; // TODO: Only if 32-bit!
	};

	CSegmentGraph();
	~CSegmentGraph();

	bool Create(const double2* line_coords, unsigned int line_coord_count, unsigned int* line_indices, unsigned int line_count);

	unsigned int    GetSegmentCount() const { return (unsigned int)m_Segments.size(); }
	SSegment&       GetSegment(unsigned int index) { return m_Segments[index]; }
	const SSegment& GetSegment(unsigned int index) const { return m_Segments[index]; }

private:
	SIntersection* NewIntersection(unsigned int num_segments);

	std::vector<SSegment> m_Segments;
	CSimpleAlignedAllocator m_IntersectionAllocator;
	double2 m_WorldOrigin;
};