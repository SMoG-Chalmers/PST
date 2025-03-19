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

struct SPSTAAttractionDistanceDesc
{
	PSTA_DECL_STRUCT_NAME(SPSTAAttractionDistanceDesc)

	// Version
	static const unsigned int VERSION = 3;
	const unsigned int m_Version = VERSION;

	// Graph
	HPSTAGraph m_Graph = nullptr;  // Created with a call to PSTACreateGraph

	unsigned char m_OriginType = EPSTAOriginType_Lines;  // enum EOriginType

	// Distance measurement
	unsigned char m_DistanceType = EPSTADistanceType_Steps;  // enum EPSTADistanceType

	// Radius
	SPSTARadii m_Radius;

	// Attraction points
	double2*     m_AttractionPoints = nullptr;
	unsigned int m_AttractionPointCount = 0;

	// Attraction Polygons (optional)
	// If not NULL this means m_AttractionPoints should be treated as polygon 
	// corners, and the actual attraction points will be generated at every
	// 'm_AttractionPolygonPointInterval' interval along polygon edges.
	unsigned int* m_PointsPerAttractionPolygon = nullptr;  // Polygons will be closed automatically, start/end point should NOT be repeated
	unsigned int  m_AttractionPolygonCount = 0;
	float         m_AttractionPolygonPointInterval = 0;

	// Line weights (custom distance values)
	const float* m_LineWeights = nullptr;
	unsigned int m_LineWeightCount = 0;
	float m_WeightPerMeterForPointEdges = 0;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;

	// Output
	// Pointer to array of one element per input object (specified by m_OriginType)
	float* m_OutMinDistance = nullptr;
	unsigned int m_OutputCount = 0;  // For m_OutMinDistance array size verification only
};

PSTADllExport bool PSTAAttractionDistance(const SPSTAAttractionDistanceDesc* desc);