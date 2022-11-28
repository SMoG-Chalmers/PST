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

#include <vector>

#include <pstalgo/Types.h>

class CSimpleGraph
{
public:
	CSimpleGraph();
	CSimpleGraph(const CSimpleGraph& other) = delete;
	CSimpleGraph(CSimpleGraph&& other);

	void operator=(CSimpleGraph&& other);

	void Reserve(uint32 node_count, uint32 edge_count);

	size_t NodeCount() const { return m_Nodes.size(); }

	void AddNode(const uint32* neighbours, uint32 neighbour_count);

	uint32 NeighbourCount(uint32 node_index) const;

	uint32 GetNeighbour(uint32 node_index, uint32 neighbour_index) const;

private:
	struct SNode
	{
		uint32    m_NeighbourCount;
		uint32    m_FirstNeighbour;
	};
	std::vector<SNode> m_Nodes;
	std::vector<uint32> m_Neighbours;
};
