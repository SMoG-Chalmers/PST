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
#include <math.h>

#include <pstalgo/Debug.h>
#include <pstalgo/graph/AxialGraph.h>
#include "../utils/SphereTree.h"
#include "../Platform.h"

#define USE_SPHERE_TREE

#define MIN_LINE_LENGTH 0.01f





CAxialGraph::CAxialGraph()
	: m_WorldOrigin(0,0)
{
}

CAxialGraph::~CAxialGraph()
{
}

void CAxialGraph::clear()
{
	m_points.clear();
	m_lines.clear();
	m_linePoints.clear();
	m_crossings.clear();
	m_lineCrossings.clear();
	m_sphereTree->Release();
	m_tmpLineIdx.clear();
}

void CAxialGraph::createGraph(const LINE* pLines, int nLines,
						    const COORDS* pUnlinks, int nUnlinks,
						    const COORDS* pPoints, int nPoints)
{ 
	using namespace std;

	if (nLines <= 0)
		return;

	// Resize Line Array
	m_lines.reserve(nLines);
	m_lines.resize(nLines);
	memset(&m_lines.front(), 0, m_lines.size() * sizeof(m_lines.front()));

	// Copy Line Coordinates
	m_bbox.min = m_bbox.max = pLines->p1;
	for (int i=0; i<nLines; ++i) {
		m_lines[i].p1 = pLines[i].p1;
		m_lines[i].p2 = pLines[i].p2;
		const auto v = pLines[i].p2 - pLines[i].p1;
		m_lines[i].angle = OrientationAngleFromVector(v);
		m_lines[i].length = v.getLength();
		m_bbox.update(pLines[i].p1);
		m_bbox.update(pLines[i].p2);
	}

	if (pPoints) {
		for (int i=0; i<nPoints; ++i) {
			m_bbox.update(pPoints[i]);
		}
	}

	m_maxDist = sqrt((m_bbox.max.x - m_bbox.min.x) * (m_bbox.max.x - m_bbox.min.x) +
			  		 (m_bbox.max.y - m_bbox.min.y) * (m_bbox.max.y - m_bbox.min.y));

	// Create Sphere Tree
	m_sphereTree.reset(new SphereTree);
	const float a = log(4.f, (float)(m_lines.size() + 1));
	const int num_levels = max(3, (int)(a + .5f) - 1);
	m_sphereTree->Create(m_bbox.min.x, m_bbox.min.y, m_bbox.max.x, m_bbox.max.y, num_levels);
	m_sphereTree->SetLines(&pLines->p1.x, nLines, sizeof(LINE));

	// Find Crossings
	findCrossings(pUnlinks, nUnlinks);

	if (pPoints) {
		// Connect points to network
		auto tick = GetTimeMSec();
		connectPointsToNetwork(pPoints, nPoints);
		m_stat.timeConnectPoints = 0.001f * (GetTimeMSec() - tick);
	}

}

void CAxialGraph::setPointGroups(std::vector<unsigned int>&& points_per_group)
{
	m_PointGroups = std::move(points_per_group);
}

int CAxialGraph::getClosestLine(const COORDS& pt, REAL* pRetDist, REAL* pRetPos) const
{
	int iClosestLine = -1;
	REAL minDist = -1, pos = -1;

	const auto graph_center = (m_bbox.max + m_bbox.min) * .5f;
	const auto max_dist = m_maxDist + (graph_center - pt).getLength();

	float tolerance = 15;
	do
	{
		tolerance *= 2;

		iClosestLine = -1;
		minDist = pos = -1;

		m_sphereTree->TForEachCloseLine(pt.x, pt.y, tolerance, [&](int line_index)
		{
			const auto& l = m_lines[line_index];
			// Find closest point on line
			REAL dist;
			const auto t = getNearestPoint(pt, l.p1, l.p2, &dist);
			// Better than what we've found so far?
			if (iClosestLine < 0 || dist < minDist)
			{
				minDist = dist;
				iClosestLine = line_index;
				pos = t * l.length;
			}
		});

		// IMPORTANT: Only accept this line as the closest one if it is closer than the tolerance
		// we used in the query. If the closest line we found is farther away than the tolerance 
		// then there might be lines that are closer that we can find by increasing tolerance.
		if (minDist >= 0 && minDist < tolerance)
			break;
	} while (tolerance < max_dist);

	if (pRetDist)
		*pRetDist = minDist;

	if (pRetPos)
		*pRetPos = pos;

	return iClosestLine;
}

int CAxialGraph::getLinesFromPoint(const COORDS& ptCenter, float radius, int** ppRetLinesIdx)
{
	if (ppRetLinesIdx)
		*ppRetLinesIdx = NULL;

	if (m_lines.empty()) 
		return 0;

	if (m_tmpLineIdx.size() < m_lines.size())
		m_tmpLineIdx.resize(m_lines.size());


	int nFound = m_sphereTree->GetCloseLines(&m_tmpLineIdx.front(), ptCenter.x, ptCenter.y, radius);
	if (nFound <= 0)
		return 0;

	// Remove lines that are outside the radius
	for (int i=0; i<nFound; ++i) {
		REAL dist;
		getNearestPoint(ptCenter, m_lines[m_tmpLineIdx[i]].p1, m_lines[m_tmpLineIdx[i]].p2, &dist);
		if (dist > radius) {
			--nFound;
			if (i < nFound)
				m_tmpLineIdx[i] = m_tmpLineIdx[nFound];
			--i;
		}
	}

	if (ppRetLinesIdx) 
		*ppRetLinesIdx = &m_tmpLineIdx.front();

	return nFound;
}

int CAxialGraph::getCloseLines(int* pRetIdx, REAL x1, REAL y1, REAL x2, REAL y2)
{
	return m_sphereTree->GetCloseLines(pRetIdx, x1, y1, x2, y2);
}

void CAxialGraph::findCrossings(const COORDS* pUnlinks, int nUnlinks) 
{
	std::vector<int> lineList(m_lines.size());

	struct SCrossMapEntry
	{
		VEC2 m_Point;
		int  m_CrossingIndex;
		int  m_Line0;
		int  m_Line1;
	};
	std::vector<SCrossMapEntry> cross_map;

	// Find Crossings
	cross_map.reserve(m_lines.size() * 2);  // Estimation
	for (int iLine0 = 0; iLine0<(int)m_lines.size() - 1; iLine0++)
	{
		const auto& line0 = m_lines[iLine0];

		if (line0.length < MIN_LINE_LENGTH)
			continue;

	#ifdef USE_SPHERE_TREE
		const int nClose = m_sphereTree->GetCloseLines(&lineList.front(), line0.p1.x, line0.p1.y, line0.p2.x, line0.p2.y);
		for (int i=0; i<nClose; ++i) {
			const int iLine1 = lineList[i];
			// Only store connections to lines with greater index
			if (iLine1 <= iLine0)
				continue; 
	#else
		for (int iLine1=iLine+1; iLine1<(int)m_lines.size(); ++iLine1) {
	#endif

			const auto& line1 = m_lines[iLine1];
			
			if (line1.length < MIN_LINE_LENGTH)
				continue;

			float t0, t1;
			if (FindLineIntersection2(*(LINE*)&line0.p1, *(LINE*)&line1.p1, &t0, &t1)) 
			{
				SCrossMapEntry e;
				e.m_CrossingIndex = -1;  // Not yet known
				e.m_Point = (line0.p1 * (1.f - t0)) + (line0.p2 * t0);
				e.m_Line0 = iLine0;
				e.m_Line1 = iLine1;
				cross_map.push_back(e);
			}
		}
	}

	// Unlink Crossings
	// NOTE: We only unlink actual crossings, points where lines meet at end-points are not removed.
	// NOTE: This algorithm has complexity O(n^2). It could be made
	//       much more efficient with a Space Partitioning Tree.
	for (int iUnlink = 0; iUnlink < nUnlinks; ++iUnlink) 
	{
		const COORDS& u = pUnlinks[iUnlink];

		// Find closest crossing for this unlink point
		int iClosestCrossing = -1;
		REAL minSqrDist = -1;
		for (size_t i = 0; i < cross_map.size(); ++i)
		{
			const auto& c = cross_map[i];
			if (c.m_Line0 < 0)
				continue;  // Already unlinked
			const REAL sqrDist = (c.m_Point - u).getLengthSqr();
			if (iClosestCrossing < 0 || sqrDist < minSqrDist) {
				// Verify it is an actual croossing - not only a point where two end-points connect
				const auto& line0 = m_lines[c.m_Line0];
				if (line0.p1 != c.m_Point && line0.p2 != c.m_Point)
				{
					minSqrDist = sqrDist;
					iClosestCrossing = (int)i;
				}
			}
		}

		if (iClosestCrossing >= 0)
			cross_map[iClosestCrossing].m_Line0 = -1;  // Mark as unlinked
	}

	// Remove unlinked crossings
	{
		size_t n = 0;
		for (size_t i = 0; i < cross_map.size(); ++i)
		{
			if (cross_map[i].m_Line0 < 0)
				continue;
			if (n != i)
				cross_map[n] = cross_map[i];
			++n;
		}
		cross_map.resize(n);
	}

	// Create crossing array
	{
		// Create an ordering of line crossings by coordinate
		std::vector<unsigned int> order(cross_map.size());
		for (unsigned int i = 0; i < order.size(); ++i)
			order[i] = i;
		std::sort(order.begin(), order.end(), [&](unsigned int a, unsigned int b) -> bool
		{
			const auto& p0 = cross_map[a].m_Point;
			const auto& p1 = cross_map[b].m_Point;
			return (p0.x == p1.x) ? (p0.y < p1.y) : (p0.x < p1.x);
		});
		
		if (!order.empty())
		{
			// Count unique crossings and store crossing index in cross_map
			cross_map[order[0]].m_CrossingIndex = 0;
			unsigned int n = 0;
			for (unsigned int i = 1; i < order.size(); ++i)
			{
				if (cross_map[order[i]].m_Point != cross_map[order[i - 1]].m_Point)
					++n;
				cross_map[order[i]].m_CrossingIndex = n;
			}
			++n;
			m_crossings.resize(n);  // Allocate array of unique crossings

			// Fill-in array of unique crossings
			int last_crossing = -1;
			n = 0;
			for (unsigned int i = 0; i < order.size(); ++i)
			{
				const auto& c = cross_map[order[i]];
				if (c.m_CrossingIndex != last_crossing)
				{
					last_crossing = c.m_CrossingIndex;
					m_crossings[c.m_CrossingIndex].pt = c.m_Point;
					m_crossings[c.m_CrossingIndex].nLines = 1;
				}
				else
				{
					++m_crossings[c.m_CrossingIndex].nLines;
				}
			}
		}
	}

	// Count crossings per line
	for (auto& line : m_lines)
		line.nCrossings = 0;
	for (const auto& c : cross_map)
	{
		++m_lines[c.m_Line0].nCrossings;
		++m_lines[c.m_Line1].nCrossings;
	}

	// Calculate index of first line crossing for each line
	{
		unsigned int n = 0;
		for (auto& line : m_lines)
		{
			line.iFirstCrossing = n;
			n += line.nCrossings;
			line.nCrossings = 0;
		}
		ASSERT(cross_map.size() * 2 == n);
	}

	// Create line crossings
	m_lineCrossings.resize(cross_map.size() * 2);
	for (size_t i = 0; i < cross_map.size(); ++i)
	{
		const auto& c = cross_map[i];
		auto& line0 = m_lines[c.m_Line0];
		auto& line1 = m_lines[c.m_Line1];
		const auto lc0_index = line0.iFirstCrossing + line0.nCrossings++;
		const auto lc1_index = line1.iFirstCrossing + line1.nCrossings++;
		auto& lc0 = m_lineCrossings[lc0_index];
		auto& lc1 = m_lineCrossings[lc1_index];
		lc0.iCrossing = c.m_CrossingIndex;
		lc0.iLine = c.m_Line0;
		lc0.iOpposite = lc1_index;
		lc0.linePos = (c.m_Point == line0.p2) ? line0.length : (dot(c.m_Point - line0.p1, line0.p2 - line0.p1) / line0.length);
		lc1.iCrossing = c.m_CrossingIndex;
		lc1.iLine = c.m_Line1;
		lc1.iOpposite = lc0_index;
		lc1.linePos = (c.m_Point == line1.p2) ? line1.length : (dot(c.m_Point - line1.p1, line1.p2 - line1.p1) / line1.length);
	}
}

void CAxialGraph::updateLinesPerCrossingCount()
{
	for (size_t i = 0; i < m_crossings.size(); ++i)
		m_crossings[i].nLines = 0;
	std::vector<int> found;
	for (size_t i = 0; i < m_lines.size(); ++i)
	{
		found.clear();
		const NETWORKLINE& line = m_lines[i];
		for (int ilc = 0; ilc < line.nCrossings; ++ilc)
		{
			const LINECROSSING& lc = m_lineCrossings[line.iFirstCrossing+ilc];
			if (std::find(found.begin(), found.end(), lc.iCrossing) != found.end())
				continue; // Already increased count for this crossing
			++m_crossings[lc.iCrossing].nLines;
			found.push_back(lc.iCrossing);
		}
	}
}


void CAxialGraph::connectPointsToNetwork(const COORDS* pPoints, int nPoints)
{

	if (!nPoints || !pPoints || m_lines.empty())
		return;

	for (int i=0; i<(int)m_lines.size(); ++i)
		m_lines[i].nPoints = 0;

	m_points.resize(nPoints);
	memset(&m_points.front(), 0, nPoints * sizeof(m_points.front()));

	for (int iPoint = 0;  iPoint < nPoints; ++iPoint) {

		POINT& pt = m_points[iPoint];
		pt.coords = pPoints[iPoint];
		
		pt.iLine = getClosestLine(pt.coords, &pt.distFromLine, &pt.linePos);

		if (pt.iLine >= 0) 
			++m_lines[pt.iLine].nPoints;

	}


	// Create Line to point indexes

	m_linePoints.resize(m_points.size());

	m_lines[0].iFirstPoint = 0;
	for (int i=1; i<(int)m_lines.size(); ++i) {
		m_lines[i].iFirstPoint = m_lines[i-1].iFirstPoint + m_lines[i-1].nPoints;
		m_lines[i-1].nPoints = 0;
	}
	m_lines.back().nPoints = 0;

	for (int i=0; i<(int)m_points.size(); ++i) {
		POINT& pt = m_points[i];
		if (pt.iLine < 0)
			continue;
		NETWORKLINE& l = m_lines[pt.iLine];
		m_linePoints[l.iFirstPoint + l.nPoints] = i;
		++l.nPoints;
	}


}


///////////////////////////////////////////////////////////////////////////////
//
//  getNearestPoint(...)
//
//  Finds the closest point on a line to a specified point.
//
//  Returns: The position on the line [0..1]
//

REAL CAxialGraph::getNearestPoint(const COORDS& pt, const COORDS& l1, const COORDS& l2, REAL* pRetDist)
{
	REAL dx = l2.x - l1.x;
	REAL dy = l2.y - l1.y;
	
	REAL t = ((dx * (pt.x - l1.x)) + (dy * (pt.y - l1.y))) / ((dx*dx)+(dy*dy));
	if (t < 0) 
		t = 0;
	else if (t > 1)
		t = 1;

	if (pRetDist) {
		REAL x = l1.x + (dx * t) - pt.x;
		REAL y = l1.y + (dy * t) - pt.y;
		*pRetDist = sqrt((x*x)+(y*y));
	}

	return t;
}


void CAxialGraph::BBOX::update(const COORDS& c)
{
	if (c.x < min.x) min.x = c.x;
	if (c.x > max.x) max.x = c.x;
	if (c.y < min.y) min.y = c.y;
	if (c.y > max.y) max.y = c.y;
}

