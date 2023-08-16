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

from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor
import array, math

import qgis
from qgis.core import Qgis, QgsWkbTypes, QgsPoint, QgsPointXY, QgsProject, QgsMapLayerType

from qgis.core import *  # TODO: Remove


class GeometryType(object):
	POINT   = 'point'
	LINE    = 'line'
	POLYGON = 'polygon'

QGIS_GEO_TYPE_STR_FROM_GEO_TYPE = {
	GeometryType.POINT   : "Point",
	GeometryType.LINE    : "LineString",
	GeometryType.POLYGON : "Polygon",
}

VARIANT_FROM_COLUMN_TYPE = {
	"integer" : QVariant.Int,
	"float"   : QVariant.Double,
	"double"  : QVariant.Double,
}

QGISTYPESTR_FROM_COLUMN_TYPE = {
	"integer" : "integer",
	"float"   : "double",
	"double"  : "double",
	"string"  : "string",
}

def QGISStringFromColumnType(typename):
	p = typename.find('(')
	suffix = '' if p < 0 else typename[p:]
	typepart = typename if p < 0 else typename[:p]
	return QGISTYPESTR_FROM_COLUMN_TYPE[typepart] + suffix

def QGISGeometryTypeStringFromGeometryType(geo_type):
	s = QGIS_GEO_TYPE_STR_FROM_GEO_TYPE.get(geo_type)
	if s is None:
		raise Exception("Unknown geometry type '%s'" % geo_type)
	return s

class QGISModel(object):
	def __init__(self):
		pass

	def tableNames(self):
		names = []
		for layerid, layer in QgsProject.instance().mapLayers().items():
			if type(layer) == QgsVectorLayer:
				names.append(layer.name())
		return names

	def columnNames(self, table):
		layer = self._layerFromName(table)
		return [field.name() for field in layer.fields()]

	def columnType(self, table, column):
		layer = self._layerFromName(table)
		field = layer.fields()[self._safeFieldIndex(layer, column)]
		field_type = field.type()
		# Type strings from https://api.qgis.org/api/classQgsVectorLayer.html (section "Memory data providerType (memory)")
		# Allowed type strings are "integer", "double" and "string".
		if QVariant.Int == field_type:
			return "integer"
		elif QVariant.UInt == field_type:
			return "integer"  # Isn't there a better one?
		elif QVariant.LongLong == field_type:
			return "integer"  # Isn't there a better one?
		elif QVariant.ULongLong == field_type:
			return "integer"  # Isn't there a better one?
		elif QVariant.Double == field_type:
			return "double"
		elif QVariant.String == field_type:
			return "string(%d)" % field.length()
		return None

	def createPoint(self, x, y):
		return QgsGeometry.fromPointXY(QgsPointXY(x, y))

	def createLine(self, x1, y1, x2, y2):
		return QgsGeometry.fromPolyline([QgsPoint(x1, y1), QgsPoint(x2, y2)])

	def createPolygonFromCoordinateElements(self, coordinate_elements, coordinate_count, first_index = 0):
		""" coordinate_elements = [x0, y0, x1, y1, ...] """
		points = [ QgsPointXY( coordinate_elements[first_index + i * 2], coordinate_elements[first_index + 1 + i * 2]) for i in range(coordinate_count) ]
		return QgsGeometry.fromPolygonXY( [points] ) 

	def createTable(self, name, crs, columns, geo_iter, row_count, progress, geo_type=GeometryType.LINE):
		# Generate URI
		uri = "%s?crs=%s" % (QGISGeometryTypeStringFromGeometryType(geo_type), crs)
		for column in columns:
			uri = uri + "&field=%s:%s" % (column[0], QGISStringFromColumnType(column[1]))
		layer = QgsVectorLayer(uri, name, "memory")
		if geo_iter is not None or columns:
			self._append(layer, geo_iter, [c[2] for c in columns], row_count, progress)
		QgsProject.instance().addMapLayer(layer)
		return layer.id()

	def makeThematic(self, table, column, ranges):
		layer = self._layerFromName(table)
		old_renderer = layer.renderer()
		symbol_props = None if isinstance(old_renderer, QgsCategorizedSymbolRenderer) else old_renderer.symbol().symbolLayer(0).properties()
		symbol_props = None
		layer.setRenderer(self._createCategoryRenderer(symbol_props, column, ranges, layer.geometryType()))
		self._refreshLayer(layer)

	def _createCategoryRenderer(self, symbol_props, column, ranges, geometryType):
		categories = []
		for r in ranges:
			if symbol_props is None:
				#symbol = QgsLineSymbol.createSimple({})
				symbol = QgsSymbol.defaultSymbol(geometryType)
				symbol.setColor(QColor(*r[1]))
				symbol.symbolLayer(0).setStrokeStyle(Qt.PenStyle(Qt.NoPen))
			else:
				symbol_props['line_color'] = ','.join([str(b) for b in r[1]])
				symbol = QgsLineSymbol.createSimple(symbol_props)
			categories.append(QgsRendererCategory(r[2], symbol, r[0]))
		return QgsCategorizedSymbolRenderer(column, categories)

	def cloneTable(self, table, new_name):
		base_layer = self._layerFromName(table)
		layer = QgsVectorLayer(base_layer.source(), new_name, base_layer.providerType())
		QgsProject.instance().addMapLayer(layer)

	def rowCount(self, table_name):
		return self._layerFromName(table_name).featureCount()

	def coordinateReferenceSystem(self, table_name):
		return self._layerFromName(table_name).crs().authid()

	# DEPRECATED: Use geometryType instead
	def getFirstGeometryType(self, table_name):
		layer = self._layerFromName(table_name)
		for feature in layer.getFeatures():
			g = feature.geometry()
			if not g:
				continue
			geo_type = g.type()
			if geo_type == QgsWkbTypes.PointGeometry:
				return GeometryType.POINT
			if geo_type == QgsWkbTypes.LineGeometry:
				return GeometryType.LINE
			if geo_type == QgsWkbTypes.PolygonGeometry:
				return GeometryType.POLYGON
			raise Exception("Unsupported geometry type (#%d)" % geo_type)
		return None

	def geometryType(self, table_name):
		layer = self._layerFromName(table_name)
		if layer.type() != QgsMapLayerType.VectorLayer:
			return None
		return self._geometryTypeFromQgsWkbTypes(layer.geometryType())
	
	def _geometryTypeFromQgsWkbTypes(self, geo_type):
		if geo_type == QgsWkbTypes.PointGeometry:
			return GeometryType.POINT
		if geo_type == QgsWkbTypes.LineGeometry:
			return GeometryType.LINE
		if geo_type == QgsWkbTypes.PolygonGeometry:
			return GeometryType.POLYGON
		return None

	def values(self, table_name, column_names, rowids=None):
		""" A single element list will return plain values, while a multi-element list will return tuples """
		layer = self._layerFromName(table_name)
		if isinstance(column_names, str):
			column_names = (column_names,)
		field_indices = [self._safeFieldIndex(layer, name) for name in column_names]
		request = QgsFeatureRequest()
		request.setFlags(QgsFeatureRequest.NoGeometry)
		request.setSubsetOfAttributes(field_indices)
		if rowids:
			row_idx = 0
			if len(field_indices) == 1:
				field_index = field_indices[0]
				for feature in layer.getFeatures(request):
					if row_idx >= rowids.size():
						break
					if feature.id() == rowids.at(row_idx):
						row_idx += 1
						yield feature[field_index]
			else:
				for feature in layer.getFeatures(request):
					if row_idx >= rowids.size():
						break
					if feature.id() == rowids.at(row_idx):
						row_idx += 1
						yield tuple(feature[field_index] for field_index in field_indices)
			if row_idx != rowids.size():
				raise Exception("QGISModel.readValues: Only %d of %d values could be read!" % (row_idx, num_rows))
		else:
			if len(field_indices) == 1:
				field_index = field_indices[0]
				for feature in layer.getFeatures(request):
					yield feature[field_index]
			else:
				for feature in layer.getFeatures(request):
					yield tuple(feature[field_index] for field_index in field_indices)

	def readValues(self, table_name, column_name, rowids, out_values, progress=None):
		num_rows = rowids.size()
		for i,v in enumerate(self.values(table_name, column_name, rowids)):
			out_values.append(v)
			if progress is not None and (i % 1000) == 0:
				progress.setProgress(float(i) / num_rows)
		if progress is not None:
			progress.setProgress(1)

	def readPoints(self, table_name, out_coords, out_rowids, progress = None):
		layer = self._layerFromName(table_name)
		num_features = layer.featureCount()
		for feature_index, feature in enumerate(layer.getFeatures()):
			g = feature.geometry()
			if g is not None:
				point = g.centroid().asPoint()
				out_coords.append(point.x())
				out_coords.append(point.y())
				if out_rowids is not None:
					out_rowids.append(feature.id())
			if progress is not None and feature_index % 1000 == 0:
				progress.setProgress(float(feature_index) / num_features)
		if progress is not None:
			progress.setProgress(1)

	def readLines(self, table_name, out_coords, out_rowids, progress = None):
		layer = self._layerFromName(table_name)
		num_features = layer.featureCount()
		for feature_index, feature in enumerate(layer.getFeatures()):
			g = feature.geometry()
			if g and g.type() == QgsWkbTypes.LineGeometry:
				poly = None
				if g.isMultipart():
					multiPolyline = g.asMultiPolyline()
					if len(multiPolyline) != 1:
						raise Exception("Table '%s' contains multi-polyline geometry, which is not supported." % (table_name)) 
					poly = multiPolyline[0]
				else:
					poly = g.asPolyline()
				if len(poly) == 2:
					out_coords.append(poly[0].x())
					out_coords.append(poly[0].y())
					out_coords.append(poly[1].x())
					out_coords.append(poly[1].y())
					if out_rowids is not None:
						out_rowids.append(feature.id())
				elif len(poly) > 2:
					raise Exception("Table '%s' contains polyline geometry, which is not supported." % (table_name)) 
			if progress is not None and feature_index % 1000 == 0:
				progress.setProgress(float(feature_index) / num_features)
		if progress is not None:
			progress.setProgress(1)

	def readPolylines(self, table_name, progress = None):
		layer = self._layerFromName(table_name)
		coords = array.array('d')
		polys = array.array('i')
		num_features = layer.featureCount()
		for feature_index, feature in enumerate(layer.getFeatures()):
			g = feature.geometry()
			if g is None:
				continue  # Seems strange that a feature could be without geometry, but this was encountered once
			if g.type() == QgsWkbTypes.LineGeometry:
				if g.isMultipart():
					multiPolyline = g.asMultiPolyline()
					for poly in multiPolyline:
						for c in poly:
							coords.append(c.x())
							coords.append(c.y())
						polys.append(len(poly))
				else:
					poly = g.asPolyline()
					for c in poly:
						coords.append(c.x())
						coords.append(c.y())
					polys.append(len(poly))
			if progress is not None and feature_index % 1000 == 0:
				progress.setProgress(float(feature_index) / num_features)
		if progress is not None:
			progress.setProgress(1)
		return (coords, polys)

	def readPolygons(self, table_name, out_coord_counts, out_rowids = None, progress = None, out_coords = None):
		coords = array.array('d') if out_coords is None else out_coords
		layer = self._layerFromName(table_name)
		num_features = layer.featureCount()
		for feature_index, feature in enumerate(layer.getFeatures()):
			g = feature.geometry()
			if g.type() == QgsWkbTypes.PolygonGeometry:
				if g.isMultipart():  # not QgsWkbTypes.isSingleType(g.wkbType()):
					polygons = g.asMultiPolygon()
					if len(polygons) != 1:
						raise Exception("Multipolygon geometry is not supported.")
					rings = polygons[0]
				else:
					rings = g.asPolygon()
				#rings = g.asPolygon()
				outer_ring = rings[0]  # First polyline is outer ring, the rest are inner rings (if any)
				out_coord_counts.append(len(outer_ring))
				for point in outer_ring:
					coords.append(point.x())
					coords.append(point.y())
				if out_rowids is not None:
					out_rowids.append(feature.id())
			if progress is not None and feature_index % 1000 == 0:
				progress.setProgress(float(feature_index) / num_features)
		if progress is not None:
			progress.setProgress(1)
		return coords

	def writeColumns(self, table_name, rowids, name_type_iter_list, progress):
		# Status text
		# TODO: Move status text to separate utility wrapper instead?
		if len(name_type_iter_list) == 1:
			progress.setStatus("Writing column '%s' to table '%s'" % (name_type_iter_list[0][0], table_name))
		else:
			column_names = [c[0] for c in name_type_iter_list]
			progress.setStatus("Writing columns ('%s') to table '%s'" % ("','".join(column_names), table_name))

		# Aquire layer and data provider from table name
		layer = self._layerFromName(table_name)
		data_provider = layer.dataProvider()

		# Create new fields in table (if any)
		new_fields = [QgsField(t[0], VARIANT_FROM_COLUMN_TYPE[t[1]]) for t in name_type_iter_list if -1 == data_provider.fieldNameIndex(t[0])]
		if new_fields:
			if not data_provider.addAttributes(new_fields):
				raise Exception("Couldn't add fields to table '%s'!"%table_name)

		# Needed?
		layer.updateFields()

		# Create list of (field index, value_iter) pairs
		columns = []
		for name, ctype, value_iter in name_type_iter_list:
			field_index = data_provider.fieldNameIndex(name)
			if -1 == field_index:
				raise Exception("Field '%s' was added to table '%s', but then its index couldn't be looked up! The column name was probably cut due to limits in the file format that is used. Please save the file as tab file before using PST." % (name, table_name))
			columns.append((field_index, value_iter))

		# Change attribute values in batches
		BATCH_SIZE = 256
		num_rows = rowids.size()
		row_idx = 0
		while row_idx < num_rows:
			end = min(row_idx + BATCH_SIZE, num_rows)
			data_provider.changeAttributeValues({rowids.at(i):{fidx : next(viter) for fidx, viter in columns} for i in range(row_idx, end)})
			row_idx = end
			if progress is not None:
				progress.setProgress(float(row_idx) / num_rows)
		if progress is not None:
			progress.setProgress(1)

	def _append(self, layer, geo_iter, value_iters, row_count, progress):
		# TODO: Experiment with different batch sizes
		BATCH_SIZE = 4096
		batch_count = int(math.ceil(row_count / BATCH_SIZE))  # for progress
		features = [None]*BATCH_SIZE
		dp = layer.dataProvider()
		n = 0
		batch_index = 0
		for geo in geo_iter:
			fet = QgsFeature()
			fet.initAttributes(len(value_iters))
			fet.setGeometry(geo)
			for i, value_iter in enumerate(value_iters):
				fet.setAttribute(i, next(value_iter))
			features[n] = fet
			n = n + 1
			if n == BATCH_SIZE:
				dp.addFeatures(features)
				n = 0
				batch_index = batch_index + 1
				progress.setProgress(float(batch_index) / batch_count)
		if n > 0:
			dp.addFeatures(features[:n])
		progress.setProgress(1)
		layer.updateExtents()

	def _layerFromName(self, nameOrId):
		for _, layer in QgsProject.instance().mapLayers().items():
			if layer.name() == nameOrId or layer.id() == nameOrId:
				return layer
		raise Exception("Table '%s' not found!" % nameOrId)

	def _safeFieldIndex(self, layer, name):
		idx = layer.fields().indexFromName(name)
		if -1 == idx:
			raise Exception("QGISModel: Column '%s' not found!" % name)
		return idx

	def _refreshLayer(self, layer):
		# If caching is enabled, a simple canvas refresh might not be sufficient
		# to trigger a redraw and you must clear the cached image for the layer
		if qgis.utils.iface.mapCanvas().isCachingEnabled():
			layer.triggerRepaint()
		else:
			qgis.utils.iface.mapCanvas().refresh()