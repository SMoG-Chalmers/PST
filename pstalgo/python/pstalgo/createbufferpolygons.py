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
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, DOUBLE_PTR, CreateCallbackWrapper, UnpackArray, DumpStructure

class SCreateBufferPolygonsDesc(Structure) :
	_fields_ = [
		("Version", c_uint),
		("LineCount1", c_uint),
		("LineCoords1", POINTER(c_double)),
		("Values1", POINTER(c_float)),
		("LineCount2", c_uint),
		("LineCoords2", POINTER(c_double)),
		("Values2", POINTER(c_float)),
		("BufferSize", c_float),
		("Resolution", c_float),
		("CreateRangesPolygons", c_bool),
		("CreateRangesRaster", c_bool),
		("CreateGradientRaster", c_bool),
		("OutCategoryCount", c_uint),
		("OutPolygonCountPerCategory", POINTER(c_uint)),
		("OutPolygonData", POINTER(c_uint)),
		("OutPolygonCoords", POINTER(c_double)),
		("OutRangesRaster", c_void_p),
		("OutGradientRaster", c_void_p),
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.Version = 1


def PSTACreateBufferPolygons(psta, desc):
	#print("\SCreateBufferPolygonsDesc:")
	#DumpStructure(desc)
	fn = psta.PSTACreateBufferPolygons
	fn.argtypes = [POINTER(SCreateBufferPolygonsDesc)]
	fn.restype = c_void_p
	return fn(byref(desc))


""" The returned handle must be freed with call to Free(). """
def CreateBufferPolygons(lineCoords1, values1, lineCoords2, values2, resolution, bufferSize, createRangesPolygons, createRangesRaster, createGradientRaster, progress_callback = None):
	desc = SCreateBufferPolygonsDesc()
	(desc.Values1, valueCount1) = UnpackArray(values1, 'f')
	(desc.Values2, valueCount2) = UnpackArray(values2, 'f')
	(desc.LineCoords1, n) = UnpackArray(lineCoords1, 'd')
	desc.LineCount1 = int(n / 4); assert(n % 4 == 0)
	assert(valueCount1 == desc.LineCount1)
	if lineCoords2 is None:
		assert(valueCount1 == valueCount2)
	else:
		(desc.LineCoords2, n) = UnpackArray(lineCoords2, 'd')
		desc.LineCount2 = int(n / 4); assert(n % 4 == 0)
		assert(valueCount2 == desc.LineCount2)
	desc.BufferSize = bufferSize
	desc.Resolution = resolution
	desc.CreateRangesPolygons = createRangesPolygons
	desc.CreateRangesRaster = createRangesRaster
	desc.CreateGradientRaster = createGradientRaster
	desc.ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.ProgressCallbackUser = c_void_p() 
	handle = PSTACreateBufferPolygons(_DLL, desc)
	if 0 == handle:
		raise Exception("CreateBufferPolygons failed.")
	polygonCountPerCategory = [desc.OutPolygonCountPerCategory[i] for i in range(desc.OutCategoryCount)]
	return (polygonCountPerCategory, desc.OutPolygonData, desc.OutPolygonCoords, desc.OutRangesRaster, desc.OutGradientRaster, handle)