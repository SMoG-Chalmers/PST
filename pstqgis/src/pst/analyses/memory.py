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

from __future__ import print_function
from builtins import str
from builtins import range
from builtins import object
import ctypes

DEBUG_OUTPUT=False

class StackAllocator(object):

	def __init__(self, min_block_size=64*1024*1024):
		self._minBlockSize = min_block_size
		self._blocks = []
		self._dbgPeakUsage = 0

	def state(self):
		return tuple([block.state() for block in self._blocks])

	def reset(self):
		self.restore(())

	def restore(self, state):
		if DEBUG_OUTPUT:
			print("StackAllocator: Restore " + str(state))
		for i in range(len(state)):
			self._blocks[i].restore(state[i])
		for i in range(len(state), len(self._blocks)):
			self._blocks[i].reset()

	def alloc(self, ctype, elem_count):
		size_bytes = int(elem_count * ctypes.sizeof(ctype))
		for block in self._blocks:
			if size_bytes <= block.availBytes():
				return ctypes.cast(block.alloc(size_bytes), ctypes.POINTER(ctype))
		while self._minBlockSize < size_bytes:
			self._minBlockSize *= 2
		new_block = self._allocBlock(self._minBlockSize)
		self._minBlockSize *= 2  # We want next block to be at least double the size
		self._blocks.append(new_block)
		return ctypes.cast(new_block.alloc(size_bytes), ctypes.POINTER(ctype))

	def _allocBlock(self, size_bytes):
		if DEBUG_OUTPUT:
			print("StackAllocator: Allocating block (%d bytes)"%(size_bytes))
		return StackAllocatorBlock((ctypes.c_double*int(size_bytes/8))(), size_bytes)


class StackAllocatorBlock(object):
	def __init__(self, arr, size_bytes):
		self._arr = arr
		self._sizeBytes = size_bytes
		self._used = 0
		self._dbgMarkers = []

	def reset(self):
		self._used = 0
		if DEBUG_OUTPUT:
			print("StackAllocatorBlock: Reset")
		self._dbgCheckMarkers()

	def state(self):
		return self._used

	def availBytes(self):
		return self._sizeBytes - self._used - 8  # 8 for debug marker

	def alloc(self, size_bytes):
		if DEBUG_OUTPUT:
			print("StackAllocatorBlock: Allocating %d bytes at 0x%.8X-0x%.8X"%(size_bytes, self._used, self._used+size_bytes))
		assert(self.availBytes() >= size_bytes)
		size_rounded = int((size_bytes+7)/8)*8
		addr = self._addrAt(self._used)
		self._used += size_rounded
		self._dbgAddMarker()
		return addr

	def restore(self, state):
		self._used = state
		if DEBUG_OUTPUT:
			print("StackAllocatorBlock: Restore 0x%.8X"%self._used)
		self._dbgCheckMarkers()

	def _addrAt(self, byte_offset):
		assert(byte_offset >= 0 and byte_offset <= self._sizeBytes)
		return ctypes.addressof(self._arr) + byte_offset

	def _dbgAddMarker(self):
		""" Add 8 bytes with value 0xDEADBEEFDEADBEEF directly after current allocation """
		ptr = ctypes.cast(self._addrAt(self._used), ctypes.POINTER(ctypes.c_uint))
		ptr[0] = 0xDEADBEEF
		ptr[1] = 0xDEADBEEF
		self._dbgMarkers.append(self._used)
		self._used += 8

	def _dbgCheckMarkers(self):
		""" Check if the markers added with _dbgAddMarker for freed blocks are still intact """
		while self._dbgMarkers and self._dbgMarkers[-1] >= self._used:
			marker_pos = self._dbgMarkers.pop()
			ptr = ctypes.cast(self._addrAt(marker_pos), ctypes.POINTER(ctypes.c_uint))
			if 0xDEADBEEF != ptr[0] or 0xDEADBEEF != ptr[1]:
				raise Exception("StackAllocator out-of-bounds write detected at 0x%.8X (data: 0x%.8X 0x%.8x)" % (marker_pos, ptr[0], ptr[1]))
			if DEBUG_OUTPUT:
				print("StackAllocator: Marker at 0x%.8X was intact" % marker_pos)


stack_allocator = StackAllocator(64*1024*1024)