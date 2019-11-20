"""
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
"""

import array
import pstalgo

def CreateChainGraph(line_count, line_length):
	line_coords = []	
	for x in range(line_count+1): 
		line_coords.append(x*line_length)
		line_coords.append(0)
	line_indices = []	
	for i in range(line_count): 
		line_indices.append(i)
		line_indices.append(i+1)
	line_coords = array.array('d', line_coords)
	line_indices = array.array('I', line_indices)
	graph_handle = pstalgo.CreateGraph(line_coords, line_indices, None, None, None)
	return graph_handle

def CreateSquareGraph(line_length):
	line_coords = array.array('d', [0, 0, line_length, 0, line_length, line_length, 0, line_length])
	line_indices = array.array('I', [0, 1, 1, 2, 2, 3, 3, 0])
	graph_handle = pstalgo.CreateGraph(line_coords, line_indices, None, None, None)
	return graph_handle

def CreateSegmentChainGraph(line_count, line_length):
	line_coords = []	
	for x in range(line_count+1): 
		line_coords.append(x*line_length)
		line_coords.append(0)
	line_indices = []	
	for i in range(line_count): 
		line_indices.append(i)
		line_indices.append(i+1)
	line_coords = array.array('d', line_coords)
	line_indices = array.array('I', line_indices)
	graph_handle = pstalgo.CreateSegmentGraph(line_coords, line_indices, None)
	return graph_handle

def CreateSegmentSquareGraph(line_length):
	line_coords = array.array('d', [0, 0, line_length, 0, line_length, line_length, 0, line_length])
	line_indices = array.array('I', [0, 1, 1, 2, 2, 3, 3, 0])
	graph_handle = pstalgo.CreateSegmentGraph(line_coords, line_indices, None)
	return graph_handle

def CreateCrosshairSegmentGraph():
	#  ___
	# |_|_|
	# |_|_|
	#
	line_coords = array.array('d', [-1, -1, 0, -1, 1, -1, 1, 0, 1, 1, 0, 1, -1, 1, -1, 0, 0, 0])
	line_indices = array.array('I', [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 0, 3, 8, 8, 7, 1, 8, 8, 5])
	graph_handle = pstalgo.CreateSegmentGraph(line_coords, line_indices, None)
	return graph_handle