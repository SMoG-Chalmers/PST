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

import unittest
import pstalgo

class TestCallback(unittest.TestCase):

    STATUS_TEXT = "Status test string"
    PROGRESS_VALUE = 0.5
    RETURN_VALUE = 123

    def callback1(self, status, progress):
        if status is not None:
            self.status = status
        else:
            self.progress = progress
        return False  # 0 means continue

    def callback2(self, status, progress):
        return True  # means cancel

    def test_callback(self):
        return_value = pstalgo.CallbackTest(self.STATUS_TEXT, self.PROGRESS_VALUE, self.RETURN_VALUE, self.callback1)
        self.assertEqual(self.status, self.STATUS_TEXT)
        self.assertEqual(self.progress, self.PROGRESS_VALUE)
        self.assertEqual(return_value, self.RETURN_VALUE)

    def test_cancel(self):
        return_value = pstalgo.CallbackTest(self.STATUS_TEXT, self.PROGRESS_VALUE, self.RETURN_VALUE, self.callback2)
        self.assertEqual(return_value, 0)