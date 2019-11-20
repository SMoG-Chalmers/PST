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

#include "pstalgo.h"

#ifdef _MFC_VER
	#undef ASSERT
	#undef VERIFY
#endif

#ifdef _DEBUG
	#include <cassert>
	#define ASSERT(x) assert(x)
	#define VERIFY(x) assert(x)
#else
	#define ASSERT(x)
	#define VERIFY(x) x
#endif

#define LOG_VERBOSE(fmt, ...) pstdbg::Log(pstdbg::EErrorLevel_Verbose, 0x0, fmt, ##__VA_ARGS__)
#define LOG_INFO(fmt, ...)    pstdbg::Log(pstdbg::EErrorLevel_Info, 0x0, fmt, ##__VA_ARGS__)
#define LOG_WARNING(fmt, ...) pstdbg::Log(pstdbg::EErrorLevel_Warning, 0x0, fmt, ##__VA_ARGS__)
#define LOG_ERROR(fmt, ...)   pstdbg::Log(pstdbg::EErrorLevel_Error, 0x0, fmt, ##__VA_ARGS__)

#define LOG_VERBOSE_DOMAIN(domain, fmt, ...) pstdbg::Log(pstdbg::EErrorLevel_Verbose, domain, fmt, ##__VA_ARGS__)
#define LOG_INFO_DOMAIN(domain, fmt, ...)    pstdbg::Log(pstdbg::EErrorLevel_Info, domain, fmt, ##__VA_ARGS__)
#define LOG_WARNING_DOMAIN(domain, fmt, ...) pstdbg::Log(pstdbg::EErrorLevel_Warning, domain, fmt, ##__VA_ARGS__)
#define LOG_ERROR_DOMAIN(domain, fmt, ...)   pstdbg::Log(pstdbg::EErrorLevel_Error, domain, fmt, ##__VA_ARGS__)

namespace pstdbg
{
	enum EErrorLevel : int
	{
		EErrorLevel_Verbose,
		EErrorLevel_Info,
		EErrorLevel_Warning,
		EErrorLevel_Error,
	};

	typedef void(*FLogCallback)(EErrorLevel level, const char* domain, const char* msg, void* user_data);

	typedef unsigned int HLogCallback;

	HLogCallback RegisterLogCallback(FLogCallback func, void* user_data);

	void UnregisterLogCallback(HLogCallback handle);

	void Log(EErrorLevel level, const char* domain, const char* fmt, ...);
}

PSTADllExport pstdbg::HLogCallback PSTARegisterLogCallback(pstdbg::FLogCallback func, void* user_data);

PSTADllExport void PSTAUnregisterLogCallback(pstdbg::HLogCallback handle);
