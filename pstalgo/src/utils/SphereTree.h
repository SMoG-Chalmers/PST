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

#include <pstalgo/maths.h>

typedef struct {
	REAL x;
	REAL y;
	REAL rad;
	bool bHasLeaves;
	char reserved[3];
	int children[4];
} SPHERE_NODE;

typedef struct {
	int iFirstElement;
	int nElements;
} SPHERE_LEAF;


class SphereTree {

private:

	int nNodes;
	SPHERE_NODE *nodes;

	int nLeaves;
	SPHERE_LEAF *leaves;

	int *elementList;
	int nElements;

	char *elementFlags;

	// Search result
	int *result_list;
	int nResult;


public:

	//SphereTree(REAL minx, REAL miny, REAL maxx, REAL maxy, int nLevels);
	SphereTree();
	~SphereTree();

	void Release();

	void Create(REAL minx, REAL miny, REAL maxx, REAL maxy, int nLevels);

	bool SetLines(const REAL *lines, int nLines, int stride);

	// WARNING: DEPRECATED: NOT THREAD SAFE!
	int GetCloseLines(int *list, REAL x1, REAL y1, REAL x2, REAL y2);

	// WARNING: DEPRECATED: NOT THREAD SAFE!
	int GetCloseLines(int *list, REAL x, REAL y, REAL rad);

	// NOTE: Callback might be called multiple times for same line index
	template <class TCallback>
	void TForEachCloseLine(REAL x, REAL y, REAL rad, TCallback&& cb) const { TForEachCloseLineRecursive(0, x, y, rad, cb); }

private:

	// NOTE: Callback might be called multiple times for same line index
	template <class TCallback>
	void TForEachCloseLineRecursive(int iNode, REAL x, REAL y, REAL rad, TCallback&& cb) const
	{
		const auto& node = nodes[iNode];
		if (sqr(node.x - x) + sqr(node.y - y) > sqr(node.rad + rad))
			return;
		if (node.bHasLeaves)
		{
			const auto& leaf = leaves[node.children[0]];
			for (int element_index = leaf.iFirstElement; element_index < leaf.iFirstElement + leaf.nElements; ++element_index)
				cb(elementList[element_index]);
		}
		else
		{
			for (int i = 0; i < 4; ++i) 
				TForEachCloseLineRecursive(node.children[i], x, y, rad, cb);
		}
	}

	bool IsLineInSphere(REAL sx, REAL sy, REAL rad,
						REAL lx, REAL ly, REAL nx, REAL ny, REAL length);

	void CreateSubTree(int currNode, int nLevels);

	void Count(int iNode, REAL x, REAL y, REAL nx, REAL ny, REAL length);

	void Add(int iNode, int iElement, REAL x, REAL y, REAL nx, REAL ny, REAL length);

	void FindCloseLines(int iNode, REAL x, REAL y, REAL nx, REAL ny, REAL length);
};

