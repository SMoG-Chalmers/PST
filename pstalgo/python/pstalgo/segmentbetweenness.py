"""
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
"""

import ctypes
from ctypes import byref, cdll, POINTER, Structure, c_double, c_float, c_int, c_uint, c_void_p
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, CreateCallbackWrapper, UnpackArray, DumpStructure, Radii

class SPSTASegmentBetweennessDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Graph
		("m_Graph", c_void_p),

		# Distance type
		("m_DistanceType", ctypes.c_ubyte),  # DistanceType enum in common.py

		# Radius
		("m_Radius", Radii),

		# Weights (optional)
		("m_Weights", POINTER(c_float)),

		# Attraction Points (optional)
		("m_AttractionPointCoords", POINTER(c_double)),
		("m_AttractionPointCount", c_uint),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),

		# Outputs (optional)
		("m_OutBetweenness", POINTER(c_float)),
		("m_OutNodeCount", POINTER(c_uint)),
		("m_OutTotalDepth", POINTER(c_float)),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


def SegmentBetweenness(graph_handle, distance_type, radius, weights = None, attraction_points = None, progress_callback = None, out_betweenness = None, out_node_count = None, out_total_depth = None):
	desc = SPSTASegmentBetweennessDesc()
	# Graph
	desc.m_Graph = graph_handle
	# Attraction Poiints
	(desc.m_AttractionPointCoords, n) = UnpackArray(attraction_points, 'd')
	desc.m_AttractionPointCount  = int(n / 2); assert((n % 2) == 0)
	# Weights
	if weights is not None:
		(desc.m_Weights, n) = UnpackArray(weights, 'f')
		# TODO: We should verify valid n here somehow
	# Points
	desc.m_DistanceType = distance_type
	# Radius
	desc.m_Radius = radius
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Outputs
	# TODO: Verify length of these
	desc.m_OutBetweenness = UnpackArray(out_betweenness, 'f')[0]  
	desc.m_OutNodeCount = UnpackArray(out_node_count, 'I')[0]
	desc.m_OutTotalDepth = UnpackArray(out_total_depth, 'f')[0]
	# Make the call
	fn = _DLL.PSTASegmentBetweenness
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTASegmentBetweenness failed.")
	return True

def BetweennessNormalize(in_values, node_counts, count, out_normalized):
	_DLL.PSTABetweennessNormalize(
		UnpackArray(in_values, 'f')[0],
		UnpackArray(node_counts, 'I')[0],
		ctypes.c_uint(count),
		UnpackArray(out_normalized, 'f')[0])

def BetweennessSyntaxNormalize(in_values, total_depths, count, out_normalized):
	_DLL.PSTABetweennessSyntaxNormalize(
		UnpackArray(in_values, 'f')[0],
		UnpackArray(total_depths, 'f')[0],
		ctypes.c_uint(count),
		UnpackArray(out_normalized, 'f')[0])
