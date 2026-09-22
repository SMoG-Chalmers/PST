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

from qgis.core import QgsProject, QgsRasterShader, QgsColorRampShader, QgsSingleBandPseudoColorRenderer, QgsGeometry, QgsPointXY, QgsCoordinateReferenceSystem, QgsMessageLog, Qgis
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

# Log-spaced fractions for the raster's optional logarithmic colour scale. The raster
# needs a wider span than the object output: blurring spreads each object's value over
# the surrounding area, so an ordinary building's cell value sits several decades below
# the peak produced by a large one. Measured on the Gothenburg time model (B_GFA
# 1960 -> 2015): a new building under 500 m2 GFA reaches ~1e-4 of the peak while one
# over 10 000 m2 reaches ~2e-2. With the linear scale (first visible band at 0.01) only
# 2 % of new buildings got any colour; over five decades 98 % do.
LOG_RASTER_DECADES = 5
LOG_RASTER_RANGES = [10.0 ** (-LOG_RASTER_DECADES * (1.0 - i / (len(RANGES) - 1.0)))
                     for i in range(len(RANGES))]

# Default/fallback tolerance for matching "identical" geometry (line endpoints, or
# centroid for points/polygons) when the wizard value is missing. The user sets the
# actual value in the wizard ('match_tolerance'). Coordinate drift varies by source:
# a few cm within one export, up to ~1-2 m between differently digitised networks.
# On the Gothenburg 1960/1990 nets, matches plateau by ~2 m and false merges/degenerate
# short segments appear from ~5-10 m, so 2 m is a safe default.
IDENTICAL_LINE_TOLERANCE_M = 2.0


class PointRegistry(object):
	""" Matches points between two tables by distance, within a tolerance.

	    Points of the first table are registered and each gets an id; a point of the
	    second table is then looked up and takes the id of the nearest registered point
	    within the tolerance. Two objects match when their identifying points resolve to
	    the same ids.

	    The distance is measured rather than quantised. Rounding coordinates onto a grid
	    of cell size 'tol' is much cheaper but loses every pair that happens to straddle
	    a cell boundary: on the Boras networks, whose coordinates differ by a median of
	    5 cm because the two exports use different precision, a 2 m grid failed to match
	    9.9 % of segments that are in fact the same street (predicted 9.2 % for that
	    drift), while measuring the distance leaves only 19 of 127 015 unmatched.

	    Points are bucketed into cells of side 'tol', so a point within the tolerance is
	    always found in one of the nine cells around the query. """

	def __init__(self, tol):
		self._tol = tol
		self._tolSq = tol * tol
		self._cells = {}   # (column, row) -> [(x, y, id), ...]
		self._ids = {}     # exact coordinate (mm) -> id, so a shared node keeps one id
		self._next = 0

	def _cell(self, x, y):
		return (int(math.floor(x / self._tol)), int(math.floor(y / self._tol)))

	def add(self, x, y):
		""" Register a point and return its id. Points repeated at the same coordinate
		    (segments meeting at a node) share one id. """
		exact = (round(x, 3), round(y, 3))
		pid = self._ids.get(exact)
		if pid is None:
			pid = self._next
			self._next += 1
			self._ids[exact] = pid
			self._cells.setdefault(self._cell(x, y), []).append((x, y, pid))
		return pid

	def find(self, x, y):
		""" Id of the nearest registered point within the tolerance, or None. """
		column, row = self._cell(x, y)
		bestSq = None
		bestId = None
		for c in range(column - 1, column + 2):
			for r in range(row - 1, row + 2):
				for (px, py, pid) in self._cells.get((c, r), ()):
					distSq = (px - x) ** 2 + (py - y) ** 2
					if bestSq is None or distSq < bestSq:
						bestSq = distSq
						bestId = pid
		return bestId if bestSq is not None and bestSq <= self._tolSq else None

	def findOrAdd(self, x, y):
		""" Id of the nearest registered point within the tolerance, registering the
		    point as a new one when there is none. Used for the second table, where an
		    object without a counterpart must still get a key of its own. """
		pid = self.find(x, y)
		return self.add(x, y) if pid is None else pid


def RangeFractions(log_scale):
	""" Class boundaries as fractions of the largest absolute value, shared by the
	    gradient raster and the range polygons so the two outputs classify identically. """
	return LOG_RASTER_RANGES if log_scale else RANGES

def RangeLabels(fractions):
	""" Legend labels for the classes defined by 'fractions', negative classes first
	    (strongest negative to weakest), then positive (weakest to strongest). """
	def fmt(f):
		return "%.2f" % f if f >= 0.01 else "%.3g" % f
	labels = ["%s - %s (-)" % (fmt(fractions[-i-2]), fmt(fractions[-i-1])) for i in range(len(fractions) - 1)]
	labels += ["%s - %s (+)" % (fmt(fractions[i]), fmt(fractions[i+1])) for i in range(len(fractions) - 1)]
	return labels

def OutputName(base, props):
	""" Output layer name carrying the compared attribute(s), so several comparisons
	    in one project stay distinguishable: 'Object comparison_AB5k', or
	    'Object comparison_AB5k vs AI5k' when the two columns differ. """
	col1, col2 = props['in_column1'], props['in_column2']
	return "%s_%s" % (base, col1 if col1 == col2 else "%s vs %s" % (col1, col2))

def WarnIfDuplicateIds(table, id_column, duplicate_count):
	""" ID matching pairs one object per ID value; repeated IDs are matched by their
	    first occurrence only, which the user should know about. """
	if duplicate_count > 0:
		QgsMessageLog.logMessage(
			"Compare Results: %d objects in '%s' share an ID value in column '%s' with another object; "
			"only the first object per ID value is matched." % (duplicate_count, table, id_column),
			'PST', Qgis.Warning)

def SetGradientRasterShader(layer, valueRange, log_scale=False):
	""" Colours the gradient raster with the same discrete classes as the range
	    polygons, so the two outputs of an area comparison look alike. 'log_scale'
	    switches the class boundaries from linearly to logarithmically spaced fractions
	    of the value range, which keeps ordinary changes visible when a few extreme
	    objects dominate the range.

	    A discrete ramp gives each cell the colour of the class its value falls in; an
	    interpolated ramp would instead fade the weakest class from transparent to its
	    colour and make it nearly invisible while the polygons draw it solid. """
	fractions = RangeFractions(log_scale)
	labels = RangeLabels(fractions)
	n = len(fractions) - 1
	posRange = max(0, valueRange[1])
	negRange = min(0, valueRange[0])
	shader = QgsRasterShader()
	fnc = QgsColorRampShader()
	fnc.setColorRampType(QgsColorRampShader.Discrete)
	# Discrete: an item colours every value up to its own value (and above the previous
	# item's), so items carry the UPPER boundary of their class.
	ramp_items = []
	if negRange < 0:
		for i in range(n):
			ramp_items.append(QgsColorRampShader.ColorRampItem(fractions[n-1-i] * negRange, QColor(*tupleFromHtmlColor(COLORS[i])), labels[i]))
	ramp_items.append(QgsColorRampShader.ColorRampItem(fractions[0] * posRange if posRange > 0 else 0, QColor(255, 255, 255, 0), ""))
	if posRange > 0:
		for i in range(n):
			ramp_items.append(QgsColorRampShader.ColorRampItem(fractions[i+1] * posRange, QColor(*tupleFromHtmlColor(COLORS[i + n])), labels[i + n]))
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

			log_scale = props.get('log_scale', False)
			fractions = RangeFractions(log_scale)
			labels = RangeLabels(fractions)

			if createRangesPolygons:

				ranges = [(-fractions[-i-1], -fractions[-i-2]) for i in range(len(fractions) - 1)]
				ranges += [(fractions[i], fractions[i+1]) for i in range(len(fractions) - 1)]

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
					OutputName('Area comparison polygons', props),
					model.coordinateReferenceSystem(props['in_table1']),
					columns,
					polygon_gen(totalPolygonCount, polygonData, polygonCoords),
					totalPolygonCount,
					progress,
					geo_type=GeometryType.POLYGON)

				# Create thematic. Listed strongest positive first so the legend reads red at
				# the top and blue at the bottom, like the raster's.
				ranges = [(labels[i], tupleFromHtmlColor(COLORS[i]), i) for i in range(len(labels))]
				model.makeThematic(tableId, 'category', list(reversed(ranges)))

			if createGradientRaster:
				# The raster must carry the input layer's CRS; without it the layer would be
				# given the project CRS and land in the wrong place whenever the two differ.
				inputCrs = QgsCoordinateReferenceSystem(model.coordinateReferenceSystem(props['in_table1']))
				rasterLayer = CreateRasterFromPstaHandle(gradientRaster, crs=inputCrs if inputCrs.isValid() else None)
				SetGradientRasterShader(
					rasterLayer,
					(rasterMin, rasterMax) if compareMode == pstalgo.CompareResultsMode.RELATIVE_PERCENT else (-1, 1),
					log_scale=log_scale)
				rasterLayer.setName(OutputName('Area comparison raster', props))
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
		      else   : geometry — line endpoints (direction-independent), or the
		               representative point for points and polygons, paired between the
		               tables by distance (see PointRegistry)
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

		registry = PointRegistry(self._tolerance(props))

		def geom_key(geom, first_table):
			# A line is identified by its two endpoints, a point or polygon by its
			# representative point. The first table registers its points, the second one
			# looks up the nearest within the tolerance.
			if geomType == GeometryType.LINE:
				pts = geom.asMultiPolyline()[0] if geom.isMultipart() else geom.asPolyline()
				points = (pts[0], pts[-1])
			else:
				points = (geom.centroid().asPoint(),)
			ids = [registry.add(p.x(), p.y()) if first_table else registry.findOrAdd(p.x(), p.y())
			       for p in points]
			return tuple(sorted(ids))

		def read_map(table, value_col, id_col, first_table):
			# key -> (geometry, value, feature id, ID column value); the first object per
			# key wins, so the user is told when an ID value is shared by several objects.
			m = {}
			duplicates = 0
			for geom, val, idval, fid in self._model.readObjects(table, value_col, id_col, with_fid=True):
				k = idval if filter_mode == 'id' else geom_key(geom, first_table)
				if k in m:
					duplicates += 1
				else:
					m[k] = (geom, val, fid, idval)
			if filter_mode == 'id':
				WarnIfDuplicateIds(table, id_col, duplicates)
			return m

		mapA = read_map(table1, col1, id1, True)
		mapB = read_map(table2, col2, id2, False)

		# Build the features: (geometry, diff, value A, value B, fid A, fid B, ID value)
		def value(obj):
			return (obj[1] or 0.0) if obj is not None else None

		features = []
		keys = set(mapA.keys()) | set(mapB.keys()) if filter_mode == 'all' else set(mapA.keys()) & set(mapB.keys())
		for k in keys:
			a = mapA.get(k)
			b = mapB.get(k)
			va, vb = value(a), value(b)
			present = b if b is not None else a
			features.append((present[0], (vb or 0.0) - (va or 0.0), va, vb,
			                 a[2] if a is not None else None, b[2] if b is not None else None,
			                 present[3]))

		if not features:
			raise AnalysisException(
				"No objects to compare between '%s' and '%s'. "
				"Try a different matching mode." % (table1, table2))

		# Write the vector layer (same geometry type as the input). Besides the diff it
		# carries both values and the source feature ids, so a row can be traced back
		# to the objects it was computed from; 'id' is only a running number.
		def column_gen(index):
			for f in features:
				yield f[index]

		def id_gen():
			for i in range(len(features)):
				yield i + 1

		progress.setCurrentTask(Tasks.WRITE)
		columns = [
			('id', 'integer', id_gen()),
			('diff', 'float', column_gen(1)),
			('value_a', 'float', column_gen(2)),
			('value_b', 'float', column_gen(3)),
			('fid_a', 'integer', column_gen(4)),
			('fid_b', 'integer', column_gen(5)),
		]
		if filter_mode == 'id':
			columns.append(('match_id', 'string', (None if v is None else str(v) for v in column_gen(6))))
		tableId = self._model.createTable(
			OutputName('Object comparison', props),
			self._model.coordinateReferenceSystem(table1),
			columns,
			column_gen(0),
			len(features),
			progress,
			geo_type=geomType)

		# Styling: graduated red/blue with mirrored class breaks around zero.
		# Boundaries are the RANGES fractions scaled by the largest absolute diff, so
		# +X and -X get equally strong colour. The innermost +/- 0.01 band is left
		# unclassified (no change), matching the raster/polygon output.
		maxAbs = max((abs(f[1]) for f in features), default=0.0)
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
			# Strongest positive first, so the legend reads red at the top like the raster's
			self._model.makeGraduated(tableId, 'diff', list(reversed(obj_ranges)))

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
		    representative point within the matching tolerance. Same semantics as the
		    object comparison path. """
		registry = PointRegistry(self._tolerance(props))

		def key(geom, idval, first_table):
			if filter_mode == 'id':
				return idval
			c = geom.centroid().asPoint()
			# Only objects present in both tables are kept, so an unmatched object of the
			# second table needs no key of its own.
			return registry.add(c.x(), c.y()) if first_table else registry.find(c.x(), c.y())

		map1 = {}
		for g, v, i in objs1:
			k = key(g, i, True)
			if k not in map1:
				map1[k] = (g, v, i)
		map2 = {}
		for g, v, i in objs2:
			k = key(g, i, False)
			if k is None:
				continue
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
				"Try a different matching mode, or use 'All objects'." % (
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

	def _matchByGeometry(self, lines0, lines1, tol):
		""" Return (keep_indices0, keep_indices1) — indices of lines whose endpoint
		    geometry matches in the other table (within tolerance, direction-independent). """
		n0 = len(lines0) // 4
		n1 = len(lines1) // 4
		registry = PointRegistry(tol)
		keys0 = {}
		for i in range(n0):
			a = registry.add(lines0[i*4], lines0[i*4+1])
			b = registry.add(lines0[i*4+2], lines0[i*4+3])
			k = (a, b) if a <= b else (b, a)
			# If duplicate keys exist within the same table, keep the first seen
			if k not in keys0:
				keys0[k] = i
		keys1 = {}
		for i in range(n1):
			a = registry.find(lines1[i*4], lines1[i*4+1])
			b = registry.find(lines1[i*4+2], lines1[i*4+3])
			# An endpoint with no counterpart means the line cannot be an identical one
			if a is None or b is None:
				continue
			k = (a, b) if a <= b else (b, a)
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
		# One line per ID value and table: keeping every line that merely shares its ID
		# with a matched one would let lines that exist in only one table through.
		first0 = {}
		for i, v in enumerate(ids0):
			first0.setdefault(v, i)
		first1 = {}
		for i, v in enumerate(ids1):
			first1.setdefault(v, i)
		WarnIfDuplicateIds(table0, id_col0, len(ids0) - len(first0))
		WarnIfDuplicateIds(table1, id_col1, len(ids1) - len(first1))
		common = first0.keys() & first1.keys()
		keep0 = sorted(first0[v] for v in common)
		keep1 = sorted(first1[v] for v in common)
		return keep0, keep1
