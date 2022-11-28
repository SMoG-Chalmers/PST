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

#include <pstalgo/analyses/AngularChoice.h>
#include "../ProgressUtil.h"
#include "AngularChoiceAlgo.h"

SPSTAAngularChoiceDesc::SPSTAAngularChoiceDesc()
	: m_Version(VERSION)
	, m_Graph(0)
	, m_WeighByLength(false)
	, m_AngleThreshold(0)
	, m_AnglePrecision(1)
	, m_ProgressCallback(nullptr)
	, m_ProgressCallbackUser(nullptr)
	, m_OutChoice(nullptr)
	, m_OutNodeCount(nullptr)
	, m_OutTotalDepth(nullptr)
	, m_OutTotalDepthWeight(nullptr)
{}

PSTADllExport bool PSTAAngularChoice(const SPSTAAngularChoiceDesc* desc)
{
	CAngularChoiceAlgo algo;
	CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);
	return algo.Run(
		*(CSegmentGraph*)desc->m_Graph,
		CAngularChoiceAlgo::EMode_AngularChoice,
		desc->m_Radius,
		desc->m_WeighByLength,
		desc->m_AngleThreshold,
		desc->m_AnglePrecision,
		desc->m_OutChoice,
		desc->m_OutNodeCount,
		desc->m_OutTotalDepth,
		nullptr,
		desc->m_OutTotalDepthWeight,
		progress);
}

PSTADllExport void PSTAAngularChoiceNormalize(const float* in_scores, const unsigned int* N, unsigned int count, float* out_normalized_score)
{
	for (unsigned int i = 0; i < count; ++i)
		out_normalized_score[i] = (N[i] > 2) ? (in_scores[i] / ((float)(N[i] - 1) * (float)(N[i] - 2))) : in_scores[i];
}

PSTADllExport void PSTAAngularChoiceSyntaxNormalize(const float* in_scores, const float* TD, unsigned int count, float* out_normalized_score)
{
	using namespace std;
	for (unsigned int i = 0; i < count; ++i)
		out_normalized_score[i] = log10(in_scores[i] + 1.0f) / log10(2.0f + TD[i]);
}