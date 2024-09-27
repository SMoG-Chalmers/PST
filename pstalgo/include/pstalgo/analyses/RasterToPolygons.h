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

struct SRasterToPolygonsDesc 
{
	SRasterToPolygonsDesc() : m_Version(VERSION) {}

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	psta_raster_handle_t Raster;

	struct SRange
	{
		float Min;
		float Max;
	};
	unsigned int RangeCount;
	const SRange* Ranges;

	unsigned int* OutPolygonCountPerRange;
	unsigned int* OutPolygonData;  // <ring count> <size of ring 1> ... <size of ring N>,  <ring count> <size of ring 1> ... <size of ring N> ...
	double* OutPolygonCoords;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;
};

//  NOTE: The returned handle must be freed with call to PSTAFree().
PSTADllExport psta_handle_t PSTARasterToPolygons(SRasterToPolygonsDesc* desc);