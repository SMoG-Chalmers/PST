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

#include <algorithm>
#include <pstalgo/geometry/AABSPTree.h>
#include <pstalgo/experimental/ArrayView.h>

namespace psta
{
	template <typename TOriginPoints, typename TDestinationPoints, typename TMinDistArr, typename TDestIndexArr>
	void CalcStraightLineMinDistances(const TOriginPoints& origin_pts, const TDestinationPoints& dest_pts, float radius, TMinDistArr&& ret_min_dist_per_origin, TDestIndexArr&& ret_dest_idx_per_origin)
	{
		const auto radius_sqrd = radius * radius;
		if (radius < std::numeric_limits<float>::infinity())
		{
			// Create origin point tree
			std::vector<unsigned int> origin_lookup(ret_min_dist_per_origin.size());
			auto origin_tree = CPointAABSPTree::Create(origin_pts, origin_lookup);
			// Invert origin_lookup so that it can be used to look up
			// origin index for a given element index from bsp tree.
			{
				std::vector<unsigned int> tmp(origin_lookup.size());
				for (size_t i = 0; i < origin_lookup.size(); ++i)
					tmp[origin_lookup[i]] = (unsigned int)i;
				std::swap(origin_lookup, tmp);
			}
			// Clear results
			std::fill(ret_min_dist_per_origin.begin(), ret_min_dist_per_origin.end(), std::numeric_limits<float>::infinity());
			if (ret_dest_idx_per_origin)
				for (auto& x : ret_dest_idx_per_origin)
					x = -1;
			// Find minimum squared distance for each origin
			std::vector<CAABSPTree::SObjectSet> origin_point_sets;
			enumerate(dest_pts, [&](auto dest_idx, const float2& dest_pt)
			{
				origin_tree.TestSphere(dest_pt, radius, origin_point_sets);
				for (const auto& point_set : origin_point_sets)
				{
					for (size_t pt_idx = 0; pt_idx < point_set.m_Count; ++pt_idx)
					{
						const auto origin_idx = origin_lookup[point_set.m_FirstObject + pt_idx];
						const auto& origin_pt = origin_pts[origin_idx];
						const auto dist_sqrd = (dest_pt - origin_pt).getLengthSqr();
						auto& result = ret_min_dist_per_origin[origin_idx];
						if (dist_sqrd <= radius_sqrd)
						{
							result = std::min(result, dist_sqrd);
							if (ret_dest_idx_per_origin)
								ret_dest_idx_per_origin[origin_idx] = dest_idx;
						}
					}
				}
			});
			// Square root results
			for (auto& d : ret_min_dist_per_origin)
				d = sqrt(d);
		}
		else
		{
			// Brute force, O(N*M)
			enumerate(origin_pts, [&](auto origin_idx, const float2& origin_pt)
			{
				float min_dist_sqrd = std::numeric_limits<float>::infinity();
				if (ret_dest_idx_per_origin)
				{
					int closest_destination = -1;
					enumerate(dest_pts, [&](auto dest_idx, const float2& dest_pt)
					{
						const auto dist_sqrd = (origin_pt - dest_pt).getLengthSqr();
						if (dist_sqrd < min_dist_sqrd)
						{
							min_dist_sqrd = dist_sqrd;
							closest_destination = dest_idx;
						}
					});
					ret_dest_idx_per_origin[origin_idx] = closest_destination;
				}
				else
				{
					for (const auto& dest_pt : dest_pts)
						min_dist_sqrd = std::min(min_dist_sqrd, (origin_pt - dest_pt).getLengthSqr());
				}
				ret_min_dist_per_origin[origin_idx] = sqrt(min_dist_sqrd);
			});
		}
	}
}