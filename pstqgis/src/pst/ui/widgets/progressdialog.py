from qgis.PyQt.QtWidgets import (
	QApplication,
	QDialog,
	QLabel,
	QProgressBar,
	QVBoxLayout,
)

MAX_PROGRESS = 10000

class ProgressDialog(QDialog):
	def __init__(self, title = "Progress", text = "", parent = None):
		QDialog.__init__(self, parent)
		self.setWindowTitle(title)

		self._app = QApplication.instance()

		vlayout = QVBoxLayout()

		self._label = QLabel(text, self)
		vlayout.addWidget(self._label)

		self._progressBar = QProgressBar(self)
		self._progressBar.setMinimum(0)
		self._progressBar.setMaximum(MAX_PROGRESS)
		vlayout.addWidget(self._progressBar)

		self.setLayout(vlayout)

	def setProgress(self, progress):
		self._progressBar.setValue(int(progress * MAX_PROGRESS + 0.5))
		self._app.processEvents()

	def setText(self, text):
		self._label.setText(text)
		self._app.processEvents()