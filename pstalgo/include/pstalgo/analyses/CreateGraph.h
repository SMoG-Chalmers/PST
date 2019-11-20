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

#include <pstalgo/pstalgo.h>
#include <pstalgo/Vec2.h>


bool GeneratePointGroupsFromRegions(
	const unsigned int* points_per_region, unsigned int region_count,
	const double2* region_points, unsigned int point_count,
	const double2& world_origin,
	float interval,
	std::vector<unsigned int>& ret_point_group_sizes,
	std::vector<float2>& ret_points);


///////////////////////////////////////////////////////////////////////////////
// Axial Graph

typedef void* HPSTAGraph;

struct SPSTACreateGraphDesc
{
	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version = VERSION;

	// Lines
	double2*      m_LineCoords = nullptr;
	unsigned int* m_Lines = nullptr;  // pairs of indices into 'm_LineCoords'
	unsigned int  m_LineCoordCount = 0; // Number of coordinates in 'm_LineCoords'
	unsigned int  m_LineCount = 0;

	// Unlinks (optional)
	double2*     m_UnlinkCoords = nullptr;
	unsigned int m_UnlinkCount = 0;

	// Points (optional)
	double2*     m_PointCoords = nullptr;
	unsigned int m_PointCount = 0;

	// Polygons (optional)
	// If not NULL this means m_PointCoords should be treated as polygon 
	// corners, and the actual points for the graph will be generated at 
	// every 'm_PolygonPointInterval' interval along polygon edges.
	unsigned int* m_PointsPerPolygon = nullptr;  // Polygons will be closed automatically, start/end point should NOT be repeated
	unsigned int  m_PolygonCount = 0;
	float         m_PolygonPointInterval = 0;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;
};

struct SPSTAGraphInfo
{
	SPSTAGraphInfo();

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	unsigned int m_LineCount;
	unsigned int m_CrossingCount;
	unsigned int m_PointCount;
	unsigned int m_PointGroupCount;
};

PSTADllExport HPSTAGraph PSTACreateGraph(const SPSTACreateGraphDesc* desc);

PSTADllExport void PSTAFreeGraph(HPSTAGraph handle);

PSTADllExport bool PSTAGetGraphInfo(HPSTAGraph handle, SPSTAGraphInfo* ret_info);

PSTADllExport int PSTAGetGraphLineLengths(HPSTAGraph handle, float* out_lengths, unsigned int count);

PSTADllExport int PSTAGetGraphCrossingCoords(HPSTAGraph handle, double2* out_coords, unsigned int count);


///////////////////////////////////////////////////////////////////////////////
// Segment Graph

typedef void* HPSTASegmentGraph;

struct SPSTACreateSegmentGraphDesc
{
	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version = VERSION;

	// Lines
	double2*      m_LineCoords = nullptr;
	unsigned int* m_Lines = nullptr;  // pairs of indices into 'm_LineCoords'
	unsigned int  m_LineCoordCount = 0; // Number of coordinates in 'm_LineCoords'
	unsigned int  m_LineCount = 0;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;
};

PSTADllExport HPSTASegmentGraph PSTACreateSegmentGraph(const SPSTACreateSegmentGraphDesc* desc);

PSTADllExport void PSTAFreeSegmentGraph(HPSTASegmentGraph handle);


///////////////////////////////////////////////////////////////////////////////
// Segment Group Graph

typedef void* HPSTASegmentGroupGraph;

struct SPSTACreateSegmentGroupGraphDesc
{
	SPSTACreateSegmentGroupGraphDesc();

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	// Segment Graph
	HPSTASegmentGraph m_SegmentGraph;  // Created with a call to PSTACreateSegmentGraph

	// Grouping
	const unsigned int* m_GroupIndexPerSegment;
	unsigned int m_SegmentCount;  // For verification only
	unsigned int m_GroupCount;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;
};

PSTADllExport HPSTASegmentGroupGraph PSTACreateSegmentGroupGraph(const SPSTACreateSegmentGroupGraphDesc* desc);

PSTADllExport void PSTAFreeSegmentGroupGraph(HPSTASegmentGroupGraph handle);