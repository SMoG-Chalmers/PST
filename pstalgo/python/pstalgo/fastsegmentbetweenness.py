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

import ctypes
from ctypes import byref, cdll, POINTER, Structure, c_double, c_float, c_int, c_uint, c_void_p
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, CreateCallbackWrapper, UnpackArray, DumpStructure, Radii

class SPSTAFastSegmentBetweennessDesc(Structure) :
	_fields_ = [
		("m_Version", c_uint),

		# Graph
		("m_Graph", c_void_p),

		# Distance type
		("m_DistanceType", ctypes.c_ubyte),  # DistanceType enum in common.py
		
		# Weight mode
		("m_WeighByLength", ctypes.c_bool),

		# Radius (only WALKING supported)
		("m_Radius", Radii),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),

		# Outputs (optional)
		("m_OutBetweenness", POINTER(c_float)),
		("m_OutNodeCount",   POINTER(c_uint)),
		("m_OutTotalDepth",  POINTER(c_float)),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 2

def FastSegmentBetweenness(graph_handle, distance_type, weigh_by_length, radius, progress_callback = None, out_betweenness = None, out_node_count = None, out_total_depth = None):
	desc = SPSTAFastSegmentBetweennessDesc()
	desc.m_Graph = graph_handle
	desc.m_DistanceType = distance_type
	desc.m_WeighByLength = weigh_by_length
	desc.m_Radius = radius
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	desc.m_OutBetweenness = UnpackArray(out_betweenness, 'f')[0]  
	desc.m_OutNodeCount = UnpackArray(out_node_count, 'I')[0]  
	desc.m_OutTotalDepth = UnpackArray(out_total_depth, 'f')[0]  
	# Make the call
	fn = _DLL.PSTAFastSegmentBetweenness
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTAFastSegmentBetweenness failed.")
	return True