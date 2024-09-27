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
#include <pstalgo/Raster.h>
#include "Common.h"


struct SVisualConnectivityDesc
{
	SVisualConnectivityDesc() : m_Version(VERSION) {}

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	unsigned int m_PolygonCount;
	unsigned int* m_PointCountPerPolygon;
	double* m_PolygonPoints;

	double m_RangeMinX;
	double m_RangeMinY;
	double m_RangeMaxX;
	double m_RangeMaxY;
	float  m_CellSize;
	float  m_MaxViewDistance;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;
};

//  NOTE: The handle must be freed with call to PSTAFree().
PSTADllExport psta_raster_handle_t PSTAVisualConnectivity(SVisualConnectivityDesc* desc);