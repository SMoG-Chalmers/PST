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

#include <cmath>
#include <cstdlib>
#include <cstring>

#include <pstalgo/Debug.h>

#include "SphereTree.h"

//#define DEBUG_OUTPUT

SphereTree::SphereTree() 
: nNodes(0),
  nodes(nullptr),
  nLeaves(0),
  leaves(nullptr),
  elementList(nullptr),
  nElements(0),
  elementFlags(nullptr),
  result_list(nullptr),
  nResult(0)
{
}

SphereTree::~SphereTree() 
{
	Release();
}

void SphereTree::Release() {

	if (elementFlags) {
		free(elementFlags);
		elementFlags = nullptr;
	}

	if (elementList) {
		free(elementList);
		elementList = nullptr;
	}
	nElements = 0;

	if (leaves) {
		free(leaves);
		leaves = nullptr;
	}
	nLeaves = 0;

	if (nodes) {
		free(nodes);
		nodes = nullptr;
	}
	nNodes = 0;
}

void SphereTree::Create(REAL minx, REAL miny, REAL maxx, REAL maxy, int nLevels)
{
	#ifdef DEBUG_OUTPUT
		LOG_INFO("Creating SphereTree...");
	#endif

	int i,ii;

	nNodes = 0;
	ii=1;
	for (i=0; i<nLevels; i++) {
		nNodes += ii;
		ii <<= 2;
	}
	nLeaves = ii >> 2;


	nodes = (SPHERE_NODE *)malloc(nNodes * sizeof(SPHERE_NODE));	
	memset(nodes, 0, nNodes * sizeof(SPHERE_NODE));
	
	leaves = (SPHERE_LEAF *)malloc(nLeaves * sizeof(SPHERE_LEAF));
	memset(leaves, 0, nLeaves * sizeof(SPHERE_LEAF));

	#ifdef DEBUG_OUTPUT
		LOG_INFO("SphereTree: Creating tree structure... %d nodes, %d leaves.", nNodes, nLeaves);
	#endif

	nodes[0].x = (minx + maxx) / 2.0f;
	nodes[0].y = (miny + maxy) / 2.0f;
	nodes[0].rad = maxx - minx;
	if ((maxy - miny) > nodes[0].rad) 
		nodes[0].rad = maxy - miny;
	nodes[0].rad /= 2.0f;
	nodes[0].rad = (REAL)sqrt( (nodes[0].rad*nodes[0].rad) * 2.0f );
	
	nNodes = 1;
	nLeaves = 0;
	CreateSubTree(0, nLevels);

	elementList = nullptr;
	nElements = 0;
	elementFlags = nullptr;

	#ifdef DEBUG_OUTPUT
		LOG_INFO("SphereTree created.", nNodes, nLeaves);
	#endif
}

void SphereTree::CreateSubTree(int currNode, int nLevels) 
{
	int i;

	if (nLevels <= 1) {
		nodes[currNode].bHasLeaves = true;
		nodes[currNode].children[0] = nLeaves++;
		/*
		char string[256];
		sprintf(string,"leaf: (%f %f) rad = %f\r\n", 
				nodes[currNode].x, nodes[currNode].y, nodes[currNode].rad);
		Debug(string);
		*/
		return;
	}

	nodes[currNode].bHasLeaves = false;

	for (i=0; i<4; i++) {
		nodes[currNode].children[i] = nNodes+i;
		nodes[nNodes+i].rad = nodes[currNode].rad / 1.99f;  // 1.99 instead of 2.0 here to fight numerical precision, by having circles overlap slightly at corners
	}

	REAL d = nodes[currNode].rad * 0.7071068f / 2.0f;
		
	nodes[nNodes+0].x = nodes[currNode].x - d;
	nodes[nNodes+0].y = nodes[currNode].y - d;
	nodes[nNodes+1].x = nodes[currNode].x + d;
	nodes[nNodes+1].y = nodes[currNode].y - d;
	nodes[nNodes+2].x = nodes[currNode].x + d;
	nodes[nNodes+2].y = nodes[currNode].y + d;
	nodes[nNodes+3].x = nodes[currNode].x - d;
	nodes[nNodes+3].y = nodes[currNode].y + d;
	
	nNodes += 4;

	for (i=0; i<4; i++) {
		CreateSubTree(nodes[currNode].children[i], nLevels-1);
	}

}


bool SphereTree::IsLineInSphere(REAL sx, REAL sy, REAL rad,
								REAL lx, REAL ly, REAL nx, REAL ny, REAL length) {
	
	REAL dx,dy,d;
	
	dx = sx - lx;		
	dy = sy - ly;
	
	d = (dx * ny) + (dy * -nx);
	if (d > rad)
		return false;

	d = (dx * nx) + (dy * ny);
	if ((d < 0.0f) || (d > length)) {
		if ((REAL)sqrt((dx*dx)+(dy*dy)) > rad) {
			dx = sx - (lx + (nx * length));		
			dy = sy - (ly + (ny * length));		
			if ((REAL)sqrt((dx*dx)+(dy*dy)) > rad)
				return false;
		}
	}

	return true;

}

bool SphereTree::SetLines(const REAL *lines, int nLines, int stride) {

	int i;
	REAL x,y,length;

	stride >>= 2;

	#ifdef DEBUG_OUTPUT
		LOG_INFO("SphereTree: Counting lines per leaf...");
	#endif

	// Count lines per leaf
	for (i=0; i<nLeaves; i++) {
		leaves[i].nElements = 0;
	}
	
	const REAL* flines = lines;
	for (i=0; i<nLines; i++) {
		x = flines[2] - flines[0];
		y = flines[3] - flines[1];
		length = (REAL)sqrt((x*x)+(y*y));
		if (length > 0.0f) {
			x /= length;
			y /= length;
			Count(0, flines[0], flines[1], x, y, length);
		}
		flines += stride;
	}

	nElements = 0;
	for (i=0; i<nLeaves; i++) {
		leaves[i].iFirstElement = nElements;
		nElements += leaves[i].nElements;
		leaves[i].nElements = 0;
	}

	#ifdef DEBUG_OUTPUT
		LOG_INFO("SphereTree: Counted %d entries.", nElements);
	#endif

	elementList = (int *)malloc(nElements * sizeof(int));

	// Add lines to leaves
	flines = (REAL *)lines;
	for (i=0; i<nLines; i++) {
		x = flines[2] - flines[0];
		y = flines[3] - flines[1];
		length = (REAL)sqrt((x*x)+(y*y));
		if (length > 0.0f) {
			x /= length;
			y /= length;
			Add(0, i, flines[0], flines[1], x, y, length);
		}
		flines += stride;
	}

	elementFlags = (char *)malloc(nLines * sizeof(char));
	memset(elementFlags, 0, nLines * sizeof(char));

	#ifdef DEBUG_OUTPUT
		LOG_INFO("SphereTree elements set. %d elements, %d entries.", nLines, nElements);
	#endif

	return true;
}

void SphereTree::Count(int iNode, REAL x, REAL y, REAL nx, REAL ny, REAL length) {

	if ( !IsLineInSphere(nodes[iNode].x, nodes[iNode].y, nodes[iNode].rad,
						 x, y, nx, ny, length) ) {
		return;
	}

	if (nodes[iNode].bHasLeaves) {
		leaves[nodes[iNode].children[0]].nElements++;
	} else {
		int i;
		for (i=0; i<4; i++) {
			Count(nodes[iNode].children[i], x, y, nx, ny, length);
		}
	}

}

void SphereTree::Add(int iNode, int iElement, REAL x, REAL y, REAL nx, REAL ny, REAL length) {

	if ( !IsLineInSphere(nodes[iNode].x, nodes[iNode].y, nodes[iNode].rad,
						 x, y, nx, ny, length) ) {
		return;
	}

	if (nodes[iNode].bHasLeaves) {
		int i;
		i = leaves[nodes[iNode].children[0]].iFirstElement + 
			leaves[nodes[iNode].children[0]].nElements;
		elementList[i] = iElement;
		leaves[nodes[iNode].children[0]].nElements++;
	} else {
		int i;
		for (i=0; i<4; i++) {
			Add(nodes[iNode].children[i], iElement, x, y, nx, ny, length);
		}
	}

}


int SphereTree::GetCloseLines(int *list, REAL x1, REAL y1, REAL x2, REAL y2) {

	REAL length;
	
	result_list = list;
	nResult = 0;

	x2 -= x1;
	y2 -= y1;
	length = (REAL)sqrt((x2*x2)+(y2*y2));
	x2 /= length;
	y2 /= length;
	FindCloseLines(0, x1, y1, x2, y2, length);

	int i;
	for (i=0; i<nResult; i++) {
		elementFlags[result_list[i]] = 0;
	}

	return nResult;
}

void SphereTree::FindCloseLines(int iNode, REAL x, REAL y, REAL nx, REAL ny, REAL length) {

	if ( !IsLineInSphere(nodes[iNode].x, nodes[iNode].y, nodes[iNode].rad,
						 x, y, nx, ny, length) ) {
		return;
	}

	if (nodes[iNode].bHasLeaves) {
		
		int i,ii,iLeaf;
		
		iLeaf = nodes[iNode].children[0];
		
		ii = leaves[iLeaf].iFirstElement;
		
		for (i=0; i<leaves[iLeaf].nElements; i++) {
			if (!elementFlags[elementList[ii]]) {
				result_list[nResult++] = elementList[ii]; 
				elementFlags[elementList[ii]] = 1;
			}
			ii++;
		}

	} else {
		int i;
		for (i=0; i<4; i++) {
			FindCloseLines(nodes[iNode].children[i], x, y, nx, ny, length);
		}
	}

}

int SphereTree::GetCloseLines(int *list, REAL x, REAL y, REAL rad) {

	int count = 0;

	TForEachCloseLine(x, y, rad, [&](int line_index)
	{
		if (!elementFlags[line_index]) 
		{
			list[count++] = line_index;
			elementFlags[line_index] = 1;
		}
	});
		
	for (int i = 0; i < count; ++i) 
		elementFlags[list[i]] = 0;

	return nResult;
}