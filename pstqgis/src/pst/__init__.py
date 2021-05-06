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

from __future__ import absolute_import

# Load Metadata
metadata = None
def MetaData():
	global metadata
	if metadata is None:
		import os, configparser
		my_dir = os.path.dirname(os.path.abspath(__file__))
		metadata_path = os.path.join(my_dir, 'metadata.txt')
		metadata_contents = open(metadata_path, encoding="utf-8").read()
		metadata = configparser.ConfigParser()
		metadata.read_string(metadata_contents)
	return metadata

APP_TITLE = MetaData()['general']['name']

def GetPSTAlgoPath():
	import os
	path = os.environ.get('PSTALGO_PATH')
	if path is not None:
		return os.path.join(path, 'python')
	import inspect
	folder_of_this_file = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	return os.path.join(folder_of_this_file, 'pstalgo', 'python')

# Add PSTAlgo to sys path
import sys
PSTALGO_PATH = GetPSTAlgoPath()
if PSTALGO_PATH not in sys.path:
	sys.path.append(PSTALGO_PATH)

def classFactory(iface):
  from .main import PSTPlugin
  return PSTPlugin(iface)