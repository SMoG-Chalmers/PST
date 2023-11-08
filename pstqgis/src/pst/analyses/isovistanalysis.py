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

from qgis.core import (
		Qgis,
		QgsFeature,
		QgsField,
		QgsFillSymbol,
		QgsVectorLayer,
		QgsMapLayerType,
		QgsPoint,
		QgsPointXY,
		QgsProject,
		QgsGeometry,
)
from builtins import range, object
import array, ctypes
from ..model import GeometryType
from .base import BaseAnalysis
from .memory import stack_allocator
from .utils import MultiTaskProgressDelegate
from ..maptools.isovist.common import allLayers, isPointLayer, isPolygonLayer, FIELD_NAME_X, FIELD_NAME_Y, FIELD_NAME_MAX_DISTANCE, FIELD_NAME_FOV, FIELD_NAME_DIRECTION, FIELD_NAME_AREA, POINT_FIELDS, POLYGON_FIELDS, CreateIsovistContext, CreateIsovistPolygonLayer, ISOVIST_PERIMETER_RESOLUTION


class Tasks(object):
	CREATE_ISOVIST_CONTEXT = 1
	ANALYSIS = 2
	CREATE_ISOVISTS_LAYER = 3


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
		progress.addTask(Tasks.CREATE_ISOVIST_CONTEXT, 1, None)
		progress.addTask(Tasks.ANALYSIS, 1, None)
		progress.addTask(Tasks.CREATE_ISOVISTS_LAYER, 1, None)

		qgisLayersByName = {qgisLayer.name() : qgisLayer for qgisLayer in allLayers()}

		algo = None

		max_view_distance = props['max_view_distance']
		visibilityCounters = {}
		fieldValues = {}
		isovistContext = None
		try:
			# Build context
			progress.setCurrentTask(Tasks.CREATE_ISOVIST_CONTEXT)
			obstacleLayers = [qgisLayersByName[layerName] for layerName in props['obstacles']]
			attractionLayers = [qgisLayersByName[layerName] for layerName in props['attractions']]
			attractionPointLayers = [qgisLayer for qgisLayer in attractionLayers if isPointLayer(qgisLayer)]
			attractionPolygonLayers = [qgisLayer for qgisLayer in attractionLayers if isPolygonLayer(qgisLayer)]
			isovistContext = CreateIsovistContext(self._model, obstacleLayers, attractionPointLayers, attractionPolygonLayers, progressContext=progress)

			counterNames = props['obstacles'] + props['attractions']
			outputLayer = CreateIsovistPolygonLayer(layerName="isovists", counterNames=counterNames)
			if not outputLayer.isEditable():
				outputLayer.startEditing()
			outputFieldNames = [field.name() for field in outputLayer.fields()]

			# Generate isovists
			progress.setCurrentTask(Tasks.ANALYSIS)
			progress.setStatus("Calculating isovists")
			for (originX, originY) in self._model.points(props['in_origins']):
				isovistHandle = None
				try:
					(point_count, points, isovistHandle, area, visibleObstacles, visibleAttractionPoints, visibleAttractionPolygons) = pstalgo.CalculateIsovist(
						isovistContext, 
						originX, originY, 
						max_view_distance, 
						360, 
						0, 
						ISOVIST_PERIMETER_RESOLUTION)

					# Visibility counters
					for visibleObjects, qgisLayers in [(visibleObstacles, obstacleLayers), (visibleAttractionPoints, attractionPointLayers), (visibleAttractionPolygons, attractionPolygonLayers)]:
						assert(visibleObjects.GroupCount == len(qgisLayers))
						for i in range(visibleObjects.GroupCount):
							visibilityCounters[qgisLayers[i].name()] = visibleObjects.CountPerGroup[i]

					# Create output record and feature
					feature = QgsFeature()

					# Geometry
					map_points = [QgsPointXY(points[i * 2], points[i * 2 + 1]) for i in range(point_count)]
					layer_points = map_points  # [self.toLayerCoordinates(layer, point) for point in map_points]
					feature.setGeometry(QgsGeometry.fromPolygonXY([layer_points]))

					# Attributes
					fieldValues[FIELD_NAME_X]            = originX
					fieldValues[FIELD_NAME_Y]            = originY
					fieldValues[FIELD_NAME_MAX_DISTANCE] = max_view_distance
					fieldValues[FIELD_NAME_FOV]          = 360
					fieldValues[FIELD_NAME_DIRECTION]    = 0
					fieldValues[FIELD_NAME_AREA]         = area
					for name, value in visibilityCounters.items():
						fieldValues[name.lower()] = value
					feature.initAttributes(len(outputFieldNames))
					for fieldIndex, fieldName in enumerate(outputFieldNames):
						value = fieldValues.get(fieldName.lower())
						if value is not None:
							feature.setAttribute(fieldIndex, value)

					outputLayer.addFeature(feature)
					
				finally:
					if isovistHandle != None:
						pstalgo.Free(isovistHandle)
						isovistHandle = None

			outputLayer.commitChanges()

		finally:
			if isovistContext != None:
				pstalgo.Free(isovistContext)
				isovistContext = None
