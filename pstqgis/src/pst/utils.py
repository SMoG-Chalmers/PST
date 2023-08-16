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

def lerp(a, b, t):
	return a + (b - a) * t

def lerpIntegerTuple(a, b, t):
	return tuple(int(round(lerp(a[i], b[i], t))) for i in len(a))

def tupleFromHtmlColor(htmlColor):
	firstCharIndex = 1 if htmlColor[0] == '#' else 0
	colorCharCount = len(htmlColor) - firstCharIndex
	if colorCharCount == 3 or colorCharCount == 4:
		return tuple(int(htmlColor[firstCharIndex+i],16)*16 for i in range(colorCharCount))
	elif colorCharCount == 6 or colorCharCount == 8:
		return tuple(int(htmlColor[firstCharIndex+(i*2):firstCharIndex+((i+1)*2)],16) for i in range(int(colorCharCount/2)))
	raise TypeError("Invalid HTML color format")