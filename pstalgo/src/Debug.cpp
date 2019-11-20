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


#include <stddef.h>
#include <stdarg.h>
#include <stdio.h>
#include <vector>

#include <pstalgo/Debug.h>

#ifndef _MSC_VER
	#define vsnprintf_s vsnprintf
#endif

namespace pstdbg
{
	struct SCallback
	{
		HLogCallback m_Handle;
		FLogCallback m_Func;
		void*        m_UserData;
	};

	HLogCallback g_CallbackCounter = 0;

	std::vector<SCallback> g_Callbacks;

	HLogCallback RegisterLogCallback(FLogCallback func, void* user_data)
	{
		ASSERT(func && "Tried to register a null function as log callback");

		++g_CallbackCounter;
		ASSERT((g_CallbackCounter != 0) && "Log callback handle counter overflowed!");

		SCallback cb;
		cb.m_Handle   = g_CallbackCounter;
		cb.m_Func     = func;
		cb.m_UserData = user_data;

		g_Callbacks.push_back(cb);

		return g_CallbackCounter;
	}

	void UnregisterLogCallback(HLogCallback handle)
	{
		for (size_t i = 0; i < g_Callbacks.size(); ++i)
		{
			if (g_Callbacks[i].m_Handle == handle)
			{
				g_Callbacks.erase(g_Callbacks.begin() + i);
				return;
			}
		}
		ASSERT(!"Tried to unregister log callback that wasn't registered");
	}

	void Log(EErrorLevel level, const char* domain, const char* fmt, ...)
	{
		char buf[4096];
		va_list args;
		va_start (args, fmt);
		vsnprintf_s(buf, sizeof(buf), fmt, args);

		for (size_t i = 0; i < g_Callbacks.size(); ++i)
		{
			g_Callbacks[i].m_Func(level, domain, buf, g_Callbacks[i].m_UserData);
		}
	}
}

PSTADllExport pstdbg::HLogCallback PSTARegisterLogCallback(pstdbg::FLogCallback func, void* user_data)
{
	return pstdbg::RegisterLogCallback(func, user_data);
}

PSTADllExport void PSTAUnregisterLogCallback(pstdbg::HLogCallback handle)
{
	pstdbg::UnregisterLogCallback(handle);
}
