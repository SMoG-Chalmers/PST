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

"""
Unlike the other analyses this is dependent on QGIS itself, to save some
time developing it. If needed this could be made independent of QGIS as well...
"""
from builtins import range
from qgis.core import QgsFeature, QgsGeometry, QgsPoint, QgsProject, QgsVectorLayer, QgsWkbTypes

from .base import BaseAnalysis


class SplitPolylinesAnalysis(BaseAnalysis):
	def __init__(self, model, props):
		BaseAnalysis.__init__(self)
		self._model = model
		self._props = props

	def run(self, delegate):
		import pstalgo  # Do it here when it is needed instead of on plugin load
		props = self._props
		model = self._model

		table_name = props['in_network']
		new_table_name = table_name + "_lines"

		layer = model._layerFromName(table_name)

		copy_column = model._safeFieldIndex(layer, props['copy_column_in']) if props['copy_column_enabled'] else None

		# Generate URI
		uri = "LineString?crs=%s" % model.coordinateReferenceSystem(table_name)
		if copy_column is not None:
			uri += "&field=%s:%s" % (props['copy_column_out'], model.columnType(table_name, props['copy_column_in']))
		new_layer = QgsVectorLayer(uri, table_name + "_lines", "memory")

		delegate.setStatus("Splitting polylines '%s' -> '%s'" % (table_name, new_table_name))

		BATCH_SIZE = 4096
		features = [None]*BATCH_SIZE
		dp = new_layer.dataProvider()
		n = 0
		for feature in LinesAndValueFeatures(layer, copy_column, delegate):
			features[n] = feature
			n += 1
			if n == BATCH_SIZE:
				dp.addFeatures(features)
				n = 0
		if n > 0:
			dp.addFeatures(features[:n])

		new_layer.updateExtents()

		QgsProject.instance().addMapLayer(new_layer)


def LinesAndValueFeatures(layer, value_index, progress):
	num_features = layer.featureCount()
	line = [None, None]
	for feature_index, feature in enumerate(layer.getFeatures()):
		geom = feature.geometry()
		if geom.type() == QgsWkbTypes.LineGeometry:
			pts = [QgsPoint(pt.x(), pt.y()) for pt in geom.asPolyline()]
			value = None if value_index is None else feature[value_index]
			for i in range(len(pts)-1):
				fet = QgsFeature()
				if value is not None:
					fet.initAttributes(1)
					fet.setAttribute(0, value)
				line[0] = pts[i]
				line[1] = pts[i+1]
				fet.setGeometry(QgsGeometry.fromPolyline(line))
				yield fet
		if (feature_index % 1000) == 0:
			progress.setProgress(float(feature_index) / num_features)