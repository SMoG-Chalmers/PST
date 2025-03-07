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

#include <limits>
#include <stdexcept>
#include <pstalgo/pstalgo.h>
#include <pstalgo/Error.h>

enum EPSTANetworkElement
{
	EPSTANetworkElement_Point,
	EPSTANetworkElement_Junction,
	EPSTANetworkElement_Line,
};

enum EPSTAOriginType
{
	EPSTAOriginType_Points,
	EPSTAOriginType_Junctions,
	EPSTAOriginType_Lines,
	EPSTAOriginType_PointGroups,
};

enum EPSTADistanceType
{
	EPSTADistanceType_Straight = 0,
	EPSTADistanceType_Walking,
	EPSTADistanceType_Steps,
	EPSTADistanceType_Angular,
	EPSTADistanceType_Axmeter,
	EPSTADistanceType_Weights,

	EPSTADistanceType_Undefined,
	EPSTADistanceType__COUNT = EPSTADistanceType_Undefined
};

#define EPSTADistanceMaskFromType(distance_type) (1 << (distance_type))

enum EPSTADistanceTypeMask
{
	EPSTADistanceTypeMask_Straight = EPSTADistanceMaskFromType(EPSTADistanceType_Straight),
	EPSTADistanceTypeMask_Walking  = EPSTADistanceMaskFromType(EPSTADistanceType_Walking),
	EPSTADistanceTypeMask_Steps    = EPSTADistanceMaskFromType(EPSTADistanceType_Steps),
	EPSTADistanceTypeMask_Angular  = EPSTADistanceMaskFromType(EPSTADistanceType_Angular),
	EPSTADistanceTypeMask_Axmeter  = EPSTADistanceMaskFromType(EPSTADistanceType_Axmeter),
	EPSTADistanceTypeMask_Weights  = EPSTADistanceMaskFromType(EPSTADistanceType_Weights),
};

enum EPSTARoadNetworkType
{
	EPSTARoadNetworkType_Unknown         = 0,
	EPSTARoadNetworkType_AxialOrSegment  = 1,
	EPSTARoadNetworkType_RoadCenterLines = 2,
};

struct PSTADllExportClass SPSTARadii
{
	SPSTARadii();
	
	void Clear();

	bool HasStraight() const { return (m_Mask & EPSTADistanceTypeMask_Straight) != 0; }
	bool HasWalking() const  { return (m_Mask & EPSTADistanceTypeMask_Walking) != 0; }
	bool HasSteps() const    { return (m_Mask & EPSTADistanceTypeMask_Steps) != 0; }
	bool HasAngular() const  { return (m_Mask & EPSTADistanceTypeMask_Angular) != 0; }
	bool HasAxmeter() const  { return (m_Mask & EPSTADistanceTypeMask_Axmeter) != 0; }

	float Straight() const     { return HasStraight() ? m_Straight : std::numeric_limits<float>::infinity(); }
	float StraightSqr() const  { return HasStraight() ? m_Straight*m_Straight : std::numeric_limits<float>::infinity(); }
	float Walking() const      { return HasWalking() ? m_Walking : std::numeric_limits<float>::infinity(); }
	unsigned int Steps() const { return HasSteps()    ? m_Steps    : std::numeric_limits<unsigned int>::max(); }
	float Angular() const      { return HasAngular()  ? m_Angular  : std::numeric_limits<float>::infinity(); }
	float Axmeter() const      { return HasAxmeter()  ? m_Axmeter  : std::numeric_limits<float>::infinity(); }

	void SetStraight(float amount)     { m_Straight = amount; m_Mask |= EPSTADistanceTypeMask_Straight; }
	void SetWalking(float amount)      { m_Walking = amount;  m_Mask |= EPSTADistanceTypeMask_Walking; }
	void SetSteps(unsigned int amount) { m_Steps = amount;    m_Mask |= EPSTADistanceTypeMask_Steps; }
	void SetAngular(float amount)      { m_Angular = amount;  m_Mask |= EPSTADistanceTypeMask_Angular; }
	void SetAxmeter(float amount)      { m_Axmeter = amount;  m_Mask |= EPSTADistanceTypeMask_Axmeter; }

	float Get(EPSTADistanceType distance_type) const;

	unsigned int m_Mask;

	float m_Straight;
	float m_Walking;
	int   m_Steps;
	float m_Angular;
	float m_Axmeter;
};

// Rescales to [0..1] range (1 if min = max)
PSTADllExport void PSTAStandardNormalize(const float* in, unsigned int count, float* out);

template <class T>
inline void VerifyStructVersion(const T& s)
{
	if (T::VERSION != s.m_Version)
	{
		throw psta::FormatException<std::runtime_error>("Version mismatch for struct '%s'. Got version %d but expected %d.", PSTA_STRUCT_NAME(T), s.m_Version, T::VERSION);
	}
}