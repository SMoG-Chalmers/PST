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

#include <string>
#include <vector>

#include <pstalgo/analyses/Common.h>

// DEPRECATED
enum DistanceType {
	DIST_NONE = -1,
	DIST_STRAIGHT = 0,
	DIST_WALKING,
	DIST_LINES,
	DIST_ANGULAR,
	DIST_AXMETER,
	_DIST_COUNT
};

// DEPRECATED
struct LIMITS {
	enum {
		MASK_STRAIGHT = 0x01,
		MASK_WALKING  = 0x02,
		MASK_TURNS    = 0x04,
		MASK_ANGLE    = 0x08,
		MASK_AXMETER  = 0x10,
	};
	unsigned int mask;
	float straightSqr;   // NOTE: Stored as straight distance^2 for performance reasons
	float walking;
	int   turns;
	float angle;
	float axmeter;
public:
	LIMITS() : mask(0) {}
public:
	bool set(struct DistanceSpec ds);
	std::string toString();
};

extern const char* DistanceTypeShortNames[_DIST_COUNT];

struct DistanceSpec {
	DistanceType type;
	float        amount;
	const char*  toString() const;
};

class DistanceSet : public std::vector<DistanceSpec> {
public:
	bool addString(const char* pcszText, DistanceType distType);
};

LIMITS LimitsFromSPSTARadii(const struct SPSTARadii& r);

struct SPSTARadii PSTARadiiFromLimits(const LIMITS& lim);

EPSTADistanceType EPSTADistanceTypeFromDistanceType(DistanceType distance_type);

DistanceType DistanceTypeFromEPSTADistanceType(EPSTADistanceType distance_type);
