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


class SPSTAReachDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Graph
		("m_Graph", c_void_p),

		# Radius
		("m_Radius", Radii),

		# Origin Points (optional)
		("m_OriginPointCoords", POINTER(c_double)),
		("m_OriginPointCount", c_uint),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),

		# Outputs (optional)
		("m_OutReachedCount", POINTER(c_uint)),
		("m_OutReachedLength", POINTER(c_float)),
		("m_OutReachedArea", POINTER(c_float)),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


def Reach(graph_handle, radius, origin_points = None, progress_callback = None, out_reached_count = None, out_reached_length = None, out_reached_area = None):
	desc = SPSTAReachDesc()
	# Graph
	desc.m_Graph = graph_handle
		# Radius
	desc.m_Radius = radius
	# Origin Poiints
	(desc.m_OriginPointCoords, n) = UnpackArray(origin_points, 'd')
	desc.m_OriginPointCount  = int(n / 2); assert((n % 2) == 0)
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Outputs
	# TODO: Verify length of these
	desc.m_OutReachedCount = UnpackArray(out_reached_count, 'I')[0]  
	desc.m_OutReachedLength = UnpackArray(out_reached_length, 'f')[0]
	desc.m_OutReachedArea = UnpackArray(out_reached_area, 'f')[0]
	# Make the call
	fn = _DLL.PSTAReach
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTAReach failed.")
	return True