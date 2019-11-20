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
#include <queue>
#include <stack>
#include <vector>

#include <pstalgo/analyses/SegmentBetweenness.h>
#include <pstalgo/utils/BitVector.h>
#include <pstalgo/Debug.h>
#include <pstalgo/graph/AxialGraph.h>

#include "../ProgressUtil.h"

#define USE_MULTIPLE_CORES

//#define DEBUG_OUTPUT

namespace
{
	class CBetweennessAlgoWorker
	{
	public:
		// NOTE: All of the segment pointers here (weight_per_segment, ret_node_counts, ret_total_depths) point 
		//       to segment #0, NOT #first_segment_to_process! It is up to this method to index correctly.
		void Run(
			unsigned int first_segment_to_process,
			unsigned int num_segments_to_process,
			CAxialGraph& graph,
			EPSTADistanceType distType,
			const SPSTARadii& limits,
			const float* weight_per_segment,
			unsigned int* ret_node_counts,
			float* ret_total_depths,
			std::atomic<unsigned int>& segments_processed_counter);

		const double* GetBetweennessScores() const { return m_result.data(); }

	private:
		struct SPredecessorElement
		{
			static const unsigned int END = (unsigned int)-1;

			unsigned int m_Predecessor = END;
			unsigned int m_Next = END;

			inline bool HasPredecessor() const { return END != m_Predecessor; }
			inline bool HasNext() const { return END != m_Next; }
			inline void Clear() { m_Predecessor = m_Next = END; }
		};
		std::vector<SPredecessorElement> m_Predecessors;

		struct SEGDATA {
			float    dist;
			int      nPaths;
			SPredecessorElement pred;
		};
		typedef std::vector<SEGDATA> SegDataArray;

		void AddPredecessor(SEGDATA& seg_data, unsigned int pred);
		template <class TLambda> void PopPredecessors(SEGDATA& seg_data, TLambda&& lambda);

		void ProcessSegment(const int iSegment, unsigned int& ret_node_count, float& ret_total_depth);
		inline bool UseWeights() const { return nullptr != m_WeightPerSegment; }
		inline bool IsBiDirectional() const { return (int)m_segData.size() > m_Graph->getLineCount(); }
		unsigned int GetReverseSegmentIndex(unsigned int index) const;

		struct DIST {
			float walking;
			float turns;
			float angle;
			float axmeter;
		};

		struct STATE {
			unsigned int iSegment;
			unsigned int iPrevSegment;
			float        cmpdist;
			DIST         dist;
		public:
			inline bool operator<(const STATE& s) const { return cmpdist > s.cmpdist; }
		};
		typedef std::priority_queue<STATE> Queue;

		CAxialGraph* m_Graph;
		EPSTADistanceType m_distType;
		SPSTARadii m_limits;
		const float* m_WeightPerSegment;

		Queue              m_queue;
		CBitVector         m_visitFlags;
		SegDataArray       m_segData;
		std::stack<unsigned int> m_segStack;
		std::vector<float> m_dep;
		std::vector<double> m_result;
	};

	class CBetweennessAlgo
	{
	public:
		CBetweennessAlgo();

		bool Run(CAxialGraph& graph, EPSTADistanceType distType, const SPSTARadii& limits, const float* weight_per_segment, float* ret_betweenness, unsigned int* ret_node_counts, float* ret_total_depths, IProgressCallback& progress);

	private:
		std::vector<CBetweennessAlgoWorker> m_Workers;
	};

	void CBetweennessAlgoWorker::Run(
		unsigned int first_segment_to_process,
		unsigned int num_segments_to_process,
		CAxialGraph& graph,
		EPSTADistanceType distType,
		const SPSTARadii& limits,
		const float* weight_per_segment,
		unsigned int* ret_node_counts,
		float* ret_total_depths,
		std::atomic<unsigned int>& segments_processed_counter)
	{
		#ifdef DEBUG_OUTPUT		
			LOG_INFO("worker started");
		#endif

		m_Graph = &graph;
		m_WeightPerSegment = weight_per_segment;
		m_distType = distType;
		m_limits = limits;

		const int segment_count = (EPSTADistanceType_Angular == distType) ? graph.getLineCount() * 2 : graph.getLineCount();

		m_Predecessors.reserve(segment_count);

		m_visitFlags.resize(segment_count);
		m_segData.resize(segment_count);
		m_dep.resize(segment_count);

		m_result.resize(graph.getLineCount());
		memset(m_result.data(), 0, m_result.size() * sizeof(m_result.front()));

		for (unsigned int i = first_segment_to_process; i < first_segment_to_process+num_segments_to_process; ++i)
		{
			unsigned int dummy_node_count;
			float dummy_total_depth;
			ProcessSegment(i, ret_node_counts ? ret_node_counts[i] : dummy_node_count, ret_total_depths ? ret_total_depths[i] : dummy_total_depth);
			segments_processed_counter++;
			// TODO: Handle cancelling
		}

		#ifdef DEBUG_OUTPUT		
			LOG_INFO("worker finished");
		#endif
	}

	void CBetweennessAlgoWorker::AddPredecessor(SEGDATA& seg_data, unsigned int pred)
	{
		if (!seg_data.pred.HasPredecessor())
		{
			seg_data.pred.m_Predecessor = pred;
			ASSERT(!seg_data.pred.HasNext());
		}
		else
		{
			m_Predecessors.push_back(seg_data.pred);
			seg_data.pred.m_Next = (unsigned int)(m_Predecessors.size() - 1);
			seg_data.pred.m_Predecessor = pred;
		}
	}
	
	template <class TLambda> void CBetweennessAlgoWorker::PopPredecessors(SEGDATA& seg_data, TLambda&& lambda)
	{
		auto* p = &seg_data.pred;
		if (!p->HasPredecessor())
			return;
		for (;;)
		{
			lambda(p->m_Predecessor);
			if (!p->HasNext())
				break;
			p = &m_Predecessors[p->m_Next];
		}
		seg_data.pred.Clear();
	}

	void CBetweennessAlgoWorker::ProcessSegment(const int iSegment, unsigned int& ret_node_count, float& ret_total_depth)
	{

		if (UseWeights() && !(m_WeightPerSegment[iSegment] > 0.0f))
			return;

		unsigned int num_segments_reached = 0;  // Will be sum of lines that was reached within radius from iSegment
		double total_depth = 0;                 // Will be sum of minimum distances from iSegment to all reached segments

		m_visitFlags.clearAll();

		m_Predecessors.clear();

		m_visitFlags.set(iSegment);
		m_segData[iSegment].nPaths = 1;
		m_segData[iSegment].dist = 0.0f;
		//m_segStack.push(iLine); // Should we do this???

		int iReverseSegment = iSegment + m_Graph->getLineCount();
		if (IsBiDirectional()) {
			m_visitFlags.set(iReverseSegment);
			m_segData[iReverseSegment].nPaths = 1;
			m_segData[iReverseSegment].dist = 0.0f;
			//m_segStack.push(iReverseSegment); // Should we do this???
		}

		CAxialGraph::NETWORKLINE& seg = m_Graph->getLine(iSegment);

		// For Straight radius calculation
		const float2 ptCenter = (seg.p1 + seg.p2) * 0.5f;

		for (int i = 0; i < seg.nCrossings; ++i) {

			STATE state;

			int iLC = seg.iFirstCrossing + i;

			const CAxialGraph::LINECROSSING& lc = m_Graph->getLineCrossing(iLC);
			const CAxialGraph::LINECROSSING& olc = m_Graph->getLineCrossing(lc.iOpposite);
			const CAxialGraph::NETWORKLINE&  seg2 = m_Graph->getLine(olc.iLine);

			bool bReverse = (lc.linePos < (seg.length * 0.5f));
			bool bNextReverse = (olc.linePos >(seg2.length * 0.5f));

			// Walking Distance
			state.dist.walking = (seg.length + seg2.length) * 0.5f;

			// Turns
			state.dist.turns = 1.0f;

			// Angle
			float currAngle = bReverse ? reverseAngle(seg.angle) : seg.angle;
			float targetAngle = bNextReverse ? reverseAngle(seg2.angle) : seg2.angle;
			state.dist.angle = angleDiff(currAngle, targetAngle);

			// Ax-meter
			state.dist.axmeter = (seg.length * 0.5f) + seg2.length;

			// Radius Tests
			if (EPSTADistanceTypeMask_Walking & m_limits.m_Mask) {
				if (state.dist.walking > m_limits.m_Walking)
					continue;
			}
			if (EPSTADistanceTypeMask_Steps & m_limits.m_Mask) {
				if ((int)state.dist.turns > m_limits.m_Steps)
					continue;
			}
			if (EPSTADistanceTypeMask_Angular & m_limits.m_Mask) {
				if (state.dist.angle > m_limits.m_Angular)
					continue;
			}
			if (EPSTADistanceTypeMask_Axmeter & m_limits.m_Mask) {
				if (state.dist.axmeter > m_limits.m_Axmeter)
					continue;
			}
			if (EPSTADistanceTypeMask_Straight & m_limits.m_Mask) {
				if ((((seg2.p1 + seg2.p2) * 0.5f) - ptCenter).getLengthSqr() > m_limits.m_Straight*m_limits.m_Straight)
					continue;
			}

			switch (m_distType) {
			case EPSTADistanceType_Walking: state.cmpdist = state.dist.walking; break;
			case EPSTADistanceType_Steps:   state.cmpdist = state.dist.turns;   break;
			case EPSTADistanceType_Angular: state.cmpdist = state.dist.angle;   break;
			case EPSTADistanceType_Axmeter: state.cmpdist = state.dist.axmeter; break;
			
			// Unhandled
			case EPSTADistanceType_Undefined:
			default:
				ASSERT(false && "Unsupported distance type");
			}

			state.iPrevSegment = iSegment;
			if (bReverse)
				state.iPrevSegment += m_Graph->getLineCount();

			state.iSegment = olc.iLine;
			if (bNextReverse)
				state.iSegment += m_Graph->getLineCount();

			m_queue.push(state);

		}


		// Traverse graph

		while (!m_queue.empty()) {

			const STATE state = m_queue.top();
			m_queue.pop();

			unsigned int iSegment = state.iSegment;

			bool bReverse = (iSegment >= (unsigned int)m_Graph->getLineCount());

			unsigned int iRealSegment = iSegment;
			if (bReverse)
				iRealSegment -= (unsigned int)m_Graph->getLineCount();

			const CAxialGraph::NETWORKLINE& seg = m_Graph->getLine(iRealSegment);

			if (!IsBiDirectional())
				iSegment = iRealSegment;

			SEGDATA &segData = m_segData[iSegment];

			if (!m_visitFlags.get(iSegment)) {

				// Check if first time this segment is reached in EITHER direction
				if (!IsBiDirectional() || !m_visitFlags.get(GetReverseSegmentIndex(iSegment)))
				{
					total_depth += state.cmpdist;
					++num_segments_reached;
				}

				m_visitFlags.set(iSegment);

				m_segStack.push(iSegment);

				segData.dist = state.cmpdist;
				segData.nPaths = 0;

				for (int i = 0; i < seg.nCrossings; ++i) {

					int iNLC = seg.iFirstCrossing + i;

					const CAxialGraph::LINECROSSING& nlc = m_Graph->getLineCrossing(iNLC);

					if ((nlc.linePos > seg.length * 0.5f) == bReverse)
						continue; // Never leave the same end we entered

					const CAxialGraph::LINECROSSING& olc = m_Graph->getLineCrossing(nlc.iOpposite);
					const CAxialGraph::NETWORKLINE&  seg2 = m_Graph->getLine(olc.iLine);

					// ----------------------
					STATE nextState;

					int iNextSegment = olc.iLine;

					// Check if we'll enter the next segment in reverse direction
					bool bNextReverse = (olc.linePos > (seg2.length * 0.5f));

					if (bNextReverse)
						iNextSegment += m_Graph->getLineCount();

					// Don't visit the next segment if it has already been visited
					if (m_visitFlags.get(IsBiDirectional() ? iNextSegment : olc.iLine))
						continue;

					// Walking Distance
					nextState.dist.walking = state.dist.walking + (seg.length + seg2.length) * 0.5f;

					// Turns
					nextState.dist.turns = state.dist.turns + 1;

					// Angle
					float currAngle = bReverse ? reverseAngle(seg.angle) : seg.angle;
					float targetAngle = bNextReverse ? reverseAngle(seg2.angle) : seg2.angle;
					nextState.dist.angle = state.dist.angle + angleDiff(currAngle, targetAngle);

					// Ax-meter
					nextState.dist.axmeter = state.dist.axmeter +
						((seg.length * (state.dist.turns + 1.0f)) + (seg2.length * (state.dist.turns + 2.0f))) * 0.5f;

					// Radius Tests
					if (EPSTADistanceTypeMask_Walking & m_limits.m_Mask) {
						if (nextState.dist.walking > m_limits.m_Walking)
							continue;
					}
					if (EPSTADistanceTypeMask_Steps & m_limits.m_Mask) {
						if ((int)nextState.dist.turns > m_limits.m_Steps)
							continue;
					}
					if (EPSTADistanceTypeMask_Angular & m_limits.m_Mask) {
						if (nextState.dist.angle > m_limits.m_Angular)
							continue;
					}
					if (EPSTADistanceTypeMask_Axmeter & m_limits.m_Mask) {
						if (nextState.dist.axmeter > m_limits.m_Axmeter)
							continue;
					}
					if (EPSTADistanceTypeMask_Straight & m_limits.m_Mask) {
						if ((((seg2.p1 + seg2.p2) * 0.5f) - ptCenter).getLengthSqr() > m_limits.m_Straight*m_limits.m_Straight)
							continue;
					}

					switch (m_distType) {
					case EPSTADistanceType_Walking: nextState.cmpdist = nextState.dist.walking; break;
					case EPSTADistanceType_Steps:   nextState.cmpdist = nextState.dist.turns;   break;
					case EPSTADistanceType_Angular: nextState.cmpdist = nextState.dist.angle;   break;
					case EPSTADistanceType_Axmeter: nextState.cmpdist = nextState.dist.axmeter; break;

					// Unhandled
					case EPSTADistanceType_Undefined:
					default:
						ASSERT(false && "Unsupported distance type");
					}

					nextState.iPrevSegment = iSegment;
					nextState.iSegment = iNextSegment;

					m_queue.push(nextState);

				}

			} // [end] if (!m_visitFlags.get(state.iSegment))


			if (state.cmpdist == segData.dist) {

				unsigned int iPrevSegment = state.iPrevSegment;

				if (!IsBiDirectional() && (iPrevSegment >= (unsigned int)m_Graph->getLineCount()))
					iPrevSegment -= m_Graph->getLineCount();

				segData.nPaths += m_segData[iPrevSegment].nPaths;
				AddPredecessor(segData, iPrevSegment);
			}

		} // [end] while (!m_queue.empty())



		///////////////
		// Accumulate

		if (!m_dep.empty())
			memset(&m_dep.front(), 0, m_dep.size() * sizeof(m_dep.front()));

		//float srcLength = m_pGraph->getLine(iSegment).length;

		float srcWeight = 0.0f;
		if (UseWeights()) {
			srcWeight = m_WeightPerSegment[iSegment];
		}

		while (!m_segStack.empty()) {

			const unsigned int w = m_segStack.top();
			m_segStack.pop();

			SEGDATA& segdata = m_segData[w];

			if (IsBiDirectional()) {

				// Bi-directional algorithm

				unsigned int iRealSegment = w;
				if (iRealSegment >= (unsigned int)m_Graph->getLineCount())
					iRealSegment -= m_Graph->getLineCount();

				//const CAxialGraph::NETWORKLINE& targetSegment = m_pGraph->getLine(iRealSegment);

				// Get index of reverse line 
				unsigned int iOpposite =
					(w < (unsigned int)m_Graph->getLineCount()) ?
					m_Graph->getLineCount() + w :
					w - m_Graph->getLineCount();

				bool bShortestPath = (!m_visitFlags.get(iOpposite) || (segdata.dist <= m_segData[iOpposite].dist));

				// Loop through predecessors
				PopPredecessors(segdata, [&](unsigned int v)
				{
					if (bShortestPath) {
						if (UseWeights()) {
							//m_dep[v] += ((float)m_segData[v].nPaths / segdata.nPaths) * (targetSegment.length + m_dep[w]);
							m_dep[v] += ((float)m_segData[v].nPaths / segdata.nPaths) * (m_WeightPerSegment[iRealSegment] + m_dep[w]);
						}
						else {
							m_dep[v] += ((float)m_segData[v].nPaths / segdata.nPaths) * (1.0f + m_dep[w]);
						}
					}
					else {
						m_dep[v] += ((float)m_segData[v].nPaths / segdata.nPaths) * m_dep[w];
					}
				});

				// NOTE: We only add half the score because the algorithm counts
				//       each path twice - once for each direction.
				if (UseWeights()) {
					//m_result[iRealSegment] += srcLength * m_dep[w] * 0.5f;			
					m_result[iRealSegment] += srcWeight * m_dep[w] * 0.5f;
					if (bShortestPath) {
						//m_result[iRealSegment] += srcLength * targetSegment.length * 0.25f;			
						m_result[iRealSegment] += srcWeight * m_WeightPerSegment[iRealSegment] * 0.25f;
					}
				}
				else {
					m_result[iRealSegment] += m_dep[w] * 0.5f;
				}

			}
			else {

				// Uni-directional algorithm

				//const CAxialGraph::NETWORKLINE& targetSegment = m_pGraph->getLine(w);

				// Loop through predecessors
				PopPredecessors(segdata, [&](unsigned int v)
				{
					if (UseWeights()) {
						//m_dep[v] += ((float)m_segData[v].nPaths / segdata.nPaths) * (targetSegment.length + m_dep[w]);
						m_dep[v] += ((float)m_segData[v].nPaths / segdata.nPaths) * (m_WeightPerSegment[w] + m_dep[w]);
					}
					else {
						m_dep[v] += ((float)m_segData[v].nPaths / segdata.nPaths) * (1.0f + m_dep[w]);
					}
				});

				// NOTE: We only add half the score because the algorithm counts
				//       each path twice - once for each direction.
				if (UseWeights()) {
					//m_result[w] += srcLength * (m_dep[w] + (targetSegment.length * 0.5f)) * 0.5f; 
					m_result[w] += srcWeight * (m_dep[w] + (m_WeightPerSegment[w] * 0.5f)) * 0.5f;
				}
				else {
					m_result[w] += m_dep[w] * 0.5f;
				}

			}

		}

		if (UseWeights()) {

			// NOTE: We only add half the score because the algorithm count
			//       each path twice - once for each direction.
			//m_result[iSegment] += m_dep[iSegment] * srcLength * 0.5f * 0.5f;
			m_result[iSegment] += m_dep[iSegment] * srcWeight * 0.5f * 0.5f;

			if (IsBiDirectional()) {
				//m_result[iSegment] += m_dep[iReverseSegment] * srcLength * 0.5f * 0.5f;
				m_result[iSegment] += m_dep[iReverseSegment] * srcWeight * 0.5f * 0.5f;
			}

			// This "self-betweenness" score however is only counted once per 
			// segment and is therefore not divided by two.
			//m_result[iSegment] += srcLength * srcLength * 0.25f;	
			m_result[iSegment] += srcWeight * srcWeight * 0.25f;

		}

		ret_node_count = num_segments_reached + 1;  // We want to store count INCLUDING origin segment (so +1 here)!
		ret_total_depth = (EPSTADistanceType_Angular == m_distType) ? SyntaxAngleWeightFromDegrees((float)total_depth) : (float)total_depth;
	}

	unsigned int CBetweennessAlgoWorker::GetReverseSegmentIndex(unsigned int index) const
	{
		const unsigned int line_count = (unsigned int)m_Graph->getLineCount();
		return (index < line_count) ? (index + line_count) : (index - line_count);
	}

	/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	//  CBetweennessAlgo

	CBetweennessAlgo::CBetweennessAlgo()
	{
		using namespace std;
		#ifdef USE_MULTIPLE_CORES
			m_Workers.resize(max(std::thread::hardware_concurrency(), 1u));
		#else
			m_Workers.resize(1);
		#endif
	}

	bool CBetweennessAlgo::Run(
		CAxialGraph& graph, 
		EPSTADistanceType distType, 
		const SPSTARadii& limits, 
		const float* weight_per_segment, 
		float* ret_betweenness, 
		unsigned int* ret_node_counts, 
		float* ret_total_depths, 
		IProgressCallback& progress)
	{
		using namespace std;

		// Verify valid distance type
		switch (distType) {
			case EPSTADistanceType_Walking:
			case EPSTADistanceType_Steps:
			case EPSTADistanceType_Angular:
			case EPSTADistanceType_Axmeter:
				break;
			default:
				LOG_ERROR("Unsupported distance type");
				return false;
		}

		std::atomic<unsigned int> num_processed_segments(0);

		VERIFY(num_processed_segments.is_lock_free());

		const unsigned int segments_per_worker = (unsigned int)(graph.getLineCount() / m_Workers.size()) + 1;

		std::vector<std::future<void>> tasks;
		tasks.reserve(m_Workers.size());
		
		for (unsigned int worker_index = 0; worker_index < m_Workers.size(); ++worker_index)
		{
			const unsigned int first_segment_to_process = segments_per_worker * worker_index;
			const int num_segments_to_process = min((int)graph.getLineCount() - (int)first_segment_to_process, (int)segments_per_worker);
			if (num_segments_to_process <= 0)
				break;
			tasks.push_back(std::async(
				std::launch::async,
				&CBetweennessAlgoWorker::Run,
				&m_Workers[worker_index],
				first_segment_to_process,
				num_segments_to_process,
				std::ref(graph),
				distType,
				std::ref(limits),
				weight_per_segment,
				ret_node_counts,
				ret_total_depths,
				std::ref(num_processed_segments)));
		}

		// Loop through tasks and wait for each one to finish
		for (size_t task_index = 0; task_index < tasks.size(); ++task_index)
		{
			auto& task = tasks[task_index];
			
			// Wait for task to finish, and update progress every 100ms
			while (std::future_status::ready != task.wait_for(std::chrono::milliseconds(100)))
			{
				progress.ReportProgress((float)num_processed_segments.load() / graph.getLineCount());
			}

			// Update progress
			progress.ReportProgress((float)num_processed_segments.load() / graph.getLineCount());
		}

		if (ret_betweenness)
		{
			// Accumulate scores from all workers.
			// We iterate over lines first and workers second, even though this
			// is likely to be less cache efficient, in favor of precision.
			for (int line_index = 0; line_index < graph.getLineCount(); ++line_index)
			{
				double score = 0;
				for (size_t task_index = 0; task_index < tasks.size(); ++task_index)
					score += m_Workers[task_index].GetBetweennessScores()[line_index];
				ret_betweenness[line_index] = (float)score;
			}
		}

		// Verify that all segments were processed
		if (num_processed_segments.load() != (unsigned int)graph.getLineCount())
		{
			// Failed
			LOG_ERROR("Segment betweenness analysis failed (all segments were not processed!?).");
			return false;
		}

		progress.ReportProgress(1.f);

		return true;
	}
}

// node_counts[i] = number of nodes reached from node i, INCLUDING origin node i
PSTADllExport void PSTABetweennessNormalize(const float* in_values, const unsigned int* node_counts, unsigned int count, float* out_normalized)
{
	for (unsigned int i = 0; i < count; ++i)
	{
		const auto N = node_counts[i];
		out_normalized[i] = (N > 2) ?
			(in_values[i] / (0.5f * (float)(N - 1) * (float)(N - 2))) :
			in_values[i];
	}
}

PSTADllExport void PSTABetweennessSyntaxNormalize(const float* in_values, const float* total_depths, unsigned int count, float* out_normalized)
{
	for (unsigned int i = 0; i < count; ++i)
	{
		out_normalized[i] = log10(in_values[i] + 1.0f) / log10(2.0f + total_depths[i]);
	}
}

PSTADllExport bool PSTASegmentBetweenness(const SPSTASegmentBetweennessDesc* desc)
{
	if (desc->VERSION != desc->m_Version)
		return false;

	auto* graph = static_cast<CAxialGraph*>(desc->m_Graph);

	// Weights
	float* weights_per_segment = nullptr;
	std::vector<float> weights;
	if (desc->m_AttractionPoints)
	{
		// Weights are given per attraction point.
		// Transfer them to segments.
		weights.resize(graph->getLineCount(), 0.0f);
		for (size_t i = 0; i < desc->m_AttractionPointCount; ++i)
		{
			const auto local_coords = graph->worldToLocal(*(const double2*)(desc->m_AttractionPoints + i * 2));
			const int seg_index = graph->getClosestLine(local_coords, NULL, NULL);
			if (seg_index >= 0)
				weights[seg_index] += desc->m_Weights ? desc->m_Weights[i] : 1.f;
		}
		weights_per_segment = weights.data();
	}
	else
	{
		weights_per_segment = desc->m_Weights;
	}

	// Create algorithm object
	CBetweennessAlgo algo;
	CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

	// Run the algorithm
	return algo.Run(*graph, (EPSTADistanceType)desc->m_DistanceType, desc->m_Radius, weights_per_segment, desc->m_OutBetweenness, desc->m_OutNodeCount, desc->m_OutTotalDepth, progress);
}
