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


class SPSTAAttractionDistanceDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Graph
		("m_Graph", c_void_p),

		# Origin Type (see OriginType enum class above)
		("m_OriginType", ctypes.c_ubyte),
		
		# Distance Type (DistanceType enum class in common)
		("m_DistanceType", ctypes.c_ubyte),

		# Radius
		("m_Radius", Radii),

		# Attraction points
		("m_AttractionPoints", POINTER(c_double)),
		("m_AttractionPointCount", c_uint),

		# Attraction Polygons (optional)
		# If not NULL this means m_AttractionPoints should be treated as polygon 
		# corners, and the actual attraction points will be generated at every
		# 'm_AttractionPolygonPointInterval' interval along polygon edges.
		("m_PointsPerAttractionPolygon", POINTER(c_uint)),
		("m_AttractionPolygonCount", c_uint),
		("m_AttractionPolygonPointInterval", c_float),

		# Line weights (custom distance values)
		("m_LineWeights", POINTER(c_float)),
		("m_LineWeightCount", c_uint),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),

		# Outputs
		# Pointer to array of one element per input object (specified by m_OriginType)
		("m_OutMinDistances", POINTER(c_float)),
		("m_OutputCount", c_uint),  # For m_OutMinDistances array size verification only
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 2


def AttractionDistance(graph_handle, origin_type=OriginType.LINES, distance_type=DistanceType.STEPS, radius=Radii(), attraction_points=None, points_per_polygon=None, polygon_point_interval=0, line_weights=None, progress_callback = None, out_min_distances=None):
	desc = SPSTAAttractionDistanceDesc()
	# Graph
	desc.m_Graph = graph_handle
	# Origin Type
	desc.m_OriginType = origin_type
	# Distance Type
	desc.m_DistanceType = distance_type
	# Radius
	desc.m_Radius = radius
	# AttractionPoints
	(desc.m_AttractionPoints, n) = UnpackArray(attraction_points, 'd')
	desc.m_AttractionPointCount = int(n / 2); assert(n % 2 == 0)
	# Attraction Polygons
	if points_per_polygon is not None:
		(desc.m_PointsPerAttractionPolygon, desc.m_AttractionPolygonCount) = UnpackArray(points_per_polygon, 'I')
	else:
		desc.m_AttractionPolygonCount = 0
	desc.m_AttractionPolygonPointInterval = polygon_point_interval
	# Line Weights
	(desc.m_LineWeights, desc.m_LineWeightCount) = UnpackArray(line_weights, 'f')
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Outputs
	(desc.m_OutMinDistances, desc.m_OutputCount) = UnpackArray(out_min_distances, 'f')
	# Make the call
	fn = _DLL.PSTAAttractionDistance
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTAAttractionDistance failed.")
	return True