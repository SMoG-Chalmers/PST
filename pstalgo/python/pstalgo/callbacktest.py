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

import ctypes
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, CreateCallbackWrapper, DumpStructure

class SCallbackTestDesc(ctypes.Structure) :
	_fields_ = [
		("m_Version", ctypes.c_uint),
		("m_Status", ctypes.c_char_p),
		("m_Progress", ctypes.c_float),
		("m_ReturnValue", ctypes.c_int),
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", ctypes.c_void_p)
	]
	def __init__(self, *args):
		ctypes.Structure.__init__(self, *args)
		self.m_Version = 1

def PSTACallbackTest(psta, desc):
	fn = psta.PSTACallbackTest
	fn.argtypes = [ctypes.POINTER(SCallbackTestDesc)]
	fn.restype = ctypes.c_int
	return fn(ctypes.byref(desc))

def CallbackTest(status, progress, return_value, progress_callback):
	desc = SCallbackTestDesc()
	desc.m_Status = ctypes.c_char_p(status.encode('utf-8'))  # ctypes.create_string_buffer(status.encode('utf-8')))
	desc.m_Progress = progress
	desc.m_ReturnValue = return_value
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = ctypes.c_void_p() 
	return PSTACallbackTest(_DLL, desc)