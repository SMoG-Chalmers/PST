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

#include <vector>
#include <cstring>

#include "Limits.h"
#include "Vec2.h"

class CAxialGraph;

class CPSTBFS {

public:
	enum Target {
		TARGET_POINTS,
		TARGET_LINES,
		TARGET_CROSSINGS
	};

	CPSTBFS();
	~CPSTBFS();

	void init(CAxialGraph* pGraph, Target target, DistanceType distType, const LIMITS& limits);
	int  getTargetCount();

	inline void       cancel() { m_bCancel = true; }
	inline const bool getCancel() const { return m_bCancel; }

protected:
	struct DIST {
		float walking;
		int   turns;
		float angle;
		float axmeter;
	public:
		inline bool operator<(const DIST& d) { return (walking < d.walking) || (turns < d.turns) || (angle < d.angle) || (axmeter < d.axmeter); }
	};

	struct CHECKPOINT {
		float walking;
		int   turns;
		float fwAngle;
		float bkAngle;
		float axmeter;
	};

	struct STATE {
		int   iLineCrossing;
		DIST  dist;
		float lastAngle;
	};

	void         doBFSFromPoint(const float2& pt);
	void		 doBFSFromLine(int iLine);
	void         doBFS(int iStartLine, float startPos, const DIST& startDist);
	virtual void visitBFS(int iTarget, const DIST& dist) = 0;
	bool         testLimit(const DIST& dist);
	virtual bool testStraightLineLimit(const float2& pt);
	bool         updateCheckPoint(CHECKPOINT& c, const DIST& d, float fwAngle, float bkAngle);
	inline void  clrVisitedLineCrossings()       { if (!m_lcVisitedBits.empty()) memset(&m_lcVisitedBits.front(), 0, m_lcVisitedBits.size() * sizeof(m_lcVisitedBits.front())); }
	inline bool  hasVisitedLineCrossing(int iLC) { return (m_lcVisitedBits[iLC >> 5] & (1 << (iLC & 31))) != 0; }
	inline void  setVisitedLineCrossing(int iLC) { m_lcVisitedBits[iLC >> 5] |= (1 << (iLC & 31)); }

	CAxialGraph*      m_pGraph;
	const float2*   m_pDest;
	int             m_nDest;
	LIMITS          m_lim;
	Target          m_target;
	DistanceType    m_distType;
	std::vector<CHECKPOINT> m_lcCheckPoints;
	std::vector<unsigned int> m_lcVisitedBits;
	float2          m_origin;
	bool            m_bCancel;

};