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

struct SPSTAAttractionReachDesc
{
	enum EWeightFunc
	{
		EWeightFunc_Constant,  // y = 1
		EWeightFunc_Pow,       // y = 1 - x^C
		EWeightFunc_Curve,     // y = 1-((2x)^C)/2 0<=x<0.5, ((2-2x)^C)/2 0.5<=x<=1
		EWeightFunc_Divide,    // y = (x+1)^-C
	};

	// TODO: DEPRECATED: Remove
	enum EScoreAccumulationMode
	{
		EScoreAccumulationMode_Sum,
		EScoreAccumulationMode_Max,
	};

	enum EAttractionDistributionFunc
	{
		EAttractionDistributionFunc_Copy,
		EAttractionDistributionFunc_Divide,
	};

	enum EAttractionCollectionFunc
	{
		EAttractionCollectionFunc_Avarage,
		EAttractionCollectionFunc_Sum,
		EAttractionCollectionFunc_Min,
		EAttractionCollectionFunc_Max,
	};

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version = VERSION;

	// Graph
	HPSTAGraph m_Graph = nullptr;  // Created with a call to PSTACreateGraph

	unsigned char m_OriginType = EPSTAOriginType_Lines;  // enum EOriginType

	// Distance measurement
	unsigned char m_DistanceType = EPSTADistanceType_Steps;  // enum EPSTADistanceType

	// Radius
	SPSTARadii m_Radius;

	// Weight Function
	unsigned char m_WeightFunc = EWeightFunc_Constant;  // enum EWeightFunc
	float m_WeightFuncConstant = 0;

	// Score accumulation mode
	EScoreAccumulationMode m_ScoreAccumulationMode = EScoreAccumulationMode_Sum;  // DEPRECATED: TODO: Remove when pstmb also uses the destination region functionality of this analysis

	// Attraction Points
	const double2* m_AttractionPoints = nullptr;
	unsigned int   m_AttractionPointCount = 0;

	// Attraction Polygons (optional)
	// If not NULL this means m_AttractionPoints should be treated as polygon 
	// corners, and the actual attraction points will be generated at every
	// 'm_AttractionPolygonPointInterval' interval along polygon edges.
	unsigned int* m_PointsPerAttractionPolygon = nullptr;  // Polygons will be closed automatically, start/end point should NOT be repeated
	unsigned int  m_AttractionPolygonCount = 0;
	float         m_AttractionPolygonPointInterval = 0;

	// Attraction Values (per polygon if polygons area available, otherwise per point)
	// If NULL then score 1 is assumed for all.
	const float* m_AttractionValues = nullptr;

	// Attraction Distribution Function, only applicable if attraction polygons are available
	unsigned char m_AttractionDistributionFunc = EAttractionDistributionFunc_Divide;  // enum EAttractionDistributionFunc

	// Attraction Collection Function, only applicable if the graph has point groups
	unsigned char m_AttractionCollectionFunc = EAttractionCollectionFunc_Avarage;  // enum EAttractionCollectionFunc

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback = nullptr;
	void*                 m_ProgressCallbackUser = nullptr;

	// Output
	// Pointer to array of one element per input object (specified by m_OriginType)
	float* m_OutScores = nullptr;
	unsigned int m_OutputCount = 0;  // For m_OutScores array size verification only
};

PSTADllExport bool PSTAAttractionReach(const SPSTAAttractionReachDesc* desc);