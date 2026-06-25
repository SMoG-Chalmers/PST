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
import array, ctypes, math
from .base import BaseAnalysis, AnalysisException
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate, CreateRasterFromPstaHandle
from ..utils import tupleFromHtmlColor
from ..model import GeometryType

COLORS = ['#5149f6cc', '#69b7f7cc', '#d0f1e2cc', '#f8feeacc', '#f9f8d6cc', '#f2e262cc', '#f1b152cc', '#e04d4dcc']
RANGES = [0.01, 0.10, 0.25, 0.5, 1.0]
RANGE_TEXTS = ["%.2f - %.2f (-)" % (RANGES[-i-2], RANGES[-i-1]) for i in range(len(RANGES) - 1)]
RANGE_TEXTS += ["%.2f - %.2f (+)" % (RANGES[i], RANGES[i+1]) for i in range(len(RANGES) - 1)]

# Tolerance for matching "identical" line geometry between two networks.
# Coordinate drift between QGIS exports is typically < 5 cm; 10 cm is generous.
IDENTICAL_LINE_TOLERANCE_M = 0.1


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
			rowids_per_table = []  # for ID-based filtering

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
					rowids_per_table.append(rowids)
					#QgsMessageLog.logMessage('%s: %d' % (table_name, lines.size()), 'PST', Qgis.Info)
				else:
					line_arrays.append(None)
					rowids_per_table.append(rowids_per_table[0])

				progress.setCurrentTask(task_index)
				task_index += 1
				values = Vector(ctypes.c_float, max_line_count, stack_allocator)
				self._model.readValues(table_name, column_name, rowids, values)
				value_arrays.append(values)

			# --- Object comparison (vector) path (Frame 2) ---
			if props.get('comparison_method', 'area') == 'object':
				progress.setCurrentTask(Tasks.WRITE)
				self._runObjectComparison(props, line_arrays, value_arrays, rowids_per_table, progress)
				return

			# --- Apply 'identical lines' filter (Frame 3) ---
			filter_mode = props.get('filter_mode', 'all')
			if filter_mode != 'all' and separateTables:
				line_arrays, value_arrays = self._applyIdenticalFilter(
					filter_mode, props, line_arrays, value_arrays, rowids_per_table)

			pixelSize = max(1, int(props['pixel_size']))
			blurRadius = max(1, int(props['blur_extent'])) if props['custom_blur_extent'] else pixelSize * 7

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
				blurRadius = blurRadius, 
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

	def _runObjectComparison(self, props, line_arrays, value_arrays, rowids_per_table, progress):
		""" Object (vector) comparison for line geometry. Matches objects between the two
		    tables, computes per-object diff (B - A), and writes a vector layer of the
		    original geometry with a 'diff' attribute.

		    filter_mode:
		      'geom' / 'id' : only objects present in both tables (intersection)
		      'all'         : union of all objects, with the missing side treated as 0
		                      (correspondence by geometry) """
		filter_mode = props.get('filter_mode', 'all')

		lines0 = line_arrays[0]
		lines1 = line_arrays[1] if line_arrays[1] is not None else line_arrays[0]
		vals0 = value_arrays[0]
		vals1 = value_arrays[1]
		n0 = len(lines0) // 4
		n1 = len(lines1) // 4

		# Build a matching key per object
		if filter_mode == 'id':
			id_col0 = props.get('id_column1', '')
			id_col1 = props.get('id_column2', '')
			if not id_col0 or not id_col1:
				raise AnalysisException(
					"ID matching requires an ID column to be selected for both tables.")
			keys0 = list(self._model.values(props['in_table1'], id_col0, rowids_per_table[0]))
			keys1 = list(self._model.values(props['in_table2'], id_col1, rowids_per_table[1]))
		else:
			keys0 = [self._canonKey(lines0[i*4], lines0[i*4+1], lines0[i*4+2], lines0[i*4+3]) for i in range(n0)]
			keys1 = [self._canonKey(lines1[i*4], lines1[i*4+1], lines1[i*4+2], lines1[i*4+3]) for i in range(n1)]

		# Map key -> (index, value); first occurrence wins on duplicate keys
		mapA = {}
		for i, k in enumerate(keys0):
			if k not in mapA:
				mapA[k] = (i, vals0[i])
		mapB = {}
		for i, k in enumerate(keys1):
			if k not in mapB:
				mapB[k] = (i, vals1[i])

		def line_geom(lines, idx):
			return QgsGeometry.fromPolylineXY([
				QgsPointXY(lines[idx*4],   lines[idx*4+1]),
				QgsPointXY(lines[idx*4+2], lines[idx*4+3])])

		# Build the list of (geometry, diff) features
		features = []
		if filter_mode == 'all':
			for k in set(mapA.keys()) | set(mapB.keys()):
				a = mapA.get(k)
				b = mapB.get(k)
				va = a[1] if a is not None else 0.0
				vb = b[1] if b is not None else 0.0
				geom = line_geom(lines1, b[0]) if b is not None else line_geom(lines0, a[0])
				features.append((geom, vb - va))
		else:
			for k in set(mapA.keys()) & set(mapB.keys()):
				a = mapA[k]
				b = mapB[k]
				features.append((line_geom(lines1, b[0]), b[1] - a[1]))

		if not features:
			raise AnalysisException(
				"No objects to compare between '%s' and '%s'. "
				"Try a different matching mode." % (props['in_table1'], props['in_table2']))

		# Write the vector layer
		def id_gen():
			for i in range(len(features)):
				yield i + 1

		def diff_gen():
			for _, d in features:
				yield d

		def geom_gen():
			for g, _ in features:
				yield g

		columns = [('id', 'integer', id_gen()), ('diff', 'float', diff_gen())]
		self._model.createTable(
			'Object Comparison',
			self._model.coordinateReferenceSystem(props['in_table1']),
			columns,
			geom_gen(),
			len(features),
			progress,
			geo_type=GeometryType.LINE)

	def _applyIdenticalFilter(self, mode, props, line_arrays, value_arrays, rowids_per_table):
		""" Filter line and value arrays so that only lines considered 'identical' between
		    the two tables are kept. Returns (new_line_arrays, new_value_arrays). """
		if mode == 'geom':
			keep0, keep1 = self._matchByGeometry(line_arrays[0], line_arrays[1])
			mode_label = "geometry matching (tolerance %.2f m)" % IDENTICAL_LINE_TOLERANCE_M
		elif mode == 'id':
			keep0, keep1 = self._matchById(props, rowids_per_table)
			mode_label = "ID matching"
		else:
			return line_arrays, value_arrays

		if not keep0 or not keep1:
			raise AnalysisException(
				"No identical lines found between '%s' and '%s' using %s. "
				"Try a different matching mode, or use 'All lines'." % (
					props['in_table1'], props['in_table2'], mode_label))

		new_line_arrays = []
		new_value_arrays = []
		for keep_indices, line_vec, value_vec in [
			(keep0, line_arrays[0], value_arrays[0]),
			(keep1, line_arrays[1], value_arrays[1]),
		]:
			coords = array.array('d')
			vals = array.array('f')
			for idx in keep_indices:
				coords.append(line_vec[idx*4])
				coords.append(line_vec[idx*4+1])
				coords.append(line_vec[idx*4+2])
				coords.append(line_vec[idx*4+3])
				vals.append(value_vec[idx])
			new_line_arrays.append(coords)
			new_value_arrays.append(vals)
		return new_line_arrays, new_value_arrays

	@staticmethod
	def _canonKey(x0, y0, x1, y1):
		""" Canonical key for a line segment: endpoints snapped to tolerance grid,
		    sorted so the key is direction-independent. """
		tol = IDENTICAL_LINE_TOLERANCE_M
		a = (round(x0 / tol) * tol, round(y0 / tol) * tol)
		b = (round(x1 / tol) * tol, round(y1 / tol) * tol)
		return (a, b) if a <= b else (b, a)

	def _matchByGeometry(self, lines0, lines1):
		""" Return (keep_indices0, keep_indices1) — indices of lines whose endpoint
		    geometry matches in the other table (within tolerance, direction-independent). """
		n0 = len(lines0) // 4
		n1 = len(lines1) // 4
		keys0 = {}
		for i in range(n0):
			k = CompareResultsAnalysis._canonKey(
				lines0[i*4], lines0[i*4+1], lines0[i*4+2], lines0[i*4+3])
			# If duplicate keys exist within the same table, keep the first seen
			if k not in keys0:
				keys0[k] = i
		keys1 = {}
		for i in range(n1):
			k = CompareResultsAnalysis._canonKey(
				lines1[i*4], lines1[i*4+1], lines1[i*4+2], lines1[i*4+3])
			if k not in keys1:
				keys1[k] = i
		common = keys0.keys() & keys1.keys()
		keep0 = sorted(keys0[k] for k in common)
		keep1 = sorted(keys1[k] for k in common)
		return keep0, keep1

	def _matchById(self, props, rowids_per_table):
		""" Return (keep_indices0, keep_indices1) — indices of lines whose ID field
		    value appears in both tables. """
		table0 = props['in_table1']
		table1 = props['in_table2']
		id_col0 = props.get('id_column1', '')
		id_col1 = props.get('id_column2', '')
		if not id_col0 or not id_col1:
			raise AnalysisException(
				"ID matching requires an ID column to be selected for both tables.")
		ids0 = list(self._model.values(table0, id_col0, rowids_per_table[0]))
		ids1 = list(self._model.values(table1, id_col1, rowids_per_table[1]))
		common = set(ids0) & set(ids1)
		keep0 = [i for i, v in enumerate(ids0) if v in common]
		keep1 = [i for i, v in enumerate(ids1) if v in common]
		return keep0, keep1
