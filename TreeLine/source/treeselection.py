#!/usr/bin/env python3

#******************************************************************************
# treeselection.py, provides a class for the tree view's selection model
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import operator
from PyQt4 import QtCore, QtGui
import treenodelist


_maxHistoryLength = 10

class TreeSelection(QtGui.QItemSelectionModel):
    """Class override for the tree view's selection model.

    Provides methods for easier access to selected nodes.
    """
    def __init__(self, model, parent=None):
        """Initialize the selection model.

        Arguments:
            model -- the initial model for view data
            parent -- the parent tree view
        """
        super().__init__(model, parent)
        self.tempExpandedNodes = []
        self.previousNodes = []
        self.nextNodes = []
        self.restoreFlag = False
        self.selectionChanged.connect(self.updateSelectLists)

    def selectedNodes(self):
        """Return a TreeNodeList of the currently selected tree nodes.
        """
        return treenodelist.TreeNodeList([index.internalPointer() for index in
                                          self.selectedIndexes()])

    def currentNode(self):
        """Return the current tree node.
        """
        return self.currentIndex().internalPointer()

    def uniqueBranches(self):
        """Return a TreeNodeList of selected nodes on top of unique branches.

        Eliminate nodes that are already descendants of other selected nodes.
        """
        result = treenodelist.TreeNodeList()
        selectedNodes = self.selectedNodes()
        for node in selectedNodes:
            parent = node.parent
            while parent and parent not in selectedNodes:
                parent = parent.parent
            if not parent:
                result.append(node)
        return result

    def selectNode(self, node, signalUpdate=True, expandParents=False):
        """Clear the current selection and select the given node.

        Arguments:
            node -- the TreeNode to be selected
            signalUpdate -- if False, block normal right-view update signals
            expandParents -- open parent nodes to make selection visible
        """
        expandedNodes = []
        if expandParents:
            for expNode in self.tempExpandedNodes:
                expNode.collapseInView()
            self.tempExpandedNodes = []
            parent = node.parent
            while parent:
                if not parent.isExpanded():
                    parent.expandInView()
                    expandedNodes.append(parent)
                parent = parent.parent
        if not signalUpdate:
            self.blockSignals(True)
            self.addToHistory([node])
        self.clear()
        self.setCurrentIndex(node.index(), QtGui.QItemSelectionModel.Select)
        self.blockSignals(False)
        self.tempExpandedNodes = expandedNodes

    def selectNodes(self, nodeList, signalUpdate=True, expandParents=False):
        """Clear the current selection and select the nodes in the given list.

        Arguments:
            nodeList -- a list of nodes to be selected.
            signalUpdate -- if False, block normal right-view update signals
            expandParents -- open parent nodes to make selection visible
        """
        expandedNodes = []
        if expandParents:
            for expNode in self.tempExpandedNodes:
                expNode.collapseInView()
            self.tempExpandedNodes = []
            for node in nodeList:
                parent = node.parent
                while parent:
                    if not parent.isExpanded():
                        parent.expandInView()
                        expandedNodes.append(parent)
                    parent = parent.parent
        if not signalUpdate:
            self.blockSignals(True)
            self.addToHistory(nodeList)
        self.clear()
        for node in nodeList:
            self.select(node.index(), QtGui.QItemSelectionModel.Select)
        if nodeList:
            self.setCurrentIndex(nodeList[0].index(),
                                 QtGui.QItemSelectionModel.Current)
        self.blockSignals(False)
        self.tempExpandedNodes = expandedNodes

    def selectNodeById(self, nodeId):
        """Select a node when given its unique ID and return True.

        Return False if not found.
        Arguments:
            nodeId -- the unique ID string for the node
        """
        try:
            self.selectNode(self.model().nodeIdDict[nodeId])
            return True
        except KeyError:
            return False

    def sortSelection(self):
        """Sorts the selection by tree position.
        """
        self.selectNodes(sorted(self.selectedNodes(),
                                key=operator.methodcaller('treePosSortKey')),
                         False)

    def addToHistory(self, nodes):
        """Add given nodes to previous select list.

        Arguments:
            nodes -- a list of nodes to be added
        """
        if nodes and not self.restoreFlag and (not self.previousNodes or
                                              nodes != self.previousNodes[-1]):
            self.previousNodes.append(nodes)
            if len(self.previousNodes) > _maxHistoryLength:
                del self.previousNodes[:2]
            self.nextNodes = []

    def restorePrevSelect(self):
        """Go back to the most recent saved selection.
        """
        self.validateHistory()
        if len(self.previousNodes) > 1:
            del self.previousNodes[-1]
            oldSelect = self.selectedNodes()
            if oldSelect and (not self.nextNodes or
                              oldSelect != self.nextNodes[-1]):
                self.nextNodes.append(oldSelect)
            self.restoreFlag = True
            self.selectNodes(self.previousNodes[-1], expandParents=True)
            self.restoreFlag = False

    def restoreNextSelect(self):
        """Go forward to the most recent saved selection.
        """
        self.validateHistory()
        if self.nextNodes:
            select = self.nextNodes.pop(-1)
            if select and (not self.previousNodes or
                           select != self.previousNodes[-1]):
                self.previousNodes.append(select)
            self.restoreFlag = True
            self.selectNodes(select, expandParents=True)
            self.restoreFlag = False

    def validateHistory(self):
        """Clear invalid items from history lists.
        """
        for histList in (self.previousNodes, self.nextNodes):
            for nodeList in histList:
                nodeList[:] = [node for node in nodeList if node.isValid()]
            histList[:] = [nodeList for nodeList in histList if nodeList]

    def updateSelectLists(self):
        """Update history and clear temp expanded nodes after a select change.
        """
        self.addToHistory(self.selectedNodes())
        self.tempExpandedNodes = []
