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
from .common import _DLL, Radii, PSTALGO_PROGRESS_CALLBACK, CreateCallbackWrapper, UnpackArray, DumpStructure


class SPSTANetworkIntegration(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Graph
		("m_Graph", c_void_p),

		# Radius
		("m_Radius", Radii),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),

		# Output per Junction (optional)
		("m_OutJunctionCoords", POINTER(c_double)),
		("m_OutJunctionScores", POINTER(c_float)),
		("m_OutJunctionCount", c_uint),

		# Output per Line (optional)
		("m_OutLineIntegration", POINTER(c_float)),
		("m_OutLineNodeCount", POINTER(c_uint)),
		("m_OutLineTotalDepth", POINTER(c_float)),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


def NetworkIntegration(graph_handle, radius, progress_callback = None, out_junction_coords = None, out_junction_scores = None, out_line_integration = None, out_line_node_count = None, out_line_total_depth = None):
	desc = SPSTANetworkIntegration()
	# Graph
	desc.m_Graph = graph_handle
		# Radius
	desc.m_Radius = radius
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Outputs per Junction
	(desc.m_OutJunctionCoords, n) = UnpackArray(out_junction_coords, 'd')
	desc.m_OutJunctionCount  = int(n / 2); assert((n % 2) == 0)
	(desc.m_OutJunctionScores, n) = UnpackArray(out_junction_scores, 'f')
	if out_junction_scores:
		if out_junction_coords is not None:
			assert(n == desc.m_OutJunctionCount)
		else:
			desc.m_OutJunctionCount = n
	# Outputs per Line 
	# TODO: Verify length of these
	desc.m_OutLineIntegration = UnpackArray(out_line_integration, 'f')[0]  
	desc.m_OutLineNodeCount = UnpackArray(out_line_node_count, 'I')[0]
	desc.m_OutLineTotalDepth = UnpackArray(out_line_total_depth, 'f')[0]
	# Make the call
	fn = _DLL.PSTANetworkIntegration
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTANetworkIntegration failed.")
	return True