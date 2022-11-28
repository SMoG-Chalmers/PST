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

struct SPSTAODBetweenness
{
	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version = VERSION;

	// Graph
	HPSTAGraph m_Graph = nullptr;  // Created with a call to PSTACreateGraph

	// Origins
	const double2* m_OriginPoints = nullptr;
	const float*   m_OriginWeights = nullptr;
	unsigned int   m_OriginCount = 0;

	// Destinations (must match points in m_Graph member)
	const float* m_DestinationWeights = nullptr;
	unsigned int m_DestinationCount = 0;

	enum EDestinationMode
	{
		EDestinationMode_AllReachableDestinations = 0,
		EDestinationMode_ClosestDestinationOnly = 1,
	};
	unsigned char m_DestinationMode = EDestinationMode_AllReachableDestinations;

	// Distance measurement
	unsigned char m_DistanceType = EPSTADistanceType_Walking;  // enum EPSTADistanceType

	// Radius
	SPSTARadii m_Radius;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;

	// Output
	// Pointer to array of one element per network element
	float* m_OutScores = nullptr;
	unsigned int m_OutputCount = 0;  // For m_OutScores array size verification only
};

PSTADllExport bool PSTAODBetweenness(const SPSTAODBetweenness* desc);