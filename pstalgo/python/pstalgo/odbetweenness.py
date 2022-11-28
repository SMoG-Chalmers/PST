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
from ctypes import byref, cdll, POINTER, Structure, c_double, c_float, c_int, c_uint, c_void_p, c_bool
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, CreateCallbackWrapper, UnpackArray, DumpStructure, Radii, DistanceType, OriginType


class ODBDestinationMode:
	ALL_REACHABLE_DESTINATIONS = 0
	CLOSEST_DESTINATION_ONLY = 1

class SPSTAODBetweenness(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Graph
		("m_Graph", c_void_p),

		# Origins
		("m_OriginPoints",  POINTER(c_double)),
		("m_OriginWeights", POINTER(c_float)),
		("m_OriginCount",   c_uint),

		# Destinations (must match points in m_Graph member)
		("m_DestinationWeights", POINTER(c_float)),
		("m_DestinationCount",   c_uint),

		# Origin Type (OriginType enum in common.py)
		("m_DestinationMode", ctypes.c_ubyte),  # DestinationMode enum

		# Distance Type (DistanceType enum in common.py)
		("m_DistanceType", ctypes.c_ubyte),

		# Radius
		("m_Radius", Radii),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),

		# Outputs
		("m_OutScores", POINTER(c_float)),  # Pointer to array of one element per origin object (specified by m_OriginType)
		("m_OutputCount", c_uint),  # For m_OutScores array size verification only
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


def ODBetweenness(
		graph_handle, 
		origin_points,
		origin_weights,
		destination_weights = None,
		destination_mode = ODBDestinationMode.ALL_REACHABLE_DESTINATIONS, 
		distance_type = DistanceType.WALKING, 
		radius=Radii(), 
		progress_callback = None, 
		out_scores=None):

	desc = SPSTAODBetweenness()
	desc.m_Graph = graph_handle
	(desc.m_OriginPoints, n0) = UnpackArray(origin_points, 'd')
	(desc.m_OriginWeights, n1) = UnpackArray(origin_weights, 'f')
	assert(origin_weights is None or n0 == n1 * 2)
	desc.m_OriginCount = int(n0 / 2); assert(n0 % 2 == 0)
	(desc.m_DestinationWeights, desc.m_DestinationCount) = UnpackArray(destination_weights, 'f')
	desc.m_DestinationMode = destination_mode
	desc.m_DistanceType = distance_type
	desc.m_Radius = radius
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	(desc.m_OutScores, desc.m_OutputCount) = UnpackArray(out_scores, 'f')
	# Make the call
	fn = _DLL.PSTAODBetweenness
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTAODBetweenness failed.")
	return True