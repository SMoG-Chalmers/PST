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
from .common import _DLL

class ErrorLevel:
	VERBOSE=0
	INFO=1
	WARNING=2
	ERROR=3

ERROR_LEVEL_TEXT = [
	"VERBOSE",
	"INFO",
	"WARNING",
	"ERROR",
]

LOG_CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p)

def FormatLogMessage(error_level, domain, msg):
	if domain is None:
		return "%s: %s" % (ERROR_LEVEL_TEXT[error_level], msg)
	return "%s: (%s) %s" % (ERROR_LEVEL_TEXT[error_level], domain, msg)

def RegisterLogCallback(pyfunc):
	def CallbackWrapper(error_level, domain, msg, user_data):
		pyfunc(
			error_level, 
			None if domain is None else domain.decode("utf-8"), 
			None if msg is None else msg.decode("utf-8"))
	cfunc = LOG_CALLBACK_TYPE(CallbackWrapper)
	handle = _DLL.PSTARegisterLogCallback(cfunc, ctypes.c_void_p())
	if 0 == handle:
		raise Exception("PSTARegisterLogCallback failed.")
	return (cfunc, handle)

def UnregisterLogCallback(handle):
	# Make the call
	fn = _DLL.PSTAUnregisterLogCallback
	fn(ctypes.c_int(handle[1]))