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

#pragma once

#include <pstalgo/pstalgo.h>
#include "Common.h"
#include "CreateGraph.h"

struct SPSTAAngularIntegrationDesc
{
	// Version
	static const unsigned int VERSION = 2;
	unsigned int m_Version = VERSION;

	// Graph
	HPSTASegmentGraph m_Graph = nullptr;  // Created with a call to PSTACreateSegmentGraph

	// Radius
	SPSTARadii m_Radius;

	// Settings
	bool  m_WeighByLength = false;
	float m_AngleThreshold = 0;
	unsigned int m_AnglePrecision = 1;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;

	// Output
	// These can either be NULL or pointer to arrays of one element per line
	unsigned int* m_OutNodeCounts        = nullptr;  // Number of reached lines, INCLUDING origin line
	float*        m_OutTotalDepths       = nullptr;  // SUM(depth) for each reached lines
	float*        m_OutTotalWeights      = nullptr;  // SUM(weight) for each reached lines
	float*        m_OutTotalDepthWeights = nullptr;  // SUM(depth*weight) for each reached lines
};

PSTADllExport bool PSTAAngularIntegration(const SPSTAAngularIntegrationDesc* desc);

// Normalization (Turner 2007)
// N = number of reached nodes INCLUDING origin node
// TD = total depth
// reached_length = sum of lengths of all reached nodes
PSTADllExport void PSTAAngularIntegrationNormalize(const unsigned int* N, const float *TD, unsigned int count, float* out_normalized_score);
PSTADllExport void PSTAAngularIntegrationNormalizeLengthWeight(const float* reached_length, const float *TD, unsigned int count, float* out_normalized_score);

// Syntax Normalization (NAIN)
// N = number of reached nodes INCLUDING origin node
// TD = total depth
// reached_length = sum of lengths of all reached nodes
PSTADllExport void PSTAAngularIntegrationSyntaxNormalize(const unsigned int* N, const float* TD, unsigned int count, float* out_normalized_score);
PSTADllExport void PSTAAngularIntegrationSyntaxNormalizeLengthWeight(const float* reached_length, const float* TD, unsigned int count, float* out_normalized_score);