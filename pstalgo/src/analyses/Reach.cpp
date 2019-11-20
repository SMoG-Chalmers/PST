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

#include <algorithm>

#include <pstalgo/analyses/Reach.h>
#include <pstalgo/geometry/ConvexHull.h>
#include <pstalgo/BFS.h>
#include <pstalgo/utils/BitVector.h>
#include <pstalgo/Limits.h>
#include <pstalgo/graph/AxialGraph.h>
#include "../ProgressUtil.h"

namespace
{
	template <typename TVec>
	REAL TGetLineMidPointDist(const TVec& a1, const TVec& a2, const TVec& b1, const TVec& b2)
	{
		TVec a((a1.x + a2.x) * 0.5f, (a1.y + a2.y) * 0.5f);
		TVec b((b1.x + b2.x) * 0.5f, (b1.y + b2.y) * 0.5f);
		TVec diff(a.x - b.x, a.y - b.y);
		return sqrt(diff.x*diff.x + diff.y*diff.y);
	}
}

class CReachAlgorithm : public CPSTBFS 
{
	typedef CPSTBFS super_t;
public:

	CReachAlgorithm()
		: m_ReachedCount(nullptr)
		, m_ReachedLength(nullptr)
		, m_ReachedArea(nullptr)
	{
	}

	void Run(CAxialGraph* pGraph, 
			 const LIMITS& limits, 
			 const double2* origin_points,
			 unsigned int origin_point_count, 
			 unsigned int* ret_reached_count, 
			 float* ret_reached_length, 
			 float* ret_reached_area,
			 IProgressCallback& progress)
	{
		super_t::init(pGraph, TARGET_LINES, DIST_NONE, limits);
		m_TargetReachedBits.resize(getTargetCount());

		const unsigned int origin_count = origin_points ? origin_point_count : pGraph->getLineCount();

		if (ret_reached_count)
			memset(ret_reached_count, 0, origin_count * sizeof(ret_reached_count[0]));
		m_ReachedCount = ret_reached_count;

		if (ret_reached_length)
			memset(ret_reached_length, 0, origin_count * sizeof(ret_reached_length[0]));
		m_ReachedLength = ret_reached_length;

		if (ret_reached_area)
			memset(ret_reached_area, 0, origin_count * sizeof(ret_reached_area[0]));
		m_ReachedArea = ret_reached_area;

		if (origin_points)
		{
			for (unsigned int point_index = 0; point_index < origin_point_count; ++point_index)
			{
				processPoint(point_index, pGraph->worldToLocal(origin_points[point_index]));
				progress.ReportProgress((float)(point_index + 1) / origin_point_count);
			}
		}
		else
		{
			for (int line_index = 0; line_index < pGraph->getLineCount(); ++line_index)
			{
				processLine(line_index);
				progress.ReportProgress((float)(line_index + 1) / pGraph->getLineCount());
			}
		}
	}

private:
	void processPoint(unsigned int index, const float2& pt)
	{
		m_iCurrOrigin = (int)index;

		m_ReachedEndPoints.clear();

		if (LIMITS::MASK_STRAIGHT == m_lim.mask)
		{
			int nLines = m_pGraph->getLineCount();
			for (int i = 0; (i < nLines) && !getCancel(); ++i)
			{
				const CAxialGraph::NETWORKLINE& line = m_pGraph->getLine(i);
				if (((line.p1 + line.p2) *.5f - pt).getLengthSqr() < m_lim.straightSqr)
				{
					if (m_ReachedCount)
						m_ReachedCount[index]++;
					if (m_ReachedLength)
						m_ReachedLength[index] += line.length;
					if (m_ReachedArea)
					{
						m_ReachedEndPoints.push_back(line.p1);
						m_ReachedEndPoints.push_back(line.p2);
					}
				}
			}
		}
		else
		{
			m_iCurrOrigin = index;

			m_origin = pt;

			m_TargetReachedBits.clearAll();

			clrVisitedLineCrossings();  // NOTE: Shouldn't this be in CPSTPBS::doBFSFromPoint (called below)!?!?!?

			doBFSFromPoint(pt);
		}

		if (m_ReachedArea)
		{
			m_ReachedEndPoints.push_back(pt);
			m_ReachedArea[index] = CalculateReachedArea();
		}
	}

	void processLine(int iLine)
	{
		m_ReachedEndPoints.clear();

		if (LIMITS::MASK_STRAIGHT == m_lim.mask)
		{
			const CAxialGraph::NETWORKLINE& l1 = m_pGraph->getLine(iLine);

			int nLines = m_pGraph->getLineCount();
			for (int i = 0; (i < nLines) && !getCancel(); ++i) {

				const CAxialGraph::NETWORKLINE& l2 = m_pGraph->getLine(i);

				const float dist = TGetLineMidPointDist(l1.p1, l1.p2, l2.p1, l2.p2);

				if (dist*dist <= m_lim.straightSqr)
				{
					if (m_ReachedCount)
						m_ReachedCount[iLine]++;
					if (m_ReachedLength)
						m_ReachedLength[iLine] += l2.length;
					if (m_ReachedArea)
					{
						m_ReachedEndPoints.push_back(l2.p1);
						m_ReachedEndPoints.push_back(l2.p2);
					}
				}

			}
		}
		else
		{
			m_iCurrOrigin = iLine;

			m_TargetReachedBits.clearAll();

			doBFSFromLine(iLine);
		}

		if (m_ReachedArea)
			m_ReachedArea[iLine] = CalculateReachedArea();
	}

	void visitBFS(int iTarget, const DIST& /*dist*/) override
	{
		if (m_TargetReachedBits.get(iTarget))
			return;

		m_TargetReachedBits.set(iTarget);

		if (m_ReachedCount)
			m_ReachedCount[m_iCurrOrigin]++;

		const CAxialGraph::NETWORKLINE& line = m_pGraph->getLine(iTarget);

		if (m_ReachedLength)
			m_ReachedLength[m_iCurrOrigin] += line.length;

		if (m_ReachedArea)
		{
			m_ReachedEndPoints.push_back(line.p1);
			m_ReachedEndPoints.push_back(line.p2);
		}
	}

	float CalculateReachedArea()
	{
		if (LIMITS::MASK_STRAIGHT == m_lim.mask)
		{
			// Use exact area instead of convex hull when radius specified as straight line distance.
			return m_lim.straightSqr * 3.1415927f;
		}
		else
		{
			if (m_ReachedEndPoints.size() < 3)
				return 0;

			// Sort
			std::sort(m_ReachedEndPoints.begin(), m_ReachedEndPoints.end(), [&](const float2& a, const float2& b) -> bool
			{
				if (a.x > b.x)
					return false;
				return (a.x < b.x) ? true : (a.y < b.y);
			});

			// Remove duplicates
			unsigned int n = 1;
			for (unsigned int i = 1; i < m_ReachedEndPoints.size(); ++i)
			{
				if (m_ReachedEndPoints[n - 1] != m_ReachedEndPoints[i])
				{
					if (n != i)
						m_ReachedEndPoints[n] = m_ReachedEndPoints[i];
					++n;
				}
			}
			m_ReachedEndPoints.resize(n);

			if (m_ReachedEndPoints.size() < 3)
				return 0;

			// Calculate convex hull
			m_ConvexHull.resize(m_ReachedEndPoints.size());
			const int hull_point_count = ConvexHull(&m_ReachedEndPoints.front(), (int)m_ReachedEndPoints.size(), &m_ConvexHull.front());
			m_ConvexHull.resize(hull_point_count);

			// Calculate area of convex hull
			return ConvexPolyArea(&m_ConvexHull.front(), hull_point_count);
		}
	}

	int           m_iCurrOrigin;
	CBitVector    m_TargetReachedBits;
	unsigned int* m_ReachedCount;
	float*        m_ReachedLength;
	float*        m_ReachedArea;

	// Area Calculation
	std::vector<COORDS> m_ReachedEndPoints;
	std::vector<COORDS> m_ConvexHull;
};


PSTADllExport bool PSTAReach(const SPSTAReachDesc* desc)
{
	if (desc->VERSION != desc->m_Version)
		return false;

	CReachAlgorithm algo;
	CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);
	algo.Run(
		(CAxialGraph*)desc->m_Graph,
		LimitsFromSPSTARadii(desc->m_Radius),
		desc->m_OriginCoords,
		desc->m_OriginCount,
		desc->m_OutReachedCount,
		desc->m_OutReachedLength,
		desc->m_OutReachedArea,
		progress);

	return true;
}
