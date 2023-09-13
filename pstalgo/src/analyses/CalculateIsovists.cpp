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

#include <cmath>
#include <memory>
#include <pstalgo/analyses/CalculateIsovists.h>
#include <pstalgo/Debug.h>
#include <pstalgo/utils/Perf.h>
#include <pstalgo/geometry/Geometry.h>
#include <pstalgo/geometry/IsovistCalculator.h>
#include <pstalgo/geometry/LooseBspTree.h>
#include <pstalgo/geometry/Plane2D.h>
#include <pstalgo/geometry/Polygon.h>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/maths.h>

#include "../ProgressUtil.h"

// NOTE: Objects must be movable!
template <class T>
class ObjectPool
{
public:
	~ObjectPool()
	{
		if (m_OutstandingBorrowCount)
		{
			LOG_ERROR("ObjectPool: Dangling objects when destroyed");
		}
	}

	inline T Borrow() 
	{ 
		++m_OutstandingBorrowCount;
		if (m_FreeObjects.empty())
		{
			return T();
		}
		auto obj = std::move(m_FreeObjects.back());
		m_FreeObjects.pop_back();
		return obj;
	}

	inline void Return(T&& obj)
	{
		m_FreeObjects.push_back(std::forward<T>(obj));
		--m_OutstandingBorrowCount;
	}

private:
	std::vector<T> m_FreeObjects;
	size_t m_OutstandingBorrowCount = 0;
};

void CalculateArcClippingPlanesAndSegments(unsigned int perimeter_resolution, float max_distance, float fov_degrees, float direction_degrees, std::vector<Plane2Df>& ret_planes, std::vector<std::pair<float2, float2>>& ret_segments)
{
	const size_t first_segment_index = ret_segments.size();

	fov_degrees = clamp<float>(fov_degrees, 0, 360);
	const auto segment_count = (uint32_t)ceil((fov_degrees * perimeter_resolution) / 360.0f);

	const float segment_angle = deg2rad(fov_degrees / segment_count);
	const float outer_clipping_distance = max_distance;
	const float inner_clipping_distance = max_distance * cosf(segment_angle * .5f);

	float direction_rad = (fov_degrees == 360) ? -(float)PI + segment_angle : deg2rad(direction_degrees - fov_degrees * .5f);
	auto pt_prev = directionVectorfromAngleRad(direction_rad) * outer_clipping_distance;
	for (uint32_t i = 0; i < segment_count; ++i)
	{
		direction_rad += segment_angle;
		const auto clipping_plane_angle = direction_rad - segment_angle * .5f;
		ret_planes.push_back({ float2(-cosf(clipping_plane_angle), -sinf(clipping_plane_angle)), -inner_clipping_distance });
		const auto pt = directionVectorfromAngleRad(direction_rad) * outer_clipping_distance;
		ret_segments.push_back({ pt_prev, pt });
		pt_prev = pt;
	}
	if (fov_degrees >= 360)
	{
		ret_segments.back().second = ret_segments[first_segment_index].first;
	}
}

class CIsovistContext: public IPSTAlgo
{
public:
	CIsovistContext(const SCreateIsovistContextDesc& desc, CPSTAlgoProgressCallback& progress);

	void CalculateIsovist(SCalculateIsovistDesc& desc, CPSTAlgoProgressCallback& progress);


private:
	inline float2 WorldToLocal(const double2& world_coords) const 
	{
		return (float2)(world_coords - m_WorldOrigin);
	}

	inline double2 LocalToWorld(const float2& local_coords) const
	{
		return (double2)local_coords + m_WorldOrigin;
	}

	static const uint32_t MAX_TREE_DEPTH = 10;
	static const uint32_t MAX_POLYGONS_PER_LEAF = 64;

	typedef TRect<float> bb_t;

	struct SPolygon
	{
		bb_t BB;
		uint32_t FirstPointIndex;
		uint32_t PointCount;
	};
	typedef std::vector<SPolygon> polygon_vector_t;

	polygon_vector_t m_Polygons;
	std::vector<float2> m_PolygonPoints;

	typedef psta::LooseBspTree<SPolygon, polygon_vector_t::iterator> tree_t;
	tree_t m_Tree;

	double2 m_WorldOrigin;

	std::vector<float2> m_Attractions;
	std::vector<Plane2Df> m_ClippingPlanes;
	std::vector<std::pair<float2, float2>> m_Edges;
	std::vector<uint32_t> m_EdgeCountPerObstacle;
	CBitVector m_ObstacleVisibilityMask;

	ObjectPool<std::vector<float2>> m_LocalIsovistPool;
	ObjectPool<std::vector<double2>> m_WorldIsovistPool;

	CIsovistCalculator m_IsovistCalculator;

	class Result : IPSTAlgo 
	{
	public:
		Result(CIsovistContext& context, std::vector<double2>&& isovist)
			: m_Context(context)
			, m_Isovist(std::forward< std::vector<double2>>(isovist))
		{
		}

		~Result()
		{
			m_Context.m_WorldIsovistPool.Return(std::move(m_Isovist));
		}

	private:
		CIsovistContext& m_Context;
		std::vector<double2> m_Isovist;
	};

	friend class Result;
};

CIsovistContext::CIsovistContext(const SCreateIsovistContextDesc& desc, CPSTAlgoProgressCallback& progress)
{
	// Count total polygon points
	uint32_t total_polygon_point_count = 0;
	for (uint32_t polygon_index = 0; polygon_index < desc.m_PolygonCount; ++polygon_index)
	{
		total_polygon_point_count += desc.m_PointCountPerPolygon[polygon_index];
	}

	// Decide origin for local space
	m_WorldOrigin = double2(0, 0);
	if (total_polygon_point_count || desc.m_AttractionCount)
	{
		CRectd aabb;
		if (desc.m_AttractionCount)
		{
			aabb = CRectd::BBFromPoints((const double2*)desc.m_AttractionCoords, desc.m_AttractionCount);
			if (total_polygon_point_count)
			{
				aabb = CRectd::Union(aabb, CRectd::BBFromPoints((const double2*)desc.m_PolygonPoints, total_polygon_point_count));
			}
		}
		else
		{
			aabb = CRectd::BBFromPoints((const double2*)desc.m_PolygonPoints, total_polygon_point_count);
		}
		m_WorldOrigin = double2(trunc(aabb.CenterX()), trunc(aabb.CenterY()));
	}

	if (total_polygon_point_count)
	{
		// Calculate polygon bounding boxes
		m_Polygons.resize(desc.m_PolygonCount);
		{
			const double2* const points_ptr = (const double2*)desc.m_PolygonPoints;
			uint32_t point_index = 0; 
			for (uint32_t polygon_index = 0; polygon_index < desc.m_PolygonCount; ++polygon_index)
			{
				const auto point_count = desc.m_PointCountPerPolygon[polygon_index];
				const auto bb = CRectd::BBFromPoints(points_ptr + point_index, point_count);
				auto& polygon = m_Polygons[polygon_index];
				polygon.BB = (TRect<float>)(bb - m_WorldOrigin);
				polygon.FirstPointIndex = point_index;
				polygon.PointCount = point_count;
				point_index += point_count;
			}
		}

		m_Tree = tree_t::FromObjects(m_Polygons.begin(), m_Polygons.end(), MAX_TREE_DEPTH, MAX_POLYGONS_PER_LEAF, [](const SPolygon& polygon) -> const bb_t& { return polygon.BB; });

		m_PolygonPoints.reserve(total_polygon_point_count);
		{
			const double2* const points_ptr = (const double2*)desc.m_PolygonPoints;
			for (auto& polygon : m_Polygons)
			{
				const auto original_first_point = polygon.FirstPointIndex;
				polygon.FirstPointIndex = (uint32_t)m_PolygonPoints.size();
				for (uint32_t point_index = original_first_point; point_index < original_first_point + polygon.PointCount; ++point_index)
				{
					m_PolygonPoints.push_back(WorldToLocal(points_ptr[point_index]));
				}
			}
		}
	}
	else
	{
	}

	// Attractions
	m_Attractions.resize(desc.m_AttractionCount);
	for (uint32_t i = 0; i < desc.m_AttractionCount; ++i)
	{
		m_Attractions[i] = WorldToLocal(((const double2*)desc.m_AttractionCoords)[i]);
	}

	progress.ReportProgress(1);
}

// Calculates the radius needed for a segmented circle to have same area as circle with radius 1
float CalcRadForSegmentedCircle(int seg_count) {
	const float half_angle = (float)PI / seg_count;
	return sqrt((float)PI / ((float)seg_count * sin(half_angle) * cos(half_angle)));
}

void CIsovistContext::CalculateIsovist(SCalculateIsovistDesc& desc, CPSTAlgoProgressCallback& progress)
{
	desc.m_OutPointCount = 0;
	desc.m_OutPoints = nullptr;
	desc.m_OutIsovistHandle = nullptr;

	progress.ReportProgress(1);

	const float perimeter_segment_angle = desc.m_PerimeterSegmentCount ? (float)PI * 2.f / desc.m_PerimeterSegmentCount : (float)PI * 2.f;
	const float outer_clipping_radius = (float)desc.m_MaxViewDistance * CalcRadForSegmentedCircle(desc.m_PerimeterSegmentCount);
	const float inner_clipping_radius = outer_clipping_radius * cosf(perimeter_segment_angle * .5f);

	const float2 origin_local = WorldToLocal(double2(desc.m_OriginX, desc.m_OriginY));

	m_EdgeCountPerObstacle.clear();

	// Clipping planes and edges
	m_ClippingPlanes.clear();
	m_Edges.clear();
	CalculateArcClippingPlanesAndSegments(desc.m_PerimeterSegmentCount, outer_clipping_radius, (float)desc.m_FieldOfViewDegrees, (float)desc.m_DirectionDegrees, m_ClippingPlanes, m_Edges);
	m_EdgeCountPerObstacle.push_back((uint32_t)m_Edges.size());  // Perimeter is first obstacle

	const auto view_direction_vec = directionVectorfromAngleRad(deg2rad((float)desc.m_DirectionDegrees));
	const auto view_dir_plane = Plane2Df({ view_direction_vec, 0 });

	const auto vec_fov_min = directionVectorfromAngleRad(deg2rad((float)desc.m_DirectionDegrees - .5f * (float)desc.m_FieldOfViewDegrees + 90));
	const auto vec_fov_max = directionVectorfromAngleRad(deg2rad((float)desc.m_DirectionDegrees + .5f * (float)desc.m_FieldOfViewDegrees - 90));
	const Plane2Df plane_fov_min = { vec_fov_min, dot(origin_local, vec_fov_min) };
	const Plane2Df plane_fov_max = { vec_fov_max, dot(origin_local, vec_fov_max) };

	// Add edges from polygons
	{
		bool done = false;  // TODO: Do this with cancellation token instead
		m_Tree.VisitItems(
			[&](const bb_t& bb) -> bool
			{
				return !done && bb.OverlapsCircle(origin_local, outer_clipping_radius);
			},
			[&](const SPolygon& polygon)
			{
				if (done || !polygon.BB.OverlapsCircle(origin_local, outer_clipping_radius))
				{
					return;
				}

				const auto* points = m_PolygonPoints.data() + polygon.FirstPointIndex;

				if (polygon.BB.Contains(origin_local.x, origin_local.y) && TestPointInRing(origin_local, psta::make_span(points, polygon.PointCount)))
				{
					// Origin is inside a polygon
					done = true;
					return;
				}

				// Check if bb is outside edges of field of view
				if (desc.m_FieldOfViewDegrees < 360)
				{
					const bool behind_fov_edge_min = plane_fov_min.IsBehind(polygon.BB);
					const bool behind_fov_edge_max = plane_fov_max.IsBehind(polygon.BB);
					const bool outside = (desc.m_FieldOfViewDegrees <= 180) ? (behind_fov_edge_min | behind_fov_edge_max) : (behind_fov_edge_min & behind_fov_edge_max);
					if (outside)
					{
						return;
					}
				}

				const bool needs_clipping = !polygon.BB.FullyInsideCircle(origin_local, inner_clipping_radius);

				const auto prev_edge_count = m_Edges.size();

				auto pt_prev = points[polygon.PointCount - 1] - origin_local;
				for (uint32_t point_index = 0; point_index < polygon.PointCount; ++point_index)
				{
					const auto pt_next = points[point_index] - origin_local;
					auto edge = std::make_pair(pt_prev, pt_next);
					pt_prev = pt_next;

					if (needs_clipping)
					{
						size_t plane_index;
						for (plane_index = 0; plane_index < m_ClippingPlanes.size(); ++plane_index)
						{
							if (!ClipLineSegment(edge.first, edge.second, m_ClippingPlanes[plane_index]))
								break;
						};
						if (plane_index == m_ClippingPlanes.size())
						{
							m_Edges.push_back(edge);
						}
					}
					else
					{
						m_Edges.push_back(edge);
					}
				}

				m_EdgeCountPerObstacle.push_back((uint32_t)(m_Edges.size() - prev_edge_count));
			});

		if (done)
		{
			return;
		}
	}

	size_t visible_obstacle_count = 0;
	auto local_points = m_LocalIsovistPool.Borrow();
	local_points.clear();
	m_IsovistCalculator.CalculateIsovist(float2(0, 0), (float)desc.m_FieldOfViewDegrees, (float)desc.m_DirectionDegrees, m_Edges.data(), m_Edges.size(), m_EdgeCountPerObstacle.data(), m_EdgeCountPerObstacle.size(), local_points, visible_obstacle_count, m_ObstacleVisibilityMask);

	// Don't include perimeter in object count
	if (m_ObstacleVisibilityMask.get(0))
	{
		m_ObstacleVisibilityMask.clear(0);
		--visible_obstacle_count;
	}

	// Calculate area
	double area = 0;
	{
		auto prev_v = local_points.back();
		for (size_t i = 0; i < local_points.size(); ++i)
		{
			const auto base_v = local_points[i];
			const auto base_len = base_v.getLength();
			if (base_len > 0.f) {
				const auto base_len_inv = 1.f / base_len;
				const float2 base_n(-base_v.y * base_len_inv, base_v.x * base_len_inv);
				area += dot(base_n, prev_v) * base_len;  // We divide by two after loop instedad of here!
			}
			prev_v = base_v;
		}
		area = std::abs(area * .5);  // Don't forget to divide by two here!
	}

	auto world_isovist = m_WorldIsovistPool.Borrow();
	world_isovist.clear();
	world_isovist.reserve(local_points.size());

	// Translate isovis coordinates to local space (from isovist object space)
	for (auto& pt : local_points)
	{
		pt += origin_local;
	}

	// Count attractions inside isovist
	uint32_t attraction_count = 0;
	for (const auto& pt : m_Attractions)
	{
		attraction_count += (uint32_t)TestPointInRing(pt, psta::make_span(local_points));
	}
	desc.m_OutAttractionCount = attraction_count;

	// Translate isovist to world coordinates
	for (auto it = local_points.crbegin(); local_points.crend() != it; ++it)
	{
		world_isovist.push_back(LocalToWorld(*it));
	}

	m_LocalIsovistPool.Return(std::move(local_points));

	desc.m_OutPointCount = (uint32_t)world_isovist.size();
	desc.m_OutPoints = &world_isovist.data()->x;
	desc.m_OutIsovistHandle = new Result(*this, std::move(world_isovist));
	desc.m_OutArea = (float)area;
	desc.m_OutVisibleObstacleCount = visible_obstacle_count;

	progress.ReportProgress(1);
}

#include <pstalgo/geometry/SignedDistanceField.h>

PSTADllExport psta_handle_t PSTACreateIsovistContext(const SCreateIsovistContextDesc* desc)
{
	/*
	float sdf[] = {
		3, 2, 1, 2,
		2, 1, 0, 1,
		1, 0, 1, 2,
		2, 1, 2, 3,
	};
	auto polys = psta::PolygonsFromSdfGrid(sdf, 0.5f, uint2(4, 4));
	*/

	/*
	psta::Arr2d<float> sdf(100, 100);
	sdf.Clear(std::numeric_limits<float>::max());
	psta::AddLineSegmentToSdf(sdf, float2(20, 20), float2(40, 30), 10);
	auto polys = psta::PolygonsFromSdfGrid(sdf, 8);
	*/

	try {
		VerifyStructVersion(*desc);

		CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

		//psta::CPerfTimer timer;
		//timer.Start();

		auto isovity_context = std::make_unique<CIsovistContext>(*desc, progress);

		//const auto tick_count = timer.ReadAndRestart();
		//LOG_INFO("Isovist context created in %.3f msec", psta::CPerfTimer::SecondsFromTicks(tick_count) * 1000.0f);

		return isovity_context.release();
	}
	catch (const std::exception& e) {
		LOG_ERROR(e.what());
	}
	catch (...) {
		LOG_ERROR("Unknown exception");
	}
	return nullptr;
}

PSTADllExport void PSTACalculateIsovist(SCalculateIsovistDesc* desc)
{
	try {
		VerifyStructVersion(*desc);

		auto& context = *(CIsovistContext*)desc->m_IsovistContext;

		CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

		//psta::CPerfTimer timer;
		//timer.Start();

		context.CalculateIsovist(*desc, progress);

		//const auto tick_count = timer.ReadAndRestart();
		//LOG_INFO("Isovist calculated in %.3f msec", psta::CPerfTimer::SecondsFromTicks(tick_count) * 1000.0f);
	}
	catch (const std::exception& e) {
		LOG_ERROR(e.what());
	}
	catch (...) {
		LOG_ERROR("Unknown exception");
	}
}

/*
// !!! DEPRECATED !!!
PSTADllExport IPSTAlgo* PSTACalculateIsovists(const SCalculateIsovistsDesc* desc, SCalculateIsovistsRes* res)
{
	try {
		VerifyStructVersion(*desc);
		VerifyStructVersion(*res);

		auto algo = std::make_unique<CCalculateIsovists>();

		CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

		return algo->Run(*desc, *res, progress) ? algo.release() : nullptr;
	}
	catch (const std::exception& e) {
		LOG_ERROR(e.what());
	}
	catch (...) {
		LOG_ERROR("Unknown exception");
	}
	return nullptr;
}
*/