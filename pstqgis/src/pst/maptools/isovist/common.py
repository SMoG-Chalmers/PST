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

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
		QgsMapLayerType,
		QgsVectorLayer,
		QgsWkbTypes,
)

FIELD_NAME_X            = 'x'
FIELD_NAME_Y            = 'y'
FIELD_NAME_MAX_DISTANCE = 'max_dist'
FIELD_NAME_FOV          = 'fov'
FIELD_NAME_DIRECTION    = 'dir'
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