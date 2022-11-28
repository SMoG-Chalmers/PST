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

#include <algorithm>
#include <cstring>
#include <pstalgo/analyses/Common.h>
#include <pstalgo/Debug.h>

SPSTARadii::SPSTARadii()
{
	Clear();
}

void SPSTARadii::Clear()
{
	memset(this, 0, sizeof(*this));
}

float SPSTARadii::Get(EPSTADistanceType distance_type) const
{
	if (!(m_Mask & EPSTADistanceMaskFromType(distance_type)))
		return std::numeric_limits<float>::infinity();
	switch (distance_type)
	{
	case EPSTADistanceType_Straight:
		return m_Straight;
	case EPSTADistanceType_Walking:
		return m_Walking;
	case EPSTADistanceType_Steps:
		return (float)m_Steps;
	case EPSTADistanceType_Angular:
		return m_Angular;
	case EPSTADistanceType_Axmeter:
		return m_Axmeter;
	
	// Unhandled
	case EPSTADistanceType_Undefined:
	default:
		break;
	}
	ASSERT(false && "Unsupported distance type!");
	return std::numeric_limits<float>::infinity();
}

PSTADllExport void PSTAStandardNormalize(const float* in, unsigned int count, float* out)
{
	using namespace std;

	if (0 == count)
		return;

	// Calculate min and max
	float low, high;
	low = high = in[0];
	for (size_t i = 1; i < count; ++i)
	{
		low = min(low, in[i]);
		high = max(high, in[i]);
	}

	// Rescale to [0..1] range
	if (low < high)
	{
		const float s = 1.0f / (high - low);
		for (size_t i = 0; i < count; ++i)
			out[i] = (in[i] - low) * s;
	}
	else
	{
		for (size_t i = 0; i < count; ++i)
			out[i] = 1;
	}
}