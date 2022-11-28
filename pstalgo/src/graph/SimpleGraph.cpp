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

#include <pstalgo/graph/SimpleGraph.h>

CSimpleGraph::CSimpleGraph() 
{
}

CSimpleGraph::CSimpleGraph(CSimpleGraph&& other)
	: m_Nodes(std::move(other.m_Nodes))
	, m_Neighbours(std::move(other.m_Neighbours))
{}

void CSimpleGraph::operator=(CSimpleGraph&& other)
{
	if (&other == this)
		return;
	std::swap(m_Nodes, other.m_Nodes);
	std::swap(m_Neighbours, other.m_Neighbours);
}

void CSimpleGraph::Reserve(uint32 node_count, uint32 edge_count)
{
	m_Nodes.reserve(node_count);
	m_Neighbours.reserve(edge_count * 2);
}

void CSimpleGraph::AddNode(const uint32* neighbours, uint32 neighbour_count)
{
	m_Nodes.resize(m_Nodes.size() + 1);
	auto& node = m_Nodes.back();
	node.m_NeighbourCount = neighbour_count;
	node.m_FirstNeighbour = (uint32)m_Neighbours.size();
	for (uint32 i = 0; i < neighbour_count; ++i)
		m_Neighbours.push_back(neighbours[i]);
}

uint32 CSimpleGraph::NeighbourCount(uint32 node_index) const
{ 
	return m_Nodes[node_index].m_NeighbourCount;
}

uint32 CSimpleGraph::GetNeighbour(uint32 node_index, uint32 neighbour_index) const
{
	return m_Neighbours[m_Nodes[node_index].m_FirstNeighbour + neighbour_index];
}

