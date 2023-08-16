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
from ctypes import byref, cdll, POINTER, Structure, c_double, c_float, c_int, c_uint, c_void_p, c_byte
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, DOUBLE_PTR, CreateCallbackWrapper, UnpackArray, DumpStructure

class RasterFormat:
	Undefined = 0
	Byte = 1
	Float = 2

class SRasterData(Structure) :
	_fields_ = [
		("Version", c_uint),
		("BBMinX", c_double),
		("BBMinY", c_double),
		("BBMaxX", c_double),
		("BBMaxY", c_double),
		("Width", c_uint),
		("Height", c_uint),
		("Pitch", c_uint),
		("Format", c_byte),  # RasterFormat
		("Bits", c_void_p),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.Version = 1

def PSTAGetRasterData(psta, rasterHandle, rasterData):
	fn = psta.PSTAGetRasterData
	fn.argtypes = [c_void_p, POINTER(SRasterData)]
	fn.restype = c_int
	return fn(rasterHandle, byref(rasterData))

def GetRasterData(rasterHandle):
	rasterData = SRasterData()
	if 0 != PSTAGetRasterData(_DLL, rasterHandle, rasterData):
		raise Exception('PSTAGetRasterData failed')
	DumpStructure(rasterData)
	return rasterData