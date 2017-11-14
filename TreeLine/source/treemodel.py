#!/usr/bin/env python3

#******************************************************************************
# treemodel.py, provides a class for the tree's data
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import copy
import io
from xml.etree import ElementTree
from PyQt4 import QtCore, QtGui
import treeformats
import nodeformat
import treenode
import treeopener
import undo
import linkref
import globalref

defaultRootName = _('Main')


class TreeModel(QtCore.QAbstractItemModel):
    """Class containing the tree's model/document information
    
    Stores document information and interfaces with view classes.
    """
    allModified = QtCore.pyqtSignal()
    nodeTitleModified = QtCore.pyqtSignal(bool)
    storedDragNodes = []
    storedDragModel = None
    def __init__(self, newFile=False, parent=None):
        """Initialize a TreeModel.
        
        Arguments:
            newFile -- if true, adds default root node and formats
            parent -- optional QObject parent for the model
        """
        super().__init__(parent)
        self.root = None
        self.configDialogFormats = None
        self.undoList = None
        self.redoList = None
        self.nodeIdDict = {}
        self.linkRefCollect = linkref.LinkRefCollection()
        self.mathZeroBlanks = True
        if newFile:
            self.formats = treeformats.TreeFormats(True)
            self.root = treenode.TreeNode(None, treeformats.defaultTypeName,
                                          self)
            self.root.setTitle(defaultRootName)
        else:
            self.formats = treeformats.TreeFormats()
        self.fileInfoNode = treenode.TreeNode(None,
                                              self.formats.fileInfoFormat.name,
                                              self)

    def index(self, row, column, parentIndex):
        """Returns the index of a node in the model based on the parent index.

        Uses createIndex() to generate the model indices.
        Arguments:
            row         -- the row of the model node
            column      -- the column (always 0 for now)
            parentIndex -- the parent's model index in the tree structure
        """
        if not parentIndex.isValid():
            return self.createIndex(row, column, self.root)
        parent = parentIndex.internalPointer()
        try:
            return self.createIndex(row, column, parent.childList[row])
        except IndexError:
            return QtCore.QModelIndex()

    def parent(self, index):
        """Returns the parent model index of the node at the given index.

        Arguments:
            index -- the child model index
        """
        try:
            parent = index.internalPointer().parent
            return self.createIndex(parent.row(), 0, parent)
        except AttributeError:
            return QtCore.QModelIndex()

    def rowCount(self, parentIndex):
        """Returns the number of children for the node at the given index.

        Arguments:
            parentIndex -- the parent model index
        """
        try:
            parent = parentIndex.internalPointer()
            return parent.numChildren()
        except AttributeError:
            return 1  # a single root node has no valid parentIndex

    def columnCount(self, parentIndex):
        """The number of columns -- always 1 for now.
        """
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Return the output data for the node in the given role.

        Arguments:
            index -- the node's model index
            role  -- the type of data requested
        """
        node = index.internalPointer()
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return node.title()
        if (role == QtCore.Qt.DecorationRole and
            globalref.genOptions.getValue('ShowTreeIcons')):
            return globalref.treeIcons.getIcon(node.nodeFormat().iconName,
                                               True)
        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Set node title after edit operation.

        Return True on success.
        Arguments:
            index -- the node's model index
            value -- the string result of the editing
            role -- the edit role of the data
        """
        if role != QtCore.Qt.EditRole:
            return super().setData(index, value, role)
        node = index.internalPointer()
        dataUndo = undo.DataUndo(self.undoList, node)
        if node.setTitle(value):
            self.dataChanged.emit(index, index)
            self.nodeTitleModified.emit(True)
            return True
        self.undoList.removeLastUndo(dataUndo)
        return False

    def flags(self, index):
        """Return the flags for the node at the given index.

        Arguments:
            index -- the node's model index
        """
        return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled |
                QtCore.Qt.ItemIsDropEnabled)

    def mimeData(self, indexList):
        """Return a mime data object for the given node index branches.

        Arguments:
            indexList -- a list of node indexes to convert
        """
        allNodes = [index.internalPointer() for index in indexList]
        nodes = []
        # accept only nodes on top of unique branches
        for node in allNodes:
            parent = node.parent
            while parent and parent not in allNodes:
                parent = parent.parent
            if not parent:
                nodes.append(node)
        TreeModel.storedDragNodes = nodes
        TreeModel.storedDragModel = self
        dummyFormat = None
        if len(nodes) > 1:
            dummyFormat = self.formats.addDummyRootType()
            root = treenode.TreeNode(None, dummyFormat.name, self)
            for node in nodes:
                root.childList.append(copy.copy(node))
                root.childList[-1].parent = root
        else:
            root = nodes[0]
        text = ElementTree.tostring(root.elementXml({dummyFormat}, True,
                                                    False), 'utf-8')
        self.formats.removeDummyRootType()
        mime = QtCore.QMimeData()
        mime.setData('text/xml', text)
        return mime

    def mimeTypes(self):
        """Return a list of supported mime types for model objects.
        """
        return ['text/xml']

    def supportedDropActions(self):
        """Return drop action enum values that are supported by this model.
        """
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def dropMimeData(self, mimeData, dropAction, row, column, index):
        """Decode mime data and add as a child node to the given index.

        Return True if successful.
        Arguments:
            mimeData -- data for the node branch to be added
            dropAction -- a drop type enum value
            row -- a row number for the drop location (ignored, can be 0)
            column -- the coumn number for the drop location (normally 0)
            index -- the index of the parent node for the drop

        """
        parent = index.internalPointer()
        if not parent:
            return False
        isMove = (dropAction == QtCore.Qt.MoveAction and
                  TreeModel.storedDragModel == self)
        undoParents = [parent]
        if isMove:
            moveParents = {node.parent for node in TreeModel.storedDragNodes}
            undoParents.extend(list(moveParents))
        undoObj = undo.BranchFormatUndo(self.undoList, undoParents,
                                        self.formats)
        if self.addMimeData(mimeData, parent, row):
            if isMove:
                for node in TreeModel.storedDragNodes:
                    node.delete()
            self.allModified.emit()
            return True
        self.undoList.removeLastUndo(undoObj)
        return False

    def addMimeData(self, mimeData, parent, position=-1):
        """Decode mime data and add as a child node to the given parent.

        Return True if successful.
        Arguments:
            mimeData -- data for the node branch to be added
            parent -- the parent node for the drop
            position -- the location to insert (-1 is appended)
        """
        text = str(mimeData.data('text/xml'), 'utf-8')
        opener = treeopener.TreeOpener()
        try:
            newModel = opener.readFile(io.StringIO(text))
        except treeopener.ParseError:
            return False
        if newModel.root.formatName == treeformats.dummyRootTypeName:
            newNodes = newModel.root.childList
        else:
            newNodes = [newModel.root]
        for format in newModel.formats.values():
            self.formats.addTypeIfMissing(format)
        for node in newNodes:
            if position >= 0:
                parent.childList.insert(position, node)
                position += 1
            else:
                parent.childList.append(node)
            node.parent = parent
            for child in node.descendantGen():
                child.modelRef = self
                child.setUniqueId(True)
        self.formats.removeDummyRootType()
        return True

    def getConfigDialogFormats(self, forceReset=False):
        """Return duplicate formats for use in the config dialog.

        Arguments:
            forceReset -- if True, sets duplicate formats back to original
        """
        if not self.configDialogFormats or forceReset:
            self.configDialogFormats = copy.deepcopy(self.formats)
        return self.configDialogFormats

    def applyConfigDialogFormats(self, addUndo=True):
        """Replace the formats with the duplicates and signal for view update.

        Also updates all nodes for changed type and field names.
        """
        self.configDialogFormats.updateMathFieldRefs()
        if addUndo:
            undo.FormatUndo(self.undoList, self.formats,
                            self.configDialogFormats)
        self.formats = self.configDialogFormats
        self.getConfigDialogFormats(True)
        if self.formats.typeRenameDict or self.formats.fieldRenameDict:
            for node in self.root.descendantGen():
                node.formatName = (self.formats.typeRenameDict.
                                   get(node.formatName, node.formatName))
                fieldRenameDict = (self.formats.fieldRenameDict.
                                   get(node.formatName, {}))
                for oldName, newName in fieldRenameDict.items():
                    if oldName in node.data:
                        node.data[newName] = node.data[oldName]
                        del node.data[oldName]
        self.formats.typeRenameDict = {}
        self.formats.fieldRenameDict = {}
        if self.formats.changedIdFieldTypes:
            for node in self.root.descendantGen():
                if node.nodeFormat() in self.formats.changedIdFieldTypes:
                    node.updateUniqueId()
            self.formats.changedIdFieldTypes = set()
        if self.formats.emptiedMathDict:
            for node in self.root.descendantGen():
                for fieldName in self.formats.emptiedMathDict.get(node.
                                                                  formatName,
                                                                  set()):
                    node.data.pop(fieldName, None)
            self.formats.emptiedMathDict = {}
        self.allModified.emit()
