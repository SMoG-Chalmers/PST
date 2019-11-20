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

struct SPSTASegmentGroupingDesc
{
	SPSTASegmentGroupingDesc();

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	// Graph
	HPSTASegmentGraph m_SegmentGraph;  // Created with a call to PSTACreateGraph

	// Parameters
	float m_AngleThresholdDegrees;  // [0..90]
	bool  m_SplitGroupsAtJunctions;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;

	unsigned int  m_LineCount;  // For verification of output array sizes

	// Output
	unsigned int* m_OutGroupIdPerLine;
	unsigned int  m_OutGroupCount;  // Will contain number of groups created on return
	unsigned int* m_OutColorPerLine;
	unsigned int  m_OutColorCount;  // Will contain number of colors used for coloring
};

PSTADllExport bool PSTASegmentGrouping(SPSTASegmentGroupingDesc* desc);