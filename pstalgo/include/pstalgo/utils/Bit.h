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

#include <stdint.h>

#ifdef _MSC_VER
	#include <intrin.h>  // for _BitScanReverse
	#if _MSC_VER <= 1800
		#define alignof __alignof
	#endif
#endif

#include <pstalgo/system/System.h>

namespace psta
{
	// Returns zero-based index of most significant bit set in 'val' (i.e. val = 0x1000 --> 12)
	inline unsigned int bit_scan_reverse_32(unsigned long val)
	{
		#ifdef _MSC_VER
			unsigned long msb = 0;
			_BitScanReverse(&msb, val);
			return msb;
		#else
			return sizeof(val) * 8 - 1 - __builtin_clzl(val);
		#endif
	}

	// Returns zero-based index of most significant bit set in 'val' (i.e. val = 0x1000 --> 12)
	#ifdef PSTA_64
		inline unsigned int bit_scan_reverse_64(unsigned long long val)
		{
			#ifdef _MSC_VER
				unsigned long msb = 0;
				_BitScanReverse64(&msb, val);
				return msb;
			#else
				return sizeof(val) * 8 - 1 - __builtin_clzll(val);
			#endif
		}
	#endif

	inline unsigned int bit_scan_reverse(size_t val)
	{
		#ifdef PSTA_64
			return bit_scan_reverse_64(val);
		#else
			return bit_scan_reverse_32(val);
		#endif
	}

	template <typename T> T align_up(T val, T alignment)
	{
		const auto align_mask = alignment - 1;
		return (val + align_mask) & ~align_mask;
	}

	template <typename T> T* align_ptr_up(T* ptr, size_t alignment)
	{
		return (T*)align_up((size_t)ptr, alignment);
	}

	template <typename T> T round_up_to_closest_power_of_two(T value)
	{
		if (!value)
			return 0;
		const T res = 1 << bit_scan_reverse(value);
		return (res < value) ? (res << 1) : res;
	}
}