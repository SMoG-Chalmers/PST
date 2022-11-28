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
from builtins import object
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QApplication, QLabel, QMessageBox, QProgressBar, QVBoxLayout, QWizardPage
from ...analyses import AnalysisException

class ProgressPage(QWizardPage):
	def __init__(self, title = "Performing analysis", sub_title = " "):
		QWizardPage.__init__(self)
		self._task = None
		self._done = False
		self.setTitle(title);
		self.setSubTitle(sub_title);
		self.createWidgets()

	def createWidgets(self):
		vlayout = QVBoxLayout()

		vlayout.addStretch(1);

		self._statusLabel = QLabel("")
		vlayout.addWidget(self._statusLabel)

		self._progressBar = QProgressBar()
		self._progressBar.setMaximum(1000)
		vlayout.addWidget(self._progressBar)

		self._etaLabel = QLabel("")
		vlayout.addWidget(self._etaLabel)

		vlayout.addStretch(1);

		self.setLayout(vlayout);

	# QWizardPage overrides
	def initializePage(self):
		self._done = False
		self._statusLabel.setText("")
		self._progressBar.setValue(0)
		self._etaLabel.setText("")
		self.startDeferred()

	# QWizardPage override
	def isComplete(self):
		return self._done

	def start(self):
		props = self.wizard().properties()
		task = self.wizard().createTask(props)
		if not task:
			self._done = True
			self.finish()
			return
		self._task = task
		#task.terminated.connect(self.onTaskTerminated)
		#task.finished.connect(self.onTaskFinished)
		#task.statusChanged.connect(self.onTaskStatusChanged)
		#task.progressChanged.connect(self.onTaskProgressChanged)
		#if THREADED:
		#	task.start()   # Run as separate thread
		dlgt = AnalysisDelegateFilter(self)
		try:
			task.run(dlgt)
		except AnalysisException as e:
			QMessageBox.critical(self, "PST Error", str(e))
			self.wizard().restart()
			return
		dlgt.outputStats()
		self.finish()

	def startDeferred(self):
		QTimer.singleShot(0, self.start)

	def finish(self):
		self._task = None
		self._done = True
		self.completeChanged.emit()
		self.wizard().next()

	# AnalysisDelegate interface
	def setProgress(self, progress):
		self._progressBar.setValue(1000 * progress)
		QApplication.processEvents()  # UI update

	# AnalysisDelegate interface
	def setStatus(self, text):
		self._statusLabel.setText(text + "...")
		QApplication.processEvents()  # UI update

	# AnalysisDelegate interface
	def getCancel(self):
		return False

	# slot, unused
	def onTaskTerminated(self):
		print("ProgressPage.onTaskTerminated")
		# TODO: Show error popup
		self.finish()

	# slot, unused
	def onTaskFinished(self):
		print("ProgressPage.onTaskFinished")
		self.finish()

	# slot, unused
	def onTaskStatusChanged(self, text):
		self.setStatus(text)

	# slot, unused
	def onTaskProgressChanged(self, progress):
		self.setProgress(progress)


import time
class AnalysisDelegateFilter(object):
	def __init__(self, delegate, min_interval_sec=0.1):
		self._delegate = delegate
		self._minIntervalSec = min_interval_sec
		self._tsLastUpdate = -1
		# DEBUG
		self._statusText = None
		self._tsLastStatus = -1
		# DEBUG

	def outputStats(self):
		pass

	# AnalysisDelegate interface
	def setProgress(self, progress):
		if self._testFrequencyFilter():
			self._delegate.setProgress(progress)

	# AnalysisDelegate interface
	def setStatus(self, text):
		# DEBUG
		ts = time.perf_counter()
		if self._statusText:
			print("%s (%.3f sec)" % (self._statusText, ts - self._tsLastStatus))
		self._statusText = text
		self._tsLastStatus = ts
		# DEBUG

		self._delegate.setStatus(text)
		self._resetFrequencyFilter()

	# AnalysisDelegate interface
	def getCancel(self):
		return self._delegate.getCancel()

	def _resetFrequencyFilter(self):
		self._tsLastUpdate = -1

	def _testFrequencyFilter(self):
		ts = time.perf_counter()
		if ts - self._tsLastUpdate < self._minIntervalSec:
			return False
		self._tsLastUpdate = ts;
		return True