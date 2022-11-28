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


###############################################################################
# Axial Graph

class SPSTACreateGraphDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Lines
		("m_LineCoords", POINTER(c_double)),
		("m_Lines", POINTER(c_uint)),
		("m_LineCoordCount", c_uint),
		("m_LineCount", c_uint),

		# Unlinks (optional)
		("m_UnlinkCoords", POINTER(c_double)),
		("m_UnlinkCount", c_uint),

		# Points (optional)
		("m_PointCoords", POINTER(c_double)),
		("m_PointCount", c_uint),

		# Polygons (optional)
		# If not None this means m_PointCoords should be treated as polygon 
		# corners, and the actual points for the graph will be generated at 
		# every 'm_PolygonPointInterval' interval along polygon edges.
		("m_PointsPerPolygon", POINTER(c_uint)),
		("m_PolygonCount", c_uint),
		("m_PolygonPointInterval", c_float),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p)
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


class SPSTAGraphInfo(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Lines
		("m_LineCount",       c_uint),
		("m_CrossingCount",   c_uint),
		("m_PointCount",      c_uint),
		("m_PointGroupCount", c_uint),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1


def CreateGraph(line_coords, line_indices=None, unlinks=None, points=None, points_per_polygon=None, polygon_point_interval=0, progress_callback=None):
	desc = SPSTACreateGraphDesc()
	# Lines
	(desc.m_LineCoords, n) = UnpackArray(line_coords, 'd')
	desc.m_LineCoordCount  = int(n / 2); assert((n % 2) == 0)
	(desc.m_Lines, n) = UnpackArray(line_indices, 'I')
	if line_indices is None:
		desc.m_LineCount  = int(desc.m_LineCoordCount / 2); assert((desc.m_LineCoordCount % 2) == 0)
	else:
		desc.m_LineCount  = int(n / 2); assert((n % 2) == 0)
	# Unlinks
	if unlinks is not None:
		(desc.m_UnlinkCoords, n) = UnpackArray(unlinks, 'd')
		desc.m_UnlinkCount  = int(n / 2); assert((n % 2) == 0)
	else:
		desc.m_UnlinkCount = 0
	# Points
	if points is not None:
		(desc.m_PointCoords, n) = UnpackArray(points, 'd')
		desc.m_PointCount  = int(n / 2); assert((n % 2) == 0)
	else:
		desc.m_PointCount = 0
	# Polygons
	if points_per_polygon is not None:
		(desc.m_PointsPerPolygon, desc.m_PolygonCount) = UnpackArray(points_per_polygon, 'I')
	else:
		desc.m_PolygonCount = 0
	desc.m_PolygonPointInterval = polygon_point_interval
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 

	# Make the call
	fn = _DLL.PSTACreateGraph
	fn.restype = c_void_p
	graph_handle = fn(byref(desc))
	if 0 == graph_handle:
		raise Exception("PSTACreateGraph failed.")

	return graph_handle

def FreeGraph(graph_handle):
	_DLL.PSTAFreeGraph(c_void_p(graph_handle))

def GetGraphInfo(graph_handle):
	info = SPSTAGraphInfo()
	fn = _DLL.PSTAGetGraphInfo
	fn.restype = ctypes.c_bool
	if not fn(c_void_p(graph_handle), byref(info)):
		raise Exception("PSTAGetGraphInfo failed.")
	return info

def GetGraphLineLengths(graph_handle, out_lengths):
	if out_lengths is None:
		return _DLL.PSTAGetGraphLineLengths(c_void_p(graph_handle), c_void_p(), c_uint(0))
	(ptr, n) = UnpackArray(out_lengths, 'f')
	count = _DLL.PSTAGetGraphLineLengths(c_void_p(graph_handle), ptr, c_uint(n))
	if count != n:
		raise Exception("PSTAGetGraphLineLengths failed.")

def GetGraphCrossingCoords(graph_handle, out_coords):
	if out_coords is None:
		return _DLL.PSTAGetGraphCrossingCoords(c_void_p(graph_handle), c_void_p(), c_uint(0))
	(ptr, n) = UnpackArray(out_coords, 'd')
	assert((n % 2) == 0)
	n = int(n / 2)
	count = _DLL.PSTAGetGraphCrossingCoords(c_void_p(graph_handle), ptr, c_uint(n))
	if count != n:
		raise Exception("PSTAGetGraphCrossingCoords failed.")

###############################################################################
# Segment Graph

class SPSTACreateSegmentGraphDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Lines
		("m_LineCoords", POINTER(c_double)),
		("m_Lines", POINTER(c_uint)),
		("m_LineCoordCount", c_uint),
		("m_LineCount", c_uint),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p)
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1

def CreateSegmentGraph(line_coords, line_indices, progress_callback):
	desc = SPSTACreateSegmentGraphDesc()
	# Lines
	(desc.m_LineCoords, n) = UnpackArray(line_coords, 'd')
	desc.m_LineCoordCount  = int(n / 2); assert((n % 2) == 0)
	(desc.m_Lines, n) = UnpackArray(line_indices, 'I')
	if line_indices is None:
		desc.m_LineCount  = int(desc.m_LineCoordCount / 2); assert((desc.m_LineCoordCount % 2) == 0)
	else:
		desc.m_LineCount  = int(n / 2); assert((n % 2) == 0)
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 

	# Make the call
	fn = _DLL.PSTACreateSegmentGraph
	fn.restype = c_void_p
	graph_handle = fn(byref(desc))
	if 0 == graph_handle:
		raise Exception("PSTACreateSegmentGraph failed.")

	return graph_handle

def FreeSegmentGraph(segment_graph_handle):
	_DLL.PSTAFreeSegmentGraph(c_void_p(segment_graph_handle))

###############################################################################
# Segment Group Graph

class SPSTACreateSegmentGroupGraphDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		# Segment Graph
		("m_SegmentGraph", c_void_p),
		# Grouping
		("m_GroupIndexPerSegment", POINTER(c_uint)),
		("m_SegmentCount", c_uint),  # For verification only
		("m_GroupCount", c_uint),
		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p)
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 1

def CreateSegmentGroupGraph(segment_graph, group_index_per_segment, group_count, progress_callback=None):
	desc = SPSTACreateSegmentGroupGraphDesc()
	# Segment Graph
	desc.m_SegmentGraph = segment_graph
	# Grouping
	(desc.m_GroupIndexPerSegment, desc.m_SegmentCount) = UnpackArray(group_index_per_segment, 'I')
	desc.m_GroupCount = group_count
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Make the call
	fn = _DLL.PSTACreateSegmentGroupGraph
	fn.restype = c_void_p
	graph_handle = fn(byref(desc))
	if 0 == graph_handle:
		raise Exception("PSTACreateSegmentGroupGraph failed.")
	return graph_handle

def FreeSegmentGroupGraph(handle):
	_DLL.PSTAFreeSegmentGroupGraph(c_void_p(handle))

