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
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, DOUBLE_PTR, CreateCallbackWrapper, UnpackArray, DumpStructure

class SCreateIsovistContextDesc(Structure) :
	_fields_ = [
		("m_Version", c_uint),
		("m_PolygonCount", c_uint),
		("m_PointCountPerPolygon", POINTER(c_uint)),
		("m_PolygonPoints", POINTER(c_double)),
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1

class SCalculateIsovistDesc(Structure) :
	_fields_ = [
		("m_Version", c_uint),
		("m_IsovistContext", c_void_p),
		("m_OriginX", c_double),
		("m_OriginY", c_double),
		("m_MaxViewDistance", c_float),
		("m_FieldOfViewDegrees", c_float),
		("m_DirectionDegrees", c_float),
		("m_PerimeterSegmentCount", c_uint),
		("m_OutPointCount", c_uint),
		("m_OutPoints", POINTER(c_double)),
		("m_OutIsovistHandle", c_void_p),
		("m_OutArea", c_float),
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


def PSTACreateIsovistContext(psta, desc):
	#print("\SCreateIsovistContextDesc:")
	#DumpStructure(desc)
	fn = psta.PSTACreateIsovistContext
	fn.argtypes = [POINTER(SCreateIsovistContextDesc)]
	fn.restype = c_void_p
	return fn(byref(desc))

def PSTACalculateIsovist(psta, desc):
	#print("\PSTACalculateIsovist:")
	#DumpStructure(desc)
	fn = psta.PSTACalculateIsovist
	fn.argtypes = [POINTER(SCalculateIsovistDesc)]
	fn.restype = None
	return fn(byref(desc))


""" The returned context must be freed with call to Free(). """
def CreateIsovistContext(point_count_per_polygon, polygon_coords, progress_callback = None):
	desc = SCreateIsovistContextDesc()
	(desc.m_PointCountPerPolygon, desc.m_PolygonCount) = UnpackArray(point_count_per_polygon, 'I')
	(desc.m_PolygonPoints, n) = UnpackArray(polygon_coords, 'd')
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	isovist_context = PSTACreateIsovistContext(_DLL, desc)
	if 0 == isovist_context:
		raise Exception("CreateIsovistContext failed.")
	return isovist_context

""" The returned handle must be freed with call to Free(). """
def CalculateIsovist(isovist_context, originX, originY, max_view_distance, field_of_view_degrees, direction_degrees, perimeter_segment_count, progress_callback = None):
	desc = SCalculateIsovistDesc()
	desc.m_IsovistContext = isovist_context
	desc.m_OriginX = originX
	desc.m_OriginY = originY
	desc.m_MaxViewDistance = max_view_distance
	desc.m_FieldOfViewDegrees = field_of_view_degrees
	desc.m_DirectionDegrees = direction_degrees
	desc.m_PerimeterSegmentCount = perimeter_segment_count
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p()
	PSTACalculateIsovist(_DLL, desc)
	return (desc.m_OutPointCount, desc.m_OutPoints, desc.m_OutIsovistHandle, desc.m_OutArea)


"""
class SCalculateIsovistsDesc(Structure) :
	_fields_ = [
		("m_Version", c_uint),
		("m_PolygonCount", c_uint),
		("m_PointCountPerPolygon", POINTER(c_uint)),
		("m_PolygonPoints", POINTER(c_double)),
		("m_OriginCount", c_uint),
		("m_OriginPoints", POINTER(c_double)),
		("m_MaxRadius", c_float),
		("m_PerimeterSegmentCount", c_uint),
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p)
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


class SCalculateIsovistsRes(Structure) :
	_fields_ = [
		("m_Version", c_uint),
		("m_IsovistCount", c_uint),
		("m_PointCountPerIsovist", POINTER(c_uint)),
		("m_IsovistPoints", POINTER(c_double)),
	]
	def __init__(self, *args):
		ctypes.Structure.__init__(self, *args)
		self.m_Version = 1


def PSTACalculateIsovists(psta, desc, res):
	#print("\SCalculateIsovistsDesc:")
	#DumpStructure(desc)
	fn = psta.PSTACalculateIsovists
	fn.argtypes = [POINTER(SCalculateIsovistsDesc), POINTER(SCalculateIsovistsRes)]
	fn.restype = c_void_p
	return fn(byref(desc), byref(res))

def CalculateIsovists(point_count_per_polygon, polygon_coords, origin_coords, max_radius, perimeter_segment_count, progress_callback = None):
	desc = SCalculateIsovistsDesc()

	(desc.m_PointCountPerPolygon, desc.m_PolygonCount) = UnpackArray(point_count_per_polygon, 'I')
	(desc.m_PolygonPoints, n) = UnpackArray(polygon_coords, 'd')
	(desc.m_OriginPoints, n) = UnpackArray(origin_coords, 'd')
	desc.m_OriginCount = int(n / 2)
	desc.m_MaxRadius = max_radius
	desc.m_PerimeterSegmentCount = perimeter_segment_count
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 

	res = SCalculateIsovistsRes()

	algo = PSTACalculateIsovists(_DLL, desc, res)
	if 0 == algo:
		raise Exception("CalculateIsovists failed.")

	return (res, algo)
"""
