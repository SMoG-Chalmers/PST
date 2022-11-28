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
#include <pstalgo/graph/SimpleGraph.h>

unsigned int ColorGraph(const CSimpleGraph& graph, unsigned int* out_colors)
{
	const uint32 NO_COLOR = (uint32)-1;

	for (uint32 i = 0; i < graph.NodeCount(); ++i)
		out_colors[i] = NO_COLOR;

	// Create ordering of nodes by (valency, index)
	std::vector<uint32> order(graph.NodeCount());
	for (uint32 i = 0; i < graph.NodeCount(); ++i)
		order[i] = i;
	std::sort(order.begin(), order.end(), [&](uint32 a, uint32 b) -> bool
	{
		const uint32 a_valency = graph.NeighbourCount(a);
		const uint32 b_valency = graph.NeighbourCount(b);
		return (a_valency == b_valency) ? (a < b) : (a_valency > b_valency);
	});

	uint32 num_colors = 0;
	for (unsigned int i = 0; i < order.size(); ++i)
	{
		const auto node_index = order[i];
		uint32 n, color = (uint32)-1;
		do 
		{
			++color;
			for (n = 0; n < graph.NeighbourCount(node_index); ++n)
			{
				if (color == out_colors[graph.GetNeighbour(node_index, n)])
					break;
			}
		} while (graph.NeighbourCount(node_index) != n);
		out_colors[node_index] = color;
		if (color >= num_colors)
			num_colors = color + 1;
	}

	return num_colors;
}