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

from .angularintegration import AngularIntegration, AngularIntegrationNormalize, AngularIntegrationNormalizeLengthWeight, AngularIntegrationSyntaxNormalize, AngularIntegrationSyntaxNormalizeLengthWeight, AngularIntegrationHillierNormalize, AngularIntegrationHillierNormalizeLengthWeight
from .attractiondistance import AttractionDistance
from .attractionreach import AttractionReach, AttractionScoreAccumulationMode, AttractionWeightFunction, AttractionDistributionFunc, AttractionCollectionFunc
from .calculateisovists import CreateIsovistContext, CalculateIsovist, IsovistContextGeometry
from .callbacktest import CallbackTest
from .createbufferpolygons import CompareResults, CompareResultsMode, RasterToPolygons
from .creategraph import CreateGraph, FreeGraph, GetGraphInfo, GetGraphLineLengths, GetGraphCrossingCoords, CreateSegmentGraph, FreeSegmentGraph, CreateSegmentGroupGraph, FreeSegmentGroupGraph
from .createjunctions import CreateJunctions
from .createsegmentmap import CreateSegmentMap
from .log import ErrorLevel, FormatLogMessage, RegisterLogCallback, UnregisterLogCallback
from .networkintegration import NetworkIntegration
from .angularchoice import AngularChoice, AngularChoiceNormalize, AngularChoiceSyntaxNormalize
from .odbetweenness import ODBetweenness, ODBDestinationMode
from .raster import RasterFormat, GetRasterData
from .reach import Reach
from .segmentbetweenness import SegmentBetweenness, BetweennessNormalize, BetweennessSyntaxNormalize
from .fastsegmentbetweenness import FastSegmentBetweenness
from .segmentgrouping import SegmentGrouping
from .segmentgroupintegration import SegmentGroupIntegration
from .common import Free, DistanceType, Radii, StandardNormalize, OriginType, RoadNetworkType
from .vector import Vector

# TODO: Possibly move out of pstalgo module? This should probably be in an analysis module instead.
def CreateAnalysisDelegateCallbackWrapper(delegate):
	def callback(status, progress):
		if status is not None:
			delegate.setStatus(status)
		delegate.setProgress(progress)
		return 1 if delegate.getCancel() else 0
	return callback