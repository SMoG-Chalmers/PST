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

from qgis.core import QgsProject, QgsRasterShader, QgsColorRampShader, QgsSingleBandPseudoColorRenderer, QgsGeometry, QgsPointXY
from qgis.PyQt.QtGui import QColor

from builtins import object, range
import ctypes, math
from .base import BaseAnalysis
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, CreateRasterFromPstaHandle
from ..utils import tupleFromHtmlColor
from ..model import GeometryType

COLORS = ['#5149f6cc', '#69b7f7cc', '#d0f1e2cc', '#f8feeacc', '#f9f8d6cc', '#f2e262cc', '#f1b152cc', '#e04d4dcc']
RANGES = [0.01, 0.10, 0.25, 0.5, 1.0]
RANGE_TEXTS = ["%.2f - %.2f (-)" % (RANGES[-i-2], RANGES[-i-1]) for i in range(len(RANGES) - 1)]
RANGE_TEXTS += ["%.2f - %.2f (+)" % (RANGES[i], RANGES[i+1]) for i in range(len(RANGES) - 1)]


def SetGradientRasterShader(layer, valueRange):
	posRange = max(0, valueRange[1])
	negRange = min(0, valueRange[0])
	shader = QgsRasterShader()
	fnc = QgsColorRampShader()
	fnc.setColorRampType(QgsColorRampShader.Interpolated)
	ramp_items = []
	if negRange < 0:
		for i in range(len(RANGES) - 1):
			ramp_items.append(QgsColorRampShader.ColorRampItem(RANGES[-i-1] * negRange, QColor(*tupleFromHtmlColor(COLORS[i]))))
	if negRange < 0 and posRange > 0:
		ramp_items.append(QgsColorRampShader.ColorRampItem(RANGES[0] * negRange, QColor(255, 255, 255, 0)))
		ramp_items.append(QgsColorRampShader.ColorRampItem(RANGES[0] * posRange, QColor(255, 255, 255, 0)))
	else:
		ramp_items.append(QgsColorRampShader.ColorRampItem(0, QColor(255, 255, 255, 0)))
	if posRange > 0:
		for i in range(len(RANGES) - 1):
			ramp_items.append(QgsColorRampShader.ColorRampItem(RANGES[i+1] * posRange, QColor(*tupleFromHtmlColor(COLORS[i + len(RANGES) - 1]))))
	fnc.setColorRampItemList(ramp_items)
	shader.setRasterShaderFunction(fnc)
	renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
	renderer.setClassificationMin(-1)
	renderer.setClassificationMax(1)
	layer.setRenderer(renderer)

# NOTE: Unused
# def SetRangesRasterShader(layer):
# 	shader = QgsRasterShader()
# 	fnc = QgsColorRampShader()
# 	fnc.setColorRampType(QgsColorRampShader.Exact)
# 	ramp_items = [QgsColorRampShader.ColorRampItem(i + 1, QColor(*tupleFromHtmlColor(COLORS[i])), RANGE_TEXTS[i]) for i in range(len(COLORS))]
# 	fnc.setColorRampItemList(ramp_items)
# 	shader.setRasterShaderFunction(fnc)
# 	renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
# 	renderer.setClassificationMin(1)
# 	renderer.setClassificationMax(len(COLORS))
# 	layer.setRenderer(renderer)

class Tasks(object):
	READ1 = 1
	READ2 = 2
	READ3 = 3
	READ4 = 4
	COMPARE = 5
	POLYGONS = 6
	WRITE = 7

class CompareResultsAnalysis(BaseAnalysis):

	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):
		import pstalgo  # Do it here when it is needed instead of on plugin load
		Vector = pstalgo.Vector
		props = self._props
		model = self._model

		separateTables = props['in_table1'] != props['in_table2']
		compareMode = pstalgo.CompareResultsMode.NORMALIZED  # pstalgo.CompareResultsMode.NORMALIZED if props['calc_normalized'] else pstalgo.CompareResultsMode.RELATIVE_PERCENT

		# Tasks
		progress = MultiTaskProgressDelegate(delegate)
		progress.addTask(Tasks.READ1, 5, "Reading lines from '%s'" % props['in_table1'])
		progress.addTask(Tasks.READ2, 5, "Reading values from %s.%s" % (props['in_table1'], props['in_column1']))
		progress.addTask(Tasks.READ3, 5 if separateTables else 0, "Reading lines from '%s'" % props['in_table2'])
		progress.addTask(Tasks.READ4, 5, "Reading values from '%s.%s'" % (props['in_table2'], props['in_column2']))
		progress.addTask(Tasks.COMPARE, 1, "Comparing results")
		progress.addTask(Tasks.POLYGONS, 1, "Generating polygons")
		progress.addTask(Tasks.WRITE, 5, "Writing polygons")

		initial_alloc_state = stack_allocator.state()
		result1 = None
		result2 = None

		try:

			line_arrays = []
			value_arrays = []

			# --- Read input
			task_index = Tasks.READ1
			for i in range(1,3):
				table_name = props['in_table%d' % i]
				column_name = props['in_column%d' % i]

				progress.setCurrentTask(task_index)
				task_index += 1
				if separateTables or len(line_arrays) == 0:
					max_line_count = model.rowCount(table_name)
					lines = Vector(ctypes.c_double, max_line_count*4, stack_allocator)
					rowids = Vector(ctypes.c_longlong, max_line_count, stack_allocator)
					model.readLines(table_name, lines, rowids, progress)
					line_arrays.append(lines)
					#QgsMessageLog.logMessage('%s: %d' % (table_name, lines.size()), 'PST', Qgis.Info)
				else:
					line_arrays.append(None)

				progress.setCurrentTask(task_index)
				task_index += 1
				values = Vector(ctypes.c_float, max_line_count, stack_allocator)
				self._model.readValues(table_name, column_name, rowids, values)
				value_arrays.append(values)

			radius = max(1, int(props['radius']))
			pixelSize = max(1, round(math.sqrt(radius)))

			createRangesPolygons = props['ranges_polygons'] 
			createGradientRaster = props['gradient_raster']

			# --- ANALYSIS ---
			progress.setCurrentTask(Tasks.COMPARE)
			(gradientRaster, rasterMin, rasterMax, result1) = pstalgo.CompareResults(
				lineCoords1 = line_arrays[0], 
				values1 = value_arrays[0], 
				lineCoords2 = line_arrays[1], 
				values2 = value_arrays[1],
				mode = compareMode,
				# M = props['M'],
				resolution = pixelSize, 
				blurRadius = radius, 
				progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(progress))

			if createRangesPolygons:

				ranges = [(-RANGES[-i-1], -RANGES[-i-2]) for i in range(len(RANGES) - 1)]
				ranges += [(RANGES[i], RANGES[i+1]) for i in range(len(RANGES) - 1)]

				progress.setCurrentTask(Tasks.POLYGONS)
				(polygonCountPerRange, polygonData, polygonCoords, result2) = pstalgo.RasterToPolygons(
					raster = gradientRaster,
					ranges = ranges,
					progress_callback = pstalgo.CreateAnalysisDelegateCallbackWrapper(progress))

				def id_gen(count):
					i = 1
					while i <= count:
						yield i
						i = i + 1

				def category_gen(polygonCountPerRange):
					for categoryIndex, polygonCountInCategory in enumerate(polygonCountPerRange):
						for _ in range(polygonCountInCategory):
							yield categoryIndex

				def range_limit_gen(polygonCountPerRange, limit_index):
					for rangeIndex, polygonCountForRange in enumerate(polygonCountPerRange):
						limit = ranges[rangeIndex][limit_index]
						for _ in range(polygonCountForRange):
							yield limit

				totalPolygonCount = sum(polygonCountPerRange)

				columns = [('id', 'integer', id_gen(totalPolygonCount)), ('range_min', 'float', range_limit_gen(polygonCountPerRange, 0)), ('range_max', 'float', range_limit_gen(polygonCountPerRange, 1)), ('category', 'integer', category_gen(polygonCountPerRange))]

				def polygon_gen(polygonCount, polygonData, polygonCoords):
					dataPos = 0
					coordPos = 0
					for polygonIndex in range(polygonCount):
						ringCount = polygonData[dataPos]
						dataPos += 1
						rings = []
						for ringIndex in range(ringCount):
							ringSize = polygonData[dataPos]
							dataPos += 1
							rings.append([QgsPointXY(polygonCoords[coordPos + i*2], polygonCoords[coordPos + i*2 + 1]) for i in range(ringSize)])
							coordPos += ringSize * 2
						yield QgsGeometry.fromPolygonXY(rings) 						

				# --- WRITE_---
				progress.setCurrentTask(Tasks.WRITE)
				tableId = self._model.createTable(
					'Polygons',
					model.coordinateReferenceSystem(props['in_table1']),
					columns,
					polygon_gen(totalPolygonCount, polygonData, polygonCoords),
					totalPolygonCount,
					progress,
					geo_type=GeometryType.POLYGON)

				# Create thematic
				ranges = [(RANGE_TEXTS[i], tupleFromHtmlColor(COLORS[i]), i) for i in range(len(RANGE_TEXTS))]
				model.makeThematic(tableId, 'category', ranges)

			if createGradientRaster:
				rasterLayer = CreateRasterFromPstaHandle(gradientRaster)
				SetGradientRasterShader(rasterLayer, (rasterMin, rasterMax) if compareMode == pstalgo.CompareResultsMode.RELATIVE_PERCENT else (-1, 1))
				rasterLayer.setName('Gradient Raster')
				QgsProject.instance().addMapLayer(rasterLayer)

		finally:
			stack_allocator.restore(initial_alloc_state)
			if result1 is not None:
				pstalgo.Free(result1)
			if result2 is not None:
				pstalgo.Free(result2)			