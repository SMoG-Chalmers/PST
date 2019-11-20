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

#include <memory>
#include <vector>
#include <pstalgo/maths.h>

class SphereTree;

class CAxialGraph {

// Structs
public:

	struct BBOX {
		COORDS min;
		COORDS max;
		void update(const COORDS& c);
	};

	struct STAT {
		float timeFindCrossings;
		float timeUnlinkCrossings;
		float timeConnectPoints;
	};

	struct POINT {
		COORDS coords;
		REAL   distFromLine;
		REAL   linePos;
		int    iLine;
	};

	struct NETWORKLINE {
		COORDS p1;
		COORDS p2;
		REAL   length;
		float  angle;          // [0..360)
		int    iFirstPoint;
		int    nPoints;
		int    iFirstCrossing;
		int    nCrossings;
	};

	struct CROSSING {
		COORDS pt;
		int    nLines;
	};

	struct LINECROSSING {
		int   iCrossing;
		int   iLine;
		int   iOpposite;
		REAL  linePos;
	};


// Typedefs
protected:
	typedef std::vector<POINT>        PointArray;
	typedef std::vector<NETWORKLINE>  LineArray;
	typedef std::vector<CROSSING>     CrossingArray;
	typedef std::vector<LINECROSSING> LineCrossArray;

// Data Members
protected:
	PointArray       m_points;
	LineArray        m_lines;
	std::vector<int> m_linePoints;
	CrossingArray    m_crossings;
	LineCrossArray   m_lineCrossings;
	BBOX             m_bbox;
	REAL             m_maxDist;
	std::unique_ptr<SphereTree> m_sphereTree;
	STAT             m_stat;
	std::vector<int> m_tmpLineIdx;  // TODO: Get rid of this, since it is not thread safe
	double2          m_WorldOrigin;
	std::vector<unsigned int> m_PointGroups;  // Number of points per group

// Construction / Destruction
public:
	CAxialGraph();
	~CAxialGraph();

	CAxialGraph(const CAxialGraph& other) = delete;

// Operations
public:
	void clear();
	void createGraph(const LINE* pLines, int nLines,
					 const COORDS* pUnlinks, int nUnlinks,
					 const COORDS* pPoints = NULL, int nPoints = 0);

	void setPointGroups(std::vector<unsigned int>&& points_per_group);

	void setWorldOrigin(const double2& origin) { m_WorldOrigin = origin; }
	const double2& getWorldOrigin() const { return m_WorldOrigin; }
	const float2 worldToLocal(const double2& pt) const { return float2((float)(pt.x - m_WorldOrigin.x), (float)(pt.y - m_WorldOrigin.y)); }
	const double2 localToWorld(const float2& pt) const { return (double2)pt + m_WorldOrigin; }

	inline int getLineCount()         const { return (int)m_lines.size(); }
	inline int getLineCrossingCount() const { return (int)m_lineCrossings.size(); }
	inline int getPointCount()        const { return (int)m_points.size(); }
	inline int getCrossingCount()     const { return (int)m_crossings.size(); }
	inline size_t getPointGroupCount() const { return m_PointGroups.size(); }

	inline NETWORKLINE&        getLine(int index)               { return m_lines[index]; }
	inline const NETWORKLINE&  getLine(int index) const         { return m_lines[index]; }
	inline LINECROSSING&       getLineCrossing(int index)       { return m_lineCrossings[index]; }
	inline const LINECROSSING& getLineCrossing(int index) const { return m_lineCrossings[index]; }
	inline int                 getLinePoint(int index) const    { return m_linePoints[index]; }
	inline POINT&              getPoint(int index)              { return m_points[index]; }
	inline const POINT&        getPoint(int index) const        { return m_points[index]; }
	inline CROSSING&           getCrossing(int index)           { return m_crossings[index]; }
	inline const CROSSING&     getCrossing(int index) const     { return m_crossings[index]; }
	inline unsigned int        getPointGroupSize(unsigned int group_index) const { return m_PointGroups[group_index]; }

	int getClosestLine(const COORDS& pt, REAL* pRetDist, REAL* pRetPos) const;
	int getLinesFromPoint(const COORDS& ptCenter, float radius, int** ppRetLinesIdx);

	int getCloseLines(int* pRetIdx, REAL x1, REAL y1, REAL x2, REAL y2);

// Implementation
protected:
	void findCrossings(const COORDS* pUnlinks, int nUnlinks);
	void updateLinesPerCrossingCount();
	void connectPointsToNetwork(const COORDS* pPoints, int nPoints);

public:
	static REAL getNearestPoint(const COORDS& pt, const COORDS& l1, const COORDS& l2, REAL* pRetDist);


};
