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

from builtins import range
from builtins import object
import array, ctypes
from ..model import GeometryType
from .base import BaseAnalysis
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate


class Tasks(object):
	READ_ORIGINS = 1
	READ_OBSTACLES = 2
	ANALYSIS = 3
	CREATE_ISOVISTS_LAYER = 4


class IsovistAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):
		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props
		model = self._model

		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.READ_ORIGINS, 1, None)
		progress.addTask(Tasks.READ_OBSTACLES, 1, None)
		progress.addTask(Tasks.ANALYSIS, 1, None)
		progress.addTask(Tasks.CREATE_ISOVISTS_LAYER, 1, None)

		algo = None

		initial_alloc_state = stack_allocator.state()

		try:
			progress.setCurrentTask(Tasks.READ_ORIGINS)
			progress.setStatus("Reading points from '%s'" % props['in_origins'])
			origin_coords = pstalgo.Vector(ctypes.c_double, model.rowCount(props['in_origins'])*2, stack_allocator)
			model.readPoints(props['in_origins'], origin_coords, None, progress)

			progress.setCurrentTask(Tasks.READ_OBSTACLES)
			progress.setStatus("Reading polygons from '%s'" % props['in_obstacles'])
			point_count_per_polygon = pstalgo.Vector(ctypes.c_uint, model.rowCount(props['in_obstacles']), stack_allocator)
			polygon_coords = model.readPolygons(props['in_obstacles'], point_count_per_polygon, None, progress)

			progress.setCurrentTask(Tasks.ANALYSIS)
			progress.setStatus("Calculating isovists")
			(res, algo) = pstalgo.CalculateIsovists(point_count_per_polygon, polygon_coords, origin_coords, props['max_viewing_distance'], int(props['perimeter_resolution']), progress)

			def polygon_gen(polygon_count, point_count_per_polygon, polygon_coords):
				coord_index = 0
				for polygon_index in range(polygon_count):
					point_count = point_count_per_polygon[polygon_index]
					yield model.createPolygonFromCoordinateElements(polygon_coords, point_count, coord_index)
					coord_index += point_count * 2

			progress.setCurrentTask(Tasks.CREATE_ISOVISTS_LAYER)
			output_table_name = 'Isovists'
			progress.setStatus("Writing table '%s'" % output_table_name)
			model.createTable(
				output_table_name,
				model.coordinateReferenceSystem(props['in_origins']),
				[],
				polygon_gen(res.m_IsovistCount, res.m_PointCountPerIsovist, res.m_IsovistPoints),
				res.m_IsovistCount,
				progress,
				geo_type=GeometryType.POLYGON)

		finally:
			stack_allocator.restore(initial_alloc_state)
			if algo is not None:
				pstalgo.Free(algo)