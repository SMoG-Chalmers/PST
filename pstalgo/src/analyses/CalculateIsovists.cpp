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

#include <memory>
#include <pstalgo/analyses/CalculateIsovists.h>
#include <pstalgo/Debug.h>
#include <pstalgo/geometry/Geometry.h>
#include <pstalgo/geometry/IsovistCalculator.h>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/maths.h>

#include "../ProgressUtil.h"

static const float EPSILON = 0.001f;

template <class TType>
struct TPlane2D
{
	TVec2<TType> Normal;
	TType T;
};

typedef TPlane2D<float> Plane2Df;

template <class TType>
bool ClipLineSegment(TVec2<TType>& p0, TVec2<TType>& p1, const TPlane2D<TType>& plane)
{
	const auto t0 = dot(plane.Normal, p0) - plane.T;
	const auto t1 = dot(plane.Normal, p1) - plane.T;
	if (t0 < 0)
	{
		const auto len = t1 - t0;
		if (len + t0 < EPSILON)
		{
			return false;
		}
		const float t = t0 / len;
		p0.x -= (p1.x - p0.x) * t;
		p0.y -= (p1.y - p0.y) * t;
	}
	else if (t1 < 0)
	{
		const auto len = t0 - t1;
		if (len + t1 < EPSILON)
		{
			return false;
		}
		const float t = t1 / len;
		p1.x -= (p0.x - p1.x) * t;
		p1.y -= (p0.y - p1.y) * t;
	}
	return true;
}

class CCalculateIsovists : public IPSTAlgo
{
public:
	bool Run(const SCalculateIsovistsDesc& desc, SCalculateIsovistsRes& res, IProgressCallback& progress)
	{
		struct AABB
		{
			float2 Center;
			float2 HalfSize;
		};

		const float perimeter_segment_angle = desc.m_PerimeterSegmentCount ? PI * 2.f / desc.m_PerimeterSegmentCount : PI * 2.f;
		const float outer_clipping_radius = desc.m_MaxRadius;
		const float inner_clipping_radius = desc.m_MaxRadius * cosf(perimeter_segment_angle * .5f);

		// Count total polygon points
		uint32_t total_polygon_point_count = 0;
		for (uint32_t polygon_index = 0; polygon_index < desc.m_PolygonCount; ++polygon_index)
		{
			total_polygon_point_count += desc.m_PointCountPerPolygon[polygon_index];
		}

		const bool use_cut_off_ring = desc.m_MaxRadius > 0 && desc.m_PerimeterSegmentCount > 2;

		if (total_polygon_point_count > 0 || use_cut_off_ring)
		{
			const auto aabb = CRectd::BBFromPoints((const double2*)desc.m_PolygonPoints, total_polygon_point_count);
			const auto world_origin = double2(trunc(aabb.CenterX()), trunc(aabb.CenterY()));

			std::vector<std::pair<float2, float2>> edges;
			edges.reserve((use_cut_off_ring ? desc.m_PerimeterSegmentCount : 0) + total_polygon_point_count);

			// Calculate clipping planes and also push as edges to start of edge vector
			std::vector<Plane2Df> clipping_planes;
			if (use_cut_off_ring)
			{
				float angle = -PI + perimeter_segment_angle;
				float2 pt_prev(-desc.m_MaxRadius, 0);
				for (uint32_t i = 0; i < desc.m_PerimeterSegmentCount; ++i, angle += perimeter_segment_angle)
				{
					float clipping_plane_angle = angle - perimeter_segment_angle * .5f;
					clipping_planes.push_back({ float2(-cosf(clipping_plane_angle), -sinf(clipping_plane_angle)), -inner_clipping_radius });
					const float2 pt(cosf(angle) * outer_clipping_radius, sinf(angle) * outer_clipping_radius);
					edges.push_back({ pt_prev, pt });
					pt_prev = pt;
				}
				edges.back().second = edges.front().first;
			}

			// Calculate polygon bounding boxes
			std::vector<AABB> aabb_per_polygon;
			aabb_per_polygon.reserve(desc.m_PolygonCount);
			{
				const double2* points_ptr = (const double2*)desc.m_PolygonPoints;
				for (uint32_t polygon_index = 0; polygon_index < desc.m_PolygonCount; ++polygon_index)
				{
					const auto point_count = desc.m_PointCountPerPolygon[polygon_index];
					const auto rect = (CRectf)(CRectd::BBFromPoints(points_ptr, point_count) - world_origin);
					aabb_per_polygon.push_back({ rect.Center(), float2(rect.Width() * .5f, rect.Height() * .5f) });
					points_ptr += point_count;
				}
			}
				
			std::vector<float2> pts;
			CIsovistCalculator isovist_calculator;
			for (size_t origin_index = 0; origin_index < desc.m_OriginCount; ++origin_index)
			{
				const double2 origin = ((const double2*)desc.m_OriginPoints)[origin_index];
				const float2 local_origin = (float2)(origin - world_origin);

				// Reset edges vector to only contain clipping edges
				edges.resize(clipping_planes.size());

				// Add edges from polygons
				const double2* total_points_ptr = (const double2*)desc.m_PolygonPoints;
				for (uint32_t polygon_index = 0; polygon_index < desc.m_PolygonCount; ++polygon_index)
				{
					const auto polygon_point_count = desc.m_PointCountPerPolygon[polygon_index];
					if (!polygon_point_count)
					{
						continue;
					}

					const auto& aabb = aabb_per_polygon[polygon_index];
					if (TestAABBCircleOverlap(aabb.Center, aabb.HalfSize, local_origin, outer_clipping_radius))
					{
						const bool needs_clipping = !TestAABBFullyInsideCircle(aabb.Center, aabb.HalfSize, local_origin, inner_clipping_radius);

						auto pt_prev = (float2)(total_points_ptr[polygon_point_count - 1] - origin);
						for (uint32_t point_index = 0; point_index < polygon_point_count; ++point_index)
						{
							const auto pt_next = (float2)(total_points_ptr[point_index] - origin);
							auto edge = std::make_pair(pt_prev, pt_next);
							if (needs_clipping)
							{
								size_t plane_index;
								for (plane_index = 0; plane_index < clipping_planes.size(); ++plane_index)
								{
									if (!ClipLineSegment(edge.first, edge.second, clipping_planes[plane_index]))
										break;
								};
								if (plane_index == clipping_planes.size())
								{
									edges.push_back(edge);
								}
							}
							else
							{
								edges.push_back(edge);
							}
							pt_prev = pt_next;
						}
					}

					total_points_ptr += polygon_point_count;
				}

				pts.clear();
				isovist_calculator.CalculateIsovist(float2(0, 0), edges.data(), edges.size(), pts);

				m_IsovistPoints.reserve(m_IsovistPoints.size() + pts.size());
				for (auto it = pts.rbegin(); pts.rend() != it; ++it)
				{
					m_IsovistPoints.push_back(double2(origin.x + it->x, origin.y + it->y));
				}
				m_PointCountPerIsovist.push_back((uint32_t)pts.size());

				progress.ReportProgress((float)(origin_index + 1) / desc.m_OriginCount);
			}
		}

		res.m_IsovistCount = (unsigned int)m_PointCountPerIsovist.size();
		res.m_PointCountPerIsovist = m_PointCountPerIsovist.empty() ? nullptr : m_PointCountPerIsovist.data();
		res.m_IsovistPoints = m_IsovistPoints.empty() ? nullptr : &m_IsovistPoints.front().x;

		return true;
	}

private:
	std::vector<uint32_t> m_PointCountPerIsovist;
	std::vector<double2> m_IsovistPoints;
};

PSTADllExport IPSTAlgo* PSTACalculateIsovists(const SCalculateIsovistsDesc* desc, SCalculateIsovistsRes* res)
{
	try {
		if ((desc->VERSION != desc->m_Version) ||
			(res->VERSION != res->m_Version)) {
			throw std::runtime_error("Version mismatch");
		}

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
