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

#define BIT(x) (1 << (x))

#define INFINITE_LOOP for(;;)

#ifdef _MSC_VER
	#define ALLOW_NAMELESS_STRUCT_BEGIN __pragma(warning(push)) __pragma(warning(disable:4201)) 
	#define ALLOW_NAMELESS_STRUCT_END   __pragma(warning(pop))
#else
	#define ALLOW_NAMELESS_STRUCT_BEGIN
	#define ALLOW_NAMELESS_STRUCT_END
#endif