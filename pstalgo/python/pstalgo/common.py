"""
Copyright 2019 Meta Berghauser Pont

This file is part of PST.

PST is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. The GNU General Public License
is intended to guarantee your freedom to share and change all versions
of a program--to make sure it remains free software for all its users.

PST is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PST. If not, see <http://www.gnu.org/licenses/>.
"""

import array, ctypes, os, sys
from .vector import Vector

def DebugEnabled():
	import os
	return os.environ.get('PSTALGO_DEBUG') is not None

def Is64Bit():
	return sys.maxsize > 2**32

def GetBinFolder():
	import inspect
	folder_of_this_file = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	return os.path.normpath(os.path.join(folder_of_this_file, '../../bin'))

def GetLibFileName():
	import platform
	if 'Windows' == platform.system():
		return 'pstalgo' + ('64' if Is64Bit() else '32') + ('d' if DebugEnabled() else '') + '.dll'
	elif 'Darwin' == platform.system():
		return 'libpstalgo.dylib'
	raise Exception("Unsupported plataform: %s" & platform.system())


DLL_PATH = os.path.join(GetBinFolder(), GetLibFileName())
_DLL = ctypes.cdll.LoadLibrary(DLL_PATH)


class DistanceType:
	""" NOTE: Has to match EPSTADistanceType """
	STRAIGHT = 0
	WALKING = 1
	STEPS = 2
	ANGULAR = 3
	AXMETER = 4
	UNDEFINED = 5

class OriginType:
	""" NOTE: Has to match EPSTAOriginType """
	POINTS = 0
	JUNCTIONS = 1
	LINES = 2
	POINT_GROUPS = 3

class RoadNetworkType:
	UNKNOWN           = 0
	AXIAL_OR_SEGMENT  = 1
	ROAD_CENTER_LINES = 2

	@staticmethod
	def FromString(s):
		for k, v in RoadNetworkTypeStrings.items():
			if s == v:
				return k
		raise Exception("Unknown road network type '%s'" % s)

	@staticmethod
	def ToString(road_network_type):
		return RoadNetworkTypeStrings[road_network_type]
	
RoadNetworkTypeStrings = {
	RoadNetworkType.AXIAL_OR_SEGMENT  : "Axial/Segment Lines",
	RoadNetworkType.ROAD_CENTER_LINES : "Road Centre Lines",
}


class Radii(ctypes.Structure) :
	MASK_STRAIGHT = 1
	MASK_WALKING = 2
	MASK_STEPS = 4
	MASK_ANGULAR = 8
	MASK_AXMETER = 16

	_fields_ = [
		("m_Mask", ctypes.c_uint),
		("m_Straight", ctypes.c_float),
		("m_Walking", ctypes.c_float),
		("m_Steps", ctypes.c_uint),
		("m_Angular", ctypes.c_float),
		("m_Axmeter", ctypes.c_float)
	]

	def __init__(self, straight = None, walking = None, steps = None, angular = None, axmeter = None):
		ctypes.Structure.__init__(self)
		self.m_Mask = 0
		self.m_Straight = 0
		self.m_Walking = 0
		self.m_Steps = 0
		self.m_Angular = 0
		self.m_Axmeter = 0
		if straight is not None:
			self.setStraight(straight)
		if walking is not None:
			self.setWalking(walking)
		if steps is not None:
			self.setSteps(steps)
		if angular is not None:
			self.setAngular(angular)
		if axmeter is not None:
			self.setAxmeter(axmeter)

	def straight(self):
		return self.m_Straight

	def walking(self):
		return self.m_Walking

	def steps(self):
		return self.m_Steps

	def angular(self):
		return self.m_Angular

	def axmeter(self):
		return self.m_Axmeter

	def hasStraight(self):
		return 0 != (self.MASK_STRAIGHT & self.m_Mask)

	def hasWalking(self):
		return 0 != (self.MASK_WALKING & self.m_Mask)

	def hasSteps(self):
		return 0 != (self.MASK_STEPS & self.m_Mask)

	def hasAngular(self):
		return 0 != (self.MASK_ANGULAR & self.m_Mask)

	def hasAxmeter(self):
		return 0 != (self.MASK_AXMETER & self.m_Mask)

	def setStraight(self, value):
		self.m_Straight = value
		self.m_Mask |= self.MASK_STRAIGHT

	def setWalking(self, value):
		self.m_Walking = value
		self.m_Mask |= self.MASK_WALKING

	def setSteps(self, value):
		self.m_Steps = int(value)
		self.m_Mask |= self.MASK_STEPS

	def setAngular(self, value):
		self.m_Angular = value
		self.m_Mask |= self.MASK_ANGULAR

	def setAxmeter(self, value):
		self.m_Axmeter = value
		self.m_Mask |= self.MASK_AXMETER

	def split(self):
		r = []
		if self.MASK_STRAIGHT & self.m_Mask:
			r.append(Radii(straight=self.m_Straight))
		if self.MASK_WALKING & self.m_Mask:
			r.append(Radii(walking=self.m_Walking))
		if self.MASK_STEPS & self.m_Mask:
			r.append(Radii(steps=self.m_Steps))
		if self.MASK_ANGULAR & self.m_Mask:
			r.append(Radii(angular=self.m_Angular))
		if self.MASK_AXMETER & self.m_Mask:
			r.append(Radii(axmeter=self.m_Axmeter))
		return r

	def toString(self):
		if 0 == self.m_Mask:
			return "(No limits)"
		text_limits = []
		if self.MASK_STRAIGHT & self.m_Mask:
			text_limits.append("straight=%f"%self.m_Straight)
		if self.MASK_WALKING & self.m_Mask:
			text_limits.append("walking=%f"%self.m_Walking)
		if self.MASK_STEPS & self.m_Mask:
			text_limits.append("steps=%d"%self.m_Steps)
		if self.MASK_ANGULAR & self.m_Mask:
			text_limits.append("angular=%f"%self.m_Angular)
		if self.MASK_AXMETER & self.m_Mask:
			text_limits.append("axmeter=%f"%self.m_Axmeter)
		return "(%s)" % (", ".join(text_limits))

PSTALGO_PROGRESS_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_float, ctypes.c_void_p)

ARRAY_TYPE_TO_C_TYPE = {
	'i' : ctypes.POINTER(ctypes.c_int),
	'I' : ctypes.POINTER(ctypes.c_uint),
	'f' : ctypes.POINTER(ctypes.c_float),
	'd' : ctypes.POINTER(ctypes.c_double),
}

def CreateCallbackWrapper(callable):
	if callable is None:
		return PSTALGO_PROGRESS_CALLBACK()
	def callback(status, progress, user_data):
		return 1 if callable(None if status is None else status.decode("utf-8"), progress) else 0
	return PSTALGO_PROGRESS_CALLBACK(callback)

# DEBUG
def PtrToStr(ptr):
	addr = ctypes.cast(ptr, ctypes.c_void_p).value
	if addr is None:
		return "NULL"
	return "0x%.8x" % addr

# DEBUG
def DumpStructure(s):
	for (n,t) in s._fields_:
		value = getattr(s, n)
		value_str = PtrToStr(value) if isinstance(value, ctypes._Pointer) else str(value)
		print("%s = %s" % (n, value_str))

def Free(algo):
	fn = _DLL.PSTAFree
	fn.argtypes = [ctypes.c_void_p]
	fn(algo)

def UnpackArray(arr, typecode):
	if arr is None:
		return (ARRAY_TYPE_TO_C_TYPE[typecode](), 0)
	if isinstance(arr, Vector):
		return (arr.ptr(), arr.size())
	if type(arr) == array.array:
		if typecode != arr.typecode:
			raise TypeError("Array data type error. Expected type '%s' but got '%s'." % (typecode, arr.typecode))
		addr = arr.buffer_info()[0]
		ptr = ctypes.cast(ctypes.c_void_p(addr), ARRAY_TYPE_TO_C_TYPE[typecode])
		return (ptr, len(arr))
	raise TypeError("Unsupported array type: %s" % str(type(arr)))

def StandardNormalize(in_scores, count, out_normalized_scores):
	_DLL.PSTAStandardNormalize(
		UnpackArray(in_scores, 'f')[0],
		ctypes.c_uint(count),
		UnpackArray(out_normalized_scores, 'f')[0])
