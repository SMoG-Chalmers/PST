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

#include <pstalgo/pstalgo.h>
#include "Common.h"
#include "CreateGraph.h"

struct SPSTAAngularChoiceDesc
{
	SPSTAAngularChoiceDesc();

	// Version
	static const unsigned int VERSION = 2;
	unsigned int m_Version;

	// Graph
	HPSTASegmentGraph m_Graph;  // Created with a call to PSTACreateSegmentGraph

	// Radius
	SPSTARadii m_Radius;

	// Settings
	bool m_WeighByLength;
	float m_AngleThreshold;
	unsigned int m_AnglePrecision;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;

	// Output
	// These can either be NULL or pointer to arrays of one element per line
	float*        m_OutChoice;
	unsigned int* m_OutNodeCount;        // Number of reached lines, INCLUDING origin line
	float*        m_OutTotalDepth;       // SUM(depth) for reached nodes
	float*        m_OutTotalDepthWeight; // SUM(depth*weight) for reached nodes
};

PSTADllExport bool PSTAAngularChoice(const SPSTAAngularChoiceDesc* desc);

// Normalization (Turner 2007)
// N = number of reached nodes, including origin node
PSTADllExport void PSTAAngularChoiceNormalize(const float* in_scores, const unsigned int* N, unsigned int count, float* out_normalized_score);

// Syntax Normalization (NACH)
// TD = total depth
PSTADllExport void PSTAAngularChoiceSyntaxNormalize(const float* in_scores, const float* TD, unsigned int count, float* out_normalized_score);


