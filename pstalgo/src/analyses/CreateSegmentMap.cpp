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
#include <memory>
#include <vector>

#include <pstalgo/analyses/CreateSegmentMap.h>
#include <pstalgo/geometry/AABSPTree.h>
#include <pstalgo/utils/BitVector.h>
#include <pstalgo/utils/Macros.h>
#include <pstalgo/Debug.h>
#include <pstalgo/maths.h>

#include "../ProgressUtil.h"

class CCreateSegmentMap : public IPSTAlgo
{
public:

	const float DEFAULT_MIN_TAIL = 10;
	const float DEFAULT_SNAP = 1;
	const float DEFAULT_DETAIL_THRESHOLD = 1;

	struct SLineWithCuts {
		unsigned int iFirstCut;
		union {
			unsigned int nCuts;
			unsigned int nSegments;
		};
	};

	struct SSegmentLine
	{
		SSegmentLine() {}
		SSegmentLine(unsigned int p0, unsigned int p1, unsigned int base)
			: m_P0(p0), m_P1(p1), m_Base(base) {}
		unsigned int m_P0;
		unsigned int m_P1;
		unsigned int m_Base;

		void MarkForRemoval() { m_P0 = 0xFFFFFFFF; }
		bool IsMarkedForRemoval() const { return 0xFFFFFFFF == m_P0; }
	};

	struct SCut
	{
		unsigned int m_Line;
		float m_T;
		float2 m_Point;
	};

	struct SJunction
	{
		unsigned int m_Seg0;
		unsigned int m_Seg1;

		SJunction() : m_Seg0(0xFFFFFFFF), m_Seg1(0xFFFFFFFF) {}
		SJunction(unsigned int s0, unsigned int s1) : m_Seg0(s0), m_Seg1(s1) {}

		void AddSeg(unsigned int s)
		{
			if (0xFFFFFFFF == m_Seg0)
				m_Seg0 = s;
			else if (0xFFFFFFFE == m_Seg0)
				++m_Seg1;
			else if (0xFFFFFFFF == m_Seg1)
				m_Seg1 = s;
			else
			{
				m_Seg0 = 0xFFFFFFFE;
				m_Seg1 = 3;
			}
		}

		void UpdateSegmentIndex(unsigned int old_index, unsigned int new_index)
		{
			if (GetSegCount() <= 2)
			{
				ASSERT(m_Seg0 == old_index || m_Seg1 == old_index);
				*(m_Seg0 == old_index ? &m_Seg0 : &m_Seg1) = new_index;
			}
		}

		const unsigned int GetSegCount() const
		{
			if (0xFFFFFFFF == m_Seg0)
				return 0;
			else if (0xFFFFFFFE == m_Seg0)
				return m_Seg1;
			else if (0xFFFFFFFF == m_Seg1)
				return 1;
			return 2;
		}
	};

	bool Run(const SCreateSegmentMapDesc& desc, SCreateSegmentMapRes& res)
	{
		// Progress
		enum ETask
		{
			ETask_Intersections,
			ETask_Unlinks,
			ETask_Snapping,
			ETask_RemoveDuplicates,
			ETask_TrimTails,
			ETask_RemoveDetail,
		};
		CPSTAlgoProgressCallback cb(desc.m_ProgressCallback, desc.m_ProgressCallbackUser);
		CPSTMultiTaskProgressCallback progress(cb);
		progress.AddTask(ETask_Intersections,    1, "Processing intersections");
		progress.AddTask(ETask_Unlinks,          desc.m_UnlinkCount ? 1.f : 0.f, "Processing unlinks");
		progress.AddTask(ETask_Snapping,         1, "Snapping points");
		progress.AddTask(ETask_RemoveDuplicates, 1, "Removing duplicate lines");
		progress.AddTask(ETask_TrimTails,        1, "Trimming tail segments");
		progress.AddTask(ETask_RemoveDetail,     1, "Removing detail");

		// Bounding box
		CRectd bb = CRectd::EMPTY;
		if (desc.m_PolyCoordCount)
		{
			bb.Set(desc.m_PolyCoords[0], desc.m_PolyCoords[1], desc.m_PolyCoords[0], desc.m_PolyCoords[1]);
			for (unsigned int i = 1; i < desc.m_PolyCoordCount; ++i)
				bb.GrowToIncludePoint(desc.m_PolyCoords[i << 1], desc.m_PolyCoords[(i << 1) + 1]);
		}
		const double center_x = bb.CenterX();
		const double center_y = bb.CenterY();

		std::vector<float2> points;
		{
			using namespace std;
			// Generate lines from polyline data
			vector<CLine2f> lines;
			vector<unsigned int> base_indices;
			lines.reserve(max(0, (int)desc.m_PolyCoordCount - (int)desc.m_PolySectionCount));
			base_indices.reserve(lines.capacity());

			{
				unsigned int coords_index = 0;
				unsigned int base_count = 0;
				for (unsigned int i = 0; i < desc.m_PolySectionCount; ++i)
				{
					const int point_count = (desc.m_PolySections[i] < 0) ? (-1 - desc.m_PolySections[i]) : desc.m_PolySections[i];
					for (int ii = 1; ii < point_count; ++ii)
					{
						lines.resize(lines.size() + 1);
						auto& line = lines.back();
						line.p1.x = (float)(desc.m_PolyCoords[coords_index] - center_x);
						line.p1.y = (float)(desc.m_PolyCoords[coords_index + 1] - center_y);
						line.p2.x = (float)(desc.m_PolyCoords[coords_index + 2] - center_x);
						line.p2.y = (float)(desc.m_PolyCoords[coords_index + 3] - center_y);
						coords_index += 2;
						base_indices.push_back(base_count);
					}
					if (point_count)
						coords_index += 2;
					if (desc.m_PolySections[i] >= 0)
						++base_count;
				}
			}

			// Find cuts
			progress.SetCurrentTask(ETask_Intersections);
			std::vector<SCut> cuts;
			FindCuts(lines.data(), (unsigned int)lines.size(), desc.m_ExtrudeCut, cuts, progress);

			// Unlink
			if (desc.m_UnlinkCount)
			{
				if (EPSTARoadNetworkType_AxialOrSegment != desc.m_RoadNetworkType) {
					throw std::runtime_error("Unlinks are only allowed for axial/segment road networks");
				}
				progress.SetCurrentTask(ETask_Unlinks);
				std::vector<float2> unlinks;
				unlinks.reserve(desc.m_UnlinkCount);
				for (unsigned int i = 0; i < desc.m_UnlinkCount * 2; i += 2)
					unlinks.push_back(float2((float)(desc.m_UnlinkCoords[i] - center_x), (float)(desc.m_UnlinkCoords[i + 1] - center_y)));
				ProcessUnlinks(cuts, unlinks.data(), (unsigned int)unlinks.size());
			}

			// Output unlinks if road-center-lines
			if (EPSTARoadNetworkType_RoadCenterLines == desc.m_RoadNetworkType && !cuts.empty())
			{
				m_OutUnlinks.resize(cuts.size());
				for (size_t i = 0; i < cuts.size(); ++i) {
					m_OutUnlinks[i].x = center_x + cuts[i].m_Point.x;
					m_OutUnlinks[i].y = center_y + cuts[i].m_Point.y;
				}
			}
			res.m_UnlinkCoords = m_OutUnlinks.empty() ? nullptr : (double*)m_OutUnlinks.data();
			res.m_UnlinkCount = (unsigned int)m_OutUnlinks.size();

			// Do not allow cuts during segment generation if road-center-lines
			if (EPSTARoadNetworkType_RoadCenterLines == desc.m_RoadNetworkType) {
				cuts.clear();
			}

			// Generate segments
			GenerateSegments(lines.data(), base_indices.data(), (unsigned int)lines.size(), cuts.data(), (unsigned int)cuts.size(), m_Segments, points);
		}

		// Snap
		progress.SetCurrentTask(ETask_TrimTails);
		Snap(m_Segments, points, desc.m_Snap);

		// Remove duplicate segments
		progress.SetCurrentTask(ETask_RemoveDuplicates);
		RemoveDuplicateSegments(m_Segments);

		// Remove segments with zero length
		RemoveZeroSegments(points.data(), m_Segments);

		{
			// Create junctions
			std::vector<SJunction> junctions(points.size());
			for (unsigned int i = 0; i < m_Segments.size(); ++i)
			{
				const auto& seg = m_Segments[i];
				junctions[seg.m_P0].AddSeg(i);
				junctions[seg.m_P1].AddSeg(i);
			}

			// Remove tails
			progress.SetCurrentTask(ETask_TrimTails);
			TrimTails(points.data(), desc.m_MinTail, junctions, m_Segments);

			// Remove detail
			progress.SetCurrentTask(ETask_RemoveDetail);
			RemoveDetail(points.data(), desc.m_Min3NodeColinearDeviation, junctions, m_Segments);
		}

		// Verify segments are ordered by origin object index
		for (unsigned int i = 1; i < m_Segments.size(); ++i)
		{
			ASSERT(m_Segments[i].m_Base >= m_Segments[i - 1].m_Base);
		}

		m_Points.reserve(points.size() * 2);
		for (const auto& p : points)
		{
			m_Points.push_back((double)p.x + center_x);
			m_Points.push_back((double)p.y + center_y);
		}

		res.m_SegmentCoords = m_Points.data();
		res.m_Segments = reinterpret_cast<unsigned int*>(m_Segments.data());
		res.m_SegmentCount = (unsigned int)m_Segments.size();

		return true;
	}

	// Returns a bit vector of size line_count*2, with a pair of bits for each line. A bit
	// is set for an end-point if two or more lines share that same end-point.
	CBitVector FindConnectedEndPoints(const CLine2f* lines, unsigned int line_count)
	{
		CBitVector bits;
		bits.resize(line_count * 2);

		struct STmp
		{
			STmp() {}
			STmp(const float2& pos, unsigned int index) : m_Pos(pos), m_Index(index) {}
			
			float2 m_Pos;
			unsigned int m_Index;  // [0..line_count*2)
			
			inline bool operator<(const STmp& other) const
			{
				return m_Pos.y == other.m_Pos.y ? m_Pos.x < other.m_Pos.x : m_Pos.y < other.m_Pos.y;
			}
		};
		
		std::vector<STmp> tmp;
		tmp.reserve(line_count * 2);
		for (unsigned int i = 0; i < line_count; ++i)
		{
			tmp.push_back(STmp(lines[i].p1, i * 2));
			tmp.push_back(STmp(lines[i].p2, i * 2 + 1));
		}

		std::sort(tmp.begin(), tmp.end());

		bits.clearAll();
		for (unsigned int i = 0; i < (line_count * 2) - 1; ++i)
		{
			if (tmp[i + 1].m_Pos == tmp[i].m_Pos)
			{
				bits.set(tmp[i].m_Index);
				do {
					bits.set(tmp[++i].m_Index);
				} while (i < line_count * 2 - 1 && tmp[i + 1].m_Pos == tmp[i].m_Pos);
			}
		}

		return bits;
	}

	void ProcessUnlinks(const std::vector<float2>& unlinks, const std::vector<double2>& pts, std::vector<unsigned int>& ptidx)
	{
		for (size_t iUnlink = 0; iUnlink < unlinks.size(); ++iUnlink)
		{
			double2 up(unlinks[iUnlink].x, unlinks[iUnlink].y);

			int iClosest = -1;
			double minDist;

			for (size_t iPoint = 0; iPoint < ptidx.size(); ++iPoint)
			{
				size_t ip = ptidx[iPoint];
				if (-1 == ip)
					continue;

				double2 pt = pts[ip];

				double2 v(pt - up);
				double d = v.x*v.x + v.y*v.y;

				if ((iClosest < 0) || (d < minDist)) {
					iClosest = (int)ip;
					minDist = d;
				}
			}

			if (iClosest < 0)
				break;

			ptidx[iClosest] = (unsigned int)-1;
		}
	}

	void FindCuts(const CLine2f* lines, unsigned int line_count, float extrude_len, std::vector<SCut>& ret_cuts, IProgressCallback& progress)
	{
		CLineAABSPTree bsp = CLineAABSPTree::Create(reinterpret_cast<const float2*>(lines), line_count, 16);
		progress.ReportProgress(.5f);

		const CBitVector connection_bits = FindConnectedEndPoints(lines, line_count);

		std::vector<CLineAABSPTree::SObjectSet> sets;
		std::vector<SCut> cuts;

		for (unsigned int l0_index = 0; l0_index < line_count; ++l0_index)
		{
			const auto& l0 = lines[l0_index];
			const float2 v = l0.p2 - l0.p1;
			const float l0_len = v.getLength();
			if (.0f == l0_len)
				continue;
			const auto l0_v = v * (1.0f / l0_len);
			cuts.clear();
			bsp.TestCapsule(l0.p1, l0.p2, extrude_len, sets);
			for (const auto& s : sets)
			{
				for (unsigned int o = s.m_FirstObject; o < s.m_FirstObject + s.m_Count; ++o)
				{
					const unsigned int l1_index = bsp.GetLineIndex(o);
					if (l1_index == l0_index)
						continue;
					const auto& l1 = lines[l1_index];

					// Do not count touching end-points as a cut
					if (l0.p1 == l1.p1 || l0.p1 == l1.p2 || l0.p2 == l1.p1 || l0.p2 == l1.p2)
						continue;

					if (l1.p1 == l1.p2)
						continue; // Zero length

					const float2 v = l1.p2 - l1.p1;
					const float l1_len = v.getLength();
					const float2 l1_v = v * (1.0f / l1_len);

					float t0, t1;
					if (!Find2DRayIntersection(l0.p1, l0_v, l1.p1, l1_v, t0, t1))
						continue;

					// Extrude L1 at unconnected end-points
					const float l1_min = connection_bits.get(l1_index * 2) ? 0.f : -extrude_len;
					const float l1_max = connection_bits.get(l1_index * 2 + 1) ? l1_len : l1_len + extrude_len;

					if (t0 <= .0f || t0 >= l0_len || t1 <= l1_min || t1 >= l1_max)
						continue;

					// IMPORTANT: Make sure we get exact same cutting coordinates in L0-L1 and L1-L0 cuts
					//            by always calculating cutting point on line with lowest index.
					SCut cut;
					cut.m_Line = l0_index;
					cut.m_T = t0;
					cut.m_Point = (l0_index < l1_index) ? (l0.p1 + l0_v * t0) : (l1.p1 + l1_v * t1);
					cuts.push_back(cut);
				}
			}

			// Sort cuts
			if (cuts.empty())
				continue;

			// Add unique cuts in sorted order
			std::sort(cuts.begin(), cuts.end(), [](const SCut& lhs, const SCut& rhs) -> bool { return lhs.m_T < rhs.m_T; });
			ret_cuts.push_back(cuts[0]);
			unsigned int n = 0;
			for (unsigned int i = 1; i < cuts.size(); ++i)
			{
				if (cuts[i].m_T == cuts[n].m_T)
					continue;
				ret_cuts.push_back(cuts[i]);
				n = i;
			}

			progress.ReportProgress(.5f + .5f * (float)l0_index / line_count);
		}
	}

	void ProcessUnlinks(std::vector<SCut>& cuts, const float2* unlinks, unsigned int unlink_count)
	{
		const float MAX_UNLINK_DIST = 100.0f;

		std::vector<float2> points;  // Array of unique cutting points
		points.reserve(cuts.size() / 2);
		std::vector<unsigned int> cut_to_point(cuts.size());  // Mapping from 'cuts' to 'points'
		{
			struct SPoint
			{
				unsigned int m_CutIndex;
				float2 m_Point;
			};
			std::vector<SPoint> tmp(cuts.size());
			for (unsigned int i = 0; i < cuts.size(); ++i)
			{
				tmp[i].m_CutIndex = i;
				tmp[i].m_Point = cuts[i].m_Point;
			}
			std::sort(tmp.begin(), tmp.end(), [](const SPoint& lhs, const SPoint& rhs) -> bool { return (lhs.m_Point.x == rhs.m_Point.x) ? (lhs.m_Point.y < rhs.m_Point.y) : (lhs.m_Point.x < rhs.m_Point.x); });
			for (const auto& t : tmp)
			{
				if (points.empty() || t.m_Point != points.back())
					points.push_back(t.m_Point);
				cut_to_point[t.m_CutIndex] = (unsigned int)points.size() - 1;
			}
		}

		CPointAABSPTree bsp;
		{
			std::vector<unsigned int> order(points.size(), (unsigned int)-1);
			bsp = CPointAABSPTree::Create(points, order);

			{ // Re-order points
				std::vector<float2> ordered_points(points.size());
				for (unsigned int i = 0; i < points.size(); ++i)
					ordered_points[order[i]] = points[i];
				std::swap(points, ordered_points);
			}

			// Update cut_to_point array with new index order
			for (auto& idx : cut_to_point)
				idx = order[idx];
		}

		std::vector<CLineAABSPTree::SObjectSet> sets;
		for (unsigned int i = 0; i < unlink_count; ++i)
		{
			const float2 unlink_pos = unlinks[i];
			int closest_index = -1;
			float closest_dist_sqr = 0;
			bsp.TestSphere(unlinks[i], MAX_UNLINK_DIST, sets);
			for (const auto& s : sets)
			{
				for (unsigned int o = s.m_FirstObject; o < s.m_FirstObject + s.m_Count; ++o)
				{
					if (isnan(points[o].x))
						continue;  // point is already unlinked
					const float dist_sqr = (unlink_pos - points[o]).getLengthSqr();
					if (-1 == closest_index || dist_sqr < closest_dist_sqr)
					{
						closest_index = o;
						closest_dist_sqr = dist_sqr;
					}
				}
			}
			if (-1 != closest_index && closest_dist_sqr < MAX_UNLINK_DIST*MAX_UNLINK_DIST)
				points[closest_index].x = NAN;  // Mark for removal
		}

		unsigned int n = 0;
		for (unsigned int i = 0; i < cuts.size(); ++i)
		{
			if (!isnan(points[cut_to_point[i]].x))
				cuts[n++] = cuts[i];
		}
		cuts.resize(n);
	}

	void GenerateSegments(const CLine2f* lines, const unsigned int* base_indices, unsigned int line_count, const SCut* cuts, unsigned int cut_count, std::vector<SSegmentLine>& ret_segments, std::vector<float2>& ret_points)
	{
		ret_segments.reserve(line_count + cut_count);
		ret_points.reserve(line_count * 2 + cut_count);
		unsigned int c = 0;
		for (unsigned int i = 0; i < line_count; ++i)
		{
			auto& line = lines[i];
			ret_points.push_back(line.p1);
			for (; c < cut_count && cuts[c].m_Line == i; ++c)
			{
				ret_segments.resize(ret_segments.size() + 1);
				auto& seg = ret_segments.back();
				seg.m_Base = base_indices[i];
				seg.m_P0 = (unsigned int)ret_points.size() - 1;
				seg.m_P1 = (unsigned int)ret_points.size();
				ret_points.push_back(cuts[c].m_Point);
			}
			ret_segments.resize(ret_segments.size() + 1);
			auto& seg = ret_segments.back();
			seg.m_Base = base_indices[i];
			seg.m_P0 = (unsigned int)ret_points.size() - 1;
			seg.m_P1 = (unsigned int)ret_points.size();
			ret_points.push_back(line.p2);
		}
		ASSERT(ret_segments.size() == line_count + cut_count);
		ASSERT(ret_points.size() == line_count * 2 + cut_count);
	}

	void Snap(std::vector<SSegmentLine>& segments, std::vector<float2>& points, float snap)
	{
		if (points.empty())
			return;

		CPointAABSPTree bsp;
		{
			std::vector<float2> ordered_points(points.size());
			std::vector<unsigned int> order(points.size(), (unsigned int)-1);
			bsp = CPointAABSPTree::Create(points, order);
			for (unsigned int i = 0; i < points.size(); ++i)
				ordered_points[order[i]] = points[i];
			std::swap(points, ordered_points);
			for (auto& s : segments)
			{
				s.m_P0 = order[s.m_P0];
				s.m_P1 = order[s.m_P1];
			}
		}

		// Create an array with connection count per point
		std::vector<unsigned char> connections_per_point(points.size(), 0);
		for (const auto& segment : segments)
		{
			connections_per_point[segment.m_P0]++;
			connections_per_point[segment.m_P1]++;
		}

		std::vector<unsigned int> idx(points.size());
		for (unsigned int i = 0; i < idx.size(); ++i)
			idx[i] = i;

		std::vector<CLineAABSPTree::SObjectSet> sets;

		const float snap_sqr = snap*snap;

		// Snap points
		for (unsigned int i = 0; i < points.size(); ++i)
		{
			if (idx[i] != i)
				continue;
			unsigned int point_index = i;  // Can change if point is snapped to another...
			const auto& p0 = points[point_index];
			bsp.TestSphere(p0, snap, sets);
			for (const auto& s : sets)
			{
				for (unsigned int o = s.m_FirstObject; o < s.m_FirstObject + s.m_Count; ++o)
				{
					if (o == point_index || idx[o] != o)
						continue;
					const auto& p1 = points[o];
					if ((p1 - p0).getLengthSqr() > snap_sqr)
						continue;
					
					// Snap towwards point with most connections
					// TODO: Hmm, do we want to add connection counts when two points are snapped together?
					if (connections_per_point[o] > connections_per_point[point_index])
					{
						idx[point_index] = o;
						point_index = o;
					}
					else
					{
						idx[o] = point_index;
					}
				}
			}
		}

		// Pack snapped points and calculate new indices (mark snap indices by setting most significant bit)
		unsigned int snapped_count = 0;
		for (unsigned int i = 0; i < idx.size(); ++i)
		{
			if (i != idx[i])
				continue;
			points[snapped_count] = points[i];
			idx[i] = snapped_count++ | 0x80000000;
		}
		points.resize(snapped_count);

		// Update indices of segment points to new snapped indices
		for (auto& seg : segments)
		{
			for (int i = 0; i < 2; ++i)
			{
				auto& p = i ? seg.m_P0 : seg.m_P1;
				while (!((p = idx[p]) & 0x80000000));
				p &= 0x7FFFFFFF;
			}
		}
	}

	void RemoveDuplicateSegments(std::vector<SSegmentLine>& segments)
	{
		if (segments.empty())
			return;

		struct STmp
		{
			unsigned int m_Index;
			unsigned int m_P0;
			unsigned int m_P1;
		};

		std::vector<STmp> tmp(segments.size());
		for (unsigned int i = 0; i < segments.size(); ++i)
		{
			const auto& s = segments[i];
			auto& t = tmp[i];
			t.m_Index = i;
			t.m_P0 = s.m_P0;
			t.m_P1 = s.m_P1;
			if (t.m_P0 > t.m_P1)
				std::swap(t.m_P0, t.m_P1);
		}

		// Sort
		std::sort(tmp.begin(), tmp.end(), [](const STmp& lhs, const STmp& rhs) -> bool
		{
			return (lhs.m_P0 == rhs.m_P0) ? (lhs.m_P1 < rhs.m_P1) : (lhs.m_P0 < rhs.m_P0);
		});

		unsigned int new_count = 1;
		for (unsigned int i = 1; i < tmp.size(); ++i)
		{
			auto& t = tmp[i];
			if (t.m_P0 == tmp[i - 1].m_P0 && t.m_P1 == tmp[i - 1].m_P1)
				segments[t.m_Index].MarkForRemoval();
			else
				++new_count;
		}

		// Pack
		if (segments.size() != new_count)
			PackSegments(segments);
	}

	void RemoveZeroSegments(const float2* points, std::vector<SSegmentLine>& segments)
	{
		unsigned int new_count = 0;
		for (unsigned int i = 0; i < segments.size(); ++i)
		{
			const auto& seg = segments[i];
			if (seg.m_P0 == seg.m_P1)
				continue;
			const auto& p0 = points[seg.m_P0];
			const auto& p1 = points[seg.m_P1];
			if (p0.x == p1.x && p0.y == p1.y)
				continue;
			if (i != new_count)
				segments[new_count] = seg;
			++new_count;
		}
		segments.resize(new_count);
	}

	void RemoveDetail(const float2* points, float detail_threshold, std::vector<SJunction>& junctions, std::vector<SSegmentLine>& segments)
	{
		const float detail_threshold_sqr = detail_threshold*detail_threshold;
		for (unsigned int s0_index = 0; s0_index < segments.size(); ++s0_index)
		{
			auto& s0 = segments[s0_index];
			if (s0.IsMarkedForRemoval())
				continue;  // Already merged
			const auto& p0 = points[s0.m_P0];
			const auto* j1 = &junctions[s0.m_P1];
			while (j1->GetSegCount() == 2)  // <-wtf
			{
				const unsigned int s1_index = (j1->m_Seg0 == s0_index) ? j1->m_Seg1 : j1->m_Seg0;
				auto& s1 = segments[s1_index];
				if (s0.m_Base != s1.m_Base)
					break; // Only merge segments from same base object
				const auto& p1 = points[s0.m_P1];
				const unsigned int p2_index = (s1.m_P0 == s0.m_P1) ? s1.m_P1 : s1.m_P0;
				const auto& p2 = points[p2_index];
				const float2 v1 = p1 - p0;
				const float2 v2 = p2 - p0;
				if (sqr(crp(v1, v2)) > detail_threshold_sqr * v2.getLengthSqr())
					break;
				// Merge
				s0.m_P1 = p2_index;
				auto& j2 = junctions[p2_index];
				if (j2.GetSegCount() <= 2)
					*((s1_index == j2.m_Seg0) ? &j2.m_Seg0 : &j2.m_Seg1) = s0_index;
				s1.MarkForRemoval();
				j1 = &j2;
			}
		}

		PackSegments(segments, junctions);
	}

	void TrimTails(const float2* points, const float min_length, std::vector<SJunction>& junctions, std::vector<SSegmentLine>& segments)
	{
		for (unsigned int start_index = 0; start_index < segments.size(); ++start_index)
		{
			unsigned int point_index;
			{
				const auto& s = segments[start_index];
				if (s.IsMarkedForRemoval())
					continue; // Already trimmed
				if (junctions[s.m_P0].GetSegCount() == 1)
					point_index = s.m_P0;
				else if (junctions[s.m_P1].GetSegCount() == 1)
					point_index = s.m_P1;
				else
					continue;
			}
			unsigned int segment_index = start_index;
			float acc_len = 0;
			INFINITE_LOOP
			{
				const auto& s = segments[segment_index];
				point_index = (point_index == s.m_P0) ? s.m_P1 : s.m_P0;
				const SJunction& j = junctions[point_index];
				if (j.GetSegCount() == 1)
					break; // End-point reached
				acc_len += (points[s.m_P0] - points[s.m_P1]).getLength();
				if (acc_len >= min_length)
					break; // Tail is too long to be trimmed
				if (j.GetSegCount() > 2)
				{
					// Reached intersection
					// Walk backwards and remove segments
					INFINITE_LOOP
					{
						auto& s = segments[segment_index];
						point_index = (point_index == s.m_P0) ? s.m_P1 : s.m_P0;
						s.MarkForRemoval();
						if (segment_index == start_index)
							break;
						const SJunction& j = junctions[point_index];
						segment_index = (segment_index == j.m_Seg0) ? j.m_Seg1 : j.m_Seg0;
					}
					break;
				}
				// Continue walk
				segment_index = (segment_index == j.m_Seg0) ? j.m_Seg1 : j.m_Seg0;
			}
		}

		PackSegments(segments, junctions);
	}

	void PackSegments(std::vector<SSegmentLine>& segments)
	{
		unsigned int new_count = 0;
		for (unsigned int i = 0; i < segments.size(); ++i)
		{
			const auto& seg = segments[i];
			if (seg.IsMarkedForRemoval())
				continue;
			if (i != new_count)
				segments[new_count] = seg;
			++new_count;
		}
		segments.resize(new_count);
	}

	void PackSegments(std::vector<SSegmentLine>& segments, std::vector<SJunction>& junctions)
	{
		// NOTE: This function does NOT remove/pack junctions

		unsigned int new_count = 0;
		for (unsigned int i = 0; i < segments.size(); ++i)
		{
			const auto& seg = segments[i];
			if (seg.IsMarkedForRemoval())
				continue;
			if (i != new_count)
			{
				junctions[seg.m_P0].UpdateSegmentIndex(i, new_count);
				junctions[seg.m_P1].UpdateSegmentIndex(i, new_count);
				segments[new_count] = seg;
			}
			++new_count;
		}
		segments.resize(new_count);
	}

private:
	std::vector<SSegmentLine> m_Segments;
	std::vector<double> m_Points;
	std::vector<double2> m_OutUnlinks;
};

PSTADllExport IPSTAlgo* PSTACreateSegmentMap(const SCreateSegmentMapDesc* desc, SCreateSegmentMapRes* res)
{
	try {
		if ((desc->VERSION != desc->m_Version) ||
			(res->VERSION != res->m_Version)) {
			throw std::runtime_error("Version mismatch");
		}

		auto algo = std::unique_ptr<CCreateSegmentMap>(new CCreateSegmentMap);

		return algo->Run(*desc, *res) ? algo.release() : nullptr;
	}
	catch (const std::exception& e) {
		LOG_ERROR(e.what());
	}
	catch (...) {
		LOG_ERROR("Unknown exception");
	}
	return nullptr;
}
