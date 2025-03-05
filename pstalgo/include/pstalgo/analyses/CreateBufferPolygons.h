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

struct SCompareResultsDesc 
{
	PSTA_DECL_STRUCT_NAME(SCompareResultsDesc)
		
	SCompareResultsDesc() : m_Version(VERSION) {}

	// Version
	static const unsigned int VERSION = 4;
	unsigned int m_Version;

	unsigned int LineCount1;
	double* LineCoords1;
	float* Values1;

	enum EMode : unsigned int
	{
		Normalized = 0,
		RelativePercent = 1,
	};
	EMode Mode;

	float M;  // Only applicable when Mode == RelativePercent

	unsigned int LineCount2;  // Optional, must be zero if not used
	double* LineCoords2;      // Optional, must be NULL if not used
	float* Values2;           // Number of values from LineCount2 if two line sets are used, otherwise LineCount1.

	float BlurRadius;         // Radius for 1 std dev.
	float Resolution;         // Pixel size in meters

	psta_raster_handle_t OutRaster;
	float                OutMin;
	float                OutMax;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;
};

//  NOTE: The returned handle must be freed with call to PSTAFree().
PSTADllExport psta_handle_t PSTACompareResults(SCompareResultsDesc* desc);