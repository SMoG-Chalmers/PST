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

#include <cmath>
#include <queue>

#include <pstalgo/BFS.h>
#include <pstalgo/Debug.h>
#include <pstalgo/graph/AxialGraph.h>

CPSTBFS::CPSTBFS()
: m_pGraph(nullptr)
, m_pDest(nullptr)
, m_nDest(0)
, m_bCancel(false)
{

}

CPSTBFS::~CPSTBFS()
{

}

void CPSTBFS::init(CAxialGraph* pGraph, Target target, DistanceType distType, const LIMITS& limits)
{
	m_pGraph = pGraph;
	m_target = target;
	m_lim = limits;

	m_distType = distType;

	m_lcVisitedBits.resize((pGraph->getLineCrossingCount() + 31) >> 5);
	clrVisitedLineCrossings();

	m_lcCheckPoints.resize(pGraph->getLineCrossingCount());

	switch (target) {
	case TARGET_POINTS:
		break;
	case TARGET_LINES:
		break;
	case TARGET_CROSSINGS:
		break;
	}

}

int CPSTBFS::getTargetCount()
{
	ASSERT(m_pGraph);
	switch (m_target) {
	case TARGET_POINTS:
		return m_pGraph->getPointCount();
	case TARGET_LINES:
		return m_pGraph->getLineCount();
	case TARGET_CROSSINGS:
		return m_pGraph->getCrossingCount();
	}
	ASSERT(false);
	return 0;
}

void CPSTBFS::doBFSFromPoint(const COORDS& pt)
{
	ASSERT(m_pGraph);

	REAL distToLine, pos;
	int iLine = m_pGraph->getClosestLine(pt, &distToLine, &pos);

	if (iLine < 0)
		return;

	m_origin = pt;

	DIST dist;
	memset(&dist, 0, sizeof(dist));
	dist.walking = distToLine;
	dist.axmeter = distToLine;

	doBFS(iLine, pos, dist);
}

void CPSTBFS::doBFSFromLine(int iLine)
{
	clrVisitedLineCrossings();

	CAxialGraph::NETWORKLINE& line = m_pGraph->getLine(iLine);

	// Origin is mid point of origin line
	m_origin = (line.p1 + line.p2) * 0.5f;

	// Do BFS from mid-point of line
	DIST dist;
	memset(&dist, 0, sizeof(dist));
	doBFS(iLine, line.length * .5f, dist);
}

void CPSTBFS::doBFS(int iStartLine, float startPos, const DIST& startDist)
{
	using namespace std;

	std::queue<STATE> queue;  // TODO: Move out to avoid reallocation on every call!

	{
		STATE initial_state;
		initial_state.iLineCrossing = -1;
		initial_state.dist = startDist;
		initial_state.lastAngle = -1.0f;
		queue.push(initial_state);
	}

	while (!queue.empty() && !getCancel())
	{
		// Get next state from queue
		const STATE s = queue.front();
		queue.pop();

		const auto* from_lc = (s.iLineCrossing >= 0) ? &m_pGraph->getLineCrossing(s.iLineCrossing) : nullptr;

		const int   iLine = from_lc ? from_lc->iLine : iStartLine;
		const float linePos = from_lc ? from_lc->linePos : startPos;
		const int   iCrossing = from_lc ? from_lc->iCrossing : -1;  // IMPORTANT: Crossing is not the same as "line crossing"!

		// Calculate angle 
		float fowdAccAngle, backAccAngle;
		fowdAccAngle = backAccAngle = s.dist.angle;
		if (s.lastAngle >= 0.0f) {
			float angdiff = angleDiff(m_pGraph->getLine(iLine).angle, s.lastAngle);
			fowdAccAngle += angdiff;
			backAccAngle += 180.0f - angdiff;
		}

		if (s.iLineCrossing >= 0) {
			// We came in through a "line crossing" (i.e. this is not the first time we entered the graph).
			// NOTE: A "line crossing" is unique for this particular line, it is an "entry/exit on this line".
			CHECKPOINT& c = m_lcCheckPoints[s.iLineCrossing];
			if (hasVisitedLineCrossing(s.iLineCrossing)) {
				// We have come in through this crossing before, check if we have any better metrics this time.
				if (!updateCheckPoint(c, s.dist, fowdAccAngle, backAccAngle))
					continue; // We had better values last time we visited this line crossing
			}
			else {
				// This is the first time we've come in through this line crossing. Mark it
				// as visited and note our metrics.
				setVisitedLineCrossing(s.iLineCrossing);
				c.walking = s.dist.walking;
				c.turns = s.dist.turns;
				c.fwAngle = fowdAccAngle;
				c.bkAngle = backAccAngle;
				c.axmeter = s.dist.axmeter;
			}
		}

		const CAxialGraph::NETWORKLINE& line = m_pGraph->getLine(iLine);

		// Perform result update if we have lines as target
		if (TARGET_LINES == m_target) {
			CPSTBFS::DIST dist = s.dist;
			dist.angle = (linePos < (line.length * 0.5f)) ? fowdAccAngle : backAccAngle;
			dist.walking += abs(line.length * 0.5f - linePos);  // Add distance to mid point of line
			if (testLimit(dist)) {
				visitBFS(iLine, dist);
			}
		}

		// Loop through all line crossings along this line, update their checkpoints
		// and queue them for further traversal.
		for (int i = 0; i<line.nCrossings; ++i)
		{
			const int iLC = line.iFirstCrossing + i;

			// We don't need to update checkpoint of line crossing we just came through,
			// and there is no point in queueing that line crossing for traversal either.
			if (iLC == s.iLineCrossing)
				continue;

			const CAxialGraph::LINECROSSING& lc = m_pGraph->getLineCrossing(iLC);

			// Test straight line limit
			if ((LIMITS::MASK_STRAIGHT & m_lim.mask) && !testStraightLineLimit(m_pGraph->getCrossing(lc.iCrossing).pt))
				continue;

			STATE sNext;

			// Calculate distance metrics for this line crossing
			sNext.dist = s.dist;
			if (lc.linePos > linePos) {
				// Forewards
				float distAlongThisLine = lc.linePos - linePos;
				sNext.dist.walking = s.dist.walking + distAlongThisLine;
				sNext.dist.angle = fowdAccAngle;
				sNext.dist.axmeter = s.dist.axmeter + (distAlongThisLine * (s.dist.turns + 1));
				sNext.lastAngle = line.angle;
			}
			else if (lc.linePos < linePos) {
				// Backwards
				float distAlongThisLine = linePos - lc.linePos;
				sNext.dist.walking = s.dist.walking + distAlongThisLine;
				sNext.dist.angle = backAccAngle;
				sNext.dist.axmeter = s.dist.axmeter + (distAlongThisLine * (s.dist.turns + 1));
				sNext.lastAngle = reverseAngle(line.angle);
			}
			else {
				// Leaving line at same point as we entered
				sNext.lastAngle = s.lastAngle;
			}

			// Test if we can reach this line crossing within our radius limit
			if (!testLimit(sNext.dist))
				continue;

			// Update the checkpoint of this line crossing with our current distance metrics
			// NOTE: A "line crossing" is unique for this particular line, it is an "entry/exit on this line".
			CHECKPOINT& c = m_lcCheckPoints[iLC];
			if (hasVisitedLineCrossing(iLC)) {
				// We've visited this line crossing before
				if (!updateCheckPoint(c, sNext.dist, fowdAccAngle, backAccAngle))
					continue; // We had better values last time we visited this line crossing
			}
			else {
				// First time this line crossing is visited
				setVisitedLineCrossing(iLC);
				c.walking = sNext.dist.walking;
				c.turns = sNext.dist.turns;
				c.fwAngle = fowdAccAngle;
				c.bkAngle = backAccAngle;
				c.axmeter = sNext.dist.axmeter;
			}

			// Perform result update if we have crossings as target
			if (TARGET_CROSSINGS == m_target)
				visitBFS(lc.iCrossing, sNext.dist);

			// --- From this point we handle queueing for further traversal ---

			// Do not allow leaving at same crossing (NOTE: Not 'line crossing'!) we came from
			if (lc.iCrossing == iCrossing)
				continue;

			// Do not allow leaving at same exact position as we entered this line
			// (unless this is entry line for search). This SHOULD be a redundant
			// check, since it should be handled with checks for same CROSSING and 
			// LINE CROSSING above, but we do it here as an extra safety check.
			if (s.iLineCrossing >= 0 && lc.linePos == linePos)
				continue;

			// Lookup opposite line crossing to queue the traversal towwards.
			sNext.iLineCrossing = lc.iOpposite;

			// Add this step we're about to take
			++sNext.dist.turns;

			if (!testLimit(sNext.dist))
				continue;

			// Ok, we passed all tests. Queue for further traversal.
			queue.push(sNext);
		}

		if (TARGET_POINTS == m_target) {

			for (int i = 0; i<line.nPoints; ++i) {

				int iPoint = m_pGraph->getLinePoint(line.iFirstPoint + i);
				const CAxialGraph::POINT& p = m_pGraph->getPoint(iPoint);

				// Test straight line limit
				if ((LIMITS::MASK_STRAIGHT & m_lim.mask) && !testStraightLineLimit(p.coords))
					continue;

				DIST d = s.dist;
				if ((m_origin.x == p.coords.x) && (m_origin.y == p.coords.y)) {
					// Back to Origin Point, no distance
					memset(&d, 0, sizeof(d));
				}
				else {
					d.walking += p.distFromLine;
					if (p.linePos > linePos) {
						// Forewards
						float distAlongThisLine = p.linePos - linePos;
						d.walking += distAlongThisLine;
						d.angle = fowdAccAngle;
						d.axmeter += (distAlongThisLine + p.distFromLine) * (d.turns + 1);
					}
					else if (p.linePos < linePos) {
						// Backwards
						float distAlongThisLine = linePos - p.linePos;
						d.walking += distAlongThisLine;
						d.angle = backAccAngle;
						d.axmeter += (distAlongThisLine + p.distFromLine) * (d.turns + 1);
					}
				}

				if (testLimit(d)) {
					visitBFS(iPoint, d);
				}

			}

		}

	}

}

bool CPSTBFS::testLimit(const DIST& dist)
{
	if ((LIMITS::MASK_WALKING & m_lim.mask) && (dist.walking > m_lim.walking))
		return false;
	if ((LIMITS::MASK_TURNS & m_lim.mask) && (dist.turns > m_lim.turns))
		return false;
	if ((LIMITS::MASK_ANGLE & m_lim.mask) && (dist.angle > m_lim.angle))
		return false;
	if ((LIMITS::MASK_AXMETER & m_lim.mask) && (dist.axmeter > m_lim.axmeter))
		return false;
	return true;
}

bool CPSTBFS::testStraightLineLimit(const COORDS& pt)
{
	if (!(LIMITS::MASK_STRAIGHT & m_lim.mask))
		return true;
	float dx = pt.x - m_origin.x;
	float dy = pt.y - m_origin.y;
	return (dx*dx + dy*dy <= m_lim.straightSqr);
}

//bool CPSTBFS::updateDist(DIST& d, const DIST& dNew)
bool CPSTBFS::updateCheckPoint(CHECKPOINT& c, const DIST& d, float fwAngle, float bkAngle)
{
	bool bHasImprovements = false;
	bool bHasWorse = false;

	if ((DIST_WALKING == m_distType) ||
		(DIST_AXMETER == m_distType) ||
		(LIMITS::MASK_WALKING & m_lim.mask)) {
		if (d.walking < c.walking)
			bHasImprovements = true;
		else if (d.walking > c.walking)
			bHasWorse = true;
	}

	if ((DIST_LINES == m_distType) ||
		(DIST_AXMETER == m_distType) ||
		(LIMITS::MASK_TURNS & m_lim.mask)) {
		if (d.turns < c.turns)
			bHasImprovements = true;
		else if (d.turns > c.turns)
			bHasWorse = true;
	}

	if ((DIST_ANGULAR == m_distType) ||
		(LIMITS::MASK_ANGLE & m_lim.mask)) {
		if ((fwAngle < c.fwAngle) || (bkAngle < c.bkAngle))
			bHasImprovements = true;
		if ((fwAngle > c.fwAngle) || (bkAngle > c.bkAngle))
			bHasWorse = true;
	}

	if ((DIST_AXMETER == m_distType) ||
		(LIMITS::MASK_AXMETER & m_lim.mask)) {
		if (d.axmeter < c.axmeter)
			bHasImprovements = true;
		else if (d.axmeter > c.axmeter)
			bHasWorse = true;
	}

	if (!bHasImprovements)
		return false;

	// Update Values
	if (!bHasWorse) {
		c.walking = d.walking;
		c.turns = d.turns;
		c.fwAngle = fwAngle;
		c.bkAngle = bkAngle;
		c.axmeter = d.axmeter;
	}

	return true;
}
