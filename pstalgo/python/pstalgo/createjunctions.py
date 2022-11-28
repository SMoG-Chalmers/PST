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


class SCreateJunctionsDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Layer 0
		("m_Coords0", POINTER(c_double)),
		("m_Lines0", POINTER(c_uint)),
		("m_LineCount0", c_uint),

		# Layer 1
		("m_Coords1", POINTER(c_double)),
		("m_Lines1", POINTER(c_uint)),
		("m_LineCount1", c_uint),

		# Unlinks
		("m_UnlinkCoords", POINTER(c_double)),
		("m_UnlinkCount", c_uint),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p)
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


class SCreateJunctionsRes(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),

		# Junction points
		("m_PointCoords", POINTER(c_double)),
		("m_PointCount", c_uint),
	]
	def __init__(self, *args):
		ctypes.Structure.__init__(self, *args)
		self.m_Version = 1


def PSTACreateJunctions(psta, desc, res):
	#print("\SCreateJunctionsDesc:")
	#DumpStructure(desc)
	fn = psta.PSTACreateJunctions
	fn.argtypes = [POINTER(SCreateJunctionsDesc), POINTER(SCreateJunctionsRes)]
	fn.restype = c_void_p
	return fn(byref(desc), byref(res))

def CreateJunctions(line_coords0, line_indices0=None, line_coords1=None, line_indices1=None, unlinks=None, progress_callback=None):
	desc = SCreateJunctionsDesc()
	# Layer 0
	(desc.m_Coords0, num_coord_values) = UnpackArray(line_coords0, 'd')
	(desc.m_Lines0, n) = UnpackArray(line_indices0, 'I')
	if line_indices0 is None:
		desc.m_LineCount0  = int(num_coord_values / 4); assert((num_coord_values % 4) == 0)
	else:
		desc.m_LineCount0  = int(n / 2); assert((n % 2) == 0)
	# Layer 1
	if line_coords1 is not None:
		(desc.m_Coords1, num_coord_values) = UnpackArray(line_coords1, 'd')
		(desc.m_Lines1, n) = UnpackArray(line_indices1, 'I')
		if line_indices1 is None:
			desc.m_LineCount1  = int(num_coord_values / 4); assert((num_coord_values % 4) == 0)
		else:
			desc.m_LineCount1  = int(n / 2); assert((n % 2) == 0)
	# Unlinks
	if unlinks is not None:
		(desc.m_UnlinkCoords, n) = UnpackArray(unlinks, 'd')
		desc.m_UnlinkCount  = int(n / 2); assert((n % 2) == 0)
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 

	res = SCreateJunctionsRes()

	algo = PSTACreateJunctions(_DLL, desc, res)
	if 0 == algo:
		raise Exception("CreateJunctions failed.")

	return (res, algo)