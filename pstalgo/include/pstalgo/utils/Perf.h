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

#include <chrono>

namespace psta
{
	class CPerfTimer
	{
	public:
		typedef unsigned long long ticks_t;

		inline void Start() 
		{
			m_Timestamp = CurrentTimestamp();
		}

		inline ticks_t ReadAndRestart()
		{
			const auto last = m_Timestamp;
			m_Timestamp = CurrentTimestamp();
			return m_Timestamp - last;
		}

		inline static float SecondsFromTicks(ticks_t ticks)
		{
			return SecondsPerTick() * ticks;
		}

		inline static float SecondsPerTick()
		{
			return (float)std::chrono::high_resolution_clock::duration::period::num / std::chrono::high_resolution_clock::duration::period::den;
		}

		inline static ticks_t CurrentTimestamp()
		{
			return (ticks_t)std::chrono::high_resolution_clock::now().time_since_epoch().count();
		}

	private:
		ticks_t m_Timestamp;
	};
}