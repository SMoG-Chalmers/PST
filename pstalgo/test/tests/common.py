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

def IsRoughlyEqual(v0, v1, max_rel_diff=0.0001):
	if 0 == v0: 
		return abs(v1-v0) <= max_rel_diff
	return abs((v1-v0)/v0) <= max_rel_diff

def IsArrayRoughlyEqual(a0, a1, max_rel_diff=0.0001):
	if len(a0) != len(a1):
		raise Exception("Array lengths do not match, %d != %d" % (len(a0), len(a1)))
	for i in range(len(a0)):
		if not IsRoughlyEqual(a0[i], a1[i], max_rel_diff):
			return False
	return True