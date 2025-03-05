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

#include <stdarg.h>
#include <stdio.h>
#include <stdexcept>

namespace psta
{
	template <typename TException>
	inline TException FormatException(const char* fmt, ...)
	{
		char szMessage[1024];
		va_list args;
		va_start(args, fmt);
		#ifdef _MSC_VER
			vsnprintf_s(szMessage, _TRUNCATE, fmt, args);
		#else
			vsnprintf(szMessage, sizeof(szMessage), fmt, args);
		#endif
		return TException(szMessage);
	}
}