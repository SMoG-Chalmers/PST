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

#include <atomic>
#include <future>
#include <memory>

#include <pstalgo/analyses/AttractionDistance.h>
#include <pstalgo/experimental/ShortestPathTraversal.h>
#include <pstalgo/experimental/StraightLineMinDistance.h>
#include <pstalgo/geometry/RegionPoints.h>
#include <pstalgo/Debug.h>
#include <pstalgo/graph/AxialGraph.h>

#include "../ProgressUtil.h"

#define USE_MULTIPLE_CORES

namespace psta
{
	// Atomically compares obj and expected, if bitwise-equal replaces obj 
	// with desired. Otherwise loads the actual value stored in obj into expected.
	// TODO: Move
	// template <typename T>
	// bool atomic_compare_exchange(T& obj, T& expected, T desired)
	// {
	// 	static_assert(sizeof(T) == 4, "atomic_compare_exchange only works with 32-bit values");

	// 	#ifdef WIN32
	// 		const auto prev = _InterlockedCompareExchange((long*)&obj, *(long*)&desired, *(long*)&expected);
	// 	#else	
	// 		const auto prev = __sync_val_compare_and_swap((int*)&obj, *(int*)&expected, *(int*)&desired);
	// 	#endif

	// 	if (*(T*)&prev == expected)
	// 		return true;

	// 	expected = *(T*)&prev;
		
	// 	return false;
	// }

	struct SAttractionDistanceWorkerContext
	{
	public:
		typedef CDirectedMultiDistanceGraph graph_t;

		const graph_t&     m_Graph;
		const float* const m_Limits;
		const float        m_StraightLineDistLimit;
		float* const       m_ResMinDistPerDest = nullptr;
		int*   const       m_ResOriginIdxPerDest = nullptr;

		SAttractionDistanceWorkerContext(const graph_t& graph, const float* limits, float straight_line_dist_limit, float* ret_min_distance_per_destination, int* ret_origin_index_per_destination)
			: m_Graph(graph)
			, m_Limits(limits)
			, m_StraightLineDistLimit(straight_line_dist_limit)
			, m_ResMinDistPerDest(ret_min_distance_per_destination)
			, m_ResOriginIdxPerDest(ret_origin_index_per_destination)
			, m_NextOrigin(0)
		{}

		SAttractionDistanceWorkerContext(const SAttractionDistanceWorkerContext&) = delete;

		float Progress() const { return std::min(1.f, (float)m_NextOrigin / (float)m_Graph.OriginNodeCount()); }

		bool DequeueOrigin(size_t& ret_index)
		{
			if (m_NextOrigin >= m_Graph.OriginNodeCount())
				return false;
			ret_index = m_NextOrigin++;
			return ret_index < m_Graph.OriginNodeCount();
		}

		void UpdateResults(const float* min_dists)
		{
			std::unique_lock<decltype(m_Mutex)> _cs(m_Mutex);
			for (size_t i = 0; i < m_Graph.DestinationCount(); ++i)
				m_ResMinDistPerDest[i] = std::min(min_dists[i], m_ResMinDistPerDest[i]);
		}

		void UpdateResults(const std::pair<float, int>* min_dists_and_org_idx)
		{
			std::unique_lock<decltype(m_Mutex)> _cs(m_Mutex);
			for (size_t i = 0; i < m_Graph.DestinationCount(); ++i)
			{
				if (min_dists_and_org_idx[i].first < m_ResMinDistPerDest[i])
				{
					m_ResMinDistPerDest[i]   = min_dists_and_org_idx[i].first;
					m_ResOriginIdxPerDest[i] = min_dists_and_org_idx[i].second;
				}
				else if (min_dists_and_org_idx[i].first == m_ResMinDistPerDest[i])
				{
					// To make sure the analysis is deterministic we choose origin index with lowest index if
					// minimum distance is the same. Otherwise origin index could change from one execution to the next.
					m_ResOriginIdxPerDest[i] = std::min(m_ResOriginIdxPerDest[i], min_dists_and_org_idx[i].second);
				}
			}
		}

	private:
		std::atomic<size_t> m_NextOrigin;
		std::recursive_mutex m_Mutex;
	};

	void AttractionDistanceWorker(SAttractionDistanceWorkerContext& ctx)
	{
		size_t origin_index;
		std::vector<float> min_dists;
		std::vector<std::pair<float, int>> min_dists_and_org_idx;
		IShortestPathTraversal::dist_callback_t cb;

		if (ctx.m_ResOriginIdxPerDest)
		{
			min_dists_and_org_idx = std::vector<std::pair<float, int>>(ctx.m_Graph.DestinationCount(), std::make_pair(std::numeric_limits<float>::infinity(), -1));
			cb = ([&origin_index, &min_dists_and_org_idx](size_t destination_index, float distance)
			{
				if (distance < min_dists_and_org_idx[destination_index].first)
				{
					min_dists_and_org_idx[destination_index].first  = distance;
					min_dists_and_org_idx[destination_index].second = (int)origin_index;
				}
			});
		}
		else
		{
			min_dists = std::vector<float>(ctx.m_Graph.DestinationCount(), std::numeric_limits<float>::infinity());
			cb = ([&origin_index, &min_dists](size_t destination_index, float distance)
			{
				min_dists[destination_index] = std::min(min_dists[destination_index], distance);
			});
		}

		auto traversal = CreateShortestPathTraversal(ctx.m_Graph);
		while (ctx.DequeueOrigin(origin_index))
		{
			if (ctx.m_Graph.DistanceTypeCount() == 1)
				traversal->SearchAccumulative(origin_index, cb, ctx.m_Limits, ctx.m_StraightLineDistLimit);
			else
				traversal->Search(origin_index, cb, ctx.m_Limits, ctx.m_StraightLineDistLimit);
		}

		if (!min_dists.empty())
			ctx.UpdateResults(min_dists.data());
		else
			ctx.UpdateResults(min_dists_and_org_idx.data());
	}

	void CalculateMinimumDistances(
		const CDirectedMultiDistanceGraph& graph, 
		IProgressCallback& prograss_callback, 
		const float* limits, 
		float straight_line_distance_limit, 
		psta::array_view<float> ret_min_dist_per_origin,
		psta::array_view<int>   ret_dest_idx_per_origin)
	{
		if ((ret_min_dist_per_origin.size() != graph.DestinationCount()) ||
			(ret_dest_idx_per_origin && ret_dest_idx_per_origin.size() != graph.DestinationCount()))
			throw std::runtime_error("Result buffer size doesn't match destination count");

		if (ret_min_dist_per_origin)
			for (auto& x : ret_min_dist_per_origin)
				x = std::numeric_limits<float>::infinity();

		if (ret_dest_idx_per_origin)
			for (auto& x : ret_dest_idx_per_origin)
				x = -1;

		SAttractionDistanceWorkerContext ctx(graph, limits, straight_line_distance_limit, ret_min_dist_per_origin.data(), ret_dest_idx_per_origin.data());
		
		// Start workers
		std::vector<std::future<void>> tasks;
		#ifdef USE_MULTIPLE_CORES
			tasks.resize(std::min(graph.DestinationCount(), (size_t)std::max(std::thread::hardware_concurrency(), 1u)));
		#else
			tasks.resize(1);
		#endif
		for (auto& task : tasks)
			task = std::async(std::launch::async, AttractionDistanceWorker, std::ref(ctx));

		// Wait for workers to finish, and report progres every 100ms
		for (auto& task : tasks)
		{
			do {
				prograss_callback.ReportProgress(ctx.Progress());
			} while (std::future_status::ready != task.wait_for(std::chrono::milliseconds(100)));
		}

		// Report done
		prograss_callback.ReportProgress(1);
	}

	// TEMP
	std::vector<float2> NetworkElementPositions(const CAxialGraph& graph, EPSTANetworkElement element_type)
	{
		std::vector<float2> pts;
		switch (element_type)
		{
		case EPSTANetworkElement_Point:
			pts.reserve(graph.getPointCount());
			for (int i = 0; i < graph.getPointCount(); ++i)
				pts.push_back(graph.getPoint(i).coords);
			break;
		case EPSTANetworkElement_Junction:
			pts.reserve(graph.getCrossingCount());
			for (int i = 0; i < graph.getCrossingCount(); ++i)
				pts.push_back(graph.getCrossing(i).pt);
			break;
		case EPSTANetworkElement_Line:
			pts.reserve(graph.getLineCount());
			for (int i = 0; i < graph.getLineCount(); ++i)
			{
				const auto& line = graph.getLine(i);
				pts.push_back((line.p1 + line.p2) * .5f);
			}
			break;
		default:
			throw std::runtime_error("Unsupported network element type");
		}
		return pts;
	}

	void ResolveDistanceTypes(EPSTADistanceType distance_type, const SPSTARadii& radii, std::vector<EPSTADistanceType>& ret_distance_types, std::vector<float>& ret_limits, float& ret_straight_line_limit)
	{
		auto type_mask = radii.m_Mask;

		ret_straight_line_limit = radii.Straight();
		type_mask &= ~EPSTADistanceTypeMask_Straight;

		ret_distance_types.push_back(distance_type);
		ret_limits.push_back(radii.Get(distance_type));
		type_mask &= ~EPSTADistanceMaskFromType(distance_type);

		for (unsigned int i = 0; i < EPSTADistanceType__COUNT; ++i)
		{
			if (!(type_mask & EPSTADistanceMaskFromType(i)))
				continue;
			ret_distance_types.push_back((EPSTADistanceType)i);
			ret_limits.push_back(radii.Get((EPSTADistanceType)i));
		}
	}
}

PSTADllExport bool PSTAAttractionDistance(const SPSTAAttractionDistanceDesc* desc)
{
	try
	{
		VerifyStructVersion(*desc);

		auto* axial_graph = (CAxialGraph*)desc->m_Graph;
		ASSERT(axial_graph);

		// Origin type (will be 'destination' in analysis since algorithm executes backwards)
		EPSTANetworkElement destination_type;
		switch (desc->m_OriginType)
		{
		case EPSTAOriginType_Points:      destination_type = EPSTANetworkElement_Point;    break;
		case EPSTAOriginType_Junctions:   destination_type = EPSTANetworkElement_Junction; break;
		case EPSTAOriginType_Lines:       destination_type = EPSTANetworkElement_Line;     break;
		case EPSTAOriginType_PointGroups: destination_type = EPSTANetworkElement_Point;    break;
		default:
			LOG_ERROR("Unsupported origin type #%d!", desc->m_OriginType);
			return false;
		}

		float* results            = desc->m_OutMinDistance;
		int*   result_indices     = desc->m_OutDestinationIndices;
		unsigned int result_count = desc->m_OutputCount;

		std::vector<float> point_results;
		std::vector<int>   point_result_indices;
		if (EPSTAOriginType_PointGroups == desc->m_OriginType)
		{
			if (desc->m_OutputCount != axial_graph->getPointGroupCount())
			{
				LOG_ERROR("Output array size (%d) doesen't match point group count (%d)!", desc->m_OutputCount, axial_graph->getPointGroupCount());
				return false;
			}
			point_results.resize(axial_graph->getPointCount());
			results = point_results.data();
			if (result_indices)
			{
				point_result_indices.resize(axial_graph->getPointCount());
				result_indices = point_result_indices.data();
			}
			result_count = (unsigned int)point_results.size();
		}

		std::vector<float2> attraction_points;
		attraction_points.resize(desc->m_AttractionPointCount);
		for (size_t i = 0; i < attraction_points.size(); ++i)
			attraction_points[i] = axial_graph->worldToLocal(((const double2*)desc->m_AttractionPoints)[i]);

		std::vector<float2> poly_points;
		if (desc->m_PointsPerAttractionPolygon)
		{
			poly_points = std::move(attraction_points);

			// Generate and count points
			size_t count = 0;
			const auto* pts = poly_points.data();
			for (unsigned int polygon_index = 0; polygon_index < desc->m_AttractionPolygonCount; ++polygon_index)
			{
				count += GeneratePointsAlongRegionEdge(pts, desc->m_PointsPerAttractionPolygon[polygon_index], desc->m_AttractionPolygonPointInterval);
				pts += desc->m_PointsPerAttractionPolygon[polygon_index];
			}

			// Allocate space for generated points
			attraction_points.resize(count);

			// Generate and store points
			count = 0;
			pts = poly_points.data();
			for (unsigned int polygon_index = 0; polygon_index < desc->m_AttractionPolygonCount; ++polygon_index)
			{
				count += GeneratePointsAlongRegionEdge(pts, desc->m_PointsPerAttractionPolygon[polygon_index], desc->m_AttractionPolygonPointInterval, attraction_points.data() + count, attraction_points.size() - count);
				pts += desc->m_PointsPerAttractionPolygon[polygon_index];
			}

			ASSERT(count == attraction_points.size() && "Pre-allocated region points doesn't mach generated region points");
		}

		if (EPSTADistanceType_Straight == desc->m_DistanceType && !(desc->m_Radius.m_Mask & ~(unsigned int)EPSTADistanceTypeMask_Straight))
		{
			// Spacial case where distance type and radius is straight line only
			psta::CalcStraightLineMinDistances(
				psta::NetworkElementPositions(*axial_graph, destination_type), 
				attraction_points,
				desc->m_Radius.Straight(),
				psta::make_array_view(results, result_count),
				psta::make_array_view(result_indices, result_indices ? result_count : 0));
		}
		else
		{
			std::vector<EPSTADistanceType> distance_types;
			std::vector<float> limits;
			float straight_line_limit;
			psta::ResolveDistanceTypes((EPSTADistanceType)desc->m_DistanceType, desc->m_Radius, distance_types, limits, straight_line_limit);
			ASSERT(distance_types.size() == limits.size());

			const auto analysis_graph = psta::BuildDirectedMultiDistanceGraph(
				*axial_graph, 
				psta::span<const EPSTADistanceType>(distance_types.data(), distance_types.size()),
				psta::span<const float>(desc->m_LineWeights, desc->m_LineWeightCount),
				desc->m_WeightPerMeterForPointEdges,
				false, 
				attraction_points.data(), attraction_points.size(), 
				destination_type);

			CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

			psta::CalculateMinimumDistances(analysis_graph, progress, limits.data(), std::numeric_limits<float>::infinity(), 
				psta::make_array_view(results, result_count),
				psta::make_array_view(result_indices, result_indices ? result_count : 0));

			if (desc->m_PointsPerAttractionPolygon && desc->m_OutDestinationIndices)
			{
				// Destinations points have been generated along polygon edges. Translate
				// destination indices from generated point indices to polygon indices.
				std::vector<unsigned int> point_to_polygon;
				point_to_polygon.reserve(attraction_points.size());
				const auto* pts = poly_points.data();
				for (unsigned int polygon_index = 0; polygon_index < desc->m_AttractionPolygonCount; ++polygon_index)
				{
					const auto n = GeneratePointsAlongRegionEdge(pts, desc->m_PointsPerAttractionPolygon[polygon_index], desc->m_AttractionPolygonPointInterval);
					for (size_t i = 0; i < n; ++i)
						point_to_polygon.push_back(polygon_index);
					pts += desc->m_PointsPerAttractionPolygon[polygon_index];
				}
				ASSERT(point_to_polygon.size() == attraction_points.size());
				for (size_t i = 0; i < desc->m_OutputCount; ++i)
					if (desc->m_OutDestinationIndices[i] >= 0)
						desc->m_OutDestinationIndices[i] = point_to_polygon[desc->m_OutDestinationIndices[i]];
			}

			if (EPSTAOriginType_PointGroups == desc->m_OriginType)
			{
				// Calculate scores per point group
				ASSERT(axial_graph->getPointGroupCount() == desc->m_OutputCount);
				unsigned int point_index = 0;
				for (unsigned int group_index = 0; group_index < axial_graph->getPointGroupCount(); ++group_index)
				{
					float min_dist = std::numeric_limits<float>::infinity();
					int   dest_idx = -1;
					for (unsigned int i = 0; i < axial_graph->getPointGroupSize(group_index); ++i, ++point_index)
					{
						if (results[point_index] < min_dist)
						{
							min_dist = results[point_index];
							if (result_indices)
								dest_idx = result_indices[point_index];
						}
					}
					desc->m_OutMinDistance[group_index] = min_dist;
					if (desc->m_OutDestinationIndices)
						desc->m_OutDestinationIndices[group_index] = dest_idx;
				}
				ASSERT(point_index == (unsigned int)axial_graph->getPointCount());
			}
		}

		// Replace infinity result values with -1
		if (desc->m_OutMinDistance)
			std::replace(desc->m_OutMinDistance, desc->m_OutMinDistance + desc->m_OutputCount, std::numeric_limits<float>::infinity(), -1.f);
	}
	catch (const std::exception& e)
	{
		LOG_ERROR(e.what());
		return false;
	}
	return true;
}
