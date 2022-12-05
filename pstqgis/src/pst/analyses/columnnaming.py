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
from builtins import object

class ColName(object):
	# Analyses
	REACH                     = "R"
	NETWORK_INTEGRATION       = "I"
	ANGULAR_INTEGRATION       = "AI"
	NETWORK_BETWEENNESS       = "B"
	ANGULAR_CHOICE            = "AC"
	ANGULAR_BETWEENNESS       = "AB"
	ATTRACTION_DISTANCE       = "AD"
	ATTRACTION_REACH          = "AR"
	ATTRACTION_BETWEENNESS    = "AT"
	SEGMENT_GROUP_INTEGRATION = "GI"
	ODBETWEENNESS             = "OD"

	# Distance mode
	DIST_STRAIGHT = "sl"
	DIST_WALKING  = "w"
	DIST_STEPS    = "s"
	DIST_ANGULAR  = "a"
	DIST_AXMETER  = "am"

	# Radius
	RADIUS_STRAIGHT = "l%s"
	RADIUS_WALKING  = "w%s"
	RADIUS_STEPS    = "s%s"
	RADIUS_ANGULAR  = "a%s"
	RADIUS_AXMETER  = "am%s"

	# Decay
	DECAY_NONE = None
	DECAY_FUNCTION = "f"

	# Weight
	WEIGHT_NONE   = None
	WEIGHT_LENGTH = "wl"
	# Also, custom names (i.e. attraction name) goes here as well.

	# Normalization
	NORM_NONE          = None
	NORM_SYNTAX_NAIN   = "A"
	NORM_SYNTAX_NACH   = "C"
	NORM_HILLIER       = "H"
	NORM_TURNER        = "T"
	NORM_STANDARD      = "S"

	# Extra
	EXTRA_NODE_COUNT       = "N"
	EXTRA_TOTAL_DEPTH      = "T"
	EXTRA_MEAN_DEPTH       = "M"
	EXTRA_LENGTH           = "L"
	EXTRA_AREA_CONVEX_HULL = "a"

	# Unit
	UNIT_SQUARE_METER     = "m"
	UNIT_SQUARE_KILOMETER = "k"
	UNIT_HECTARE          = "ha"


def GenColName(analysis, pst_distance_type=None, radii=None, decay=None, weight=None, normalization=None, extra=None, unit=None):
	name = analysis
	if pst_distance_type is not None:
		name += PSTADistanceTypeToString(pst_distance_type)
	if radii is not None:
		name += RadiiToString(radii)
	if decay is not None:
		name += decay
	if weight is not None:
		name += weight
	if normalization is not None:
		name += normalization
	if extra is not None:
		name += extra
	if unit is not None:
		name += unit
	return name

def FormatInteger(value):
	value = int(value)
	if value > 0 and value % 1000 == 0:
		return str(int(value / 1000)) + 'k'
	return str(value)

def RadiiToString(radii):
	name = ''
	if radii.hasStraight():
		name += ColName.RADIUS_STRAIGHT % FormatInteger(radii.straight())
	if radii.hasWalking():
		name += ColName.RADIUS_WALKING  % FormatInteger(radii.walking())
	if radii.hasSteps():
		name += ColName.RADIUS_STEPS    % FormatInteger(radii.steps())
	if radii.hasAngular():
		name += ColName.RADIUS_ANGULAR  % FormatInteger(radii.angular())
	if radii.hasAxmeter():
		name += ColName.RADIUS_AXMETER  % FormatInteger(radii.axmeter())
	return name

PSTA_DISTANCE_TYPE_TO_STRING = None
def PSTADistanceTypeToString(distance_type):
	global PSTA_DISTANCE_TYPE_TO_STRING
	if PSTA_DISTANCE_TYPE_TO_STRING is None:
		from pstalgo import DistanceType
		PSTA_DISTANCE_TYPE_TO_STRING = {
			DistanceType.STRAIGHT : ColName.DIST_STRAIGHT,
			DistanceType.WALKING  : ColName.DIST_WALKING,
			DistanceType.STEPS    : ColName.DIST_STEPS,
			DistanceType.ANGULAR  : ColName.DIST_ANGULAR,
			DistanceType.AXMETER  : ColName.DIST_AXMETER,
		}
	text = PSTA_DISTANCE_TYPE_TO_STRING.get(distance_type)
	if text is None:
		raise Exception("Unknown distance type #%d" % distance_type)
	return text