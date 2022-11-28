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

#pragma once

#include <memory>
#include <vector>
#include <pstalgo/analyses/Common.h>

class CSegmentGraph;
class IProgressCallback;

class CAngularChoiceAlgo
{
public:
	enum EMode
	{
		EMode_AngularChoice,
		EMode_AngularIntegration,
	};

	CAngularChoiceAlgo();
	~CAngularChoiceAlgo();
	
	/**
	 *  ret_choice:        Either choice or length-weighted choice values (depending on weigh_by_length).
	 *  ret_total_depths:  Sum of either depth or depth*weight (depending on weigh_by_length) of each reached segment.
	 *  ret_total_weights: Sum of weights of all reached segments. NOTE: Weight of ORIGIN segment is NOT INCLUDED. Weight will be 1 or length depending on weigh_by_length.
	 */
	bool Run(
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
		IProgressCallback& progress);

protected:

	bool IsWeighByLength() const { return m_WeighByLength; }

	CSegmentGraph& GetGraph() { return *m_Graph; }

	CSegmentGraph* m_Graph;
	EMode m_Mode;

	struct SRadius
	{
		float m_StraightLineSqr;
		float m_Walking;
		float m_Angle;
		unsigned int m_Steps;
	} m_Radius;
	
	bool         m_WeighByLength;
	float        m_AngleThresholdDegrees;
	unsigned int m_AnglePrecisionDegrees;

	// Per segment stats
	unsigned int* m_NodeCounts;
	float* m_TotalDepths;
	float* m_TotalWeights;
	float* m_TotalDepthWeights;  // SUM(depth*weight) for each reached node

	class CWorker;

	std::vector<std::unique_ptr<CWorker>> m_Workers;

	friend class CWorker;
};