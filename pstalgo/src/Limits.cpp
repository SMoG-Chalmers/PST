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

#include <cmath>
#include <cstdio>

#include <pstalgo/Debug.h>
#include <pstalgo/Limits.h>

#ifdef _MSC_VER
	#define snprintf _snprintf_s
#endif

LIMITS LimitsFromSPSTARadii(const SPSTARadii& r)
{
	LIMITS lim;

	lim.mask = 0;
	if (r.m_Mask & EPSTADistanceTypeMask_Straight)
		lim.mask |= LIMITS::MASK_STRAIGHT;
	if (r.m_Mask & EPSTADistanceTypeMask_Walking)
		lim.mask |= LIMITS::MASK_WALKING;
	if (r.m_Mask & EPSTADistanceTypeMask_Steps)
		lim.mask |= LIMITS::MASK_TURNS;
	if (r.m_Mask & EPSTADistanceTypeMask_Angular)
		lim.mask |= LIMITS::MASK_ANGLE;
	if (r.m_Mask & EPSTADistanceTypeMask_Axmeter)
		lim.mask |= LIMITS::MASK_AXMETER;

	lim.straightSqr = r.m_Straight*r.m_Straight;
	lim.walking = r.m_Walking;
	lim.turns = r.m_Steps;
	lim.angle = r.m_Angular;
	lim.axmeter = r.m_Axmeter;

	return lim;
}

bool LIMITS::set(DistanceSpec ds)
{

	switch (ds.type) {
	case DIST_STRAIGHT:
		mask = MASK_STRAIGHT;
		straightSqr = ds.amount * ds.amount;
		break;
	case DIST_WALKING:
		mask = MASK_WALKING;
		walking = ds.amount;
		break;
	case DIST_LINES:
		mask = MASK_TURNS;
		turns = (int)ds.amount;
		break;
	case DIST_ANGULAR:
		mask = MASK_ANGLE;
		angle = ds.amount;
		break;
	case DIST_AXMETER:
		mask = MASK_AXMETER;
		axmeter = ds.amount;
		break;
	default:
		mask = 0;
		break;
	}
	return true;
}

std::string LIMITS::toString()
{
	std::string text;
	DistanceSpec ds;
	if (mask & MASK_STRAIGHT)
	{
		if (!text.empty())
			text += "_";
		ds.type = DIST_STRAIGHT;
		ds.amount = round(sqrt(straightSqr));
		text += ds.toString();
	}
	if (mask & MASK_WALKING)
	{
		if (!text.empty())
			text += "_";
		ds.type = DIST_WALKING;
		ds.amount = walking;
		text += ds.toString();
	}
	if (mask & MASK_TURNS)
	{
		if (!text.empty())
			text += "_";
		ds.type = DIST_LINES;
		ds.amount = (float)turns;
		text += ds.toString();
	}
	if (mask & MASK_ANGLE)
	{
		if (!text.empty())
			text += "_";
		ds.type = DIST_ANGULAR;
		ds.amount = angle;
		text += ds.toString();
	}
	if (mask & MASK_AXMETER)
	{
		if (!text.empty())
			text += "_";
		ds.type = DIST_AXMETER;
		ds.amount = axmeter;
		text += ds.toString();
	}
	return text;
}

SPSTARadii PSTARadiiFromLimits(const LIMITS& lim)
{
	SPSTARadii r;

	if (lim.mask & LIMITS::MASK_STRAIGHT)
		r.m_Mask |= EPSTADistanceTypeMask_Straight;
	if (lim.mask & LIMITS::MASK_WALKING)
		r.m_Mask |= EPSTADistanceTypeMask_Walking;
	if (lim.mask & LIMITS::MASK_TURNS)
		r.m_Mask |= EPSTADistanceTypeMask_Steps;
	if (lim.mask & LIMITS::MASK_ANGLE)
		r.m_Mask |= EPSTADistanceTypeMask_Angular;
	if (lim.mask & LIMITS::MASK_AXMETER)
		r.m_Mask |= EPSTADistanceTypeMask_Axmeter;

	r.m_Straight = sqrt(lim.straightSqr);
	r.m_Walking = lim.walking;
	r.m_Steps = lim.turns;
	r.m_Angular = lim.angle;
	r.m_Axmeter = lim.axmeter;

	return r;
}

EPSTADistanceType EPSTADistanceTypeFromDistanceType(DistanceType distance_type)
{
	switch (distance_type)
	{
	case DIST_NONE: return EPSTADistanceType_Undefined;
	case DIST_STRAIGHT: return EPSTADistanceType_Straight;
	case DIST_WALKING: return EPSTADistanceType_Walking;
	case DIST_LINES: return EPSTADistanceType_Steps;
	case DIST_ANGULAR: return EPSTADistanceType_Angular;
	case DIST_AXMETER: return EPSTADistanceType_Axmeter;
	}
	ASSERT(false && "Unknown distance mode!");
	return EPSTADistanceType_Undefined;
}

DistanceType DistanceTypeFromEPSTADistanceType(EPSTADistanceType distance_type)
{
	switch (distance_type)
	{
	case EPSTADistanceType_Undefined: return DIST_NONE;
	case EPSTADistanceType_Straight: return DIST_STRAIGHT;
	case EPSTADistanceType_Walking: return DIST_WALKING;
	case EPSTADistanceType_Steps: return DIST_LINES;
	case EPSTADistanceType_Angular: return DIST_ANGULAR;
	case EPSTADistanceType_Axmeter: return DIST_AXMETER;
	}
	ASSERT(false && "Unknown distance mode!");
	return DIST_NONE;
}

const char* DistanceTypeShortNames[_DIST_COUNT] = {
	"str",
	"walk",
	"step",
	"ang",
	"axm",
};

const char* DistanceSpec::toString() const
{
	static char szTemp[64];
	switch (type) {
	case DIST_STRAIGHT:
		snprintf(szTemp, sizeof(szTemp), "%s_%.0fm", DistanceTypeShortNames[type], amount);
		break;
	case DIST_WALKING:
		snprintf(szTemp, sizeof(szTemp), "%s_%.0fm", DistanceTypeShortNames[type], amount);
		break;
	case DIST_LINES:
		snprintf(szTemp, sizeof(szTemp), "%s_%.0f", DistanceTypeShortNames[type], amount);
		break;
	case DIST_ANGULAR:
		snprintf(szTemp, sizeof(szTemp), "%s_%.0fdeg", DistanceTypeShortNames[type], amount);
		break;
	case DIST_AXMETER:
		snprintf(szTemp, sizeof(szTemp), "%s_%.0f", DistanceTypeShortNames[type], amount);
		break;
	default:
		*szTemp = 0;
		break;
	}
	return szTemp;
}

