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

#include <pstalgo/experimental/SparseDirectedGraph.h>
#include <pstalgo/experimental/FastSegmentBetweenness.h>
#include <pstalgo/experimental/IntPrioQueue.h>
#include <pstalgo/graph/SegmentGraph.h>
#include <pstalgo/system/System.h>
#include <pstalgo/utils/BitVector.h>
#include <pstalgo/utils/Perf.h>
#include <pstalgo/maths.h>
#include <pstalgo/Debug.h>

#include "../ProgressUtil.h"

//#define PERF_ENABLED

#define ENABLE_MULTITHREADING

#define INTEGER_ANGULAR_DISTANCE

namespace psta
{
	namespace
	{
		struct SPredecessorElement
		{
			typedef TSparseDirectedGraph<> graph_t;
			static const unsigned int END = (unsigned int)-1;

			graph_t::HNode m_Predecessor = graph_t::INVALID_HANDLE;
			unsigned int   m_Next = END;

			inline void SetEnd() { m_Next = END; }
			inline bool IsEnd() const { return END != m_Next; }
		};

		struct SNodeData 
		{
			// No node data
		};

		struct SEdgeData
		{
			#ifdef INTEGER_ANGULAR_DISTANCE
				// 4 bytes
				unsigned short m_PrimaryDist;  // Angle degrees
				unsigned short m_RadiusDist;   // Walking meters
			#else
				// 8 bytes
				float m_PrimaryDist;  // Angle degrees
				float m_RadiusDist;   // Walking meters
			#endif
		};
	}

	typedef TSparseDirectedGraph<SNodeData, SEdgeData> CSegmentBetweennessGraph;

	CSegmentBetweennessGraph CreateSegmentBetweennessGraph(const CSegmentGraph& seg_graph)
	{
		CSegmentBetweennessGraph graph;

		// Allocate nodes
		graph.ReserveNodeCount(seg_graph.GetSegmentCount() * 2);
		for (unsigned int i = 0; i < seg_graph.GetSegmentCount(); ++i)
		{
			for (auto* intersection : seg_graph.GetSegment(i).m_Intersections)
			{
				const unsigned int edge_count = intersection ? intersection->m_NumSegments - 1 : 0;
				graph.NewNode(edge_count);
			}
		}

		// Create edges
		unsigned int node_index = 0;
		for (unsigned int segment_index = 0; segment_index < seg_graph.GetSegmentCount(); ++segment_index)
		{
			auto& segment = seg_graph.GetSegment(segment_index);
			for (auto* intersection : segment.m_Intersections)
			{
				auto& node = graph.Node(graph.NodeHandleFromIndex(node_index));
				//node.m_OppositeNode = node_handles[node_index ^ 0x00000001];

				if (intersection)
				{
					const bool src_forwards = (intersection == segment.m_Intersections[1]);
					unsigned int edge_index = 0;
					for (unsigned int i = 0; i < intersection->m_NumSegments; ++i)
					{
						const auto dst_segment_index = intersection->m_Segments[i];
						if (dst_segment_index == segment_index)
							continue;
						auto& dst_segment = seg_graph.GetSegment(dst_segment_index);
						const bool dst_forwards = (dst_segment.m_Intersections[0] == intersection);
						unsigned int dst_node_index = (dst_segment_index * 2) + (dst_forwards ? 1 : 0);
						auto& edge = node.Edge(edge_index++);
						edge.SetTarget(graph.NodeHandleFromIndex(dst_node_index), dst_node_index);
						const auto src_orientation = src_forwards ? segment.m_Orientation : reverseAngle(segment.m_Orientation);
						const auto dst_orientation = dst_forwards ? dst_segment.m_Orientation : reverseAngle(dst_segment.m_Orientation);
						const auto angle_diff = angleDiff(src_orientation, dst_orientation);
						#ifdef INTEGER_ANGULAR_DISTANCE
							edge.m_PrimaryDist = (unsigned short)(angle_diff + .5f);
						#else
							edge.m_PrimaryDist = angle_diff;
						#endif
						edge.m_RadiusDist = (segment.m_Length + dst_segment.m_Length) * .5f;
					}
				}
				++node_index;
			}
		}

		return graph;
	}

	class CSegmentBetweennessWorkerContext
	{
	public:
		CSegmentBetweennessWorkerContext(unsigned int segment_count, IProgressCallback& progress_callback) : m_ProgressCallback(progress_callback), m_SegmentIndex(0), m_SegmentCount(segment_count) {}

		// Called by workers to get next node to process
		bool DequeueSegment(unsigned int& ret_segment_index)
		{
			ret_segment_index = m_SegmentIndex++;
			if (ret_segment_index >= m_SegmentCount)
				return false;
			m_ProgressCallback.ReportProgress((float)ret_segment_index / m_SegmentCount);
			return !m_ProgressCallback.GetCancel();
		}

	private:
		IProgressCallback& m_ProgressCallback;
		std::atomic<unsigned int> m_SegmentIndex;
		unsigned int m_SegmentCount;
	};

	class CSegmentBetweennessWorker
	{
	public:
		typedef CSegmentBetweennessGraph graph_t;

		CSegmentBetweennessWorker();

		void Run(CSegmentBetweennessWorkerContext& ctx, const graph_t& graph, const SPSTARadii& limits);

		const std::vector<double>& Scores() const { return m_Scores; }

		void LogPerfCounters() const;

	private:
		struct SQueueElement
		{
			float            m_PrimaryDistance;
			float            m_RadiusDistance;
			graph_t::HNode   m_NodeHandle;
			unsigned int     m_NodeIndex;
			unsigned int     m_PrevNodeIndex;

			operator unsigned int() const { return (unsigned int)(m_PrimaryDistance + .5f); }

			inline bool operator<(const SQueueElement& rhs) const { return m_PrimaryDistance > rhs.m_PrimaryDistance; }
		};

		struct SNodeState
		{
			SNodeState() { Reset(); }

			inline void Reset()
			{
				m_ShortestDistance = std::numeric_limits<float>::infinity();
				m_Accumulator = 0;
				m_PredecessorListHead = -1;
			}

			float m_ShortestDistance;
			float m_Accumulator;
			unsigned int m_PredecessorListHead;
		};

		template <class TLambda> void ForEachPredecessor(const SNodeState& node_data, TLambda&& lambda) const;
		unsigned int PredecessorCount(const SNodeState& node_data) const;
		void AddPredecessor(SNodeState& node_data, graph_t::HNode pred);

		void ProcessSegment(const graph_t& graph, graph_t::index_t origin_segment_index);

		enum EPerfCounters
		{
			EPerfCounter_QueueMax,
			EPerfCounter_QueueTicks,
			EPerfCounter_TraversalTicks,
			EPerfCounter_CollectTicks,
			EPerfCounter_NUM,
		};

		#ifdef INTEGER_ANGULAR_DISTANCE
			psta::int_prio_queue<SQueueElement> m_Queue;
		#else
			std::priority_queue<SQueueElement> m_Queue;
		#endif

		SPSTARadii m_Limits;
		std::vector<SNodeState> m_NodeStates;
		std::vector<SPredecessorElement> m_Predecessors;
		std::vector<graph_t::HNode> m_VisitedNodesStack;
		std::vector<double> m_Scores;

		unsigned long long m_PerfCounters[EPerfCounter_NUM];
	};

	CSegmentBetweennessWorker::CSegmentBetweennessWorker()
	{
		memset(m_PerfCounters, 0, sizeof(m_PerfCounters));
	}

	void CSegmentBetweennessWorker::Run(CSegmentBetweennessWorkerContext& ctx, const graph_t& graph, const SPSTARadii& limits)
	{
		CLowerThreadPrioInScope _lower_prio_scope;

		m_Limits = limits;

		const auto node_count = graph.NodeCount();
		const auto segment_count = node_count / 2;

		m_Scores.clear();
		m_Scores.resize(segment_count, 0.0);

		m_NodeStates.resize(node_count);

		m_Predecessors.reserve(node_count / 4);  // Guess

		unsigned int segment_index;
		while (ctx.DequeueSegment(segment_index))
			ProcessSegment(graph, segment_index);
	}

	void CSegmentBetweennessWorker::LogPerfCounters() const
	{
		pstdbg::Log(
			pstdbg::EErrorLevel_Info,
			nullptr,
			"Queue max: %d\n"
			"Queue:     %.3f\n"
			"Traversal: %.3f\n"
			"Collect:   %.3f",
			(unsigned int)m_PerfCounters[EPerfCounter_QueueMax],
			CPerfTimer::SecondsFromTicks(m_PerfCounters[EPerfCounter_QueueTicks]),
			CPerfTimer::SecondsFromTicks(m_PerfCounters[EPerfCounter_TraversalTicks]),
			CPerfTimer::SecondsFromTicks(m_PerfCounters[EPerfCounter_CollectTicks]));
	}

	template <class TLambda> void CSegmentBetweennessWorker::ForEachPredecessor(const SNodeState& node_data, TLambda&& lambda) const
	{
		if ((unsigned int)-1 == node_data.m_PredecessorListHead)
			return;

		if (!(0x80000000 & node_data.m_PredecessorListHead))
		{
			lambda(node_data.m_PredecessorListHead);
			return;
		}

		auto* p = &m_Predecessors[node_data.m_PredecessorListHead & 0x7FFFFFFF];
		for (;;)
		{
			lambda(p->m_Predecessor);
			if (!p->IsEnd())
				break;
			p = &m_Predecessors[p->m_Next];
		}
	}

	unsigned int CSegmentBetweennessWorker::PredecessorCount(const SNodeState& node_data) const
	{
		unsigned int predecessor_count = 0;
		ForEachPredecessor(node_data, [&predecessor_count](graph_t::HNode) { ++predecessor_count; });
		return predecessor_count;
	}

	void CSegmentBetweennessWorker::AddPredecessor(SNodeState& node_data, graph_t::HNode pred)
	{
		if ((unsigned int)-1 == node_data.m_PredecessorListHead)
		{
			node_data.m_PredecessorListHead = pred;
			return;
		}

		if (!(0x80000000 & node_data.m_PredecessorListHead))
		{
			m_Predecessors.resize(m_Predecessors.size() + 1);
			m_Predecessors.back().m_Predecessor = node_data.m_PredecessorListHead;
			m_Predecessors.back().SetEnd();
			node_data.m_PredecessorListHead = ((unsigned int)m_Predecessors.size() - 1) | 0x80000000;
		}

		m_Predecessors.resize(m_Predecessors.size() + 1);
		m_Predecessors.back().m_Predecessor = pred;
		m_Predecessors.back().m_Next = node_data.m_PredecessorListHead & 0x7FFFFFFF;

		node_data.m_PredecessorListHead = ((unsigned int)m_Predecessors.size() - 1) | 0x80000000;
	}

	void CSegmentBetweennessWorker::ProcessSegment(const graph_t& graph, graph_t::index_t origin_segment_index)
	{
		m_Predecessors.clear();

		SQueueElement qe;

		// Enqueue forward node for origin segment
		qe.m_PrimaryDistance = 0;
		qe.m_RadiusDistance = 0;
		qe.m_NodeIndex = origin_segment_index << 1;
		qe.m_NodeHandle = graph.NodeHandleFromIndex(qe.m_NodeIndex);
		qe.m_PrevNodeIndex = (unsigned int)-1;
		m_Queue.push(qe);

		// Enqueue backward node for origin segment
		qe.m_NodeIndex++;
		qe.m_NodeHandle = graph.NodeHandleFromIndex(qe.m_NodeIndex);
		m_Queue.push(qe);

		#ifdef PERF_ENABLED
			CPerfTimer perf_timer;
			perf_timer.Start();
		#endif

		while (!m_Queue.empty())
		{
			const auto qe = m_Queue.top();
			m_Queue.pop();

			#ifdef PERF_ENABLED
				m_PerfCounters[EPerfCounter_QueueTicks] += perf_timer.ReadAndRestart();
			#endif

			auto& state = m_NodeStates[qe.m_NodeIndex];
			
			if (qe.m_PrimaryDistance > state.m_ShortestDistance)
				continue;  // A shorter path has already been found to this node

			if (std::numeric_limits<float>::infinity() == state.m_ShortestDistance)
			{
				const auto& node = graph.Node(qe.m_NodeHandle);

				// First time this node is reached
				state.m_ShortestDistance = qe.m_PrimaryDistance;
				m_VisitedNodesStack.push_back(node.Index());

				// Process edges
				SQueueElement next_qe;
				next_qe.m_PrevNodeIndex = node.Index();
				for (unsigned int edge_index = 0; edge_index < node.EdgeCount(); ++edge_index)
				{
					const auto& edge = node.Edge(edge_index);

					next_qe.m_RadiusDistance = qe.m_RadiusDistance + edge.m_RadiusDist;
					if (next_qe.m_RadiusDistance > m_Limits.Walking())
						continue;
					next_qe.m_PrimaryDistance = qe.m_PrimaryDistance + edge.m_PrimaryDist;

					// Check if target already has shorter distance before queueing
					if (m_NodeStates[graph.TargetIndex(edge)].m_ShortestDistance < next_qe.m_PrimaryDistance)
						continue;

					next_qe.m_NodeHandle = edge.TargetHandle();
					next_qe.m_NodeIndex = graph.TargetIndex(edge);

					#ifdef PERF_ENABLED
						m_PerfCounters[EPerfCounter_TraversalTicks] += perf_timer.ReadAndRestart();
					#endif

					m_Queue.push(next_qe);

					#ifdef PERF_ENABLED
						m_PerfCounters[EPerfCounter_QueueMax] = std::max((size_t)m_PerfCounters[EPerfCounter_QueueMax], m_Queue.size());
						m_PerfCounters[EPerfCounter_QueueTicks] += perf_timer.ReadAndRestart();
					#endif
				}
			}
			else
			{
				// A new path was found to this node with same shortest distance
				ASSERT(qe.m_PrimaryDistance == state.m_ShortestDistance);
			}

			if ((unsigned int)-1 != qe.m_PrevNodeIndex)
				AddPredecessor(state, qe.m_PrevNodeIndex);

			#ifdef PERF_ENABLED
				m_PerfCounters[EPerfCounter_TraversalTicks] += perf_timer.ReadAndRestart();
			#endif
		}

		// Traverse list of visited nodes in reverse order
		while (!m_VisitedNodesStack.empty()) 
		{
			const auto node_index = m_VisitedNodesStack.back();
			m_VisitedNodesStack.pop_back();

			auto& state = m_NodeStates[node_index];

			const auto segment_index = node_index >> 1;

			if (segment_index != origin_segment_index)
			{
				// NOTE: We only add half the score because the algorithm counts each path twice - once for each direction.
				m_Scores[segment_index] += state.m_Accumulator * .5f;

				const auto opposite_node_index = node_index ^ 1;
				const auto& opposite_state = m_NodeStates[opposite_node_index];

				float score_to_pass_on = state.m_Accumulator;
				if (state.m_ShortestDistance < opposite_state.m_ShortestDistance)
					score_to_pass_on += 1.f;

				const auto predecessor_count = PredecessorCount(state);
				if (predecessor_count)
				{
					ForEachPredecessor(state, [&](unsigned int pred_index)
					{
						auto& pred = m_NodeStates[pred_index];
						pred.m_Accumulator += (1.f / predecessor_count) * score_to_pass_on;
					});
				}
			}

			// Reset temporary traversal state on node
			state.Reset();
		}

		#ifdef PERF_ENABLED
			m_PerfCounters[EPerfCounter_CollectTicks] += perf_timer.ReadAndRestart();
		#endif
	}

	void Apa(const CSegmentGraph& seg_graph, const SPSTARadii& radii, float* out_scores, IProgressCallback& progress_callback)
	{
		#ifdef PERF_ENABLED
				CPerfTimer perf_timer;
				perf_timer.Start();
		#endif

		#ifdef ENABLE_MULTITHREADING
			static const auto WORKER_COUNT = std::max(std::thread::hardware_concurrency(), 1u);
		#else
			static const auto WORKER_COUNT = 1;
		#endif

		const auto graph = psta::CreateSegmentBetweennessGraph(seg_graph);

		std::vector<std::future<void>> tasks;
		tasks.reserve(WORKER_COUNT);

		CSegmentBetweennessWorkerContext ctx(seg_graph.GetSegmentCount(), progress_callback);

		std::vector<std::unique_ptr<CSegmentBetweennessWorker>> workers(WORKER_COUNT);
		for (size_t i = 0; i < WORKER_COUNT; ++i)
		{
			workers[i] = std::make_unique<CSegmentBetweennessWorker>();
			tasks.push_back(std::async(
				std::launch::async,
				&CSegmentBetweennessWorker::Run,
				workers[i].get(),
				std::ref(ctx), 
				std::ref(graph), 
				std::ref(radii)));
		}

		for (auto& task : tasks)
			task.wait();

		memset(out_scores, 0, seg_graph.GetSegmentCount() * sizeof(float));

		for (auto& w : workers)
		{
			const auto& scores = w->Scores();
			ASSERT(scores.size() == seg_graph.GetSegmentCount());
			for (unsigned int i = 0; i < seg_graph.GetSegmentCount(); ++i)
				out_scores[i] += (float)scores[i];
		}

		#ifdef PERF_ENABLED
			pstdbg::Log(pstdbg::EErrorLevel_Info, nullptr, "FastSegmentBetweenness performed in %.3f sec.", CPerfTimer::SecondsFromTicks(perf_timer.ReadAndRestart()));
			workers.front()->LogPerfCounters();
		#endif
	}
}

PSTADllExport bool PSTAFastSegmentBetweenness(const SPSTAFastSegmentBetweennessDesc* desc)
{
	auto& seg_graph = *(const CSegmentGraph*)desc->m_Graph;

	CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

	psta::Apa(seg_graph, desc->m_Radius, desc->m_OutBetweenness, progress);

	return true;
}