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

#include <pstalgo/analyses/NetworkIntegration.h>
#include <pstalgo/BFS.h>
#include <pstalgo/utils/BitVector.h>
#include <pstalgo/Debug.h>
#include <pstalgo/Limits.h>
#include <pstalgo/graph/AxialGraph.h>
#include "../ProgressUtil.h"

// N  = Number of reached nodes INCLUDING origin node
// TD = Total depth
float CalculateIntegrationScore(unsigned int N, float TD)
{
	if (N < 2)
		return -1;
	const float MD = TD / (float)(N - 1);
	const float RA = 2.0f * (MD - 1.0f) / (N - 2);
	const float D = 2.0f * ((log(2.0f, (float)(N + 2) / 3) - 1.0f) * N + 1.0f) / ((N - 1)*(N - 2));
	const float RRA = RA / D;
	return 1.0f / RRA;
}

namespace
{
	class CNetworkIntegrationAlgo : public CPSTBFS 
	{
		typedef CPSTBFS super_t;
	public:
		void Run(CAxialGraph& graph, const LIMITS& limits, float* ret_integration_scores, unsigned int* ret_node_counts, float* ret_total_depths, IProgressCallback& progress);

	// Operations
	private:
		void processLine(int iLine);
		void visitBFS(int iTarget, const DIST& dist) override;

		int m_iCurrLine;
		CBitVector m_TargetVisitedBits;

		float*        m_IntegrationScores;
		unsigned int* m_NodeCounts;
		float*        m_TotalDepths;

		unsigned long long m_totalDist;
		int m_nVisitedLines;  // Origin line is NOT INCLUDED in count
	};

	void CNetworkIntegrationAlgo::Run(CAxialGraph& graph, const LIMITS& limits, float* ret_integration_scores, unsigned int* ret_node_counts, float* ret_total_depths, IProgressCallback& progress)
	{
		super_t::init(&graph, TARGET_LINES, DIST_LINES, limits);

		m_TargetVisitedBits.resize(getTargetCount());

		m_IntegrationScores = ret_integration_scores;
		m_NodeCounts = ret_node_counts;
		m_TotalDepths = ret_total_depths;

		for (int i = 0; i < graph.getLineCount(); ++i)
		{
			processLine(i);
			progress.ReportProgress((float)(i + 1) / graph.getLineCount());
		}
	}

	void CNetworkIntegrationAlgo::processLine(int iLine)
	{
		m_totalDist = 0;
		m_nVisitedLines = 0;

		m_iCurrLine = iLine;

		m_TargetVisitedBits.clearAll();

		doBFSFromLine(iLine);

		if (m_NodeCounts)
			m_NodeCounts[iLine] = m_nVisitedLines + 1;

		if (m_TotalDepths)
			m_TotalDepths[iLine] = (float)m_totalDist;

		if (m_IntegrationScores)
		{
			const auto N = m_nVisitedLines + 1;  // N = number of reached nodes INCLUDING origin node
			m_IntegrationScores[iLine] = CalculateIntegrationScore(N, (float)m_totalDist);
		}
	}

	void CNetworkIntegrationAlgo::visitBFS(int iTarget, const DIST& dist)
	{
		if (m_iCurrLine == iTarget || m_TargetVisitedBits.get(iTarget))
			return;
		m_TargetVisitedBits.set(iTarget);
		m_totalDist += dist.turns;
		++m_nVisitedLines;
	}
}

SPSTANetworkIntegrationDesc::SPSTANetworkIntegrationDesc()
: m_Version(VERSION)
, m_Graph(nullptr)
, m_ProgressCallback(nullptr)
, m_ProgressCallbackUser(nullptr)
, m_OutJunctionCoords(nullptr)
, m_OutJunctionScores(nullptr)
, m_OutJunctionCount(0)
, m_OutLineIntegration(nullptr)
, m_OutLineNodeCount(nullptr)
, m_OutLineTotalDepth(nullptr)
{}

PSTADllExport bool PSTANetworkIntegration(const SPSTANetworkIntegrationDesc* desc)
{
	if (desc->VERSION != desc->m_Version)
	{
		LOG_ERROR("Network Integration version mismatch (%d != %d)", desc->m_Version, desc->VERSION);
		return false;
	}

	const CAxialGraph& graph = *(CAxialGraph*)desc->m_Graph;

	float* line_integration_scores = desc->m_OutLineIntegration;
	std::vector<float> line_scores_needed_to_calculate_junction_scores;
	if (nullptr == line_integration_scores && desc->m_OutJunctionScores)
	{
		line_scores_needed_to_calculate_junction_scores.resize(graph.getLineCount());
		line_integration_scores = line_scores_needed_to_calculate_junction_scores.data();
	}

	CNetworkIntegrationAlgo algo;

	CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);
	algo.Run(
		*(CAxialGraph*)desc->m_Graph, 
		LimitsFromSPSTARadii(desc->m_Radius), 
		line_integration_scores,
		desc->m_OutLineNodeCount,
		desc->m_OutLineTotalDepth,
		progress);

	if ((desc->m_OutJunctionCoords || desc->m_OutJunctionScores) && (unsigned int)graph.getCrossingCount() != desc->m_OutJunctionCount)
	{
		LOG_ERROR("Junction count error (%d instead of %s)!", desc->m_OutJunctionCount, graph.getCrossingCount());
		if (desc->m_OutJunctionCoords)
			memset(desc->m_OutJunctionCoords, 0, desc->m_OutJunctionCount * sizeof(desc->m_OutJunctionCoords[0]));
		if (desc->m_OutJunctionScores)
			memset(desc->m_OutJunctionScores, 0, desc->m_OutJunctionCount * sizeof(desc->m_OutJunctionScores[0]));
	}
	else
	{
		if (desc->m_OutJunctionCoords)
		{
			for (int i = 0; i < graph.getCrossingCount(); ++i)
				desc->m_OutJunctionCoords[i] = graph.localToWorld(graph.getCrossing(i).pt);
		}
		if (desc->m_OutJunctionScores)
		{
			ASSERT(line_integration_scores);
			for (int line_index = 0; line_index < graph.getLineCount(); ++line_index)
			{
				const CAxialGraph::NETWORKLINE& line = graph.getLine(line_index);
				for (int lc = 0; lc < line.nCrossings; ++lc)
				{
					const CAxialGraph::LINECROSSING& line_crossing = graph.getLineCrossing(line.iFirstCrossing + lc);
					const CAxialGraph::CROSSING& crossing = graph.getCrossing(line_crossing.iCrossing);
					desc->m_OutJunctionScores[line_crossing.iCrossing] += line_integration_scores[line_index] / crossing.nLines;
				}
			}
		}
	}

	return true;
}
