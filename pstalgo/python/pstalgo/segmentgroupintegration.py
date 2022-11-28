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
from .common import _DLL, Radii, PSTALGO_PROGRESS_CALLBACK, CreateCallbackWrapper, UnpackArray, DumpStructure


class SPSTASegmentGroupIntegration(Structure) :
	_fields_ = [
		# Version
		("m_Version", ctypes.c_uint),
		
		# Graph
		("m_Graph", ctypes.c_void_p),

		# Radius
		("m_Radius", Radii),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", ctypes.c_void_p),

		# Output per group (optional)
		("m_OutIntegration", ctypes.POINTER(ctypes.c_float)),
		("m_OutNodeCount",   ctypes.POINTER(ctypes.c_uint)),
		("m_OutTotalDepth",  ctypes.POINTER(ctypes.c_float)),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


def SegmentGroupIntegration(group_graph, radii, progress_callback = None, out_integration = None, out_node_counts = None, out_total_depths = None):
	desc = SPSTASegmentGroupIntegration()
	# Graph
	desc.m_Graph = group_graph
		# Radius
	desc.m_Radius = radii
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Outputs per Line 
	# TODO: Verify length of these
	desc.m_OutIntegration = UnpackArray(out_integration, 'f')[0]  
	desc.m_OutNodeCount   = UnpackArray(out_node_counts, 'I')[0]
	desc.m_OutTotalDepth  = UnpackArray(out_total_depths, 'f')[0]
	# Make the call
	fn = _DLL.PSTASegmentGroupIntegration
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTASegmentGroupIntegration failed.")