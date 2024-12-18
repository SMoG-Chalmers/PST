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
 
#if defined(__x86_64__) || defined(__ppc64__) || defined(__LP64__) || defined(_WIN64)
	#define PSTA_64 1
#else
	#define PSTA_32 1
#endif

#ifdef WIN32
	#define PSTA_WIN 1
#elif defined __GNUC__
	#define PSTA_GCC 1
#endif

namespace psta
{
	class CLowerThreadPrioInScope
	{
	public:
		CLowerThreadPrioInScope();
		~CLowerThreadPrioInScope();
	private:
		int m_PrevPrio;
	};
}