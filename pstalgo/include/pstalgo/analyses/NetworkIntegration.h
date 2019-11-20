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

struct SPSTANetworkIntegrationDesc
{
	SPSTANetworkIntegrationDesc();

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	// Graph
	HPSTAGraph m_Graph;  // Created with a call to PSTACreateGraph

	// Radius
	SPSTARadii m_Radius;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;

	// Output per Junction (optional)
	double2*     m_OutJunctionCoords;
	float*       m_OutJunctionScores;
	unsigned int m_OutJunctionCount;

	// Output per Line (optional)
	float*        m_OutLineIntegration;
	unsigned int* m_OutLineNodeCount;    // Number of reached lines, INCLUDING origin line
	float*        m_OutLineTotalDepth;
};

float CalculateIntegrationScore(unsigned int N, float TD);

PSTADllExport bool PSTANetworkIntegration(const SPSTANetworkIntegrationDesc* desc);