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

struct SPSTASegmentBetweennessDesc
{
	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version = VERSION;

	// Graph
	HPSTAGraph m_Graph = nullptr;  // Created with a call to PSTACreateGraph

	// Distance measurement
	unsigned char m_DistanceType = EPSTADistanceType_Steps;  // enum EPSTADistanceType

	// Radius
	SPSTARadii m_Radius;

	// Weights (optional)
	float* m_Weights = nullptr;  // Per attraction point (if available), otherwise per segment

	// Attraction points (optional)
	double*      m_AttractionPoints = nullptr;
	unsigned int m_AttractionPointCount = 0;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;

	// Output
	// These can either be NULL or pointer to arrays of one element per line
	float*        m_OutBetweenness = nullptr;
	unsigned int* m_OutNodeCount = nullptr;    // Number of reached lines, INCLUDING origin line
	float*        m_OutTotalDepth = nullptr;
};

// N = number of nodes, INCLUDING origin node
PSTADllExport void PSTABetweennessNormalize(const float* in_values, const unsigned int* node_counts, unsigned int count, float* out_normalized);

PSTADllExport void PSTABetweennessSyntaxNormalize(const float* in_values, const float* total_depths, unsigned int count, float* out_normalized);

PSTADllExport bool PSTASegmentBetweenness(const SPSTASegmentBetweennessDesc* desc);