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
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
	QgsField,
	QgsFillSymbol,
	QgsMapLayerType,
	QgsProject,
	QgsVectorLayer,
	QgsWkbTypes,
)

ISOVIST_PERIMETER_RESOLUTION = 64
ISOVIST_FILL_COLOR = "#406d97c4"
ISOVIST_EDGE_COLOR = "#4e7094"

FIELD_NAME_X            = 'x'
FIELD_NAME_Y            = 'y'
FIELD_NAME_MAX_DISTANCE = 'max_dist'
FIELD_NAME_FOV          = 'fov_angle'
FIELD_NAME_DIRECTION    = 'direction'
FIELD_NAME_AREA         = 'area'

POINT_FIELDS = [
	(FIELD_NAME_MAX_DISTANCE, QVariant.Double),
	(FIELD_NAME_FOV,          QVariant.Double),
	(FIELD_NAME_DIRECTION,    QVariant.Double),
	(FIELD_NAME_AREA,         QVariant.Double),
]

POLYGON_FIELDS = [
	(FIELD_NAME_X,            QVariant.Double),
	(FIELD_NAME_Y,            QVariant.Double),
	(FIELD_NAME_MAX_DISTANCE, QVariant.Double),
	(FIELD_NAME_FOV,          QVariant.Double),
	(FIELD_NAME_DIRECTION,    QVariant.Double),
	(FIELD_NAME_AREA,         QVariant.Double),
]

def allLayers():
	return QgsProject.instance().mapLayers().values()

def allPointLayers():
	return [layer for layer in allLayers() if isPointLayer(layer)]

def allPolygonLayers():
	return [layer for layer in allLayers() if isPolygonLayer(layer)]

def isPointLayer(layer):
	return layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry

def isPolygonLayer(layer):
	return layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry

class IsovistLayer:
	def __init__(self, qgisLayer, obstacle):
		self.qgisLayer = qgisLayer
		self.obstacle = obstacle
		self.featureIds = None
		self.canvasItemsByIndex = {}
		self.visibleCount = 0

def CreateIsovistContext(model, obstacleLayers, attractionPointLayers, attractionPolygonLayers, outFeatureIdsPerLayer=None, progressContext = None):
	import pstalgo
	from ...analyses.memory import stack_allocator
	initial_alloc_state = stack_allocator.state()
	try:
		isovistContextGeometry = pstalgo.IsovistContextGeometry()

		def ReadPoints(layers, outPoints, outFeatureIdsPerLayer=None):
			if layers:
				point_count_per_group = pstalgo.Vector(ctypes.c_uint, len(layers), stack_allocator)
				max_point_count = 0
				for layer in layers:
					max_point_count += model.rowCount(layer.name())
				coords = pstalgo.Vector(ctypes.c_double, max_point_count * 2, stack_allocator)
				for layerIndex, layer in enumerate(layers):
					prevCoordCount = int(len(coords) / 2)
					feature_ids = None
					if outFeatureIdsPerLayer is not None:
						feature_ids = []
						outFeatureIdsPerLayer[layer.id()] = feature_ids
					model.readPoints(layer.name(), coords, out_rowids=feature_ids, progress=progressContext)
					point_count_per_group.append(int(len(coords) / 2) - prevCoordCount)
			else:
				point_count_per_group = None
				coords = None
			outPoints.pointCountPerGroup = point_count_per_group
			outPoints.coords = coords

		def ReadPolygons(layers, outPolygons, outFeatureIdsPerLayer=None):
			if layers:
				polygon_count_per_group = pstalgo.Vector(ctypes.c_uint, len(layers), stack_allocator)
				max_polygon_count = 0
				for layer in layers:
					max_polygon_count += model.rowCount(layer.name())
				point_count_per_polygon = pstalgo.Vector(ctypes.c_uint, max_polygon_count, stack_allocator)
				polygon_points = None
				for layerIndex, layer in enumerate(layers):
					prevPolyCount = len(point_count_per_polygon)
					feature_ids = None
					if outFeatureIdsPerLayer is not None:
						feature_ids = []
						outFeatureIdsPerLayer[layer.id()] = feature_ids
					polygon_points = model.readPolygons(layer.name(), point_count_per_polygon, out_rowids=feature_ids, progress=progressContext, out_coords = polygon_points)
					polygon_count_per_group.append(len(point_count_per_polygon) - prevPolyCount)
			else:
				polygon_count_per_group = None
				point_count_per_polygon = None
				polygon_points = None
			outPolygons.polygonCountPerGroup = polygon_count_per_group
			outPolygons.pointCountPerPolygon = point_count_per_polygon
			outPolygons.coords = polygon_points

		ReadPolygons(obstacleLayers, isovistContextGeometry.obstaclePolygons, outFeatureIdsPerLayer)
		ReadPoints(attractionPointLayers, isovistContextGeometry.attractionPoints, outFeatureIdsPerLayer)
		ReadPolygons(attractionPolygonLayers, isovistContextGeometry.attractionPolygons, outFeatureIdsPerLayer)

		if progressContext:
			progressContext.setProgress(1)

		return pstalgo.CreateIsovistContext(isovistContextGeometry)
	finally:
		stack_allocator.restore(initial_alloc_state)

def CreateIsovistPolygonLayer(layerName, counterNames, fillColor=ISOVIST_FILL_COLOR):
		layer = QgsVectorLayer("Polygon", layerName, "memory")
		layer.startEditing()
		symbol = QgsFillSymbol.createSimple({'color' : fillColor})
		layer.renderer().setSymbol(symbol)
		layer.setCrs(QgsProject.instance().crs())
		dataProvider = layer.dataProvider()
		dataProvider.addAttributes([QgsField(name, dataType) for name, dataType in IsovistPolygonLayerFields(counterNames)])
		layer.updateFields()
		layer.commitChanges()
		QgsProject.instance().addMapLayer(layer)
		return layer

def IsovistPointLayerFields(counterNames):
	return POINT_FIELDS + [(name, QVariant.Int) for name in counterNames]

def IsovistPolygonLayerFields(counterNames):
	return POLYGON_FIELDS + [(name, QVariant.Int) for name in counterNames]