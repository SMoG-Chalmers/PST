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

from builtins import range
from builtins import object
import ctypes
from .base import AnalysisException


class MultiTaskProgressDelegate(object):
	def __init__(self, delegate):
		self._delegate = delegate
		self._tasks = {}
		self._totWeight = 0
		self._currTaskWeight = 0
		self._finishedWeight = 0

	def addTask(self, task_id, weight, text):
		assert(task_id not in self._tasks)
		self._tasks[task_id] = (weight,text)
		self._totWeight += weight

	def setCurrentTask(self, task_id):
		self._finishedWeight += self._currTaskWeight
		task = self._tasks[task_id]
		self._currTaskWeight = task[0]
		self.setProgress(0)
		if task[1]:
			self.setStatus(task[1])

	def setStatus(self, text):
		self._delegate.setStatus(text)

	def setProgress(self, progress):
		if self._totWeight > 0:
			# print("(%f + %f * %f) / %f" % (self._finishedWeight, progress, self._currTaskWeight, self._totWeight))
			progress = float(self._finishedWeight + progress * self._currTaskWeight) / self._totWeight
		else:
			progress = 0
		self._delegate.setProgress(progress)

	def getCancel(self):
		return self._delegate.getCancel()


class TaskSplitProgressDelegate(object):
	def __init__(self, count, text, delegate):
		self._delegate = delegate
		self._count = float(count)
		self._text = text
		self._currIndex = float(-1)
		self.nextTask()

	def nextTask(self):
		self._currIndex += 1
		assert(self._currIndex <= self._count)
		self.setProgress(0)
		if self._currIndex < self._count:
			self._delegate.setStatus(self._getText())

	def setStatus(self, text):
		self._delegate.setStatus(self._getText() + " (%s)" % text)

	def setProgress(self, progress):
		if self._count > 0:
			scaled_progress = float(self._currIndex + progress) / self._count
			#print("%d + %f / %d = %f"%(self._currIndex, progress, self._count, scaled_progress))
		else:
			scaled_progress = 1
		self._delegate.setProgress(scaled_progress)

	def getCancel(self):
		return self._delegate.getCancel()

	def _getText(self):
		if self._count < 2:
			return self._text
		return self._text + " %d/%d" % (self._currIndex+1, self._count)


def BuildAxialGraph(model, pstalgo, stack_allocator, network_table, unlink_table, point_table, progress, poly_edge_point_interval=0):

	initial_alloc_state = stack_allocator.state()

	Vector = pstalgo.Vector

	# Tasks
	class Tasks(object):
		READ_LINES = 1
		READ_POINTS = 2
		READ_UNLINKS = 3
		BUILD_GRAPH = 4
	my_progress = MultiTaskProgressDelegate(progress)
	my_progress.addTask(Tasks.READ_LINES,   1, "Reading lines")
	if point_table:
		my_progress.addTask(Tasks.READ_POINTS,  1, "Reading points")
	if unlink_table:
		my_progress.addTask(Tasks.READ_UNLINKS, 1, "Reading unlinks")
	my_progress.addTask(Tasks.BUILD_GRAPH,  1, "Building graph")

	# Max counts
	max_line_count = model.rowCount(network_table)
	max_unlink_count = model.rowCount(unlink_table) if unlink_table else 0
	max_point_count = model.rowCount(point_table) if point_table else 0

	final_alloc_state = initial_alloc_state
	try:
		line_rows = Vector(ctypes.c_longlong, max_line_count, stack_allocator)
		point_rows = Vector(ctypes.c_longlong, max_point_count, stack_allocator) if point_table else None

		final_alloc_state = stack_allocator.state()

		# Read lines
		my_progress.setCurrentTask(Tasks.READ_LINES)
		lines = Vector(ctypes.c_double, max_line_count*4, stack_allocator)
		model.readLines(network_table, lines, line_rows, my_progress)
		if 0 == lines.size():
			raise AnalysisException("No lines found in table '%s'!" % network_table)

		# Read points
		points = None
		points_per_polygon = None
		if poly_edge_point_interval <= 0:
			if max_point_count:
				my_progress.setCurrentTask(Tasks.READ_POINTS)
				points = Vector(ctypes.c_double, max_point_count*2, stack_allocator)
				model.readPoints(point_table, points, point_rows, my_progress)
				if 0 == points.size():
					raise AnalysisException("No points found in table '%s'!" % point_table)
		elif max_point_count:
			my_progress.setCurrentTask(Tasks.READ_POINTS)
			points_per_polygon = Vector(ctypes.c_uint, max_point_count, stack_allocator)
			points = model.readPolygons(point_table, points_per_polygon, point_rows, my_progress)
			if 0 == points_per_polygon.size():
				raise AnalysisException("No polygons found in table '%s'!" % point_table)

		# Read unlinks
		unlinks = None
		if max_unlink_count:
			my_progress.setCurrentTask(Tasks.READ_UNLINKS)
			unlinks = Vector(ctypes.c_double, max_unlink_count*2, stack_allocator)
			model.readPoints(unlink_table, unlinks, None, my_progress)
			if 0 == unlinks.size():
				raise AnalysisException("No unlink points found in table '%s'!" % unlink_table)

		# Build graph
		my_progress.setCurrentTask(Tasks.BUILD_GRAPH)
		graph = pstalgo.CreateGraph(
			line_coords = lines,
			line_indices = None,
			unlinks = unlinks,
			points = points,
			points_per_polygon = points_per_polygon,
			polygon_point_interval = poly_edge_point_interval,
			progress_callback = my_progress)
	except:
		stack_allocator.restore(initial_alloc_state)
		raise

	stack_allocator.restore(final_alloc_state)

	return (graph, line_rows, point_rows)

def BuildSegmentGraph(model, pstalgo, stack_allocator, network_table, progress):
	initial_alloc_state = stack_allocator.state()
	final_alloc_state = initial_alloc_state
	try:
		Vector = pstalgo.Vector
		# Tasks
		class Tasks(object):
			READ_LINES = 1
			BUILD_GRAPH = 4
		my_progress = MultiTaskProgressDelegate(progress)
		my_progress.addTask(Tasks.READ_LINES,   1, "Reading lines")
		my_progress.addTask(Tasks.BUILD_GRAPH,  1, "Building graph")
		# Line rowid vector
		max_line_count = model.rowCount(network_table)
		line_rows = Vector(ctypes.c_longlong, max_line_count, stack_allocator)
		# Marker for final allocation state
		final_alloc_state = stack_allocator.state()
		# Read lines into temporary vector
		my_progress.setCurrentTask(Tasks.READ_LINES)
		lines = Vector(ctypes.c_double, max_line_count*4, stack_allocator)
		model.readLines(network_table, lines, line_rows, my_progress)
		if 0 == lines.size():
			raise AnalysisException("No lines found in table '%s'!" % network_table)
		# Build graph
		my_progress.setCurrentTask(Tasks.BUILD_GRAPH)
		graph = pstalgo.CreateSegmentGraph(lines, None, my_progress)
	except:
		stack_allocator.restore(initial_alloc_state)
		raise
	stack_allocator.restore(final_alloc_state)
	return (graph, line_rows)

def RadiiFromSettings(pstalgo, settings):
	return pstalgo.Radii(
		straight = settings['rad_straight'] if settings.get('rad_straight_enabled') else None,
		walking =  settings['rad_walking']  if settings.get('rad_walking_enabled')  else None,
		steps =    settings['rad_steps']    if settings.get('rad_steps_enabled')    else None,
		angular =  settings['rad_angular']  if settings.get('rad_angular_enabled')  else None,
		axmeter =  settings['rad_axmeter']  if settings.get('rad_axmeter_enabled')  else None)

def DistanceTypesFromSettings(pstalgo, props):
	distance_types = []
	if props.get('dist_straight'):  # Not always available
		distance_types.append(pstalgo.DistanceType.STRAIGHT)
	if props.get('dist_walking'):
		distance_types.append(pstalgo.DistanceType.WALKING)
	if props.get('dist_steps'):
		distance_types.append(pstalgo.DistanceType.STEPS)
	if props.get('dist_angular'):
		distance_types.append(pstalgo.DistanceType.ANGULAR)
	if props.get('dist_axmeter'):
		distance_types.append(pstalgo.DistanceType.AXMETER)
	return distance_types

def MeanDepthGen(TD_vector, N_vector):
	for i in range(TD_vector.size()):
		N = N_vector.at(i)-1  # IMPORTANT: -1 here since origin line is included in the count
		yield TD_vector.at(i)/N if N > 0 else 0.0

def PointGen(coord_vector, model):
	for i in range(int(coord_vector.size()/2)):
		yield model.createPoint(coord_vector.at(i*2), coord_vector.at(i*2+1))