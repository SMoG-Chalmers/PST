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

from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, CreateCallbackWrapper, UnpackArray, DumpStructure

class SCreateSegmentMapDesc(Structure) :
	_fields_ = [
		("m_Version", c_uint),
		("m_Snap", c_float),
		("m_ExtrudeCut", c_float),
		("m_MinTail", c_float),
		("m_Min3NodeColinearDeviation", c_float),
		("m_RoadNetworkType", ctypes.c_ubyte),
		("m_PolyCoords", POINTER(c_double)),
		("m_PolySections", POINTER(c_int)),
		("m_PolyCoordCount", c_uint),
		("m_PolySectionCount", c_uint),
		("m_PolyCount", c_uint),
		("m_UnlinkCoords", POINTER(c_double)),
		("m_UnlinkCount", c_uint),
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p)
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 2


class SCreateSegmentMapRes(Structure) :
	_fields_ = [
		("m_Version", c_uint),
		("m_SegmentCoords", POINTER(c_double)),
		("m_Segments", POINTER(c_uint)),  # (P0, P1, BaseIndex)
		("m_SegmentCount", c_uint),
		("m_UnlinkCoords", POINTER(c_double)),
		("m_UnlinkCount", c_uint),
	]
	def __init__(self, *args):
		ctypes.Structure.__init__(self, *args)
		self.m_Version = 2

def PSTACreateSegmentMap(psta, desc, res):
	#print("\nSCreateSegmentMapDesc:")
	#DumpStructure(desc)
	fn = psta.PSTACreateSegmentMap
	fn.argtypes = [POINTER(SCreateSegmentMapDesc), POINTER(SCreateSegmentMapRes)]
	fn.restype = c_void_p
	return fn(byref(desc), byref(res))

def CreateSegmentMap(road_network_type, poly_coords, poly_sections, unlinks = None, progress_callback = None, snap=1, tail=10, deviation=1, extrude=0):
	desc = SCreateSegmentMapDesc()
	desc.m_Snap = snap
	desc.m_ExtrudeCut = extrude
	desc.m_MinTail = tail
	desc.m_Min3NodeColinearDeviation = deviation
	desc.m_RoadNetworkType = road_network_type
	(desc.m_PolyCoords, n) = UnpackArray(poly_coords, 'd')
	desc.m_PolyCoordCount = int(n / 2); assert((n % 2) == 0)
	(desc.m_PolySections, desc.m_PolySectionCount) = UnpackArray(poly_sections, 'i')
	desc.m_PolyCount = desc.m_PolySectionCount
	(desc.m_UnlinkCoords, n) = UnpackArray(unlinks, 'd')
	desc.m_UnlinkCount = int(n / 2); assert((n % 2) == 0)
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 

	res = SCreateSegmentMapRes()

	algo = PSTACreateSegmentMap(_DLL, desc, res)
	if 0 == algo:
		raise Exception("CreateSegmentMap failed.")

	return (res, algo)