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

# Log-spaced fractions for the optional logarithmic colour scale (object output, 'all'
# mode). Spans four decades so small changes get their own colour bands instead of being
# swamped by outliers such as new streets going 0 -> large value.
LOG_RANGES = [0.0001, 0.001, 0.01, 0.1, 1.0]
LOG_RANGE_TEXTS = ["%.4f - %.4f (-)" % (LOG_RANGES[-i-2], LOG_RANGES[-i-1]) for i in range(len(LOG_RANGES) - 1)]
LOG_RANGE_TEXTS += ["%.4f - %.4f (+)" % (LOG_RANGES[i], LOG_RANGES[i+1]) for i in range(len(LOG_RANGES) - 1)]

# Default/fallback tolerance for matching "identical" geometry (line endpoints, or
# centroid for points/polygons) when the wizard value is missing. The user sets the
# actual value in the wizard ('match_tolerance'). Coordinate drift varies by source:
# a few cm within one export, up to ~1-2 m between differently digitised networks.
# On the Gothenburg 1960/1990 nets, matches plateau by ~2 m and false merges/degenerate
# short segments appear from ~5-10 m, so 2 m is a safe default.
IDENTICAL_LINE_TOLERANCE_M = 2.0


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

			# --- Object comparison (vector) path (Frame 2) ---
			# Reads geometry generically (point/line/polygon); independent of the raster path.
			if props.get('comparison_method', 'area') == 'object':
				self._runObjectComparison(props, progress)
				return

			# --- Area comparison (raster) path ---
			geomType = self._model.geometryType(props['in_table1'])
			if geomType is None:
				raise AnalysisException("Could not determine the geometry type of '%s'." % props['in_table1'])
			if separateTables:
				geomType2 = self._model.geometryType(props['in_table2'])
				if geomType2 != geomType:
					raise AnalysisException(
						"Both tables must have the same geometry type "
						"('%s' is %s, '%s' is %s)." % (props['in_table1'], geomType, props['in_table2'], geomType2))

			filter_mode = props.get('filter_mode', 'all')

			if geomType == GeometryType.LINE:
				pstalgoGeometryType = pstalgo.CompareResultsGeometryType.LINES
				polygon_data_arrays = [None, None]

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

				# --- Apply 'identical lines' filter (Frame 3) ---
				if filter_mode != 'all' and separateTables:
					line_arrays, value_arrays = self._applyIdenticalFilter(
						filter_mode, props, line_arrays, value_arrays, rowids_per_table)
			else:
				# Point/polygon raster: read geometry generically and pack into the flat
				# arrays pstalgo expects (points: bilinear splat; polygons: area-weighted fill)
				pstalgoGeometryType = (pstalgo.CompareResultsGeometryType.POINTS
					if geomType == GeometryType.POINT
					else pstalgo.CompareResultsGeometryType.POLYGONS)
				progress.setCurrentTask(Tasks.READ1)
				line_arrays, value_arrays, polygon_data_arrays = self._readObjectArrays(
					geomType, props, filter_mode, separateTables)

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
				geometryType = pstalgoGeometryType,
				polygonData1 = polygon_data_arrays[0],
				polygonData2 = polygon_data_arrays[1],
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

	def _runObjectComparison(self, props, progress):
		""" Object (vector) comparison for point, line or polygon geometry. Matches objects
		    between the two tables, computes per-object diff (B - A), and writes a vector
		    layer of the original geometry with a 'diff' attribute.

		    Matching key:
		      'id'   : value of the chosen ID column
		      else   : geometry — line endpoints (direction-independent), or the snapped
		               centroid for points and polygons
		    filter_mode:
		      'geom' / 'id' : only objects present in both tables (intersection)
		      'all'         : union of all objects, missing side treated as 0 """
		filter_mode = props.get('filter_mode', 'all')
		table1, table2 = props['in_table1'], props['in_table2']
		col1, col2 = props['in_column1'], props['in_column2']

		if filter_mode == 'id':
			id1 = props.get('id_column1', '')
			id2 = props.get('id_column2', '')
			if not id1 or not id2:
				raise AnalysisException(
					"ID matching requires an ID column to be selected for both tables.")
		else:
			id1 = id2 = None

		geomType = self._model.geometryType(table1)
		if geomType is None:
			raise AnalysisException("Could not determine the geometry type of '%s'." % table1)

		tol = self._tolerance(props)

		def geom_key(geom):
			if geomType == GeometryType.LINE:
				pts = geom.asMultiPolyline()[0] if geom.isMultipart() else geom.asPolyline()
				p0, p1 = pts[0], pts[-1]
				return self._canonKey(p0.x(), p0.y(), p1.x(), p1.y(), tol)
			# point or polygon -> representative point (centroid), snapped to tolerance grid
			c = geom.centroid().asPoint()
			return (round(c.x() / tol) * tol, round(c.y() / tol) * tol)

		def read_map(table, value_col, id_col):
			m = {}
			for geom, val, idval in self._model.readObjects(table, value_col, id_col):
				k = idval if filter_mode == 'id' else geom_key(geom)
				if k not in m:
					m[k] = (geom, val)
			return m

		mapA = read_map(table1, col1, id1)
		mapB = read_map(table2, col2, id2)

		# Build the list of (geometry, diff) features
		features = []
		if filter_mode == 'all':
			for k in set(mapA.keys()) | set(mapB.keys()):
				a = mapA.get(k)
				b = mapB.get(k)
				va = a[1] if a is not None else 0.0
				vb = b[1] if b is not None else 0.0
				geom = b[0] if b is not None else a[0]
				features.append((geom, (vb or 0.0) - (va or 0.0)))
		else:
			for k in set(mapA.keys()) & set(mapB.keys()):
				a = mapA[k]
				b = mapB[k]
				features.append((b[0], (b[1] or 0.0) - (a[1] or 0.0)))

		if not features:
			raise AnalysisException(
				"No objects to compare between '%s' and '%s'. "
				"Try a different matching mode." % (table1, table2))

		# Write the vector layer (same geometry type as the input)
		def id_gen():
			for i in range(len(features)):
				yield i + 1

		def diff_gen():
			for _, d in features:
				yield d

		def geom_gen():
			for g, _ in features:
				yield g

		progress.setCurrentTask(Tasks.WRITE)
		columns = [('id', 'integer', id_gen()), ('diff', 'float', diff_gen())]
		tableId = self._model.createTable(
			'Object Comparison',
			self._model.coordinateReferenceSystem(table1),
			columns,
			geom_gen(),
			len(features),
			progress,
			geo_type=geomType)

		# Styling: graduated red/blue with mirrored class breaks around zero.
		# Boundaries are the RANGES fractions scaled by the largest absolute diff, so
		# +X and -X get equally strong colour. The innermost +/- 0.01 band is left
		# unclassified (no change), matching the raster/polygon output.
		maxAbs = max((abs(d) for _, d in features), default=0.0)
		if maxAbs > 0:
			# Logarithmic colour scale is offered only for the 'all' comparison, where a
			# few outliers (new/removed objects) otherwise flatten the linear scale.
			use_log = props.get('log_scale', False) and filter_mode == 'all'
			frac = LOG_RANGES if use_log else RANGES
			labels = LOG_RANGE_TEXTS if use_log else RANGE_TEXTS
			norm_ranges = [(-frac[-i-1], -frac[-i-2]) for i in range(len(frac) - 1)]
			norm_ranges += [(frac[i], frac[i+1]) for i in range(len(frac) - 1)]
			obj_ranges = []
			last = len(norm_ranges) - 1
			for i, (lo, hi) in enumerate(norm_ranges):
				lower = -1e30 if i == 0 else lo * maxAbs
				upper = 1e30 if i == last else hi * maxAbs
				obj_ranges.append((lower, upper, tupleFromHtmlColor(COLORS[i]), labels[i]))
			self._model.makeGraduated(tableId, 'diff', obj_ranges)

	def _readObjectArrays(self, geomType, props, filter_mode, separateTables):
		""" Reads point or polygon objects and packs them into the flat arrays pstalgo
		    expects. Returns (coord_arrays, value_arrays, polygon_data_arrays), each a
		    2-element list. Index 1 of coord/polygon-data is None when both value
		    columns come from the same table. """
		table1, table2 = props['in_table1'], props['in_table2']
		col1, col2 = props['in_column1'], props['in_column2']

		if filter_mode == 'id' and separateTables:
			id1 = props.get('id_column1', '')
			id2 = props.get('id_column2', '')
			if not id1 or not id2:
				raise AnalysisException(
					"ID matching requires an ID column to be selected for both tables.")
		else:
			id1 = id2 = None

		objs1 = list(self._model.readObjects(table1, col1, id1))
		objs2 = list(self._model.readObjects(table2, col2, id2))

		if filter_mode != 'all' and separateTables:
			objs1, objs2 = self._intersectObjects(objs1, objs2, filter_mode, props)

		if geomType == GeometryType.POINT:
			(coords1, values1) = self._packPoints(objs1)
			(coords2, values2) = self._packPoints(objs2)
			polydata1 = polydata2 = None
		else:
			(coords1, values1, polydata1) = self._packPolygons(objs1)
			(coords2, values2, polydata2) = self._packPolygons(objs2)

		if not separateTables:
			# Same table: geometry is passed once, the second entry only carries values
			coords2 = None
			polydata2 = None

		return ([coords1, coords2], [values1, values2], [polydata1, polydata2])

	def _intersectObjects(self, objs1, objs2, filter_mode, props):
		""" Keep only objects present in both tables, matched by ID column value or by
		    centroid snapped to the matching tolerance grid. Same semantics as the
		    object comparison path. """
		tol = self._tolerance(props)

		def key(geom, idval):
			if filter_mode == 'id':
				return idval
			c = geom.centroid().asPoint()
			return (round(c.x() / tol) * tol, round(c.y() / tol) * tol)

		map1 = {}
		for g, v, i in objs1:
			k = key(g, i)
			if k not in map1:
				map1[k] = (g, v, i)
		map2 = {}
		for g, v, i in objs2:
			k = key(g, i)
			if k not in map2:
				map2[k] = (g, v, i)
		common = map1.keys() & map2.keys()
		if not common:
			raise AnalysisException(
				"No identical objects found between '%s' and '%s'. "
				"Try a different matching mode, or include all objects." % (
					props['in_table1'], props['in_table2']))
		return ([map1[k] for k in common], [map2[k] for k in common])

	@staticmethod
	def _toFloat(value):
		""" Attribute value to float; NULL/None/non-numeric becomes 0.0. """
		try:
			return float(value)
		except (TypeError, ValueError):
			return 0.0

	@staticmethod
	def _packPoints(objs):
		""" Packs point objects into pstalgo's flat coordinate format (x,y doubles).
		    The centroid is used, so multipoints and stray non-point geometry degrade
		    gracefully to their representative point. """
		coords = array.array('d')
		values = array.array('f')
		for geom, value, _ in objs:
			p = geom.centroid().asPoint()
			coords.append(p.x())
			coords.append(p.y())
			values.append(CompareResultsAnalysis._toFloat(value))
		return (coords, values)

	@staticmethod
	def _packPolygons(objs):
		""" Packs polygon objects into pstalgo's flat format: all ring vertices
		    consecutively in coords, ring structure per polygon as
		    [ring_count, points_in_ring_0, points_in_ring_1, ...]. Multipolygon parts
		    are flattened into one object (even-odd fill renders them correctly).
		    QGIS repeats the first vertex as ring closure; pstalgo closes rings
		    implicitly, so the duplicate is stripped. Features without any usable
		    ring are skipped entirely (geometry and value). """
		coords = array.array('d')
		values = array.array('f')
		polydata = array.array('I')
		for geom, value, _ in objs:
			rings = []
			if geom.isMultipart():
				for part in geom.asMultiPolygon():
					rings.extend(part)
			else:
				rings.extend(geom.asPolygon())
			clean = []
			for ring in rings:
				if len(ring) >= 2 and ring[0] == ring[-1]:
					ring = ring[:-1]
				if len(ring) >= 3:
					clean.append(ring)
			if not clean:
				continue
			polydata.append(len(clean))
			for ring in clean:
				polydata.append(len(ring))
			for ring in clean:
				for p in ring:
					coords.append(p.x())
					coords.append(p.y())
			values.append(CompareResultsAnalysis._toFloat(value))
		return (coords, values, polydata)

	def _applyIdenticalFilter(self, mode, props, line_arrays, value_arrays, rowids_per_table):
		""" Filter line and value arrays so that only lines considered 'identical' between
		    the two tables are kept. Returns (new_line_arrays, new_value_arrays). """
		if mode == 'geom':
			tol = self._tolerance(props)
			keep0, keep1 = self._matchByGeometry(line_arrays[0], line_arrays[1], tol)
			mode_label = "geometry matching (tolerance %.2f m)" % tol
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
	def _tolerance(props):
		""" Matching tolerance in meters from the wizard, with a safe positive fallback. """
		try:
			t = float(props.get('match_tolerance', IDENTICAL_LINE_TOLERANCE_M))
		except (TypeError, ValueError):
			return IDENTICAL_LINE_TOLERANCE_M
		return t if t > 0 else IDENTICAL_LINE_TOLERANCE_M

	@staticmethod
	def _canonKey(x0, y0, x1, y1, tol):
		""" Canonical key for a line segment: endpoints snapped to the tolerance grid,
		    sorted so the key is direction-independent. """
		a = (round(x0 / tol) * tol, round(y0 / tol) * tol)
		b = (round(x1 / tol) * tol, round(y1 / tol) * tol)
		return (a, b) if a <= b else (b, a)

	def _matchByGeometry(self, lines0, lines1, tol):
		""" Return (keep_indices0, keep_indices1) — indices of lines whose endpoint
		    geometry matches in the other table (within tolerance, direction-independent). """
		n0 = len(lines0) // 4
		n1 = len(lines1) // 4
		keys0 = {}
		for i in range(n0):
			k = CompareResultsAnalysis._canonKey(
				lines0[i*4], lines0[i*4+1], lines0[i*4+2], lines0[i*4+3], tol)
			# If duplicate keys exist within the same table, keep the first seen
			if k not in keys0:
				keys0[k] = i
		keys1 = {}
		for i in range(n1):
			k = CompareResultsAnalysis._canonKey(
				lines1[i*4], lines1[i*4+1], lines1[i*4+2], lines1[i*4+3], tol)
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
