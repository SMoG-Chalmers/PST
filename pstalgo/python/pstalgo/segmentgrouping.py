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


class SPSTASegmentGroupingDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", ctypes.c_uint),
		
		# Graph
		("m_SegmentGraph", ctypes.c_void_p),

		# Options
		("m_AngleThresholdDegrees",  ctypes.c_float),
		("m_SplitGroupsAtJunctions", ctypes.c_bool),

		# Progress Callback
		("m_ProgressCallback",     PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", ctypes.c_void_p),

		("m_LineCount", ctypes.c_uint),

		# Output
		("m_OutGroupIdPerLine", ctypes.POINTER(ctypes.c_uint)),
		("m_OutGroupCount",     ctypes.c_uint),
		("m_OutColorPerLine",   ctypes.POINTER(ctypes.c_uint)),
		("m_OutColorCount",     ctypes.c_uint),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


def SegmentGrouping(segment_graph, angle_threshold=1.0, split_at_junctions=False, out_group_id_per_line=None, out_color_per_line=None, progress_callback=None):
	desc = SPSTASegmentGroupingDesc()
	# Graph
	desc.m_SegmentGraph = segment_graph
	# Settings
	desc.m_AngleThresholdDegrees = float(angle_threshold)
	desc.m_SplitGroupsAtJunctions = split_at_junctions
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Outputs
	(desc.m_OutGroupIdPerLine, n1) = UnpackArray(out_group_id_per_line, 'I')
	(desc.m_OutColorPerLine, n2) = UnpackArray(out_color_per_line, 'I')
	if out_group_id_per_line is not None:
		desc.m_LineCount = n1
	elif out_color_per_line is not None:
		desc.m_LineCount = n2
	else:
		desc.m_LineCount = 0
	# Make the call
	fn = _DLL.PSTASegmentGrouping
	fn.restype = ctypes.c_bool
	if not fn(ctypes.byref(desc)):
		raise Exception("PSTASegmentGrouping failed.")
	return (desc.m_OutGroupCount, desc.m_OutColorCount if desc.m_OutColorPerLine is not None else None)