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

#include <pstalgo/system/System.h>

#ifdef WIN32
	#include <Windows.h>
	#define INVALID_THREAD_PRIO THREAD_PRIORITY_ERROR_RETURN
#else
	#define INVALID_THREAD_PRIO -1
#endif

namespace psta
{
	CLowerThreadPrioInScope::CLowerThreadPrioInScope()
		: m_PrevPrio(INVALID_THREAD_PRIO)
	{
		#ifdef WIN32
			const auto current_thread = GetCurrentThread();
			auto prio = GetThreadPriority(current_thread);
			auto new_prio = prio;
			switch (prio)
			{
			case THREAD_PRIORITY_BELOW_NORMAL:
				new_prio = THREAD_PRIORITY_LOWEST;
				break;
			case THREAD_PRIORITY_NORMAL:
				new_prio = THREAD_PRIORITY_BELOW_NORMAL;
				break;
			case THREAD_PRIORITY_ABOVE_NORMAL:
				new_prio = THREAD_PRIORITY_NORMAL;
				break;
			case THREAD_PRIORITY_HIGHEST:
				new_prio = THREAD_PRIORITY_ABOVE_NORMAL;
				break;
			default:
				// Leave priority unchanged
				return;
			}
			if (SetThreadPriority(current_thread, new_prio))
				m_PrevPrio = prio;
		#endif
	}

	CLowerThreadPrioInScope::~CLowerThreadPrioInScope()
	{
		if (INVALID_THREAD_PRIO == m_PrevPrio)
			return;
		#ifdef WIN32
			SetThreadPriority(GetCurrentThread(), m_PrevPrio);
		#endif
	}
}