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

import sys, os, unittest

def GetThisFilePath():
    import inspect
    return os.path.abspath(inspect.stack()[0][1])

def ResolvePathRelativeToThisFile(rel_path):
    return os.path.abspath(os.path.join(os.path.dirname(GetThisFilePath()), rel_path))

# Import pstalgo
sys.path.append(ResolvePathRelativeToThisFile("../python"))
import pstalgo

def MyLogCallback(error_level, domain, msg):
    print()
    print(pstalgo.FormatLogMessage(error_level, domain, msg))

if __name__ == '__main__':
    # It is important that we keep a reference to the callback handle, or callback object might get freed (causing crash)!
    callback_handle = pstalgo.RegisterLogCallback(MyLogCallback)

    testsuite = unittest.TestLoader().discover('.')
    unittest.TextTestRunner(verbosity=2).run(testsuite)

    pstalgo.UnregisterLogCallback(callback_handle)
