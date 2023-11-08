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

from qgis.PyQt.QtCore import (
	Qt,
	QAbstractItemModel,
	QModelIndex,	
	QSize,
)

from qgis.PyQt.QtWidgets import (
	QDialog,
	QHBoxLayout,
	QPushButton,
	QTreeView,
	QVBoxLayout,
	QWidget,	
)

from .common import allLayers, isPointLayer, isPolygonLayer


def iconFromLayer(qgisLayer, width=16, height=16):
	renderer = qgisLayer.renderer()
	if renderer.type() == "singleSymbol":
		symbol = renderer.symbol()
		pixmap = symbol.asImage(QSize(width, height))
		#return QIcon(pixmap)
		return pixmap
	return None


class LayerSelectionItem:
	def __init__(self, qgisLayer, selected=False, obstacle=False):
		self.qgisLayer = qgisLayer
		self.selected = selected
		self.obstacle = obstacle
		self.icon = iconFromLayer(qgisLayer)


class LayerSelectionDialog(QDialog):
	def __init__(self, parent, layerSelectionItems):
		QWidget.__init__(self, parent, Qt.Tool)

		self.setWindowTitle("Select Layers")

		vlayout = QVBoxLayout()

		self._list = LayerSelectionView(self, layerSelectionItems)
		vlayout.addWidget(self._list)

		vlayout.addSpacing(10)

		hlayout = QHBoxLayout()
		self._okButton = QPushButton("OK")
		self._okButton.clicked.connect(self.accept)
		hlayout.addWidget(self._okButton)
		self._cancelButton = QPushButton("Cancel")
		self._cancelButton.clicked.connect(self.reject)
		hlayout.addWidget(self._cancelButton)
		vlayout.addLayout(hlayout)

		self.setLayout(vlayout)


class LayerSelectionView(QTreeView):
	def __init__(self, parent, layerSelectionItems):
		QTreeView.__init__(self, parent)
		self.setIndentation(0)  # Hide expand/collapse decorators
		self._model = LayerSelectionItemModel(self, layerSelectionItems)
		self.setModel(self._model)


class LayerSelectionItemModel(QAbstractItemModel):
	def __init__(self, parent, items=None):
		super().__init__(parent)
		if items is None:
			items = [LayerSelectionItem(qgisLayer) for qgisLayer in allLayers() if isPointLayer(qgisLayer) or isPolygonLayer(qgisLayer)]
		self._items = items

	def items(self):
		return self._items

	def setItems(self, layerSelectionItems):
		self.beginResetModel()
		self._items = layerSelectionItems
		self.endResetModel()

	def rowCount(self, parent=QModelIndex()):
		if parent.isValid():
			return 0  # This is a flat list; no child items.
		return len(self._items)

	def columnCount(self, parent=QModelIndex()):
		if parent.isValid():
			return 0  # This is a flat list; no child items.
		return 2

	def data(self, index, role=Qt.DisplayRole):
		# if not index.isValid() or \
		#	not (0 <= index.row() < len(self._data)) or \
		#	not (0 <= index.column() < len(self._data[0])):
		#	 return None

		columnIndex = index.column()
		rowIndex = index.row()

		if 0 == columnIndex:
			if role == Qt.DisplayRole:
				return self._items[rowIndex].qgisLayer.name()
			if role == Qt.CheckStateRole:
				return Qt.Checked if self._items[rowIndex].selected else Qt.Unchecked
			if role == Qt.DecorationRole:
				return self._items[rowIndex].icon
		elif 1 == columnIndex:
			if role == Qt.CheckStateRole:
				return Qt.Checked if self._items[rowIndex].obstacle else Qt.Unchecked

		return None

	def setData(self, index, value, role=Qt.EditRole):
		columnIndex = index.column()
		rowIndex = index.row()

		if role == Qt.CheckStateRole:
			checked = (value == Qt.Checked)
			if columnIndex == 0:
				self._items[rowIndex].selected = checked
				return True
			if columnIndex == 1:
				self._items[rowIndex].obstacle = checked
				return True

		return False

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role == Qt.DisplayRole and orientation == Qt.Horizontal:
			if section == 0:
				return "Layer"
			elif section == 1:
				return "Obstacle"
		return None

	def index(self, row, column, parent=QModelIndex()):
		if parent.isValid() or row < 0 or row >= self.rowCount() or column < 0 or column >= self.columnCount():
			return QModelIndex()
		return self.createIndex(row, column)

	def parent(self, index=QModelIndex()):
		return QModelIndex()  # This is a flat list; no parent.

	def flags(self, index):
		if not index.isValid():
			return Qt.NoItemFlags
		#flags = Qt.ItemIsSelectable
		flags = Qt.NoItemFlags
		flags |= Qt.ItemIsUserCheckable
		if index.column() != 1 or isPolygonLayer(self._items[index.row()].qgisLayer):
			flags |= Qt.ItemIsEnabled
		# if index.column() != 1 or isPolygonLayer(self._items[index.row()].qgisLayer):
		# 	flags |= Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
		return flags
