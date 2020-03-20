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

#include <atomic>
#include <future>
#include <memory>
#include <queue>
#include <cstring>

#include <pstalgo/analyses/ODBetweenness.h>
#include <pstalgo/experimental/ShortestPathTraversal.h>
#include <pstalgo/experimental/StraightLineMinDistance.h>
#include <pstalgo/graph/AxialGraph.h>
#include <pstalgo/Debug.h>

#include "../ProgressUtil.h"

//#define USE_MULTIPLE_CORES

namespace psta
{
	namespace
	{
		float GetTurnAngle(float from, float to)
		{
			float delta = fabsf(to - from);
			if (delta > 180.0f)
				delta = 360.0f - delta;
			return delta;
		}

		inline float OppositeAngle(float angle)
		{
			angle -= 180.0f;
			return (angle < 0.0f) ? 360.0f + angle : angle;
		}
	}

	///////////////////////////////////////////////////////////////////////////////
	//
	//  CODBetweennessWorkerContext
	//

	class CODBetweennessWorkerContext
	{
	public:
		CODBetweennessWorkerContext(const SPSTAODBetweenness& desc)
			: m_Desc(desc)
			, m_OriginProcessedCounter(0)
		{
			if (desc.m_DestinationWeights && desc.m_DestinationCount != Graph().getPointCount())
				throw std::runtime_error("SPSTAODBetweenness::m_DestinationCount does not match graph point count");
			if (desc.m_OutputCount != Graph().getLineCount())
				throw std::runtime_error("SPSTAODBetweenness::m_OutputCount does not match graph line count");
		}

		float Progress() const { return (float)m_OriginProcessedCounter / m_Desc.m_OriginCount; }

		CAxialGraph& Graph() const {  return *(CAxialGraph*)m_Desc.m_Graph; }

		float GetDestinationWeight(size_t destination_index) const 
		{ 
			ASSERT(destination_index < Graph().getPointCount());
			return m_Desc.m_DestinationWeights ? m_Desc.m_DestinationWeights[destination_index] : 1.f;
		}

		SPSTAODBetweenness::EDestinationMode DestinationMode() const { return (SPSTAODBetweenness::EDestinationMode)m_Desc.m_DestinationMode; }

		EPSTADistanceType DistanceType() const { return (EPSTADistanceType)m_Desc.m_DistanceType; }
		
		const SPSTARadii& Radius() const { return m_Desc.m_Radius; }

		bool FetchNextOrigin(COORDS& coords, float& weight, int& category)
		{
			const auto origin_index = m_OriginProcessedCounter++;
			if (origin_index >= m_Desc.m_OriginCount)
				return false;
			const auto pos = m_Desc.m_OriginPoints[origin_index] - Graph().getWorldOrigin();
			coords.x = (float)pos.x;
			coords.y = (float)pos.y;
			weight = m_Desc.m_OriginWeights ? m_Desc.m_OriginWeights[origin_index] : 1.f;
			category = 0;
			return true;
		}

		int   GetDestCategoryCount() const { return 1; }

		int   GetCategoryForDestination(int destination) const { return 0; }

		float GetDestinationWeight(int destination) const { return m_Desc.m_DestinationWeights ? m_Desc.m_DestinationWeights[destination] : 1.f; }

		float GetMatrixWeight(int origin_category, int dest_category) const { return 1.f; }

	private:
		const SPSTAODBetweenness& m_Desc;
		std::atomic<unsigned int> m_OriginProcessedCounter;
	};


	///////////////////////////////////////////////////////////////////////////////
	//
	//  CODBetweennessWorker
	//

	class CODBetweennessWorker
	{
	public:
		CODBetweennessWorker(CODBetweennessWorkerContext& ctx);

		void Run();

		const float* GetLineScores() const { return m_LineScores.empty() ? NULL : &m_LineScores.front(); }

	private:
		void ProcessOrigin(const COORDS& pt, float weight, int origin_category);
		
		struct SCrossingDist
		{
			union
			{
				float m_Dist;
				float m_Forwards;
			};
			float m_Backwards;
			void SetMax() { m_Dist = m_Backwards = std::numeric_limits<float>::max(); }
		};

		struct SDist
		{
			unsigned int m_Steps;
			float m_Walking;
			float m_Angle;
			void SetZero() { m_Steps = 0;  m_Walking = m_Angle = 0; }
			void SetMax() { m_Steps = 0xFFFFFFFF;  m_Walking = m_Angle = std::numeric_limits<float>::max(); }
		};

		struct SReachedPoint
		{
			int m_Index;
			int m_PrevTrace;
		};

		struct SStep
		{
			int   m_Line;  // If negative means end point
			int   m_LineCrossing;  // Local index
			int   m_PrevTrace;
			float m_DistModeDist;  // one of the m_AccDist members, depending on distance mode
			SDist m_AccDist;
			bool  m_Forwards;

			inline bool    IsForwards() const { return m_Forwards; }
			inline void    SetForwards(bool forwards) { m_Forwards = forwards; }

			void UpdateDistModeDist(EPSTADistanceType dist_type);

			inline bool operator<(const SStep& d) const { return m_DistModeDist > d.m_DistModeDist; }
		};

		struct STrace
		{
			unsigned int m_Line;
			int          m_PrevTrace;
			float        m_Score;  // When tracing back
		};

		void QueueStep(SStep& step);
		void ClearQueue();
		bool UpdateShortestCrossingDist(int crossing_index, const SDist& dist, bool forwards);
		bool IsWithinRadius(const SDist& dist) const;
		bool IsWithinStraightRadius(const COORDS& p0, const COORDS& p1);

		typedef std::vector<SReachedPoint> ReachedPointVec;
		typedef std::priority_queue<SStep> StepQueue;
		typedef std::vector<SCrossingDist> CrossingDistVec;
		typedef std::vector<STrace>        TraceVec;
		typedef std::vector<float>         LineScoreVector;
		typedef std::vector<float>         PointDistVector;

		CODBetweennessWorkerContext& m_Ctx;

		StepQueue       m_Queue;
		ReachedPointVec m_ReachedPoints;
		CrossingDistVec m_ShortestCrossingDists;
		TraceVec        m_Trace;
		LineScoreVector m_LineScores;
		PointDistVector m_ShortestPointDists;
		std::vector<float> m_DestWeightsPerCategory;
	};

	CODBetweennessWorker::CODBetweennessWorker(CODBetweennessWorkerContext& ctx)
		: m_Ctx(ctx)
	{
		auto& graph = m_Ctx.Graph();

		m_ReachedPoints.reserve(graph.getPointCount());
		m_ShortestPointDists.resize(graph.getPointCount());
		for (size_t i = 0; i < m_ShortestPointDists.size(); ++i)
			m_ShortestPointDists[i] = -1.0f;
		m_ShortestCrossingDists.resize(graph.getLineCrossingCount());
		m_Trace.reserve(graph.getLineCrossingCount());
		m_LineScores.resize(graph.getLineCount());
		if (!m_LineScores.empty())
			memset(&m_LineScores.front(), 0, m_LineScores.size() * sizeof(m_LineScores.front()));
		m_DestWeightsPerCategory.resize(m_Ctx.GetDestCategoryCount());
	}

	void CODBetweennessWorker::Run()
	{
		COORDS coords;
		float weight;
		int category;
		while (m_Ctx.FetchNextOrigin(coords, weight, category))
			ProcessOrigin(coords, weight, category);
	}

	void CODBetweennessWorker::ProcessOrigin(const COORDS& pt, float weight, int origin_category)
	{
		CAxialGraph& graph = m_Ctx.Graph();

		// find closest line for this origin
		REAL dist_from_line, start_line_pos;
		const int start_line_index = graph.getClosestLine(pt, &dist_from_line, &start_line_pos);
		if (start_line_index < 0)
			return;

		const bool we_care_about_angles = (EPSTADistanceType_Angular == m_Ctx.DistanceType() || m_Ctx.Radius().HasAngular());

		// Clear queue, just to make sure
		ASSERT(m_Queue.empty());
		ClearQueue();

		// Generate initial step from origin to closest line
		SStep step;
		step.m_Line = start_line_index;
		step.m_LineCrossing = -1;
		step.m_PrevTrace = -1;
		step.m_AccDist.SetZero();
		step.m_AccDist.m_Walking = dist_from_line;
		if (dist_from_line*dist_from_line <= m_Ctx.Radius().StraightSqr())
		{
			if (we_care_about_angles)
			{
				step.SetForwards(true);
				QueueStep(step);
				step.SetForwards(false);
				QueueStep(step);
			}
			else
			{
				QueueStep(step);
			}
		}

		m_ReachedPoints.clear();
		m_Trace.clear();

		// Reset shortest dists per crossing
		for (size_t i = 0; i < m_ShortestCrossingDists.size(); ++i)
			m_ShortestCrossingDists[i].SetMax();

		// BFS
		while (!m_Queue.empty())
		{
			const SStep step = m_Queue.top();
			m_Queue.pop();

			if (step.m_Line < 0)
			{
				// Queued end point
				const int point_index = -step.m_Line - 1;
				if (-1 != m_ShortestPointDists[point_index])
					continue;
				m_ShortestPointDists[point_index] = step.m_DistModeDist;
				SReachedPoint rp;
				rp.m_Index = point_index;
				rp.m_PrevTrace = step.m_PrevTrace;
				m_ReachedPoints.push_back(rp);
				if (m_Ctx.DestinationMode() == SPSTAODBetweenness::EDestinationMode_ClosestDestinationOnly)
				{
					ClearQueue();
					break;
				}
				continue;
			}

			const CAxialGraph::NETWORKLINE& line = graph.getLine(step.m_Line);

			if (step.m_LineCrossing >= 0 && !UpdateShortestCrossingDist(step.m_LineCrossing, step.m_AccDist, step.IsForwards()))
				continue;

			SStep next_step;
			next_step.m_PrevTrace = (int)m_Trace.size();

			// Leave trace
			STrace trace;
			trace.m_Line = step.m_Line;
			trace.m_PrevTrace = step.m_PrevTrace;
			trace.m_Score = 0.0f;
			m_Trace.push_back(trace);

			const float from_line_pos = (-1 == step.m_LineCrossing) ? start_line_pos : graph.getLineCrossing(step.m_LineCrossing).linePos;

			// Loop through crossings
			for (int c = 0; c < line.nCrossings; ++c)
			{
				const int line_crossing_index = line.iFirstCrossing + c;
				if (line_crossing_index == step.m_LineCrossing)
					continue;  // No need to go back through same crossing we came from
				const CAxialGraph::LINECROSSING& linecrossing = graph.getLineCrossing(line_crossing_index);
				if (linecrossing.linePos == from_line_pos)
				{
					// No need to step out at same position we stepped in on a line, even 
					// if it goes to another line than the one we came in from, since this means 
					// we have visited this line in vain.
					continue;
				}
				if (we_care_about_angles && step.IsForwards() != (linecrossing.linePos > from_line_pos))
					continue;
				if (m_Ctx.Radius().HasStraight() && !IsWithinStraightRadius(pt, graph.getCrossing(linecrossing.iCrossing).pt))
					continue;

				next_step.m_AccDist = step.m_AccDist;
				next_step.m_AccDist.m_Steps += 1;
				next_step.m_AccDist.m_Walking += fabsf(from_line_pos - linecrossing.linePos);

				if (!IsWithinRadius(next_step.m_AccDist))
					continue;

				if (!UpdateShortestCrossingDist(line_crossing_index, next_step.m_AccDist, step.IsForwards()))
					continue;

				const CAxialGraph::LINECROSSING& opposite = graph.getLineCrossing(linecrossing.iOpposite);
				next_step.m_Line = opposite.iLine;
				next_step.m_LineCrossing = linecrossing.iOpposite;

				if (we_care_about_angles)
				{
					const CAxialGraph::NETWORKLINE& next_line = graph.getLine(opposite.iLine);
					const float current_angle = step.IsForwards() ? line.angle : OppositeAngle(line.angle);
					const float forward_turn = GetTurnAngle(current_angle, next_line.angle);
					next_step.m_AccDist.m_Angle += forward_turn;
					next_step.SetForwards(true);
					if (next_step.m_AccDist.m_Angle <= m_Ctx.Radius().Angular())
					{
						QueueStep(next_step);
					}
					next_step.m_AccDist.m_Angle += 180.0f - (2.0f * forward_turn);
					next_step.SetForwards(false);
					if (next_step.m_AccDist.m_Angle <= m_Ctx.Radius().Angular())
					{
						QueueStep(next_step);
					}
				}
				else
				{
					QueueStep(next_step);
				}
			}

			// Loop through destination points
			for (int p = 0; p < line.nPoints; ++p)
			{
				const int point_index = graph.getLinePoint(line.iFirstPoint + p);
				if (m_Ctx.GetDestinationWeight(point_index) <= 0.0f)
					continue;
				const CAxialGraph::POINT& point = graph.getPoint(point_index);
				if (m_Ctx.Radius().HasStraight())
				{
					if (!IsWithinStraightRadius(pt, point.coords) ||
						(line.length > 0.f && !IsWithinStraightRadius(pt, line.p1 + (line.p2 - line.p1) * (point.linePos / line.length))))
						continue;
				}
				if (we_care_about_angles && step.IsForwards() != (point.linePos > from_line_pos))
					continue;
				next_step.m_AccDist = step.m_AccDist;
				if (EPSTADistanceType_Walking == m_Ctx.DistanceType())
					next_step.m_AccDist.m_Walking += fabsf(point.linePos - from_line_pos) + point.distFromLine;
				if (!IsWithinRadius(next_step.m_AccDist))
					continue;
				if (-1 != m_ShortestPointDists[point_index])
					continue;  // Destination point already reached (with a shorter distance because of priority queue)
				// We've reached a destination
				// Queue this as end point step (negative line index)
				next_step.m_Line = -point_index - 1;
				QueueStep(next_step);
			}
		}

		ASSERT(m_Queue.empty());

		// Calculate sum of reached points' weights per category
		ASSERT(!m_DestWeightsPerCategory.empty());
		memset(&m_DestWeightsPerCategory.front(), 0, m_DestWeightsPerCategory.size() * sizeof(float));
		for (size_t i = 0; i < m_ReachedPoints.size(); ++i)
		{
			const SReachedPoint& rp = m_ReachedPoints[i];
			const int category = m_Ctx.GetCategoryForDestination(rp.m_Index);
			if (category >= 0)
				m_DestWeightsPerCategory[category] += m_Ctx.GetDestinationWeight(rp.m_Index);
			m_ShortestPointDists[rp.m_Index] = -1.0f;
		}

		// Calculate score per point by dividing them up per destination category
		for (size_t i = 0; i < m_ReachedPoints.size(); ++i)
		{
			const SReachedPoint& rp = m_ReachedPoints[i];
			const int category = m_Ctx.GetCategoryForDestination(rp.m_Index);
			if (category >= 0)
				m_Trace[rp.m_PrevTrace].m_Score += weight * m_Ctx.GetMatrixWeight(origin_category, category) * m_Ctx.GetDestinationWeight(rp.m_Index) / m_DestWeightsPerCategory[category];
		}

		m_ReachedPoints.clear();

		// Back-track traces and apply scores on lines
		for (int trace_index = (int)m_Trace.size() - 1; trace_index >= 0; --trace_index)
		{
			const STrace& trace = m_Trace[trace_index];
			if (trace.m_Score > 0.0f)
			{
				m_LineScores[trace.m_Line] += trace.m_Score;
				if (trace.m_PrevTrace >= 0)
					m_Trace[trace.m_PrevTrace].m_Score += trace.m_Score;
			}
		}

		m_Trace.clear();
	}

	void CODBetweennessWorker::SStep::UpdateDistModeDist(EPSTADistanceType dist_type)
	{
		ASSERT(EPSTADistanceType_Angular == dist_type || EPSTADistanceType_Walking == dist_type);
		m_DistModeDist = (EPSTADistanceType_Angular == dist_type) ? m_AccDist.m_Angle : m_AccDist.m_Walking;
	}

	void CODBetweennessWorker::QueueStep(SStep& step)
	{
		step.UpdateDistModeDist(m_Ctx.DistanceType());
		m_Queue.push(step);
	}

	void CODBetweennessWorker::ClearQueue()
	{
		while (!m_Queue.empty())
			m_Queue.pop();
	}

	bool CODBetweennessWorker::UpdateShortestCrossingDist(int crossing_index, const SDist& dist, bool forwards)
	{
		switch (m_Ctx.DistanceType())
		{
		case EPSTADistanceType_Angular:
		{
			float& prev_score = forwards ? m_ShortestCrossingDists[crossing_index].m_Forwards : m_ShortestCrossingDists[crossing_index].m_Backwards;
			if (dist.m_Angle > prev_score)
				return false;
			prev_score = dist.m_Angle;
		}
		break;
		case EPSTADistanceType_Walking:
			if (dist.m_Walking > m_ShortestCrossingDists[crossing_index].m_Dist)
				return false;
			m_ShortestCrossingDists[crossing_index].m_Dist = dist.m_Walking;
			break;
		default:
			ASSERT(false && "Unsupported distance type");
		}
		return true;
	}

	bool CODBetweennessWorker::IsWithinRadius(const SDist& dist) const
	{
		return
			dist.m_Walking <= m_Ctx.Radius().Walking() &&
			dist.m_Angle <= m_Ctx.Radius().Angular() &&
			dist.m_Steps <= m_Ctx.Radius().Steps();
	}

	bool CODBetweennessWorker::IsWithinStraightRadius(const COORDS& p0, const COORDS& p1)
	{
		return (p0 - p1).getLengthSqr() <= m_Ctx.Radius().StraightSqr();
	}


	///////////////////////////////////////////////////////////////////////////////
	//
	//  DoODBetweenness
	//

	void DoODBetweenness(const SPSTAODBetweenness& desc)
	{
		CODBetweennessWorkerContext ctx(desc);

		// Decide worker count
		std::vector<std::unique_ptr<CODBetweennessWorker>> workers;
		#ifdef USE_MULTIPLE_CORES
			workers.resize(max(std::thread::hardware_concurrency(), 1u));
		#else
			workers.resize(1);
		#endif

		// Create workers
		for (auto& w : workers)
			w = std::make_unique<CODBetweennessWorker>(ctx);

		// Start workers
		std::vector<std::future<void>> tasks;
		tasks.reserve(workers.size());
		for (auto& w : workers)
		{
			tasks.push_back(std::async(
				std::launch::async,
				&CODBetweennessWorker::Run,
				w.get()));
		}

		CPSTAlgoProgressCallback progress(desc.m_ProgressCallback, desc.m_ProgressCallbackUser);

		// Loop through tasks and wait for each one to finish
		for (auto& task : tasks)
		{
			// Wait for task to finish, and update progress every 100ms
			do {
				progress.ReportProgress(ctx.Progress());
			} while (std::future_status::ready != task.wait_for(std::chrono::milliseconds(100)));
		}

		// Accumulate worker scores
		memset(desc.m_OutScores, 0, desc.m_OutputCount * sizeof(desc.m_OutScores[0]));
		for (const auto& worker : workers)
		{
			const auto* worker_scores = worker->GetLineScores();
			for (size_t i = 0; i < desc.m_OutputCount; ++i)
				desc.m_OutScores[i] += worker_scores[i];
		}
	}
}

PSTADllExport bool PSTAODBetweenness(const SPSTAODBetweenness* desc)
{
	if (desc->VERSION != desc->m_Version)
	{
		LOG_ERROR("SPSTAODBetweenness version mismatch");
		return false;
	}

	try
	{
		psta::DoODBetweenness(*desc);
	}
	catch (const std::exception& e)
	{
		LOG_ERROR(e.what());
		return false;
	}

	return true;
}
