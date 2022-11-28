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
#include <vector>

#include <pstalgo/utils/DiscretePrioQueue.h>
#include <pstalgo/utils/Macros.h>
#include <pstalgo/Debug.h>
#include <pstalgo/maths.h>
#include <pstalgo/graph/SegmentGraph.h>
#include <pstalgo/Vec2.h>

#include "../Progress.h"
#include "AngularChoiceAlgo.h"

#define USE_MULTIPLE_CORES

class CAngularChoiceAlgo::CWorker
{
public:
	CWorker(CAngularChoiceAlgo& analysis)
		: m_Analysis(analysis)
	{}

	void operator=(const CWorker& other) = delete;

	void Run(unsigned int first_segment_index, unsigned int num_segments, std::atomic<unsigned int>& segments_processed_counter)
	{
		if (CAngularChoiceAlgo::EMode_AngularChoice == m_Analysis.m_Mode)
			m_Scores.resize(m_Analysis.GetGraph().GetSegmentCount(), 0.0f);
		else
			m_Scores.clear();

		m_Queue.Init(360 / m_Analysis.m_AnglePrecisionDegrees + 1);

		m_SegmentStates.resize(m_Analysis.GetGraph().GetSegmentCount() * 2);  // One entry for each direction through every segment

		for (unsigned int segment_index = first_segment_index; segment_index < first_segment_index + num_segments; ++segment_index)
		{
			float dummy_total_depth;
			float dummy_total_weight;
			float dummy_total_depth_weight;
			unsigned int dummy_node_count;
			ProcessSegment(
				segment_index,
				m_Analysis.m_TotalDepths ? m_Analysis.m_TotalDepths[segment_index] : dummy_total_depth,
				m_Analysis.m_TotalWeights ? m_Analysis.m_TotalWeights[segment_index] : dummy_total_weight,
				m_Analysis.m_TotalDepthWeights ? m_Analysis.m_TotalDepthWeights[segment_index] : dummy_total_depth_weight,
				m_Analysis.m_NodeCounts ? m_Analysis.m_NodeCounts[segment_index] : dummy_node_count);

			if (CAngularChoiceAlgo::EMode_AngularChoice == m_Analysis.m_Mode)
			{
				CollectNSCScores(segment_index);
			}

			ClearProcessedFlags(segment_index);

			segments_processed_counter++;

			// TODO: Handle cancelling
		}
	}

	const double* GetSegmentScores() const
	{
		return m_Scores.empty() ? 0x0 : &m_Scores.front();
	}

private:
	struct SSegmentState
	{
		unsigned int  m_LowestAngle;                   // The lowest accumulated angle leading to this segment from origin segment
		unsigned int  m_OutSegmentBits;                // A bit is set if the step to corresponding segment in out-intersection is part of a shortest path
		float         m_Score;
		unsigned char m_NumShortestPathsToThisSegment; // Number of shortes paths leading into this segment
		bool          m_Processed;

		void SetOutSegmentBit(unsigned int index_in_out_intersection)         { ASSERT(index_in_out_intersection < 32); m_OutSegmentBits |= BIT(index_in_out_intersection); }
		bool IsOutSegmentBitSet(unsigned int index_in_out_intersection) const { ASSERT(index_in_out_intersection < 32); return 0 != (m_OutSegmentBits & BIT(index_in_out_intersection)); }
	};

	struct STraversalState
	{
		STraversalState() {}
		STraversalState(unsigned int segment_index, bool forwards, unsigned int accumulated_angle, unsigned int source_segment_state, float acc_walking, float acc_angle, unsigned int acc_steps)
			: m_SegmentIndex(segment_index)
			, m_Forwards(forwards)
			, m_AccumulatedAngle(accumulated_angle)
			, m_SourceSegmentState(source_segment_state)
			, m_AccWalking(acc_walking)
			, m_AccAngle(acc_angle)
			, m_AccSteps(acc_steps)
		{}

		static const unsigned int NO_SOURCE_SEGMENT_STATE = (unsigned int)-1;

		bool HasSourceState() const { return NO_SOURCE_SEGMENT_STATE != m_SourceSegmentState; }

		unsigned int   m_SegmentIndex : 31;
		bool           m_Forwards : 1;
		unsigned int   m_AccumulatedAngle;
		unsigned int   m_SourceSegmentState;  // NO_SOURCE_SEGMENT_STATE if it has no source

		// Radius
		float m_AccWalking;
		float m_AccAngle;
		unsigned int m_AccSteps;
	};

	CAngularChoiceAlgo& m_Analysis;
	float2     m_CurrentOrigin;  // Center position of current start segment
	TDiscretePrioQueue<unsigned int, STraversalState> m_Queue;
	std::vector<SSegmentState> m_SegmentStates;
	std::vector<double> m_Scores;

	CSegmentGraph& GetGraph()
	{
		return m_Analysis.GetGraph();
	}

	inline unsigned int SegmentStateIndex(unsigned int segment_index, bool forwards) const
	{
		return (segment_index << 1) + (forwards ? 0 : 1);
	}

	inline unsigned int SegmentFromSourceSegmentState(unsigned segment_state_index)
	{
		return segment_state_index >> 1;
	}

	inline SSegmentState& SegmentState(unsigned int segment_index, bool forwards)
	{
		return m_SegmentStates[SegmentStateIndex(segment_index, forwards)];
	}

	inline unsigned int ScoreIndex(unsigned int segment_index, bool forwards)
	{
		return (segment_index << 1) + (forwards ? 0 : 1);
	}

	inline unsigned int GetDiscreteAngle(float angle)
	{
		return (unsigned int)(angle / m_Analysis.m_AnglePrecisionDegrees + 0.5f);
	}

	inline bool TestStraightLineDistance(const float2& pos) const
	{
		return (pos - m_CurrentOrigin).getLengthSqr() <= m_Analysis.m_Radius.m_StraightLineSqr;
	}

	void ProcessSegment(unsigned int start_segment_index, float& ret_total_depth, float& ret_total_weight, float& ret_total_depth_weight, unsigned int& ret_node_count)
	{
		m_Queue.Reset(0);

		unsigned int num_segments_reached = 0;
		double total_depth_deg = 0;
		double total_weight = 0;
		double total_depth_deg_weight = 0;

		const auto& segment = GetGraph().GetSegment(start_segment_index);
		m_CurrentOrigin = segment.m_Center;

		STraversalState state(start_segment_index, false, 0, STraversalState::NO_SOURCE_SEGMENT_STATE, 0, 0, 0);
		ProcessTraversalState(state, total_depth_deg, total_weight, total_depth_deg_weight, num_segments_reached);
		state.m_Forwards = true;
		ProcessTraversalState(state, total_depth_deg, total_weight, total_depth_deg_weight, num_segments_reached);

		while (!m_Queue.Empty())
		{
			const STraversalState state = m_Queue.Top();
			m_Queue.Pop();
			ProcessTraversalState(state, total_depth_deg, total_weight, total_depth_deg_weight, num_segments_reached);
		}

		ret_total_depth = (float)SyntaxAngleWeightFromDegrees(total_depth_deg);
		ret_total_weight = (float)total_weight;
		ret_total_depth_weight = (float)SyntaxAngleWeightFromDegrees(total_depth_deg_weight);
		ret_node_count = num_segments_reached + 1;  // Node count INCLUDING origin segment (hence +1 here)
	}

	void CollectNSCScores(int start_segment_index)
	{
		const auto prev_score = m_Scores[start_segment_index];

		CollectScores(start_segment_index, false, start_segment_index);
		CollectScores(start_segment_index, true, start_segment_index);

		if (m_Analysis.IsWeighByLength())
		{
			// When calculating WEIGHTED Choice the origin segments DO get a score, but only
			// half the score that a segment between origin and destination get (Turner 2007, page 544).
			m_Scores[start_segment_index] = prev_score + (m_Scores[start_segment_index] - prev_score) * 0.5;
		}
		else
		{
			// The start segment will be an end segment in this processing step, and should 
			// therefore get no score (only segments BETWEEN other segments will get scores).
			m_Scores[start_segment_index] = prev_score;
		}
	}

	void ProcessTraversalState(const STraversalState& state, double& total_depth_deg, double& total_weight, double& total_depth_deg_weight, unsigned int& segment_count)
	{
		const auto& segment = GetGraph().GetSegment(state.m_SegmentIndex);
		SSegmentState& segment_state = SegmentState(state.m_SegmentIndex, state.m_Forwards);

		if (segment_state.m_Processed && state.m_AccumulatedAngle > segment_state.m_LowestAngle)
			return;  // This segment has been reached via a shorter path

		if (state.HasSourceState())
		{
			// Make the step to this segment known in source segment state
			SSegmentState& source_segment_state = m_SegmentStates[state.m_SourceSegmentState];
			const auto* source_intersection = segment.m_Intersections[state.m_Forwards ? 0 : 1];
			ASSERT(source_intersection);
			for (unsigned int i = 0; i < source_intersection->m_NumSegments; ++i)
			{
				if (source_intersection->m_Segments[i] == state.m_SegmentIndex)
				{
					if (source_segment_state.IsOutSegmentBitSet(i))
					{
						ASSERT(false && "Infinite loop detected.");
						return;
					}
					source_segment_state.SetOutSegmentBit(i);
					break;
				}
			}
		}

		if (segment_state.m_Processed)
		{
			// Found another eaqually short path to this segment
			++segment_state.m_NumShortestPathsToThisSegment;
			return;
		}

		if (state.HasSourceState() && !SegmentState(state.m_SegmentIndex, !state.m_Forwards).m_Processed)
		{
			// First time we reach this segment, from any direction.
			// Update "global" metrics.
			++segment_count;
			const auto weight = m_Analysis.IsWeighByLength() ? segment.m_Length : 1.f;
			total_depth_deg += state.m_AccAngle;
			total_weight += weight;
			total_depth_deg_weight += state.m_AccAngle * weight;
		}

		segment_state.m_Processed = true;
		segment_state.m_Score = -1.0f;
		segment_state.m_NumShortestPathsToThisSegment = 1;
		segment_state.m_LowestAngle = state.m_AccumulatedAngle;
		segment_state.m_OutSegmentBits = 0;

		if (state.m_AccSteps < m_Analysis.m_Radius.m_Steps)
		{
			if (const auto* intersection = segment.m_Intersections[state.m_Forwards ? 1 : 0])
			{
				if (TestStraightLineDistance(intersection->m_Pos))
				{
					const float orientation = state.m_Forwards ? segment.m_Orientation : reverseAngle(segment.m_Orientation);

					for (unsigned int i = 0; i < intersection->m_NumSegments; ++i)
					{
						const unsigned int other_segment_index = intersection->m_Segments[i];
						if (other_segment_index == state.m_SegmentIndex)
							continue;  // Do not go back to current segment from intersection

						const auto& other_segment = GetGraph().GetSegment(other_segment_index);
						if (!TestStraightLineDistance(other_segment.m_Center))
							continue;

						const float acc_walking = state.m_AccWalking + (segment.m_Length + other_segment.m_Length) * 0.5f;
						if (acc_walking  > m_Analysis.m_Radius.m_Walking)
							continue;

						const bool other_forwards = (other_segment.m_Intersections[0] == intersection);
						const float other_orientation = other_forwards ? other_segment.m_Orientation : reverseAngle(other_segment.m_Orientation);
						float delta_angle = angleDiff(orientation, other_orientation);
						if (delta_angle < m_Analysis.m_AngleThresholdDegrees)
							delta_angle = 0.0f;

						const float acc_angle = state.m_AccAngle + delta_angle;
						if (acc_angle > m_Analysis.m_Radius.m_Angle)
							continue;

						const unsigned int delta_angle_descr = GetDiscreteAngle(delta_angle);
						const unsigned int acc_angle_descr = state.m_AccumulatedAngle + delta_angle_descr;

						m_Queue.Insert(acc_angle_descr,
							STraversalState(
							other_segment_index,
							other_forwards,
							acc_angle_descr,
							SegmentStateIndex(state.m_SegmentIndex, state.m_Forwards),
							acc_walking,
							acc_angle,
							state.m_AccSteps + 1));
					}
				}
			}
		}
	}

	void CollectScores(unsigned int segment_index, bool forwards, unsigned int origin_segment_index)
	{
		const auto& segment = GetGraph().GetSegment(segment_index);
		SSegmentState& segment_state = SegmentState(segment_index, forwards);
		const SSegmentState& opposite_segment_state = SegmentState(segment_index, !forwards);

		ASSERT(-1.0f == segment_state.m_Score);
		segment_state.m_Score = 0;

		if (const auto* intersection = segment.m_Intersections[forwards ? 1 : 0])
		{
			for (unsigned int i = 0; i < intersection->m_NumSegments; ++i)
			{
				if (!segment_state.IsOutSegmentBitSet(i))
					continue;
				const unsigned int other_segment_index = intersection->m_Segments[i];
				const auto& other_segment = GetGraph().GetSegment(other_segment_index);
				const bool other_forwards = (other_segment.m_Intersections[0] == intersection);
				SSegmentState& other_segment_state = SegmentState(other_segment_index, other_forwards);
				if (other_segment_state.m_Score < 0.0f)
					CollectScores(other_segment_index, other_forwards, origin_segment_index);
				segment_state.m_Score += other_segment_state.m_Score / other_segment_state.m_NumShortestPathsToThisSegment;
			}
		}

		m_Scores[segment_index] += segment_state.m_Score;

		const unsigned int opposite_lowest_angle = opposite_segment_state.m_Processed ? opposite_segment_state.m_LowestAngle : 0xFFFFFFFF;
		if (segment_state.m_LowestAngle <= opposite_lowest_angle)
		{
			float state_score = m_Analysis.IsWeighByLength() ? (segment.m_Length * GetGraph().GetSegment(origin_segment_index).m_Length) : 1.0f;
			if (segment_state.m_LowestAngle == opposite_lowest_angle)
			{
				const int total_shortest_paths_to_segment = segment_state.m_NumShortestPathsToThisSegment + opposite_segment_state.m_NumShortestPathsToThisSegment;
				ASSERT(total_shortest_paths_to_segment > 0);
				state_score *= (float)segment_state.m_NumShortestPathsToThisSegment / total_shortest_paths_to_segment;
			}

			segment_state.m_Score += state_score;

			if (m_Analysis.IsWeighByLength() && segment_index != origin_segment_index)
			{
				// When calculating weighted Choice the destination segments DO get a score, but only
				// half the score that a segment between origin and destination get (Turner 2007, page 544).
				m_Scores[segment_index] += state_score * 0.5f;
			}
		}
	}

	void ClearProcessedFlags(unsigned int segment_index)
	{
		ClearProcessedFlags(segment_index, false);
		ClearProcessedFlags(segment_index, true);
	}

	void ClearProcessedFlags(unsigned int segment_index, bool forwards)
	{
		SSegmentState& segment_state = SegmentState(segment_index, forwards);
		if (!segment_state.m_Processed)
			return;
		segment_state.m_Processed = false;
		const auto& segment = GetGraph().GetSegment(segment_index);
		if (const auto* intersection = segment.m_Intersections[forwards ? 1 : 0])
		{
			for (unsigned int i = 0; i < intersection->m_NumSegments; ++i)
			{
				if (!segment_state.IsOutSegmentBitSet(i))
					continue;
				const unsigned int other_segment_index = intersection->m_Segments[i];
				const auto& other_segment = GetGraph().GetSegment(other_segment_index);
				const bool other_forwards = (other_segment.m_Intersections[0] == intersection);
				ClearProcessedFlags(other_segment_index, other_forwards);
			}
		}
	}

};

CAngularChoiceAlgo::CAngularChoiceAlgo()
	: m_Graph(nullptr)
	, m_WeighByLength(false)
	, m_AngleThresholdDegrees(0)
	, m_AnglePrecisionDegrees(0)
	, m_NodeCounts(nullptr)
	, m_TotalDepths(nullptr)
	, m_TotalWeights(nullptr)
	, m_TotalDepthWeights(nullptr)
{
	using namespace std;
	
	#ifdef USE_MULTIPLE_CORES
		m_Workers.resize(max(std::thread::hardware_concurrency(), 1u));
	#else
		m_Workers.resize(1);
	#endif

	for (auto& worker : m_Workers)
		worker.reset(new CWorker(*this));
}

CAngularChoiceAlgo::~CAngularChoiceAlgo()
{
}

bool CAngularChoiceAlgo::Run(
	CSegmentGraph& graph,
	EMode mode,
	const SPSTARadii& radii,
	bool weigh_by_length,
	float angle_threshold,
	unsigned int angle_precision,
	float* ret_choice,
	unsigned int* ret_node_counts,
	float* ret_total_depths,
	float* ret_total_weights,
	float* ret_total_depth_weights,
	IProgressCallback& progress)
{
	using namespace std;

	m_Graph = &graph;
	m_Mode = mode;

	// TODO: Consider making this part of EPSTARadii
	m_Radius.m_StraightLineSqr = radii.HasStraight() ? radii.m_Straight*radii.m_Straight : std::numeric_limits<float>::infinity();
	m_Radius.m_Walking =         radii.HasWalking() ?  radii.m_Walking : std::numeric_limits<float>::infinity();
	m_Radius.m_Angle =           radii.HasAngular() ?  radii.m_Angular : std::numeric_limits<float>::infinity();
	m_Radius.m_Steps =           radii.HasSteps() ?    radii.m_Steps : 0xFFFFFFFF;

	m_WeighByLength = weigh_by_length;
	m_AngleThresholdDegrees = angle_threshold;
	m_AnglePrecisionDegrees = angle_precision;
	m_NodeCounts = ret_node_counts;
	m_TotalDepths = ret_total_depths;
	m_TotalWeights = ret_total_weights;
	m_TotalDepthWeights = ret_total_depth_weights;

	std::atomic<unsigned int> num_processed_segments(0);

	VERIFY(num_processed_segments.is_lock_free());

	const unsigned int segments_per_worker = (unsigned int)(graph.GetSegmentCount() / m_Workers.size()) + 1;

	std::vector<std::future<void>> tasks;
	tasks.reserve(m_Workers.size());

	for (unsigned int worker_index = 0; worker_index < m_Workers.size(); ++worker_index)
	{
		const unsigned int first_segment_to_process = (segments_per_worker * worker_index);
		const int num_segments_to_process = min((int)graph.GetSegmentCount() - (int)first_segment_to_process, (int)segments_per_worker);
		if (num_segments_to_process <= 0)
			break;
		tasks.push_back(std::async(
			std::launch::async,
			&CWorker::Run,
			m_Workers[worker_index].get(),
			first_segment_to_process,
			num_segments_to_process,
			std::ref(num_processed_segments)));
	}

	// Loop through tasks and wait for each one to finish
	for (size_t task_index = 0; task_index < tasks.size(); ++task_index)
	{
		auto& task = tasks[task_index];

		// Wait for task to finish, and update progress every 100ms
		while (std::future_status::ready != task.wait_for(std::chrono::milliseconds(100)))
		{
			progress.ReportProgress((float)num_processed_segments.load() / graph.GetSegmentCount());
		}

		// Update progress
		progress.ReportProgress((float)num_processed_segments.load() / graph.GetSegmentCount());
	}

	if (ret_choice)
	{
		// Accumulate scores from all workers.
		// We iterate over lines first and workers second, even though this
		// is likely to be less cache efficient, in favor of precision.
		for (unsigned int line_index = 0; line_index < graph.GetSegmentCount(); ++line_index)
		{
			double score = 0;
			for (size_t task_index = 0; task_index < tasks.size(); ++task_index)
				score += m_Workers[task_index]->GetSegmentScores()[line_index];
			ret_choice[line_index] = (float)score;
		}
	}

	// Verify that all segments were processed
	if (num_processed_segments.load() != graph.GetSegmentCount())
	{
		// Failed
		LOG_ERROR("Network Sequential Choice algorithm failed (all segments were not processed!?).");
		return false;
	}

	progress.ReportProgress(1.f);

	return true;
}