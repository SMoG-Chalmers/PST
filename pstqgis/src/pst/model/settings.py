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

from builtins import range
from builtins import object
import os, sys, copy, json

SETTINGS_DIR = 'pstqgis'
SETTINGS_FILE = 'settings.json'

def GetUserSettingsDir(app_name):
	import platform
	if 'Windows' == platform.system():
		return os.path.join(os.getenv('APPDATA'), app_name)
	elif 'Darwin' == platform.system():
		return os.path.expanduser('~/.' + app_name)  # NOTE: We prepend a dot here to also make the folder hidden
	raise Exception("Unsupported plataform: %s" & platform.system())

class Settings(object):
	def __init__(self):
		self._props = {}

	def get(self, name):
		p = self._props
		for n in name.split('/'):
			p = p.get(n)
			if p is None:
				return None
		return copy.deepcopy(p)

	def set(self, name, prop):
		p = self._props
		nodes = name.split('/')
		for i in range(len(nodes)-1):
			n = nodes[i]
			t = p.get(n)
			if t is None:
				t = {}
				p[n] = t
			p = t
		p[nodes[-1]] = copy.deepcopy(prop)

	def save(self):
		settings_directory = GetUserSettingsDir(SETTINGS_DIR)
		if not os.path.exists(settings_directory):
			os.makedirs(settings_directory)
		settings_path = os.path.join(settings_directory, SETTINGS_FILE)
		with open(settings_path, 'w') as f:
			f.write(json.dumps(self._props, sort_keys=True, indent=4, separators=(',', ': ')))

	def load(self):
		self._props = {}
		settings_path = os.path.join(GetUserSettingsDir(SETTINGS_DIR), SETTINGS_FILE)
		if os.path.exists(settings_path):
			try:
				p = None
				with open(settings_path, 'r') as f:
					p = json.loads(f.read())
				if type(p) == dict:
					self._props = p
			except:
				pass