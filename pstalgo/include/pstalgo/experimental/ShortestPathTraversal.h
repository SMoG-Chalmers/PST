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

#include <functional>
#include <memory>
#include "DirectedMultiDistanceGraph.h"

namespace psta
{
	class IShortestPathTraversal
	{
	public:
		typedef CDirectedMultiDistanceGraph graph_t;
		typedef std::function<void(size_t, float)> dist_callback_t;

		virtual ~IShortestPathTraversal() {}
		virtual void Search(size_t origin_index, dist_callback_t& cb, const float* limits, float straight_line_distance_limit = std::numeric_limits<float>::infinity()) = 0;
		virtual void SearchAccumulative(size_t origin_index, dist_callback_t& cb, const float* limits, float straight_line_distance_limit = std::numeric_limits<float>::infinity()) = 0;
	};

	std::unique_ptr<IShortestPathTraversal> CreateShortestPathTraversal(const CDirectedMultiDistanceGraph& graph);
}