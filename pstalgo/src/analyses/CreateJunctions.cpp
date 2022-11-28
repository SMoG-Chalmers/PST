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
#include <cmath>
#include <memory>
#include <vector>

#include <pstalgo/analyses/CreateJunctions.h>
#include <pstalgo/geometry/AABSPTree.h>
#include <pstalgo/Debug.h>
#include <pstalgo/maths.h>
#include "../ProgressUtil.h"

namespace
{
	const float MIN_TAIL_FRACTION = 0.02f;
}

class CCreateJunctions : public IPSTAlgo
{
public:
	bool Run(const SCreateJunctionsDesc& desc, SCreateJunctionsRes& res)
	{
		if (0 == desc.m_LineCount0)
			return true;
			
		CPSTAlgoProgressCallback progress(desc.m_ProgressCallback, desc.m_ProgressCallbackUser);
		progress.ReportStatus("Searching for junctions");

		// Bounding box
		const unsigned int coords_count_0 = desc.m_Lines0 ? *std::max_element(desc.m_Lines0, desc.m_Lines0 + (desc.m_LineCount0 * 2)) + 1 : (desc.m_LineCount0 * 2);
		const CRectd bb = CRectd::BBFromPoints(desc.m_Coords0, coords_count_0);
		const double2 center(bb.CenterX(), bb.CenterY());

		// Create lines, transformed to local coordinates for better precision
		std::vector<CLine2f> lines0;
		CreateLines(desc.m_Coords0, desc.m_Lines0, desc.m_LineCount0, center, lines0);

		if (nullptr == desc.m_Coords1)
		{
			// Single table
			FindJunctions(lines0.data(), (unsigned int)lines0.size(), m_Points, progress);
		}
		else
		{
			// Multi table
			std::vector<CLine2f> lines1;
			CreateLines(desc.m_Coords1, desc.m_Lines1, desc.m_LineCount1, center, lines1);
			FindJunctions(lines0.data(), (unsigned int)lines0.size(), lines1.data(), (unsigned int)lines1.size(), m_Points, progress);
		}

		// Transform coordinates back to absolute coordinates
		for (auto& pt : m_Points)
			pt += center;

		// Process unlinks
		if (desc.m_UnlinkCount)
		{
			ASSERT(desc.m_UnlinkCoords);
			ProcessUnlinks(desc.m_UnlinkCoords, desc.m_UnlinkCount, m_Points);
		}

		res.m_PointCoords = (double*)m_Points.data();
		res.m_PointCount = (unsigned int)m_Points.size();

		return true;
	}

private:
	
	void CreateLines(const double2* coords, unsigned int* lines, unsigned int line_count, const double2& ref, std::vector<CLine2f>& ret_lines)
	{
		ret_lines.resize(line_count);
		for (unsigned int i = 0; i < line_count; ++i)
		{
			unsigned int p0 = i << 1, p1 = (i << 1) + 1;
			if (lines)
			{
				p0 = lines[p0];
				p1 = lines[p1];
			}
			auto& l = ret_lines[i];
			l.p1.x = (float)(coords[p0].x - ref.x);
			l.p1.y = (float)(coords[p0].y - ref.y);
			l.p2.x = (float)(coords[p1].x - ref.x);
			l.p2.y = (float)(coords[p1].y - ref.y);
		}
	}

	void FindJunctions(const CLine2f* lines, unsigned int line_count, std::vector<double2>& ret_junctions, IProgressCallback& progress)
	{
		using namespace std;

		CLineAABSPTree bsp = CLineAABSPTree::Create(reinterpret_cast<const float2*>(lines), line_count, 16);

		std::vector<CLineAABSPTree::SObjectSet> sets;

		std::vector<unsigned int> tmp;

		for (unsigned int l0_index = 0; l0_index < line_count; ++l0_index)
		{
			const auto& l0 = lines[l0_index];

			if (l0.p1 == l0.p2)
				continue;  // Zero length

			bsp.TestCapsule(l0.p1, l0.p2, 0, sets);

			tmp.clear();

			for (const auto& s : sets)
			{
				for (unsigned int o = s.m_FirstObject; o < s.m_FirstObject + s.m_Count; ++o)
				{
					const unsigned int l1_index = bsp.GetLineIndex(o);

					if (l1_index <= l0_index)
						continue;  // Only compare against lines with higher indices (to only compare a pair once)

					if (tmp.end() != std::find(tmp.cbegin(), tmp.cend(), l1_index))
						continue;

					tmp.push_back(l1_index);

					const auto& l1 = lines[l1_index];

					if (l1.p1 == l1.p2)
						continue; // Zero length

					float t0, t1;
					if (!FindLineIntersection2(l0, l1, &t0, &t1))
						continue;

					// Calculate intersection coordinates (on line 0)
					const double2 pt(
						lerp(l0.p1.x, l0.p2.x, t0),
						lerp(l0.p1.y, l0.p2.y, t0));

					// Generate only one point if the lines meet at enpoints, or two points otherwise.
					ret_junctions.push_back(pt);
					if ((.5f - abs(t0 - .5f) >= MIN_TAIL_FRACTION) ||
						(.5f - abs(t1 - .5f) >= MIN_TAIL_FRACTION))
						ret_junctions.push_back(pt);
				}
			}

			progress.ReportProgress((float)(l0_index + 1) / line_count);
		}
	
		const bool remove_unique_points = true;
		SortAndRemoveDuplicates(ret_junctions, remove_unique_points);
	}
	
	void FindJunctions(const CLine2f* lines0, unsigned int line_count0, const CLine2f* lines1, unsigned int line_count1, std::vector<double2>& ret_junctions, IProgressCallback& progress)
	{
		CLineAABSPTree bsp = CLineAABSPTree::Create(reinterpret_cast<const float2*>(lines0), line_count0, 16);

		std::vector<CLineAABSPTree::SObjectSet> sets;

		std::vector<unsigned int> tmp;

		for (unsigned int l1_index = 0; l1_index < line_count1; ++l1_index)
		{
			const auto& l1 = lines1[l1_index];

			if (l1.p1 == l1.p2)
				continue;  // Zero length

			bsp.TestCapsule(l1.p1, l1.p2, 0, sets);

			tmp.clear();

			for (const auto& s : sets)
			{
				for (unsigned int o = s.m_FirstObject; o < s.m_FirstObject + s.m_Count; ++o)
				{
					const unsigned int l0_index = bsp.GetLineIndex(o);

					if (tmp.end() != std::find(tmp.cbegin(), tmp.cend(), l0_index))
						continue;

					tmp.push_back(l0_index);

					const auto& l0 = lines0[l0_index];

					if (l0.p1 == l0.p2)
						continue; // Zero length

					float t0, t1;
					if (!FindLineIntersection2(l0, l1, &t0, &t1))
						continue;

					// Calculate intersection coordinates (on line 0)
					const double2 pt(
						lerp(l0.p1.x, l0.p2.x, t0),
						lerp(l0.p1.y, l0.p2.y, t0));

					ret_junctions.push_back(pt);
				}
			}
		
			progress.ReportProgress((float)(l1_index + 1) / line_count1);
		}

		const bool remove_unique_points = false;
		SortAndRemoveDuplicates(ret_junctions, remove_unique_points);
	}

	void SortAndRemoveDuplicates(std::vector<double2>& pts, bool remove_unique_points)
	{
		std::sort(pts.begin(), pts.end(), [](const double2& lhs, const double2& rhs)
		{
			return (lhs.x == rhs.x) ? (lhs.y < rhs.y) : (lhs.x < rhs.x);
		});

		unsigned int nPts = 0;
		unsigned int i = 0;
		while (i < pts.size()) {
			// skip until last index of equal points
			unsigned int nEqu = 1;
			for (; (i < pts.size() - 1) && (pts[i + 1] == pts[i]); ++i, ++nEqu);
			if (!remove_unique_points || nEqu > 1)
			{
				if (i != nPts) {
					pts[nPts] = pts[i];
				}
				++nPts;
			}
			++i;
		}

		pts.resize(nPts);
	}

	void ProcessUnlinks(const double2* unlinks, unsigned int unlink_count, std::vector<double2>& pts)
	{
		// Using brute force solution here since there are usually quite few unlinks...

		for (size_t iUnlink = 0; iUnlink < unlink_count; ++iUnlink)
		{
			const auto& up = unlinks[iUnlink];

			int iClosest = -1;
			double minDist = std::numeric_limits<double>::infinity();

			for (int iPoint = 0; iPoint < (int)pts.size(); ++iPoint)
			{
				const auto& pt = pts[iPoint];
				if (std::isnan(pt.x))
					continue;
				const auto dist = (pt - up).getLengthSqr();
				if ((iClosest < 0) || (dist < minDist)) 
				{
					iClosest = iPoint;
					minDist = dist;
				}
			}

			if (iClosest >= 0)
				pts[iClosest].x = std::numeric_limits<double>::quiet_NaN();
		}

		unsigned int n = 0;
		for (size_t i = 0; i < pts.size(); ++i)
		{
			if (!std::isnan(pts[i].x) && (i != n))
				pts[n++] = pts[i];
		}
		pts.resize(n);
	}

	std::vector<double2> m_Points;
};

PSTADllExport IPSTAlgo* PSTACreateJunctions(const SCreateJunctionsDesc* desc, SCreateJunctionsRes* res)
{
	if ((desc->VERSION != desc->m_Version) ||
		(res->VERSION != res->m_Version))
		return nullptr;

	auto algo = std::unique_ptr<CCreateJunctions>(new CCreateJunctions);

	return algo->Run(*desc, *res) ? algo.release() : nullptr;
}
