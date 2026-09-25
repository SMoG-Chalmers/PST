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

from qgis.PyQt.QtCore import (QCoreApplication, 
							  QVariant)
from qgis.core import (QgsProcessing,
					   QgsFeatureSink,
					   QgsProcessingAlgorithm,
					   QgsProcessingParameterFeatureSource,
					   QgsProcessingParameterFeatureSink,
					   QgsProcessingParameterVectorLayer,
					   QgsProcessingParameterField,
					   QgsProcessingParameterEnum,
					   QgsProcessingParameterString,
					   QgsProcessingParameterNumber,
					   QgsProcessingParameterExpression,
					   QgsProcessingParameterBoolean,
					   QgsProcessingOutputString,
					   QgsField)

from ..analyses import ODBetweennessAnalysis, AnalysisDelegateFilter
from .processing_qgis_model import ProcessingQgisModel
from .processing_analysis_delegate import ProcessingAnalysisDelegate

class PstProcessingAlgorithmBase(QgsProcessingAlgorithm):

	def analysisClass(self):
		return ODBetweennessAnalysis

	def processAlgorithm(self, parameters, context, feedback):
		"""
		Here is where the processing itself takes place.
		"""

		network_layer = self.parameterAsVectorLayer(parameters, self.NETWORK, context)

		output_field_name = 'ODB'

		output_field_suffix = self.parameterAsString(parameters, self.OUTPUT_FIELD_SUFFIX, context)
		if output_field_suffix:
			output_field_name += '_' + output_field_suffix

		network_layer = self.parameterAsVectorLayer(parameters, self.NETWORK, context)

		# Create output field (if it doesn't already exist)
		data_provider = network_layer.dataProvider()
		if -1 == data_provider.fieldNameIndex(output_field_name):
			feedback.pushInfo("Adding output field '%s' to layer '%s'" % (output_field_name, network_layer.name()))
			new_field = QgsField(output_field_name, type=QVariant.Double)
			if not data_provider.addAttributes([new_field]):
				raise Exception("Couldn't add field '%s' to table '%s'!" % (output_field_name, network_layer.name()))
			network_layer.updateFields()
		else:
			feedback.pushInfo("Output field '%s' already exist in layer '%s'" % (output_field_name, network_layer.name()))


		return {   
			self.OUTPUT_FIELD_NAME: output_field_name
		}

	def tr(self, string):
		return QCoreApplication.translate('Processing', string)    


class ODBetweennessAlgorithm(QgsProcessingAlgorithm):

	# Parameters
	ORIGIN = 'ORIGIN'
	ORIGIN_FIELD = "ORIGIN_FIELD"
	NETWORK = 'NETWORK'
	UNLINKS = 'UNLINKS'
	DESTINATION = 'DESTINATION'
	DESTINATION_FIELD = 'DESTINATION_FIELD'
	DESTINATION_MODE = 'DESTINATION_MODE'
	ROUTE_CHOICE = 'ROUTE_CHOICE'
	COST_EXPRESSION = 'COST_EXPRESSION'
	COST_PER_METER = 'COST_PER_METER'
	STRAIGHT_LINE_RADIUS = 'STRAIGHT_LINE_RADIUS'
	WALKING_RADIUS = 'WALKING_RADIUS'
	ANGULAR_RADIUS = 'ANGULAR_RADIUS'
	OUTPUT_FIELD_SUFFIX = 'OUTPUT_FIELD_SUFFIX'

	_DESTINATION_MODES = [
		('All reachable destinations', 'all'),
		('Closest destination only',   'closest'),
	]

	_ROUTE_CHOICE_MODES = [
		('Minimum walking distance', 'walking'),
		('Least angular',            'angular'),
		('Minimum weighted distance (expression)', 'weights'),
	]

	def initAlgorithm(self, config):
		self.addParameter(
			QgsProcessingParameterFeatureSource(
				self.ORIGIN,
				self.tr('Origin'),
				[QgsProcessing.TypeVectorPoint]
			)
		)

		self.addParameter(
			QgsProcessingParameterField(
				self.ORIGIN_FIELD,
				self.tr('Origin Field'),
				parentLayerParameterName = self.ORIGIN
			)
		)

		self.addParameter(
			QgsProcessingParameterVectorLayer(
				self.NETWORK,
				self.tr('Segment/Axial'),
				types=[QgsProcessing.TypeVectorLine]
			)
		)

		self.addParameter(
			QgsProcessingParameterFeatureSource(
				self.UNLINKS,
				self.tr('Unlinks'),
				types=[QgsProcessing.TypeVectorPoint],
				optional = True
		   )
		)
		self.addParameter(
			QgsProcessingParameterFeatureSource(
				self.DESTINATION,
				self.tr('Destination'),
				[QgsProcessing.TypeVectorPoint]
			)
		)

		self.addParameter(
			QgsProcessingParameterField(
				self.DESTINATION_FIELD,
				self.tr('Destination Field'),
				optional = True,
				parentLayerParameterName = self.DESTINATION
			)
		)

		self.addParameter(
			QgsProcessingParameterEnum(
				self.DESTINATION_MODE,
				self.tr('Destination Mode'),
				options = [entry[0] for entry in self._DESTINATION_MODES],
				defaultValue = 0
			)
		)

		self.addParameter(
			QgsProcessingParameterEnum(
				self.ROUTE_CHOICE,
				self.tr('Route Choice'),
				options = [entry[0] for entry in self._ROUTE_CHOICE_MODES],
				defaultValue = 0
			)
		)

		self.addParameter(
			QgsProcessingParameterExpression(
				self.COST_EXPRESSION,
				self.tr('Line cost expression (weighted route choice)'),
				optional = True,
				parentLayerParameterName = self.NETWORK
			)
		)

		self.addParameter(
			QgsProcessingParameterBoolean(
				self.COST_PER_METER,
				self.tr('Multiply line cost by segment length'),
				defaultValue = True
			)
		)

		self.addParameter(
			QgsProcessingParameterNumber(
				self.STRAIGHT_LINE_RADIUS,
				self.tr('Straight line radius'),
				optional = True
			)
		)

		self.addParameter(
			QgsProcessingParameterNumber(
				self.WALKING_RADIUS,
				self.tr('Walking radius'),
				optional = True
			)
		)

		self.addParameter(
			QgsProcessingParameterNumber(
				self.ANGULAR_RADIUS,
				self.tr('Angular radius'),
				optional = True
			)
		)

		self.addParameter(
			QgsProcessingParameterString(
				self.OUTPUT_FIELD_SUFFIX,
				self.tr('Output field suffix'),
				optional = True
			)
		)

	def checkParameterValues(self, parameters, context):
		props = self._collectProperties(parameters, context)

		if not props["rad_angular_enabled"] and not props["rad_straight_enabled"] and not props["rad_walking_enabled"]:
			return (False, "No radius specified")

		if props["route_choice"] == "weights" and not props["dw_expression"]:
			return (False, "Weighted route choice requires a line cost expression")

		return (True, None)

	def processAlgorithm(self, parameters, context, feedback):

		props = self._collectProperties(parameters, context)

		feedback.pushInfo("Properties:\n" + str(props))

		model = ProcessingQgisModel(self, parameters, context)
		analysis = ODBetweennessAnalysis(model, props)

		delegate = AnalysisDelegateFilter(ProcessingAnalysisDelegate(feedback))
		analysis.run(delegate)

		return {}

	def _collectProperties(self, parameters, context):
		props = {}

		props["column_suffix"] = self.parameterAsString(parameters, self.OUTPUT_FIELD_SUFFIX, context)
		props["column_suffix_enabled"] = True if props["column_suffix"] else False

		props["destination_mode"] = self._DESTINATION_MODES[self.parameterAsEnum(parameters, self.DESTINATION_MODE, context)][1]

		props["in_destinations"] = self.DESTINATION
		props["in_destination_weights"] = self.parameterAsString(parameters, self.DESTINATION_FIELD, context)
		props["in_destination_weights_enabled"] = True if props["in_destination_weights"] else False

		props["in_network"] = self.NETWORK

		props["in_origins"] = self.ORIGIN
		props["in_origin_weights"] = self.parameterAsString(parameters, self.ORIGIN_FIELD, context)

		props["in_unlinks"] = self.UNLINKS
		props["in_unlinks_enabled"] = (self.parameterAsVectorLayer(parameters, self.UNLINKS, context) != None)
		
		props["rad_angular"] = self.parameterAsInt(parameters, self.ANGULAR_RADIUS, context)
		props["rad_angular_enabled"] = True if props["rad_angular"] else False
		props["rad_straight"] = self.parameterAsInt(parameters, self.STRAIGHT_LINE_RADIUS, context)
		props["rad_straight_enabled"] = True if props["rad_straight"] else False
		props["rad_walking"] = self.parameterAsInt(parameters, self.WALKING_RADIUS, context)
		props["rad_walking_enabled"] = True if props["rad_walking"] else False

		props["route_choice"] = self._ROUTE_CHOICE_MODES[self.parameterAsEnum(parameters, self.ROUTE_CHOICE, context)][1]

		props["dw_expression"] = self.parameterAsExpression(parameters, self.COST_EXPRESSION, context)
		props["dw_per_meter"] = self.parameterAsBool(parameters, self.COST_PER_METER, context)

		return props

	def name(self):
		return 'odbetweenness'

	def displayName(self):
		return 'OD Betweenness'

	def group(self):
		"""
		Returns the name of the group this algorithm belongs to. This string
		should be localised.
		"""
		return QgsProcessingAlgorithm.group(self)

	def groupId(self):
		"""
		Returns the unique ID of the group this algorithm belongs to. This
		string should be fixed for the algorithm, and must not be localised.
		The group id should be unique within each provider. Group id should
		contain lowercase alphanumeric characters only and no spaces or other
		formatting characters.
		"""
		return QgsProcessingAlgorithm.groupId(self)

	def createInstance(self):
		return ODBetweennessAlgorithm()

	def tr(self, string):
		return QCoreApplication.translate('Processing', string)        