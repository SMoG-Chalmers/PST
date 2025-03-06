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
from ctypes import byref, cdll, POINTER, Structure, c_double, c_float, c_int, c_uint, c_void_p, c_uint64
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, DOUBLE_PTR, CreateCallbackWrapper, UnpackArray, DumpStructure

class SPolygons(Structure):
	_fields_ = [
		("GroupCount", c_uint),
		("PolygonCountPerGroup", POINTER(c_uint)),
		("PointCountPerPolygon", POINTER(c_uint)),
		("Coords", POINTER(c_double))
	]

	@staticmethod
	def FromIsovistContextPolygons(polygons):
		s = SPolygons()
		(s.PolygonCountPerGroup, s.GroupCount) = UnpackArray(polygons.polygonCountPerGroup, 'I')
		s.PointCountPerPolygon = UnpackArray(polygons.pointCountPerPolygon, 'I')[0]
		s.Coords = UnpackArray(polygons.coords, 'd')[0]
		return s


class SPoints(Structure):
	_fields_ = [
		("GroupCount", c_uint),
		("PointCountPerGroup", POINTER(c_uint)),
		("Coords", POINTER(c_double))
	]

	@staticmethod
	def FromIsovistContextPoints(points):
		s = SPoints()
		(s.PointCountPerGroup, s.GroupCount) = UnpackArray(points.pointCountPerGroup, 'I')
		s.Coords = UnpackArray(points.coords, 'd')[0]
		return s


class SVisibleObjects(Structure):
	_fields_ = [
		("ObjectCount", c_uint),
		("GroupCount", c_uint),
		("CountPerGroup", POINTER(c_uint)),
		("Indices", POINTER(c_uint)),
	]

class IsovistContextGeometry:
	def __init__(self):
		self.obstaclePolygons = IsovistContextPolygons()
		self.attractionPoints = IsovistContextPoints()
		self.attractionPolygons = IsovistContextPolygons()

class IsovistContextPolygons:
	def __init__(self):
		self.polygonCountPerGroup = None
		self.pointCountPerPolygon = None
		self.coords = None

class IsovistContextPoints:
	def __init__(self):
		self.pointCountPerGroup = None
		self.coords = None


class SCreateIsovistContextDesc(Structure) :
	_fields_ = [
		("Version", c_uint),
		
		("ObstaclePolygons", SPolygons),
		("AttractionPoints", SPoints),
		("AttractionPolygons", SPolygons),
		
		("ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("ProgressCallbackUser", c_void_p),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.Version = 2

class SCalculateIsovistDesc(Structure) :
	_fields_ = [
		("Version", c_uint),
		("IsovistContext", c_void_p),
		("OriginX", c_double),
		("OriginY", c_double),
		("MaxViewDistance", c_float),
		("FieldOfViewDegrees", c_float),
		("DirectionDegrees", c_float),
		("PerimeterSegmentCount", c_uint),
		("OutPointCount", c_uint),
		("OutPoints", POINTER(c_double)),
		("OutIsovistHandle", c_void_p),
		("OutArea", c_float),

		("OutVisibleObstacles", SVisibleObjects),
		("OutVisibleAttractionPoints", SVisibleObjects),
		("OutVisibleAttractionPolygons", SVisibleObjects),

		("ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("ProgressCallbackUser", c_void_p),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.Version = 4

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
def CreateIsovistContext(isovistContextGeometry, progress_callback = None):
	desc = SCreateIsovistContextDesc()
	desc.ObstaclePolygons = SPolygons.FromIsovistContextPolygons(isovistContextGeometry.obstaclePolygons)
	desc.AttractionPoints = SPoints.FromIsovistContextPoints(isovistContextGeometry.attractionPoints)
	desc.AttractionPolygons = SPolygons.FromIsovistContextPolygons(isovistContextGeometry.attractionPolygons)
	desc.ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.ProgressCallbackUser = c_void_p() 
	isovist_context = PSTACreateIsovistContext(_DLL, desc)
	if 0 == isovist_context:
		raise Exception("CreateIsovistContext failed.")
	return isovist_context

""" The returned handle must be freed with call to Free(). """
def CalculateIsovist(isovist_context, originX, originY, max_view_distance, field_of_view_degrees, direction_degrees, perimeter_segment_count, progress_callback = None):
	desc = SCalculateIsovistDesc()
	desc.IsovistContext = isovist_context
	desc.OriginX = originX
	desc.OriginY = originY
	desc.MaxViewDistance = max_view_distance
	desc.FieldOfViewDegrees = field_of_view_degrees
	desc.DirectionDegrees = direction_degrees
	desc.PerimeterSegmentCount = perimeter_segment_count
	desc.ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.ProgressCallbackUser = c_void_p()
	PSTACalculateIsovist(_DLL, desc)
	return (desc.OutPointCount, desc.OutPoints, desc.OutIsovistHandle, desc.OutArea, desc.OutVisibleObstacles, desc.OutVisibleAttractionPoints, desc.OutVisibleAttractionPolygons)

"""
class SCalculateIsovistsDesc(Structure) :
	_fields_ = [
		("Version", c_uint),
		("PolygonCount", c_uint),
		("PointCountPerPolygon", POINTER(c_uint)),
		("PolygonPoints", POINTER(c_double)),
		("OriginCount", c_uint),
		("OriginPoints", POINTER(c_double)),
		("MaxRadius", c_float),
		("PerimeterSegmentCount", c_uint),
		("ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("ProgressCallbackUser", c_void_p)
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.Version = 1


class SCalculateIsovistsRes(Structure) :
	_fields_ = [
		("Version", c_uint),
		("IsovistCount", c_uint),
		("PointCountPerIsovist", POINTER(c_uint)),
		("IsovistPoints", POINTER(c_double)),
	]
	def __init__(self, *args):
		ctypes.Structure.__init__(self, *args)
		self.Version = 1


def PSTACalculateIsovists(psta, desc, res):
	#print("\SCalculateIsovistsDesc:")
	#DumpStructure(desc)
	fn = psta.PSTACalculateIsovists
	fn.argtypes = [POINTER(SCalculateIsovistsDesc), POINTER(SCalculateIsovistsRes)]
	fn.restype = c_void_p
	return fn(byref(desc), byref(res))

def CalculateIsovists(point_count_per_polygon, polygon_coords, origin_coords, max_radius, perimeter_segment_count, progress_callback = None):
	desc = SCalculateIsovistsDesc()

	(desc.PointCountPerPolygon, desc.PolygonCount) = UnpackArray(point_count_per_polygon, 'I')
	(desc.PolygonPoints, n) = UnpackArray(polygon_coords, 'd')
	(desc.OriginPoints, n) = UnpackArray(origin_coords, 'd')
	desc.OriginCount = int(n / 2)
	desc.MaxRadius = max_radius
	desc.PerimeterSegmentCount = perimeter_segment_count
	desc.ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.ProgressCallbackUser = c_void_p() 

	res = SCalculateIsovistsRes()

	algo = PSTACalculateIsovists(_DLL, desc, res)
	if 0 == algo:
		raise Exception("CalculateIsovists failed.")

	return (res, algo)
"""
