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
#include "../analyses/Common.h"
#include "../analyses/CreateGraph.h"

struct SPSTAFastSegmentBetweennessDesc
{
	// Version
	static const unsigned int VERSION = 2;
	unsigned int m_Version = VERSION;

	HPSTASegmentGraph m_Graph = nullptr;  // Created with a call to PSTACreateSegmentGraph

	// Distance measurement
	unsigned char m_DistanceType = EPSTADistanceType_Angular;  // enum EPSTADistanceType, only ANGULAR supported
	bool m_WeighByLength = false;  // NOT YET SUPPORTED

	// Radius
	SPSTARadii m_Radius;  // Only WALKING supported

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;

	// Output
	// These can either be NULL or pointer to arrays of one element per line
	float*        m_OutBetweenness = nullptr;
	unsigned int* m_OutNodeCount   = nullptr;  // NOT YET SUPPORTED   // Number of reached lines, INCLUDING origin line
	float*        m_OutTotalDepth  = nullptr;  // NOT YET SUPPORTED 
};

PSTADllExport bool PSTAFastSegmentBetweenness(const SPSTAFastSegmentBetweennessDesc* desc);