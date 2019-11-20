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

#include <pstalgo/analyses/CreateGraph.h>
#include <pstalgo/geometry/RegionPoints.h>
#include <pstalgo/Debug.h>
#include <pstalgo/graph/AxialGraph.h>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/graph/SegmentGraph.h>

bool GeneratePointGroupsFromRegions(
	const unsigned int* points_per_region, unsigned int region_count, 
	const double2* region_points, unsigned int point_count,
	const double2& world_origin,
	float interval,
	std::vector<unsigned int>& ret_point_group_sizes,
	std::vector<float2>& ret_points)
{
	// Points along polygon edges
	std::vector<double2> tmp_edge_points;
	unsigned int total_edge_point_count = 0;
	unsigned int point_index = 0;
	for (unsigned int i = 0; i < region_count; ++i)
	{
		const auto region_point_count = points_per_region[i];
		GeneratePointsAlongRegionEdge(region_points + point_index, region_point_count, interval, tmp_edge_points);
		point_index += region_point_count;
		total_edge_point_count += (unsigned int)tmp_edge_points.size();
		tmp_edge_points.clear();
	}
	if (point_count != point_index)
	{
		LOG_ERROR("Polygon point counts do not add up to total point count (%d vs %d)!", point_index, point_count);
		return false;
	}
	ret_point_group_sizes.reserve(region_count);
	ret_points.reserve(total_edge_point_count);
	point_index = 0;
	for (unsigned int i = 0; i < region_count; ++i)
	{
		const auto region_point_count = points_per_region[i];
		GeneratePointsAlongRegionEdge(region_points + point_index, region_point_count, interval, tmp_edge_points);
		point_index += region_point_count;
		ret_point_group_sizes.push_back((unsigned int)tmp_edge_points.size());
		for (const auto& pt : tmp_edge_points)
			ret_points.push_back((float2)(pt - world_origin));
		tmp_edge_points.clear();
	}
	ASSERT(point_count == point_index);
	return true;
}


///////////////////////////////////////////////////////////////////////////////
// Axial Graph

PSTADllExport HPSTAGraph PSTACreateGraph(const SPSTACreateGraphDesc* desc)
{
	auto graph = new CAxialGraph();

	// Bounding Box
	const auto bb = CRectd::BBFromPoints(desc->m_LineCoords, desc->m_LineCoordCount);

	// Origin in world space for local coordinate system
	const double2 world_origin(bb.CenterX(), bb.CenterY());

	// Lines in local space
	std::vector<LINE> lines;
	lines.resize(desc->m_LineCount);
	if (desc->m_Lines)
	{
		for (unsigned int i = 0; i < desc->m_LineCount; ++i)
		{
			lines[i].p1 = (float2)(desc->m_LineCoords[desc->m_Lines[i * 2]] - world_origin);
			lines[i].p2 = (float2)(desc->m_LineCoords[desc->m_Lines[i * 2 + 1]] - world_origin);
		}
	}
	else
	{
		for (unsigned int i = 0; i < desc->m_LineCount; ++i)
		{
			lines[i].p1 = (float2)(desc->m_LineCoords[i * 2] - world_origin);
			lines[i].p2 = (float2)(desc->m_LineCoords[i * 2 + 1] - world_origin);
		}
	}

	// Unlink coordinates in local space
	std::vector<COORDS> unlinks;
	unlinks.resize(desc->m_UnlinkCount);
	for (unsigned int i = 0; i < desc->m_UnlinkCount; ++i)
		unlinks[i] = (float2)(desc->m_UnlinkCoords[i] - world_origin);

	// Points
	std::vector<COORDS> points;
	std::vector<unsigned int> point_groups;
	if (desc->m_PolygonCount)
	{
		if (!GeneratePointGroupsFromRegions(
			desc->m_PointsPerPolygon, desc->m_PolygonCount,
			desc->m_PointCoords, desc->m_PointCount,
			world_origin,
			desc->m_PolygonPointInterval,
			point_groups,
			points))
		{
			return 0;
		}
	}
	else
	{
		// Regular points
		points.resize(desc->m_PointCount);
		for (unsigned int i = 0; i < desc->m_PointCount; ++i)
			points[i] = (float2)(desc->m_PointCoords[i] - world_origin);
	}

	// Create the graph
	graph->createGraph(
		lines.data(), (int)lines.size(),
		unlinks.empty() ? nullptr : unlinks.data(), (int)unlinks.size(),
		points.empty() ? nullptr : points.data(), (int)points.size());

	// Add point groups if available
	if (!point_groups.empty())
		graph->setPointGroups(std::move(point_groups));

	// Set world origin
	graph->setWorldOrigin(world_origin);

	return graph;
}

PSTADllExport void PSTAFreeGraph(HPSTAGraph handle)
{
	auto* graph = static_cast<CAxialGraph*>(handle);
	delete graph;
}

PSTADllExport bool PSTAGetGraphInfo(HPSTAGraph handle, SPSTAGraphInfo* ret_info)
{
	if (SPSTAGraphInfo::VERSION != ret_info->m_Version)
	{
		LOG_ERROR("Version mismatch");
		return false;
	}

	const auto* graph = static_cast<CAxialGraph*>(handle);

	ret_info->m_LineCount     = graph->getLineCount();
	ret_info->m_CrossingCount = graph->getCrossingCount();
	ret_info->m_PointCount    = graph->getPointCount();
	ret_info->m_PointGroupCount = 0;

	return true;
}

PSTADllExport int PSTAGetGraphLineLengths(HPSTAGraph handle, float* out_lengths, unsigned int count)
{
	const auto* graph = static_cast<CAxialGraph*>(handle);

	if (nullptr == out_lengths)
		return graph->getLineCount();

	if ((unsigned int)graph->getLineCount() != count)
	{
		LOG_ERROR("Number of lines in graph (%d) doesn't match output array size (%d)!", graph->getLineCount(), count);
		return -1;
	}

	for (unsigned int i = 0; i < (unsigned int)graph->getLineCount(); ++i)
		out_lengths[i] = graph->getLine(i).length;

	return count;
}

PSTADllExport int PSTAGetGraphCrossingCoords(HPSTAGraph handle, double2* out_coords, unsigned int count)
{
	const auto* graph = static_cast<CAxialGraph*>(handle);

	if (nullptr == out_coords)
		return graph->getCrossingCount();

	if ((unsigned int)graph->getCrossingCount() != count)
	{
		LOG_ERROR("Number of crossings in graph (%d) doesn't match output array size (%d)!", graph->getCrossingCount(), count);
		return -1;
	}

	for (unsigned int i = 0; i < (unsigned int)graph->getCrossingCount(); ++i)
		out_coords[i] = graph->localToWorld(graph->getCrossing(i).pt);

	return count;
}

///////////////////////////////////////////////////////////////////////////////
// Segment Graph

PSTADllExport HPSTASegmentGraph PSTACreateSegmentGraph(const SPSTACreateSegmentGraphDesc* desc)
{
	auto graph = new CSegmentGraph();

	if (!graph->Create(desc->m_LineCoords, desc->m_LineCoordCount, desc->m_Lines, desc->m_LineCount))
	{
		delete graph;
		return 0;
	}

	return graph;
}

PSTADllExport void PSTAFreeSegmentGraph(HPSTASegmentGraph handle)
{
	auto* graph = static_cast<CSegmentGraph*>(handle);
	delete graph;
}

///////////////////////////////////////////////////////////////////////////////
// Segment Group Graph

#include <pstalgo/graph/SegmentGroupGraph.h>

SPSTACreateSegmentGroupGraphDesc::SPSTACreateSegmentGroupGraphDesc()
	: m_Version(VERSION)
	, m_SegmentGraph(nullptr)
	, m_GroupIndexPerSegment(nullptr)
	, m_SegmentCount(0)
	, m_GroupCount(0)
	, m_ProgressCallback(nullptr)
	, m_ProgressCallbackUser(nullptr)
{}

PSTADllExport HPSTASegmentGroupGraph PSTACreateSegmentGroupGraph(const SPSTACreateSegmentGroupGraphDesc* desc)
{
	auto* segment_graph = static_cast<CSegmentGraph*>(desc->m_SegmentGraph);
	ASSERT(segment_graph);

	if (segment_graph->GetSegmentCount() != desc->m_SegmentCount)
	{
		LOG_ERROR("Length of group index array doesn't match segment count in segment graph");
		return 0;
	}

	auto graph = new CSegmentGroupGraph();

	graph->Create(*segment_graph, desc->m_GroupIndexPerSegment, desc->m_GroupCount);

	return graph;
}

PSTADllExport void PSTAFreeSegmentGroupGraph(HPSTASegmentGroupGraph handle)
{
	auto* graph = static_cast<CSegmentGroupGraph*>(handle);
	delete graph;
}