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
#include <atomic>
#include <future>
#include <memory>

#include <pstalgo/analyses/AttractionReach.h>
#include <pstalgo/geometry/RegionPoints.h>
#include <pstalgo/BFS.h>
#include <pstalgo/utils/BitVector.h>
#include <pstalgo/Debug.h>
#include <pstalgo/graph/AxialGraph.h>

#include "../ProgressUtil.h"

#define USE_MULTIPLE_CORES

namespace
{
	class CAttractionAlgo
	{
	public:
		CAttractionAlgo(const SPSTAAttractionReachDesc& desc)
			: m_Desc(desc)
			, m_Graph(*(CAxialGraph*)desc.m_Graph)
			, m_ProcessCounter(0)
			, m_PolyPointIndex(0)
		{
			// Weight Function
			m_WeightFunc = (SPSTAAttractionReachDesc::EWeightFunc)desc.m_WeightFunc;
			m_WeightFuncConstant = desc.m_WeightFuncConstant;
			m_WeightFuncMaxX = desc.m_Radius.Get((EPSTADistanceType)desc.m_DistanceType);
			if (EPSTADistanceTypeMask_Steps == desc.m_DistanceType)
				m_WeightFuncMaxX += 1.f;
		}

		static bool Run(const SPSTAAttractionReachDesc& desc);

		const SPSTAAttractionReachDesc& Desc() const { return m_Desc; }

		bool IsAttractionPolygons() const { return m_Desc.m_PointsPerAttractionPolygon && (m_Desc.m_AttractionPolygonPointInterval > 0); }

		bool NextAttractionPoint(COORDS& ret_point_local, float& ret_attraction_value);

		bool NextAttractionPolygon(std::vector<double2>& ret_points_world, float& ret_attraction_value);

		float Progress() const;

		// Weight function attributes
		SPSTAAttractionReachDesc::EWeightFunc WeightFunc() const { return m_WeightFunc; }
		float WeightFuncMaxX() const { return m_WeightFuncConstant; }
		float WeightFuncConstant() const { return m_WeightFuncMaxX; }

		float GetWeightValue(float x) const;

	private:
		class CWorker : public CPSTBFS
		{
			typedef CPSTBFS super_t;
		public:
			CWorker(CAttractionAlgo& algo)
				: m_Algo(algo) {}

			CWorker& operator=(const CWorker&) = delete;

			void Run();

			const std::vector<float>& Results() const { return m_Results; }

		private:
			void ProcessPoint(const COORDS& pt, float attraction_value);

			// CPSTBFS Overrides
			void visitBFS(int iTarget, const DIST& dist) override;

			float GetWeightValue(float x) const { return m_Algo.GetWeightValue(x); }

			CAttractionAlgo& m_Algo;

			float m_CurrentAttractionValue;

			CBitVector m_TargetVisitedBits; // Bit-mask of targets visited during last call to processPoint
			std::vector<int> m_visitedTargets;    // Indices of targets visited during last call to processPoint

			std::vector<REAL> m_bestScores;  // Temporary to each ProcessPoint call. Stores best score for each reached target for the processed point.

			std::vector<REAL> m_Results;  // Accumulated score for all processed points
		};

		const SPSTAAttractionReachDesc& m_Desc;
		CAxialGraph& m_Graph;
		
		std::mutex m_CriticalSection;
		std::atomic<unsigned int> m_ProcessCounter;

		unsigned int m_PolyPointIndex;

		// Weight function attributes
		SPSTAAttractionReachDesc::EWeightFunc m_WeightFunc;
		float m_WeightFuncMaxX;
		float m_WeightFuncConstant;
	};

	static void CollectPointGroupScores(const CAxialGraph& graph, const float** worker_point_scores, unsigned int worker_count, SPSTAAttractionReachDesc::EAttractionCollectionFunc cfunc, float* out_group_scores)
	{
		unsigned int point_index = 0;
		for (unsigned int group_index = 0; group_index < graph.getPointGroupCount(); ++group_index) 
		{
			float v = 0;
			unsigned int c = 0;
			const unsigned int group_point_count = graph.getPointGroupSize(group_index);
			for (unsigned int i = 0; i < group_point_count; ++i)
			{
				// Accumulate score from workers
				double accumulated_score = 0;
				for (unsigned int w = 0; w < worker_count; ++w)
					accumulated_score += worker_point_scores[w][i];
				const float point_score = (float)accumulated_score;
				if (point_score < 0.0f)
					continue;
				switch (cfunc) {
					case SPSTAAttractionReachDesc::EAttractionCollectionFunc_Avarage:
					case SPSTAAttractionReachDesc::EAttractionCollectionFunc_Sum:
						v += point_score;
						break;
					case SPSTAAttractionReachDesc::EAttractionCollectionFunc_Min:
						if (0 == c || point_score < v)
							v = point_score;
						break;
					case SPSTAAttractionReachDesc::EAttractionCollectionFunc_Max:
						if (0 == c || point_score > v)
							v = point_score;
						break;
					default:
						ASSERT(false && "Unsupported attraction collection function!");
						break;
				}
				++c;
			}
			if (c) 
			{
				if (SPSTAAttractionReachDesc::EAttractionCollectionFunc_Avarage == cfunc)
				{
					v /= c;
				}
				out_group_scores[group_index] = v;
			}
			else 
			{
				out_group_scores[group_index] = -1.0f;
			}
			point_index += group_point_count;
		}
		ASSERT((unsigned int)graph.getPointCount() == point_index);
	}

	bool CAttractionAlgo::Run(const SPSTAAttractionReachDesc& desc)
	{
		using namespace std;

		ASSERT(desc.m_Graph);
		CAxialGraph& graph = *(CAxialGraph*)desc.m_Graph;

		// Origin type (will be 'target' in analysis since algorithm executes backwards)
		CPSTBFS::Target target_type;
		switch (desc.m_OriginType)
		{
		case EPSTAOriginType_Points:
		case EPSTAOriginType_PointGroups:
			target_type = CPSTBFS::TARGET_POINTS;
			break;
		case EPSTAOriginType_Junctions:
			target_type = CPSTBFS::TARGET_CROSSINGS;
			break;
		case EPSTAOriginType_Lines:
			target_type = CPSTBFS::TARGET_LINES;
			break;
		default:
			LOG_ERROR("Unsupported origin type #%d!", desc.m_OriginType);
			return false;
		}

		CAttractionAlgo algo(desc);

		// Create workers
		std::vector<std::unique_ptr<CWorker>> workers;
		#ifdef USE_MULTIPLE_CORES
			workers.resize(max(std::thread::hardware_concurrency(), 1u));
		#else
			workers.resize(1);
		#endif
		for (auto& w : workers)
		{
			w.reset(new CWorker(algo));
			w->init(&graph, target_type, DistanceTypeFromEPSTADistanceType((EPSTADistanceType)desc.m_DistanceType), LimitsFromSPSTARadii(desc.m_Radius));
		}

		const auto target_count = (unsigned int)workers.front()->getTargetCount();
		const auto output_count = (EPSTAOriginType_PointGroups == desc.m_OriginType) ? graph.getPointGroupCount() : target_count;
		if (output_count != desc.m_OutputCount)
		{
			LOG_ERROR("Internal Error: CAttractionAlgo: Output count doesn't match target count!");
			return false;
		}

		CPSTAlgoProgressCallback progress(desc.m_ProgressCallback, desc.m_ProgressCallbackUser);

		// Start workers
		std::vector<std::future<void>> tasks;
		tasks.reserve(workers.size());
		for (auto& w : workers)
		{
			tasks.push_back(std::async(
				std::launch::async,
				&CWorker::Run,
				w.get()));
		}

		// Loop through tasks and wait for each one to finish
		for (size_t task_index = 0; task_index < tasks.size(); ++task_index)
		{
			auto& task = tasks[task_index];

			// Wait for task to finish, and update progress every 100ms
			do {
				progress.ReportProgress(algo.Progress());
			} while (std::future_status::ready != task.wait_for(std::chrono::milliseconds(100)));
		}

		if (algo.IsAttractionPolygons() && desc.m_AttractionPointCount != algo.m_PolyPointIndex)
		{
			LOG_ERROR("Polygon point counts do not add up to total point count (%d vs %d)!", algo.m_PolyPointIndex, desc.m_AttractionPointCount);
			return false;
		}

		// Collect scores
		if (desc.m_OutScores)
		{
			if (EPSTAOriginType_PointGroups == desc.m_OriginType)
			{
				ASSERT((unsigned int)graph.getPointCount() == workers.front()->Results().size());
				ASSERT(graph.getPointGroupCount() == desc.m_OutputCount);
				std::vector<const float*> worker_scores;
				for (const auto& w : workers)
					worker_scores.push_back(w->Results().data());
				CollectPointGroupScores(graph, worker_scores.data(), (unsigned int)worker_scores.size(), (SPSTAAttractionReachDesc::EAttractionCollectionFunc)desc.m_AttractionCollectionFunc, desc.m_OutScores);
			}
			else
			{
				ASSERT(workers.front()->Results().size() == desc.m_OutputCount);
				for (unsigned int i = 0; i < desc.m_OutputCount; ++i)
				{
					double score = 0;
					for (const auto& w : workers)
						score += w->Results()[i];
					desc.m_OutScores[i] = (float)score;
				}
			}
		}
			
		return true;
	}

	bool CAttractionAlgo::NextAttractionPoint(COORDS& ret_point_local, float& ret_attraction_value)
	{
		ASSERT(!IsAttractionPolygons());

		unsigned int index;
		do
		{
			index = m_ProcessCounter.fetch_add(1); // , std::memory_order_relaxed);
			if (index >= m_Desc.m_AttractionPointCount)
				return false;
			ret_attraction_value = m_Desc.m_AttractionValues ? m_Desc.m_AttractionValues[index] : 1.f;
		} while (ret_attraction_value <= 0);

		ret_point_local = m_Graph.worldToLocal(m_Desc.m_AttractionPoints[index]);

		return true;
	}

	bool CAttractionAlgo::NextAttractionPolygon(std::vector<double2>& ret_points_world, float& ret_polygon_attraction_value)
	{
		ASSERT(IsAttractionPolygons());

		const double2* poly_points = nullptr;
		unsigned int poly_point_count = 0;
		{
			// CRITICAL SECTION
			std::unique_lock<std::mutex> cslock(m_CriticalSection);

			ret_polygon_attraction_value = 0;
			while (ret_polygon_attraction_value <= 0)
			{
				const auto polygon_index = m_ProcessCounter.fetch_add(1); // , std::memory_order_relaxed);
				if (polygon_index >= m_Desc.m_AttractionPolygonCount)
					return false;
				poly_point_count = m_Desc.m_PointsPerAttractionPolygon[polygon_index];
				poly_points = m_Desc.m_AttractionPoints + m_PolyPointIndex;
				m_PolyPointIndex += poly_point_count;
				ret_polygon_attraction_value = m_Desc.m_AttractionValues ? m_Desc.m_AttractionValues[polygon_index] : 1.f;
			}
		}

		// Generate list of points along polygon edge
		GeneratePointsAlongRegionEdge(poly_points, poly_point_count, m_Desc.m_AttractionPolygonPointInterval, ret_points_world);

		return true;
	}

	float CAttractionAlgo::Progress() const
	{
		return (float)m_ProcessCounter / (IsAttractionPolygons() ? m_Desc.m_AttractionPolygonCount : m_Desc.m_AttractionPointCount);
	}

	float CAttractionAlgo::GetWeightValue(float x) const
	{
		switch (m_WeightFunc)
		{
		case SPSTAAttractionReachDesc::EWeightFunc_Constant:
			return 1.f;
		case SPSTAAttractionReachDesc::EWeightFunc_Pow:
			x /= m_WeightFuncMaxX;
			return 1.f - powf(x, m_WeightFuncConstant);
		case SPSTAAttractionReachDesc::EWeightFunc_Curve:
			x /= m_WeightFuncMaxX;
			return (x < .5f) ? 1.f - .5f * pow(2.f * x, m_WeightFuncConstant) : .5f * pow(2.f - 2.f * x, m_WeightFuncConstant);
		case SPSTAAttractionReachDesc::EWeightFunc_Divide:
			return powf(x + 1, -m_WeightFuncConstant);
		}
		ASSERT(false && "Unsupported weight function");
		return 0.f;
	}

	void CAttractionAlgo::CWorker::Run()
	{
		ASSERT(m_pGraph);

		const auto target_count = getTargetCount();

		m_Results.clear();
		m_Results.resize(target_count, 0);

		// These are used and reset in every call to ProcessPoint
		m_bestScores.resize(target_count);
		m_visitedTargets.clear();
		m_visitedTargets.reserve(target_count);
		m_TargetVisitedBits.resize(target_count);
		m_TargetVisitedBits.clearAll();
	
		if (m_Algo.IsAttractionPolygons())
		{
			if (SPSTAAttractionReachDesc::EAttractionDistributionFunc_Divide == m_Algo.Desc().m_AttractionDistributionFunc)
			{
				// We have chosen DIVIDE distribution function - meaning every generated point will get a fraction
				// of the attraction value of the polygon. This also means we need to SUM all attraction values on 
				// the target points during processing of the points for this polygon. 
				float polygon_attraction_value;
				std::vector<double2> edge_points;
				while (m_Algo.NextAttractionPolygon(edge_points, polygon_attraction_value))
				{
					if (edge_points.empty())
						continue;
					const float attraction_value_per_point = polygon_attraction_value / edge_points.size();
					// Process all generated points for this polygon
					for (const auto& pt : edge_points)
					{
						ProcessPoint(m_pGraph->worldToLocal(pt), attraction_value_per_point);
						for (int target_index : m_visitedTargets)
							m_Results[target_index] += m_bestScores[target_index];
					}
					edge_points.clear();
				}
			}
			else if (SPSTAAttractionReachDesc::EAttractionDistributionFunc_Copy == m_Algo.Desc().m_AttractionDistributionFunc)
			{
				// We have chosen COPY distribution function - meaning that all generated ponts get the same attraction 
				// value as the polygon - then we should store the MAX attraction value at every target during processing
				// of the points for this polygon. This is more complecated then above...
				std::vector<float> max_scores;
				max_scores.resize(target_count, 0);
				std::vector<unsigned int> poly_visited_target_indices;
				CBitVector poly_visited_target_bits;
				poly_visited_target_bits.resize(target_count);
				poly_visited_target_bits.clearAll();
				float polygon_attraction_value;
				std::vector<double2> edge_points;
				while (m_Algo.NextAttractionPolygon(edge_points, polygon_attraction_value))
				{
					// Process all generated points for this polygon
					for (const auto& pt : edge_points)
					{
						ProcessPoint(m_pGraph->worldToLocal(pt), polygon_attraction_value);
						for (auto target_index : m_visitedTargets)
						{
							if (!poly_visited_target_bits.get(target_index))
							{
								poly_visited_target_bits.set(target_index);
								poly_visited_target_indices.push_back(target_index);
								max_scores[target_index] = m_bestScores[target_index];
							}
							else
							{
								max_scores[target_index] = std::max(max_scores[target_index], m_bestScores[target_index]);
							}
						}
					}
					edge_points.clear();
					// Accumulate the max values for each reached target
					for (auto target_index : poly_visited_target_indices)
					{
						m_Results[target_index] += max_scores[target_index];
						poly_visited_target_bits.clear(target_index);
					}
					poly_visited_target_indices.clear();
				}
			}
			else
			{
				ASSERT(false && "Unsupported attraction distribution function!");
			}
		}
		else
		{
			// Attractions are points (NOT polygons)
			COORDS attraction_point_local;
			float attraction_value;
			while (m_Algo.NextAttractionPoint(attraction_point_local, attraction_value))
			{
				ProcessPoint(attraction_point_local, attraction_value);
				for (int target_index : m_visitedTargets)
					m_Results[target_index] += m_bestScores[target_index];
			}
		}
	}

	void CAttractionAlgo::CWorker::ProcessPoint(const COORDS& pt, float attraction_value)
	{
		m_CurrentAttractionValue = attraction_value;

		for (auto target_index : m_visitedTargets)
			m_TargetVisitedBits.clear(target_index);
		m_visitedTargets.clear();

		if ((DIST_STRAIGHT == m_distType) && !(~LIMITS::MASK_STRAIGHT & m_lim.mask)) 
		{
			if ((TARGET_POINTS == m_target) || (TARGET_CROSSINGS == m_target)) 
			{
				const float maxDistSqr = (LIMITS::MASK_STRAIGHT & m_lim.mask) ? m_lim.straightSqr : std::numeric_limits<float>::infinity();

				const int nTargets = getTargetCount();
				for (int iTarget = 0; (iTarget < nTargets) && !getCancel(); ++iTarget) 
				{
					const COORDS pt2 = (TARGET_POINTS == m_target) ? m_pGraph->getPoint(iTarget).coords : m_pGraph->getCrossing(iTarget).pt;
					const float dist_sqr = (pt2 - pt).getLengthSqr();
					if (dist_sqr > maxDistSqr)
						continue;
					m_bestScores[iTarget] = attraction_value * GetWeightValue(sqrt(dist_sqr));
					m_visitedTargets.push_back(iTarget);
				}
			}
			else if (TARGET_LINES == m_target) 
			{
				if (LIMITS::MASK_STRAIGHT & m_lim.mask) 
				{
					const float radius = sqrtf(m_lim.straightSqr);
					int* pLinesIdx = NULL;
					const int nFound = m_pGraph->getLinesFromPoint(pt, radius, &pLinesIdx);
					for (int i = 0; (i < nFound) && !getCancel(); ++i) 
					{
						const int iLine = pLinesIdx[i];
						const CAxialGraph::NETWORKLINE& l = m_pGraph->getLine(iLine);
						float dist;
						CAxialGraph::getNearestPoint(pt, l.p1, l.p2, &dist);
						if (dist <= radius) 
						{
							m_bestScores[iLine] = attraction_value * GetWeightValue(radius);
							m_visitedTargets.push_back(iLine);
						}
					}
				}
				else 
				{
					const int nLines = m_pGraph->getLineCount();
					for (int iLine = 0; (iLine < nLines) && !getCancel(); ++iLine) 
					{
						const CAxialGraph::NETWORKLINE& l = m_pGraph->getLine(iLine);
						float dist;
						CAxialGraph::getNearestPoint(pt, l.p1, l.p2, &dist);
						m_bestScores[iLine] = attraction_value * GetWeightValue(dist);
						m_visitedTargets.push_back(iLine);
					}
				}
			}
		}
		else 
		{
			clrVisitedLineCrossings();

			doBFSFromPoint(pt);
		}
	}

	void CAttractionAlgo::CWorker::visitBFS(int iTarget, const DIST& dist)
	{
		float d = 0;
		switch (m_distType) 
		{
			case DIST_NONE:
				break;
			case DIST_STRAIGHT:
				if (TARGET_LINES == m_target) {
					const CAxialGraph::NETWORKLINE& l = m_pGraph->getLine(iTarget);
					CAxialGraph::getNearestPoint(m_origin, l.p1, l.p2, &d);
				}
				else {
					const COORDS pt = (TARGET_POINTS == m_target) ? m_pGraph->getPoint(iTarget).coords : m_pGraph->getCrossing(iTarget).pt;
					d = (pt - m_origin).getLength();
				}
				break;
			case DIST_WALKING:
				d = dist.walking;
				break;
			case DIST_LINES:
				d = (float)dist.turns;
				break;
			case DIST_ANGULAR:
				d = dist.angle;
				break;
			case DIST_AXMETER:
				d = dist.axmeter;
				break;
			default:
				ASSERT(false && "Unsupported distance type!");
				break;
		}

		const float score = m_CurrentAttractionValue * GetWeightValue(d);

		if (!m_TargetVisitedBits.get(iTarget)) 
		{
			m_TargetVisitedBits.set(iTarget);
			m_visitedTargets.push_back(iTarget);
		}
		else if (score <= m_bestScores[iTarget]) 
			return;

		m_bestScores[iTarget] = score;
	}
}

PSTADllExport bool PSTAAttractionReach(const SPSTAAttractionReachDesc* desc)
{
	ASSERT(desc);
	if (desc->VERSION != desc->m_Version)
		return false;
	return CAttractionAlgo::Run(*desc);
}
