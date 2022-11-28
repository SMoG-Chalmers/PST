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

#include <pstalgo/analyses/AngularIntegration.h>
#include "../ProgressUtil.h"
#include "AngularChoiceAlgo.h"

PSTADllExport bool PSTAAngularIntegration(const SPSTAAngularIntegrationDesc* desc)
{
	CAngularChoiceAlgo algo;
	CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);
	return algo.Run(
		*(CSegmentGraph*)desc->m_Graph,
		CAngularChoiceAlgo::EMode_AngularIntegration,
		desc->m_Radius,
		desc->m_WeighByLength,
		desc->m_AngleThreshold,
		desc->m_AnglePrecision,
		nullptr,
		desc->m_OutNodeCounts,
		desc->m_OutTotalDepths,
		desc->m_OutTotalWeights,
		desc->m_OutTotalDepthWeights,
		progress);
}

PSTADllExport void PSTAAngularIntegrationNormalize(const unsigned int* N, const float *TD, unsigned int count, float* out_normalized_score)
{
	for (unsigned int i = 0; i < count; ++i)
		out_normalized_score[i] = (float)(N[i] - 1) / (1.0f + TD[i]);
}

PSTADllExport void PSTAAngularIntegrationNormalizeLengthWeight(const float* reached_length, const float *TDL, unsigned int count, float* out_normalized_score)
{
	for (unsigned int i = 0; i < count; ++i)
		out_normalized_score[i] = reached_length[i] / (1.0f + TDL[i]);
}

PSTADllExport void PSTAAngularIntegrationSyntaxNormalize(const unsigned int* N, const float* TD, unsigned int count, float* out_normalized_score)
{
	for (unsigned int i = 0; i < count; ++i)
		out_normalized_score[i] = std::pow((float)N[i], 1.2f) / (TD[i] + 1.0f);
}

PSTADllExport void PSTAAngularIntegrationSyntaxNormalizeLengthWeight(const float* reached_length, const float* TDL, unsigned int count, float* out_normalized_score)
{
	for (unsigned int i = 0; i < count; ++i)
		out_normalized_score[i] = std::pow(reached_length[i], 1.2f) / (TDL[i] + 1.0f);
}

PSTADllExport void PSTAAngularIntegrationHillierNormalize(const unsigned int* N, const float* TD, unsigned int count, float* out_normalized_score)
{
	for (unsigned int i = 0; i < count; ++i)
		out_normalized_score[i] = (float)N[i]*(float)N[i] / (TD[i] + 1.0f);
}

PSTADllExport void PSTAAngularIntegrationHillierNormalizeLengthWeight(const float* reached_length, const float* TDL, unsigned int count, float* out_normalized_score)
{
	for (unsigned int i = 0; i < count; ++i)
		out_normalized_score[i] = reached_length[i]*reached_length[i] / (TDL[i] + 1.0f);
}