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
from ctypes import byref, cdll, POINTER, Structure, c_double, c_float, c_int, c_uint, c_void_p, c_bool
from .common import _DLL, PSTALGO_PROGRESS_CALLBACK, CreateCallbackWrapper, UnpackArray, DumpStructure, Radii


class SPSTAAngularIntegrationDesc(Structure) :
	_fields_ = [
		# Version
		("m_Version", c_uint),
		
		# Graph
		("m_Graph", c_void_p),

		# Radius
		("m_Radius", Radii),

		# Settings (optional)
		("m_WeighByLength", c_bool),
		("m_AngleThreshold", c_float),
		("m_AnglePrecision", c_uint),

		# Progress Callback
		("m_ProgressCallback", PSTALGO_PROGRESS_CALLBACK),
		("m_ProgressCallbackUser", c_void_p),

		# Outputs (optional)
		("m_OutNodeCounts", POINTER(c_uint)),
		("m_OutTotalDepths", POINTER(c_float)),
		("m_OutTotalWeights", POINTER(c_float)),
		("m_OutTotalDepthWeights", POINTER(c_float)),
	]
	def __init__(self, *args):
		Structure.__init__(self, *args)
		self.m_Version = 2


def AngularIntegration(graph_handle, radius, weigh_by_length = False, angle_threshold = 0, angle_precision = 1, progress_callback = None, out_node_counts = None, out_total_depths = None, out_total_weights = None, out_total_depth_weights = None):
	desc = SPSTAAngularIntegrationDesc()
	# Graph
	desc.m_Graph = graph_handle
	# Radius
	desc.m_Radius = radius
	# Settings
	desc.m_WeighByLength = weigh_by_length
	desc.m_AngleThreshold = angle_threshold
	desc.m_AnglePrecision = int(angle_precision)
	# Progress Callback
	desc.m_ProgressCallback = CreateCallbackWrapper(progress_callback)
	desc.m_ProgressCallbackUser = c_void_p() 
	# Outputs
	# TODO: Verify length of these
	desc.m_OutNodeCounts = UnpackArray(out_node_counts, 'I')[0]
	desc.m_OutTotalDepths = UnpackArray(out_total_depths, 'f')[0]
	desc.m_OutTotalWeights = UnpackArray(out_total_weights, 'f')[0]  
	desc.m_OutTotalDepthWeights = UnpackArray(out_total_depth_weights, 'f')[0]  
	# Make the call
	fn = _DLL.PSTAAngularIntegration
	fn.restype = ctypes.c_bool
	if not fn(byref(desc)):
		raise Exception("PSTAAngularIntegration failed.")
	return True

def AngularIntegrationNormalize(node_counts, total_depth, count, out_scores):
	_DLL.PSTAAngularIntegrationNormalize(
		UnpackArray(node_counts, 'I')[0],
		UnpackArray(total_depth, 'f')[0],
		c_uint(count),
		UnpackArray(out_scores, 'f')[0])

def AngularIntegrationNormalizeLengthWeight(total_length, total_depth, count, out_scores):
	_DLL.PSTAAngularIntegrationNormalizeLengthWeight(
		UnpackArray(total_length, 'f')[0],
		UnpackArray(total_depth, 'f')[0],
		c_uint(count),
		UnpackArray(out_scores, 'f')[0])

def AngularIntegrationSyntaxNormalize(node_counts, total_depth, count, out_scores):
	_DLL.PSTAAngularIntegrationSyntaxNormalize(
		UnpackArray(node_counts, 'I')[0],
		UnpackArray(total_depth, 'f')[0],
		c_uint(count),
		UnpackArray(out_scores, 'f')[0])

def AngularIntegrationSyntaxNormalizeLengthWeight(total_length, total_depth, count, out_scores):
	_DLL.PSTAAngularIntegrationSyntaxNormalizeLengthWeight(
		UnpackArray(total_length, 'f')[0],
		UnpackArray(total_depth, 'f')[0],
		c_uint(count),
		UnpackArray(out_scores, 'f')[0])

def AngularIntegrationHillierNormalize(node_counts, total_depth, count, out_scores):
	_DLL.PSTAAngularIntegrationHillierNormalize(
		UnpackArray(node_counts, 'I')[0],
		UnpackArray(total_depth, 'f')[0],
		c_uint(count),
		UnpackArray(out_scores, 'f')[0])

def AngularIntegrationHillierNormalizeLengthWeight(total_length, total_depth, count, out_scores):
	_DLL.PSTAAngularIntegrationHillierNormalizeLengthWeight(
		UnpackArray(total_length, 'f')[0],
		UnpackArray(total_depth, 'f')[0],
		c_uint(count),
		UnpackArray(out_scores, 'f')[0])