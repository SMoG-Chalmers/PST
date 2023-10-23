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
#include <pstalgo/geometry/AABSPTree.h>
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

uint32_t SCreateIsovistContextDesc::SPolygons::TotalPolygonCount() const
{
	uint32_t polygon_count = 0;
	for (uint32_t group_index = 0; group_index < this->GroupCount; ++group_index)
	{
		polygon_count += this->PolygonCountPerGroup[group_index];
	}
	return polygon_count;
}

uint32_t SCreateIsovistContextDesc::SPolygons::TotalCoordCount() const
{
	uint32_t coord_count = 0;
	const auto polygon_count = this->TotalPolygonCount();
	for (uint32_t polygon_index = 0; polygon_index < polygon_count; ++polygon_index)
	{
		coord_count += this->PointCountPerPolygon[polygon_index];
	}
	return coord_count;
}

uint32_t SCreateIsovistContextDesc::SPoints::TotalPointCount() const
{
	uint32_t count = 0;
	for (uint32_t group_index = 0; group_index < this->GroupCount; ++group_index)
	{
		count += this->PointCountPerGroup[group_index];
	}
	return count;
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
		uint32_t Group;
		uint32_t IndexInGroup;
	};
	typedef std::vector<SPolygon> polygon_vector_t;

	struct SPolygonSet
	{
		typedef psta::LooseBspTree<SPolygon, polygon_vector_t::iterator> tree_t;
		uint32_t GroupCount;
		polygon_vector_t Polygons;
		std::vector<float2> PolygonPoints;
		tree_t Tree;
	};

	struct SPointSet
	{
		struct SPoint
		{
			float2 Coords;
			uint32_t Group;
			uint32_t IndexInGroup;
		};
		typedef std::vector<SPoint> point_vector_t;
		typedef psta::LooseBspTree<SPoint, point_vector_t::iterator> tree_t;
		uint32_t GroupCount;
		point_vector_t Points;
		tree_t Tree;
	};

	static SPolygonSet CreatePolygonSet(const SCreateIsovistContextDesc::SPolygons& polygons, const double2& origin);

	SPolygonSet m_Obstacles;
	SPolygonSet m_AttractionPolygons;
	SPointSet m_AttractionPoints;

	double2 m_WorldOrigin;

	std::vector<Plane2Df> m_ClippingPlanes;
	std::vector<std::pair<float2, float2>> m_Edges;
	std::vector<uint32_t> m_PolygonIndexPerObstacle;;
	std::vector<uint32_t> m_EdgeCountPerObstacle;
	bit_vector<size_t> m_ObstacleVisibilityMask;

	ObjectPool<std::vector<float2>> m_LocalIsovistPool;
	ObjectPool<std::vector<double2>> m_WorldIsovistPool;

	CIsovistCalculator m_IsovistCalculator;
	
	std::vector<uint32_t> m_TempIndexArray;

	struct SAttrPointCalc
	{
		float2 ObjCoords;
		float RelDiamondAngle;
		uint32_t Group : 8;
		uint32_t IndexInGroup : 24;
	};
	std::vector<SAttrPointCalc> m_TempAttrPointCalc;

	struct SAttrEdgeCalc
	{
		float2 P0;
		float2 P1;
		float RelDiamondAngle0;
		float RelDiamondAngle1;
		uint32_t Group;
		uint32_t IndexInGroup;
	};
	std::vector<SAttrEdgeCalc> m_TempAttrEdgeQueue;
	std::vector<SAttrEdgeCalc> m_TempAttrEdgeActive;

	struct Result
	{
		std::vector<double2> Isovist;
		std::vector<uint32_t> IndexArray;
	};

	ObjectPool<Result> m_ResultPool;

	class ResultRef : IPSTAlgo
	{
	public:
		ResultRef(CIsovistContext& context, CIsovistContext::Result&& result)
			: m_Context(context)
			, m_Result(std::forward<CIsovistContext::Result>(result))
		{}

		~ResultRef()
		{
			m_Context.m_ResultPool.Return(std::move(m_Result));
		}

		Result& Result() { return m_Result; }

	private:
		CIsovistContext& m_Context;
		CIsovistContext::Result m_Result;
	};

	friend class ResultRef;
};

CIsovistContext::SPolygonSet CIsovistContext::CreatePolygonSet(const SCreateIsovistContextDesc::SPolygons& polygons, const double2& origin)
{
	SPolygonSet polygonSet;
	
	polygonSet.GroupCount = polygons.GroupCount;

	polygonSet.Polygons.resize(polygons.TotalPolygonCount());
	{
		const double2* const points_ptr = (const double2*)polygons.Coords;
		uint32_t polygon_index = 0;
		uint32_t point_index = 0;
		for (uint32_t group_index = 0; group_index < polygons.GroupCount; ++group_index)
		{
			for (size_t i = 0; i < polygons.PolygonCountPerGroup[group_index]; ++i, ++polygon_index)
			{
				const auto point_count = polygons.PointCountPerPolygon[polygon_index];
				const auto bb = CRectd::BBFromPoints(points_ptr + point_index, point_count);
				auto& polygon = polygonSet.Polygons[polygon_index];
				polygon.BB = (TRect<float>)(bb - origin);
				polygon.FirstPointIndex = point_index;
				polygon.PointCount = point_count;
				polygon.Group = group_index;
				polygon.IndexInGroup = (uint32_t)i;
				point_index += point_count;
			}
		}
	}

	polygonSet.Tree = SPolygonSet::tree_t::FromObjects(polygonSet.Polygons.begin(), polygonSet.Polygons.end(), MAX_TREE_DEPTH, MAX_POLYGONS_PER_LEAF, [](const SPolygon& polygon) -> const bb_t& { return polygon.BB; });

	polygonSet.PolygonPoints.reserve(polygons.TotalCoordCount());
	{
		const double2* const points_ptr = (const double2*)polygons.Coords;
		for (auto& polygon : polygonSet.Polygons)
		{
			const auto original_first_point = polygon.FirstPointIndex;
			polygon.FirstPointIndex = (uint32_t)polygonSet.PolygonPoints.size();
			for (uint32_t point_index = original_first_point; point_index < original_first_point + polygon.PointCount; ++point_index)
			{
				polygonSet.PolygonPoints.push_back((float2)(points_ptr[point_index] - origin));
			}
		}
	}

	return polygonSet;
}

CIsovistContext::CIsovistContext(const SCreateIsovistContextDesc& desc, CPSTAlgoProgressCallback& progress)
{
	// Decide origin for local space
	{
		CRectd aabb_world = CRectd::INVALID;
		if (const auto coord_count = desc.ObstaclePolygons.TotalCoordCount())
		{
			const auto bb = CRectd::BBFromPoints((const double2*)desc.ObstaclePolygons.Coords, coord_count);
			aabb_world = aabb_world.Valid() ? CRectd::Union(aabb_world, bb) : bb;
		}
		if (const auto coord_count = desc.AttractionPoints.TotalPointCount())
		{
			const auto bb = CRectd::BBFromPoints((const double2*)desc.AttractionPoints.Coords, coord_count);
			aabb_world = aabb_world.Valid() ? CRectd::Union(aabb_world, bb) : bb;
		}
		if (const auto coord_count = desc.AttractionPolygons.TotalCoordCount())
		{
			const auto bb = CRectd::BBFromPoints((const double2*)desc.AttractionPolygons.Coords, coord_count);
			aabb_world = aabb_world.Valid() ? CRectd::Union(aabb_world, bb) : bb;
		}
		m_WorldOrigin = aabb_world.Valid() ? double2(trunc(aabb_world.CenterX()), trunc(aabb_world.CenterY())) : double2(0, 0);
	}

	// Obstacles
	m_Obstacles = CreatePolygonSet(desc.ObstaclePolygons, m_WorldOrigin);

	// Attraction Points
	m_AttractionPoints.GroupCount = desc.AttractionPoints.GroupCount;
	m_AttractionPoints.Points.resize(desc.AttractionPoints.TotalPointCount());
	{
		size_t point_index = 0;
		for (uint32_t group_index = 0; group_index < desc.AttractionPoints.GroupCount; ++group_index)
		{
			for (size_t i = 0; i < desc.AttractionPoints.PointCountPerGroup[group_index]; ++i, ++point_index)
			{
				auto& point = m_AttractionPoints.Points[point_index];
				point.Coords = WorldToLocal(((const double2*)desc.AttractionPoints.Coords)[point_index]);
				point.Group = group_index;
				point.IndexInGroup = (uint32_t)i;
			}
		}
		ASSERT(m_AttractionPoints.Points.size() == point_index);

		m_AttractionPoints.Tree = SPointSet::tree_t::FromObjects(
			m_AttractionPoints.Points.begin(), m_AttractionPoints.Points.end(), 
			MAX_TREE_DEPTH, MAX_POLYGONS_PER_LEAF, 
			[](const SPointSet::SPoint& point) -> const bb_t
			{
				return bb_t(point.Coords, point.Coords);
			});
	}

	// Attraction Polygons
	m_AttractionPolygons = CreatePolygonSet(desc.AttractionPolygons, m_WorldOrigin);

	progress.ReportProgress(1);
}

// Calculates the radius needed for a segmented circle to have same area as circle with radius 1
float CalcRadForSegmentedCircle(int seg_count) {
	const float half_angle = (float)PI / seg_count;
	return sqrt((float)PI / ((float)seg_count * sin(half_angle) * cos(half_angle)));
}

template <class T>
static size_t CountPointsInIsovist(const TVec2<T>& origin, psta::span<TVec2<T>> perimeter, psta::span<TVec2<T>> points)
{
	if (!TestPointInRing(point, perimeter.data(), perimeter_size.size()))
	{
		return false;
	}

	for (const auto& hole : holes)
	{
		if (TestPointInRing(point, hole.data(), hole.size()))
		{
			return false;
		}
	}

	return true;
}

// TODO: Move
template <class T>
size_t remove_duplicates(psta::span<T> items)
{
	std::sort(items.data(), items.data() + items.size());
	size_t unique_count = std::min((size_t)1, items.size());
	for (size_t i = 1; i < items.size(); ++i)
	{
		if (items[i] != items[unique_count - 1])
		{
			items[unique_count++] = items[i];
		}
	}
	return unique_count;
}

void CIsovistContext::CalculateIsovist(SCalculateIsovistDesc& desc, CPSTAlgoProgressCallback& progress)
{
	desc.m_OutPointCount = 0;
	desc.m_OutPoints = nullptr;
	desc.m_OutIsovistHandle = nullptr;

	progress.ReportProgress(1);

	const float direction_degrees = (desc.m_FieldOfViewDegrees < 360) ? desc.m_DirectionDegrees : 0;

	const float perimeter_segment_angle = desc.m_PerimeterSegmentCount ? (float)PI * 2.f / desc.m_PerimeterSegmentCount : (float)PI * 2.f;
	const float outer_clipping_radius = (float)desc.m_MaxViewDistance * CalcRadForSegmentedCircle(desc.m_PerimeterSegmentCount);
	const float inner_clipping_radius = outer_clipping_radius * cosf(perimeter_segment_angle * .5f);

	const auto outer_clipping_radius_sqrd = outer_clipping_radius * outer_clipping_radius;

	const float2 origin_local = WorldToLocal(double2(desc.m_OriginX, desc.m_OriginY));

	m_PolygonIndexPerObstacle.clear();
	m_EdgeCountPerObstacle.clear();

	// Clipping planes and edges
	m_ClippingPlanes.clear();
	m_Edges.clear();
	CalculateArcClippingPlanesAndSegments(desc.m_PerimeterSegmentCount, outer_clipping_radius, (float)desc.m_FieldOfViewDegrees, direction_degrees, m_ClippingPlanes, m_Edges);
	
	// Perimeter is first obstacle
	m_PolygonIndexPerObstacle.push_back(-1);
	m_EdgeCountPerObstacle.push_back((uint32_t)m_Edges.size());  

	const auto view_direction_vec = directionVectorfromAngleRad(deg2rad(direction_degrees));
	const auto view_dir_plane = Plane2Df({ view_direction_vec, 0 });

	// Direction of vectors along edges of field of view.
	const auto tangent_fov_min = (desc.m_FieldOfViewDegrees < 360) ? directionVectorfromAngleRad(deg2rad(direction_degrees - .5f * (float)desc.m_FieldOfViewDegrees)) : float2(-1, 0);
	const auto tangent_fov_max = (desc.m_FieldOfViewDegrees < 360) ? directionVectorfromAngleRad(deg2rad(direction_degrees + .5f * (float)desc.m_FieldOfViewDegrees)) : float2(-1, 0);
	
	// Normals of edges of field of view, pointing inwards into view cone
	const float2 normal_fov_min(-tangent_fov_min.y, tangent_fov_min.x);
	const float2 normal_fov_max(tangent_fov_max.y, -tangent_fov_max.x);

	const Plane2Df plane_fov_min = { normal_fov_min, dot(origin_local, normal_fov_min) };
	const Plane2Df plane_fov_max = { normal_fov_max, dot(origin_local, normal_fov_max) };

	const float max_view_dist_sqrd = desc.m_MaxViewDistance * desc.m_MaxViewDistance;
	const auto fov_diamond_angle_0 = DiamondAngleFromVector(tangent_fov_min);
	const auto fov_diamond_angle_1 = DiamondAngleFromVector(tangent_fov_max);
	const auto fov_diamond_angle_span = ((fov_diamond_angle_0 < fov_diamond_angle_1) ? 0 : MAX_DIAMOND_ANGLE) + fov_diamond_angle_1 - fov_diamond_angle_0;

	// Add edges from polygons
	{
		m_Obstacles.Tree.VisitItems(
			[&](const bb_t& bb) -> bool
			{
				return bb.OverlapsCircle(origin_local, outer_clipping_radius);
			},
			[&](const SPolygon& polygon)
			{
				if (!polygon.BB.OverlapsCircle(origin_local, outer_clipping_radius))
				{
					return;
				}

				const auto* points = m_Obstacles.PolygonPoints.data() + polygon.FirstPointIndex;

				if (polygon.BB.Contains(origin_local.x, origin_local.y) && TestPointInRing(origin_local, psta::make_span(points, polygon.PointCount)))
				{
					// Origin is inside a polygon
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
					if (crp(pt_prev, pt_next) >= 0 && TestLineSegmentAndCircleOverlap(pt_prev, pt_next, outer_clipping_radius, outer_clipping_radius_sqrd))
					{
						auto edge = std::make_pair(pt_prev, pt_next);
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
					pt_prev = pt_next;
				}

				m_PolygonIndexPerObstacle.push_back((uint32_t)(&polygon - m_Obstacles.Polygons.data()));
				m_EdgeCountPerObstacle.push_back((uint32_t)(m_Edges.size() - prev_edge_count));
			});
	}

	auto isovist_points = m_LocalIsovistPool.Borrow();
	isovist_points.clear();
	m_IsovistCalculator.CalculateIsovist(float2(0, 0), (float)desc.m_FieldOfViewDegrees, direction_degrees, m_Edges.data(), m_Edges.size(), m_EdgeCountPerObstacle.data(), m_EdgeCountPerObstacle.size(), isovist_points, m_ObstacleVisibilityMask);

	auto resultRef = std::make_unique<ResultRef>(*this, m_ResultPool.Borrow());
	auto& result = resultRef->Result();

	result.Isovist.clear();
	result.Isovist.reserve(isovist_points.size());

	// Calculate area
	double area = 0;
	{
		auto prev_v = isovist_points.back();
		for (size_t i = 0; i < isovist_points.size(); ++i)
		{
			const auto base_v = isovist_points[i];
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

	m_TempIndexArray.clear();
	const auto total_visibility_group_count = m_Obstacles.GroupCount + m_AttractionPoints.GroupCount + m_AttractionPolygons.GroupCount;
	m_TempIndexArray.resize(total_visibility_group_count);
	{
		uint32_t base_visible_group_index = 0;
		auto& add_visible_object = [&](uint32_t group_index, uint32_t index_in_group)
		{
			++m_TempIndexArray[base_visible_group_index + group_index];
			m_TempIndexArray.push_back(((base_visible_group_index + group_index) << 24) | (index_in_group & 0x00FFFFFF));
		};

		const auto& isovist_obj_points = isovist_points;  // Isovist points relative to view origin

		// Calculate isovist bounding box relative to view origin
		const auto isovist_obj_bb = CRectf::BBFromPoints(isovist_obj_points.data(), (uint32_t)isovist_obj_points.size());

		// Calculate isovist bounding box in local space
		const auto isovist_local_bb = isovist_obj_bb.Offsetted(origin_local.x, origin_local.y);

		// Obstacles (polygons)
		{
			const size_t prev_temp_index_array_size = m_TempIndexArray.size();

			m_ObstacleVisibilityMask.forEachSetBit([&](size_t index)
			{
				if (0 == index)  // Don't include perimeter in obstacle count
				{
					return;
				}
				auto& poly = this->m_Obstacles.Polygons[m_PolygonIndexPerObstacle[index]];
				add_visible_object(poly.Group, poly.IndexInGroup);
			});

			if (m_Obstacles.GroupCount > 1)
			{
				std::sort(m_TempIndexArray.data() + prev_temp_index_array_size, m_TempIndexArray.data() + m_TempIndexArray.size());
			}

			base_visible_group_index += m_Obstacles.GroupCount;
		}

		// Attraction points
		if (m_AttractionPoints.GroupCount)
		{
			const size_t prev_temp_index_array_size = m_TempIndexArray.size();

			// Find potential points
			m_TempAttrPointCalc.clear();
			m_AttractionPoints.Tree.ForEachRangeInBB(isovist_local_bb, [&](auto beg, auto end)
			{
				for (auto it = beg; it != end; ++it)
				{
					auto& pt = *it;
					const auto pos_obj = pt.Coords - origin_local;
					// Beyond max view distance?
					const auto dist_sqrd = pos_obj.getLengthSqr();
					if (dist_sqrd > max_view_dist_sqrd)
					{
						continue;
					}
					// Outside FOV cone?
					const auto diamond_angle = DiamondAngleFromVector(pos_obj);
					const auto rel_diamond_angle = (diamond_angle < fov_diamond_angle_0 ? MAX_DIAMOND_ANGLE : 0.0f) + diamond_angle - fov_diamond_angle_0;
					if (rel_diamond_angle > fov_diamond_angle_span)
						continue;
					// Add point
					SAttrPointCalc ap;
					ap.RelDiamondAngle = rel_diamond_angle;
					ap.ObjCoords = pos_obj;
					ap.Group = pt.Group;
					ap.IndexInGroup = pt.IndexInGroup;
					m_TempAttrPointCalc.push_back(ap);
				}
			});

			if (!m_TempAttrPointCalc.empty())
			{
				// Sort points by direction
				std::sort(m_TempAttrPointCalc.begin(), m_TempAttrPointCalc.end(), [](const auto& a, const auto& b) { return a.RelDiamondAngle < b.RelDiamondAngle; });

				float2 prev_isovist_pt;
				size_t next_isovist_index;
				if (desc.m_FieldOfViewDegrees < 360)
				{
					ASSERT(isovist_obj_points[0] == float2(0, 0));
					prev_isovist_pt = isovist_obj_points[1];
					next_isovist_index = 2;
				}
				else
				{
					prev_isovist_pt = isovist_obj_points.front();
					next_isovist_index = 1;
				}

				size_t attr_point_index = 0;
				float prev_rel_diamond_angle = 0;
				const size_t last_isovist_index = (desc.m_FieldOfViewDegrees < 360) ? isovist_obj_points.size() - 1 : isovist_obj_points.size();
				for (; next_isovist_index <= last_isovist_index; ++next_isovist_index)
				{
					const auto next_isovist_pt = isovist_obj_points[next_isovist_index < isovist_obj_points.size() ? next_isovist_index : 0];
					const auto diamond_angle = DiamondAngleFromVector(next_isovist_pt);
					auto rel_diamond_angle = (diamond_angle < fov_diamond_angle_0 ? MAX_DIAMOND_ANGLE : 0.0f) + diamond_angle - fov_diamond_angle_0;
					if (next_isovist_index == isovist_obj_points.size() && rel_diamond_angle < MAX_DIAMOND_ANGLE * .5f)
					{
						// Wrapped around at end of 360 isovist
						rel_diamond_angle += MAX_DIAMOND_ANGLE;
					}
					for (;; ++attr_point_index)
					{
						if (attr_point_index >= m_TempAttrPointCalc.size())
						{
							goto done;
						}
						const auto& attr_pt = m_TempAttrPointCalc[attr_point_index];
						if (attr_pt.RelDiamondAngle > rel_diamond_angle)
						{
							break;
						}
						if (crp(next_isovist_pt - prev_isovist_pt, attr_pt.ObjCoords - prev_isovist_pt) >= 0)
						{
							add_visible_object(attr_pt.Group, attr_pt.IndexInGroup);
						}
					}
					prev_isovist_pt = next_isovist_pt;
					prev_rel_diamond_angle = rel_diamond_angle;
				}
			}
done:
			if (m_AttractionPoints.GroupCount > 1)
			{
				std::sort(m_TempIndexArray.data() + prev_temp_index_array_size, m_TempIndexArray.data() + m_TempIndexArray.size());
			}

			base_visible_group_index += m_AttractionPoints.GroupCount;
		}

		// Attraction polygons
		if (m_AttractionPolygons.GroupCount)
		{
			const size_t prev_temp_index_array_size = m_TempIndexArray.size();
			
			m_TempAttrEdgeQueue.clear();
			m_AttractionPolygons.Tree.VisitItems(
				[&](const bb_t& bb) -> bool
				{
					return bb.OverlapsCircle(origin_local, outer_clipping_radius);
				},
				[&](const SPolygon& polygon)
				{
					if (!polygon.BB.OverlapsCircle(origin_local, outer_clipping_radius))
					{
						return;
					}
					
					const auto* points = m_AttractionPolygons.PolygonPoints.data() + polygon.FirstPointIndex;

					// Origin inside polygon?
					if (polygon.BB.Contains(origin_local.x, origin_local.y) && TestPointInRing(origin_local, psta::make_span(points, polygon.PointCount)))
					{
						add_visible_object(polygon.Group, polygon.IndexInGroup);
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

					auto pt_prev = points[polygon.PointCount - 1] - origin_local;
					const auto diamond_angle = DiamondAngleFromVector(pt_prev);
					auto prev_rel_diamond_angle = (diamond_angle < fov_diamond_angle_0 ? MAX_DIAMOND_ANGLE : 0.0f) + diamond_angle - fov_diamond_angle_0;
					for (uint32_t point_index = 0; point_index < polygon.PointCount; ++point_index)
					{
						const auto pt_next = points[point_index] - origin_local;
						const auto diamond_angle = DiamondAngleFromVector(pt_next);
						const auto rel_diamond_angle = (diamond_angle < fov_diamond_angle_0 ? MAX_DIAMOND_ANGLE : 0.0f) + diamond_angle - fov_diamond_angle_0;
						if (crp(pt_prev, pt_next) >= 0 && TestLineSegmentAndCircleOverlap(pt_prev, pt_next, outer_clipping_radius, outer_clipping_radius_sqrd))
						{
							SAttrEdgeCalc attr_edge;
							attr_edge.P0 = pt_prev;
							attr_edge.P1 = pt_next;
							attr_edge.RelDiamondAngle0 = prev_rel_diamond_angle;
							attr_edge.RelDiamondAngle1 = rel_diamond_angle;
							if (prev_rel_diamond_angle >= .5f * MAX_DIAMOND_ANGLE && rel_diamond_angle < .5f * MAX_DIAMOND_ANGLE)
							{
								// Straddling
								attr_edge.RelDiamondAngle1 += MAX_DIAMOND_ANGLE;
							}
							attr_edge.Group = polygon.Group;
							attr_edge.IndexInGroup = polygon.IndexInGroup;
							m_TempAttrEdgeQueue.push_back(attr_edge);
						}
						pt_prev = pt_next;
						prev_rel_diamond_angle = rel_diamond_angle;
					}
				});

			if (!m_TempAttrEdgeQueue.empty())
			{
				if (desc.m_FieldOfViewDegrees < 360)
				{
					// Check polygon edges agains frustum clip edges
					for (size_t i = 0; i < m_TempAttrEdgeQueue.size(); ++i)
					{
						auto& attr_edge = m_TempAttrEdgeQueue[i];
						if (TestLineSegmentsIntersection(attr_edge.P0, attr_edge.P1, isovist_obj_points.back(), isovist_obj_points.front()) ||
							TestLineSegmentsIntersection(attr_edge.P0, attr_edge.P1, isovist_obj_points.front(), isovist_obj_points[1]))
						{
							add_visible_object(attr_edge.Group, attr_edge.IndexInGroup);
							attr_edge = m_TempAttrEdgeQueue.back();
							m_TempAttrEdgeQueue.pop_back();
							--i;
						}
					}
				}

				// Sort edges by RelDiamondAngle0
				std::sort(m_TempAttrEdgeQueue.begin(), m_TempAttrEdgeQueue.end(), [](const auto& a, const auto& b) { return a.RelDiamondAngle0 < b.RelDiamondAngle0; });

				class CIsovistEdgeIterator 
				{
				public:
					CIsovistEdgeIterator() {}
					CIsovistEdgeIterator(psta::span<float2> points, bool isLoop, float fov_diamond_angle_0)
						: m_Points(points)
						, m_IsLoop(isLoop)
						, m_FovDiamondAngle0(fov_diamond_angle_0)
						, m_At(0)
					{
						this->P1 = m_Points[0];
						this->RelDiamondAngle1 = 0;
					}

					bool next()
					{
						this->P0 = this->P1;
						this->RelDiamondAngle0 = this->RelDiamondAngle1;
						if (m_At + 1 >= m_Points.size())
						{
							if (!m_IsLoop || m_At >= m_Points.size())
							{
								if (m_LapIndex > 0)
								{
									return false;
								}
								++m_LapIndex;
								m_At = 0;
								if (!m_IsLoop)
								{
									this->P0 = m_Points[0];
									this->RelDiamondAngle0 = MAX_DIAMOND_ANGLE;
								}
							}
							else
							{
								++m_At;
								this->P1 = m_Points[0];
								this->RelDiamondAngle1 = MAX_DIAMOND_ANGLE;
								return true;
							}
						}
						++m_At;
						this->P1 = m_Points[m_At];
						const auto diamond_angle = DiamondAngleFromVector(this->P1);
						this->RelDiamondAngle1 = (diamond_angle < m_FovDiamondAngle0 ? MAX_DIAMOND_ANGLE : 0.0f) + diamond_angle - m_FovDiamondAngle0;
						this->RelDiamondAngle1 += MAX_DIAMOND_ANGLE * m_LapIndex;
						return true;
					}

					float RelDiamondAngle0;
					float RelDiamondAngle1;
					float2 P0;
					float2 P1;

				private:
					bool m_IsLoop;
					uint8_t m_LapIndex = 0;
					float m_FovDiamondAngle0;
					size_t m_At;
					psta::span<float2> m_Points;
				};

				size_t attr_edges_beg = 0, attr_edges_end = 0;
				CIsovistEdgeIterator isovistEdgeIterator;
				if (desc.m_FieldOfViewDegrees < 360)
				{
					ASSERT(isovist_obj_points.front() == float2(0, 0));
					isovistEdgeIterator = CIsovistEdgeIterator(psta::make_span(isovist_obj_points.data() + 1, isovist_obj_points.size() - 1), false, fov_diamond_angle_0);
				}
				else
				{
					isovistEdgeIterator = CIsovistEdgeIterator(psta::make_span(isovist_obj_points), true, fov_diamond_angle_0);
				}

				while (isovistEdgeIterator.next() && attr_edges_beg < m_TempAttrEdgeQueue.size())
				{
					for (; attr_edges_end < m_TempAttrEdgeQueue.size(); ++attr_edges_end)
					{
						auto& attr_edge = m_TempAttrEdgeQueue[attr_edges_end];
						if (attr_edge.RelDiamondAngle0 > isovistEdgeIterator.RelDiamondAngle1)
						{
							break;
						}
						if (attr_edge.RelDiamondAngle0 >= isovistEdgeIterator.RelDiamondAngle0 && crp(isovistEdgeIterator.P1 - isovistEdgeIterator.P0, attr_edge.P0 - isovistEdgeIterator.P0) >= 0)
						{
							add_visible_object(attr_edge.Group, attr_edge.IndexInGroup);
							attr_edge = m_TempAttrEdgeQueue[attr_edges_beg++];
						}
					}

					for (size_t i = attr_edges_beg; i < attr_edges_end; ++i)
					{
						auto& attr_edge = m_TempAttrEdgeQueue[i];
						if (attr_edge.RelDiamondAngle1 > isovistEdgeIterator.RelDiamondAngle0)
						{
							if (!TestLineSegmentsIntersection(isovistEdgeIterator.P0, isovistEdgeIterator.P1, attr_edge.P0, attr_edge.P1))
							{
								continue;
							}
							add_visible_object(attr_edge.Group, attr_edge.IndexInGroup);
						}
						attr_edge = m_TempAttrEdgeQueue[attr_edges_beg++];
					}
				}
				
				// Remove duplicates
				{
					m_TempIndexArray.resize(prev_temp_index_array_size + remove_duplicates(psta::make_span(m_TempIndexArray.data() + prev_temp_index_array_size, m_TempIndexArray.size() - prev_temp_index_array_size)));
					auto* group_sizes = &m_TempIndexArray[base_visible_group_index];
					for (uint32_t group_index = 0; group_index < m_AttractionPolygons.GroupCount; ++group_index)
					{
						group_sizes[group_index] = 0;
					}
					for (size_t i = prev_temp_index_array_size; i < m_TempIndexArray.size(); ++i)
					{
						const auto group_index = (m_TempIndexArray[i] >> 24) - base_visible_group_index;
						group_sizes[group_index]++;
					}
				}
			}
			base_visible_group_index += m_AttractionPolygons.GroupCount;
		}
	}
	
	result.IndexArray.resize(m_TempIndexArray.size());

	{
		uint32_t n = 0;
		for (size_t i = 0; i < total_visibility_group_count; ++i)
		{
			result.IndexArray[i] = m_TempIndexArray[i];
			m_TempIndexArray[i] = n;
			n += result.IndexArray[i];
		}

		for (size_t i = total_visibility_group_count; i < m_TempIndexArray.size(); ++i)
		{
			const auto group_and_idx = m_TempIndexArray[i];
			const auto group_index = group_and_idx >> 24;
			const auto index_in_group = group_and_idx & 0x00FFFFFF;
			auto& group_at = m_TempIndexArray[group_index];
			result.IndexArray[total_visibility_group_count + group_at++] = index_in_group;
		}
	}

	m_TempIndexArray.clear();

	{
		desc.m_OutVisibleObstacles.GroupCount = m_Obstacles.GroupCount;
		desc.m_OutVisibleAttractionPoints.GroupCount = m_AttractionPoints.GroupCount;
		desc.m_OutVisibleAttractionPolygons.GroupCount = m_AttractionPolygons.GroupCount;
		uint32_t group_counter = 0;
		auto group_index = 0;
		auto* groups_at = result.IndexArray.data();
		auto* indices_at = result.IndexArray.data() + total_visibility_group_count;
		for (auto* visible_objects : { &desc.m_OutVisibleObstacles , &desc.m_OutVisibleAttractionPoints , &desc.m_OutVisibleAttractionPolygons })
		{
			visible_objects->CountPerGroup = groups_at;
			visible_objects->Indices = indices_at;
			for (uint32_t group_index = 0; group_index < visible_objects->GroupCount; ++group_index)
			{
				const auto group_size = *groups_at++;
				visible_objects->ObjectCount += group_size;
				indices_at += group_size;
			}
		}
	}

	// Translate isovist to world coordinates
	for (auto it = isovist_points.crbegin(); isovist_points.crend() != it; ++it)
	{
		result.Isovist.push_back(LocalToWorld(*it + origin_local));
	}

	m_LocalIsovistPool.Return(std::move(isovist_points));

	desc.m_OutPointCount = (uint32_t)result.Isovist.size();
	desc.m_OutPoints = &result.Isovist.data()->x;
	desc.m_OutIsovistHandle = resultRef.release();  // NOTE: Ownership of result is transferred here
	desc.m_OutArea = (float)area;

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