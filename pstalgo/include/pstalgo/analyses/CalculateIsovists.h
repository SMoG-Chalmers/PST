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


struct SCreateIsovistContextDesc 
{
	PSTA_DECL_STRUCT_NAME(SCreateIsovistContextDesc)
		
	struct SPolygons
	{
		uint32_t  GroupCount;
		uint32_t* PolygonCountPerGroup;
		uint32_t* PointCountPerPolygon;
		double*   Coords;

		uint32_t TotalPolygonCount() const;
		uint32_t TotalCoordCount() const;
	};

	struct SPoints
	{
		uint32_t  GroupCount;
		uint32_t* PointCountPerGroup;
		double*   Coords;

		uint32_t TotalPointCount() const;
	};

	SCreateIsovistContextDesc() : m_Version(VERSION) {}
	
	// Version
	static const unsigned int VERSION = 2;
	unsigned int m_Version;

	SPolygons ObstaclePolygons;
	SPoints   AttractionPoints;
	SPolygons AttractionPolygons;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;
};

//  NOTE: The returned handle must be freed with call to PSTAFree().
PSTADllExport psta_handle_t PSTACreateIsovistContext(const SCreateIsovistContextDesc* desc);


struct SCalculateIsovistDesc
{
	PSTA_DECL_STRUCT_NAME(SCalculateIsovistDesc)
		
	SCalculateIsovistDesc() : m_Version(VERSION) {}

	// Version
	static const unsigned int VERSION = 4;
	unsigned int m_Version;

	psta_handle_t m_IsovistContext;

	double m_OriginX;
	double m_OriginY;
	float  m_MaxViewDistance;
	float  m_FieldOfViewDegrees;
	float  m_DirectionDegrees;
	unsigned int m_PerimeterSegmentCount;

	unsigned int m_OutPointCount;
	double* m_OutPoints;
	psta_handle_t m_OutIsovistHandle;

	float m_OutArea;

	// Visibility
	struct SVisibleObjects
	{
		uint32_t  ObjectCount;
		uint32_t  GroupCount;
		uint32_t* CountPerGroup;
		uint32_t* Indices;
	};
	SVisibleObjects m_OutVisibleObstacles;
	SVisibleObjects m_OutVisibleAttractionPoints;
	SVisibleObjects m_OutVisibleAttractionPolygons;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;
};

//  NOTE: The handle desc.m_OutIsovistHandle must be freed with call to PSTAFree().
PSTADllExport void PSTACalculateIsovist(SCalculateIsovistDesc* desc);


/*

// !!! DEPRECATED !!!

struct SCalculateIsovistsDesc
{
	SCalculateIsovistsDesc() : m_Version(VERSION) {}

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	unsigned int m_PolygonCount;
	unsigned int* m_PointCountPerPolygon;
	double* m_PolygonPoints;

	unsigned int m_OriginCount;
	double* m_OriginPoints;

	float m_MaxRadius;
	unsigned int m_PerimeterSegmentCount;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;
};

struct SCalculateIsovistsRes
{
	SCalculateIsovistsRes() : m_Version(VERSION) {}

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	unsigned int m_IsovistCount;
	unsigned int* m_PointCountPerIsovist;
	double* m_IsovistPoints;
};

PSTADllExport IPSTAlgo* PSTACalculateIsovists(const SCalculateIsovistsDesc* desc, SCalculateIsovistsRes* res);

*/