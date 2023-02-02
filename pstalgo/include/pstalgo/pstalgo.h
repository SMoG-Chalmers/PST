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

#if defined(_MSC_VER) 
	// Microsoft
	#ifdef PSTADLL_EXPORTS
		#define PSTADllExport extern "C" __declspec( dllexport )
		#define PSTADllExportClass __declspec( dllexport )
	#else
		#define PSTADllExport extern "C" __declspec( dllimport )
		#define PSTADllExportClass __declspec( dllimport )
	#endif
#elif defined(__GNUC__)
	// GCC
	#define PSTADllExport extern "C" __attribute__((visibility("default")))
	#define PSTADllExportClass __attribute__((visibility("default")))
#else
	#define PSTADllExport 
	#define PSTADllExportClass
	#pragma warning Unknown dynamic link export semantics.
#endif

// Return 0 = continue, otherwise cancel
typedef int(*FPSTAProgressCallback)(const char* text, float progress, void* user_data);

class IPSTAlgo
{
public:
	virtual ~IPSTAlgo() {}

	void operator=(const IPSTAlgo&) = delete;
};

typedef void* psta_handle_t;

typedef int psta_result_t;

#define PSTA_RESULT_OK 0
#define PSTA_RESULT_ERROR 1

PSTADllExport void PSTAFree(IPSTAlgo* algo);