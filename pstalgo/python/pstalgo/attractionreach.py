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


class AttractionWeightFunction:
	CONSTANT = 0
	POW = 1
	CURVE = 2
	DIVIDE = 3

class AttractionScoreAccumulationMode:
	SUM = 0
	MAX = 1

class AttractionDistributionFunc:
	COPY   = 0
	DIVIDE = 1

class AttractionCollectionFunc:
	AVARAGE = 0
	SUM     = 1
	MIN     = 2
	MAX     = 3


class SPSTAAttractionReachDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Graph
		("m_Graph", c_void_p),

		# Origin Type (OriginType enum in common.py)
		("m_OriginType", ctypes.c_ubyte),
		
		# Distance Type (DistanceType enum in common.py)
		("m_DistanceType", ctypes.c_ubyte),

		# Radius
		("m_Radius", Radii),

		# Weight function
		("m_WeightFunc", ctypes.c_ubyte),  # (AttractionWeightFunction enum)
		("m_WeightFuncConstant", ctypes.c_float),

		# DEPRECATED!
		# Accumulation mode
		("m_ScoreAccumulationMode", ctypes.c_ubyte),  # (AttractionScoreAccumulationMode enum)

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

		# Attraction values (per polygon if polygons area available, otherwise per point)
		("m_AttractionValues", POINTER(c_float)),

		# Attraction Distribution Function, only applicable if attraction polygons are available
		("m_AttractionDistributionFunc", ctypes.c_ubyte),  # (AttractionDistributionFunc enum)

		# Attraction Collection Function, only applicable if the graph has point groups
		("m_AttractionCollectionFunc", ctypes.c_ubyte),  # (EAttractionCollectionFunc enum)

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


def AttractionReach(
		graph_handle, 
		origin_type=OriginType.LINES, 
		distance_type=DistanceType.STEPS, 
		radius=Radii(), 
		weight_func=AttractionWeightFunction.CONSTANT,
		weight_func_constant=0,
		attraction_points=None,
		points_per_attraction_polygon=None, 
		attraction_polygon_point_interval=0,
		attraction_values=None, 
		attraction_distribution_func=AttractionDistributionFunc.DIVIDE,
		attraction_collection_func=AttractionCollectionFunc.AVARAGE,
		progress_callback = None, 
		out_scores=None):
	desc = SPSTAAttractionReachDesc()
	# Graph
	desc.m_Graph = graph_handle
	# Origin Type
	desc.m_OriginType = origin_type
	# Distance Type
	desc.m_DistanceType = distance_type
	# Radius
	desc.m_Radius = radius
	# Weight function
	desc.m_WeightFunc = weight_func
	desc.m_WeightFuncConstant = weight_func_constant
	# Accumulation mode
	desc.m_ScoreAccumulationMode = AttractionScoreAccumulationMode.SUM
	# AttractionPoints
	(desc.m_AttractionPoints, n) = UnpackArray(attraction_points, 'd')
	desc.m_AttractionPointCount = int(n / 2); assert(n % 2 == 0)
	# Attraction Polygons
	if points_per_attraction_polygon is not None:
		(desc.m_PointsPerAttractionPolygon, desc.m_AttractionPolygonCount) = UnpackArray(points_per_attraction_polygon, 'I')
	else:
		desc.m_AttractionPolygonCount = 0
	desc.m_AttractionPolygonPointInterval = attraction_polygon_point_interval
	# Attraction values	
	if attraction_values is not None:
		(desc.m_AttractionValues, n) = UnpackArray(attraction_values, 'f')
		if points_per_attraction_polygon is not None:
			assert(n == desc.m_AttractionPolygonCount)
		else:
			assert(n == desc.m_AttractionPointCount)
	# Attraction Distribution Function
	desc.m_AttractionDistributionFunc = attraction_distribution_func
	# Attraction Collection Function
	desc.m_AttractionCollectionFunc = attraction_collection_func
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Outputs
	(desc.m_OutScores, desc.m_OutputCount) = UnpackArray(out_scores, 'f')
	# Make the call
	fn = _DLL.PSTAAttractionReach
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTAAttractionReach failed.")
	return True