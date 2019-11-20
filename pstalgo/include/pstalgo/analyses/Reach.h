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

struct SPSTAReachDesc
{
	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version = VERSION;

	// Graph
	HPSTAGraph m_Graph = nullptr;  // Created with a call to PSTACreateGraph

	// Radius
	SPSTARadii m_Radius;

	// Origin points (optional)
	double2*     m_OriginCoords = nullptr;
	unsigned int m_OriginCount = 0;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;

	// Output
	// These can either be NULL or pointer to arrays of one element per origin (point or line)
	unsigned int* m_OutReachedCount  = nullptr;  // Number of reached lines, INCLUDING origin line
	float*        m_OutReachedLength = nullptr;
	float*        m_OutReachedArea   = nullptr;  // Square meters
};

PSTADllExport bool PSTAReach(const SPSTAReachDesc* desc);