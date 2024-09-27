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

import array
from ctypes import byref, cdll, POINTER, Structure, c_double, c_float, c_uint, c_void_p
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, DOUBLE_PTR, CreateCallbackWrapper, UnpackArray, DumpStructure


class CompareResultsMode:
	NORMALIZED = 0
	RELATIVE_PERCENT = 1


class SCompareResultsDesc(Structure) :
	_fields_ = [
		("Version", c_uint),
		("LineCount1", c_uint),
		("LineCoords1", POINTER(c_double)),
		("Values1", POINTER(c_float)),
		("Mode", c_uint),
		("M", c_float),
		("LineCount2", c_uint),
		("LineCoords2", POINTER(c_double)),
		("Values2", POINTER(c_float)),
		("BlurRadius", c_float),
		("Resolution", c_float),
		("OutRaster", c_void_p),
		("OutMin", c_float),
		("OutMax", c_float),
		("ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("ProgressCallbackUser", c_void_p),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.Version = 4


def PSTACompareResults(psta, desc):
	#print("\SCompareResultsDesc:")
	#DumpStructure(desc)
	fn = psta.PSTACompareResults
	fn.argtypes = [POINTER(SCompareResultsDesc)]
	fn.restype = c_void_p
	return fn(byref(desc))

""" The returned handle must be freed with call to Free(). """
def CompareResults(lineCoords1, values1, lineCoords2=None, values2=None, mode=0, M=0, resolution=0, blurRadius=1, progress_callback=None):
	desc = SCompareResultsDesc()
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
	desc.Mode = mode
	desc.M = M
	desc.BlurRadius = blurRadius
	desc.Resolution = resolution if resolution > 0 else blurRadius
	desc.ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.ProgressCallbackUser = c_void_p() 
	handle = PSTACompareResults(_DLL, desc)
	if 0 == handle:
		raise Exception("CompareResults failed.")
	return (desc.OutRaster, desc.OutMin, desc.OutMax, handle)


class SRasterToPolygonsDesc(Structure) :
	_fields_ = [
		("Version", c_uint),
		("Raster", c_void_p),
		("RangeCount", c_uint),
		("Ranges", POINTER(c_float)),
		("OutPolygonCountPerRange", POINTER(c_uint)),
		("OutPolygonData", POINTER(c_uint)),
		("OutPolygonCoords", POINTER(c_double)),
		("ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("ProgressCallbackUser", c_void_p),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.Version = 1


def PSTARasterToPolygons(psta, desc):
	#print("\SRasterToPolygonsDesc:")
	#DumpStructure(desc)
	fn = psta.PSTARasterToPolygons
	fn.argtypes = [POINTER(SRasterToPolygonsDesc)]
	fn.restype = c_void_p
	return fn(byref(desc))

""" The returned handle must be freed with call to Free(). """
def RasterToPolygons(raster, ranges, progress_callback = None):
	desc = SRasterToPolygonsDesc()
	desc.Raster = raster
	desc.RangeCount = len(ranges)
	ranges_arr = []
	for r in ranges:
		ranges_arr.append(r[0])
		ranges_arr.append(r[1])
	ranges_arr = array.array('f', ranges_arr)
	(desc.Ranges, _) = UnpackArray(ranges_arr, 'f')
	desc.ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.ProgressCallbackUser = c_void_p() 
	handle = PSTARasterToPolygons(_DLL, desc)
	if 0 == handle:
		raise Exception("RasterToPolygons failed.")
	polygonCountPerCategory = [desc.OutPolygonCountPerRange[i] for i in range(desc.RangeCount)]
	return (polygonCountPerCategory, desc.OutPolygonData, desc.OutPolygonCoords, handle)