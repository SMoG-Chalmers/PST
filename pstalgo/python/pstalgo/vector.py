"""
Copyright 2019 Meta Berghauser Pont

This file is part of PST.

PST is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. The GNU General Public License
is intended to guarantee your freedom to share and change all versions
of a program--to make sure it remains free software for all its users.

PST is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PST. If not, see <http://www.gnu.org/licenses/>.
"""

import ctypes

class Vector(object):
	def __init__(self, ctype, max_size, allocator, initial_size=0):
		self._ctype = ctype
		self._ptr = allocator.alloc(ctype, max_size)
		self._max_size = max_size
		self._size = 0
		self.resize(initial_size)

	def clear(self):
		self._size = 0

	def elemtype(self):
		return self._ctype

	def clone(self, allocator):
		v = Vector(self._ctype, self._max_size, allocator, self._size)
		for i in range(self._size):
			v._ptr[i] = _ptr[i]
		return v

	def append(self, value):
		assert(self._size < self._max_size)
		self._ptr[self._size] = value
		self._size += 1

	def resize(self, size):
		assert(size <= self._max_size)
		self._size = size

	# DEPRECATED! Use len() instead
	def size(self):
		return self._size

	# DEPRECATED! Use [] operator instead
	def at(self, index):
		assert(index < self._size)
		return self._ptr[index]

	# DEPRECATED! Use [] operator instead
	def set(self, index, value):
		assert(index < self._size)
		self._ptr[index] = value

	def values(self):
		def iter():
			i = 0
			while i < self._size:
				yield self._ptr[i]
				i += 1
		return iter()

	def ptr(self):
		return self._ptr

	def __len__(self):
		return self._size

	def __getitem__(self, index):
		assert(index < self._size)
		return self._ptr[index]

	def __setitem__(self, index, value):
		assert(index < self._size)
		self._ptr[index] = value
