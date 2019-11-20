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
#include <pstalgo/Vec2.h>

struct SCreateJunctionsDesc
{
	SCreateJunctionsDesc() : m_Version(VERSION) {}

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	// Layer 0
	double2* m_Coords0;
	unsigned int* m_Lines0;  // Can be NULL if m_Coords0 contains list of simple coordinate pairs
	unsigned int m_LineCount0;  

	// Layer 1
	double2* m_Coords1;
	unsigned int* m_Lines1;  // Can be NULL if m_Coords1 contains list of simple coordinate pairs
	unsigned int m_LineCount1;

	// Unlinks
	double2*     m_UnlinkCoords;
	unsigned int m_UnlinkCount;

	// Progress Callback
	FPSTAProgressCallback m_ProgressCallback;
	void*                 m_ProgressCallbackUser;
};

struct SCreateJunctionsRes
{
	SCreateJunctionsRes() : m_Version(VERSION) {}

	// Version
	static const unsigned int VERSION = 1;
	unsigned int m_Version;

	// Junction points
	double*       m_PointCoords;
	unsigned int  m_PointCount;
};

PSTADllExport IPSTAlgo* PSTACreateJunctions(const SCreateJunctionsDesc* desc, SCreateJunctionsRes* res);