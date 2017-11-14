#!/usr/bin/env python3

#******************************************************************************
# recentfiles.py, classes to save recent file lists, states and actions
#
# TreeLine, an information storage program
# Copyright (C) 2014, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import os.path
import time
from PyQt4 import QtCore, QtGui
import globalref
import options

_maxActionPathLength = 30
_maxOpenNodesStored = 100


class RecentFileItem:
    """Class containing path, state and action info for a single recent file.
    """
    def __init__(self, posNum=1, path=''):
        """Initialize a RecentFileItem.

        Arguments:
            posNum -- the position number for use in the action text
            path -- the path to the file (can be set later)
        """
        self.posNum = posNum
        self.path = ''
        self.abbrevPath = ''
        self.stateTime = 0
        self.scrollPos = ''
        self.selectNodes = ''
        self.openNodes = ''
        self.action = QtGui.QAction(globalref.mainControl)
        self.action.triggered.connect(self.openFile)
        if path:
            self.setPath(path)

    def setPath(self, path):
        """Set the path and abbreviated path for this item and action.

        Arguments:
            path - the new path name to set
        """
        self.path = os.path.abspath(path)
        self.abbrevPath = self.path
        if len(self.path) > _maxActionPathLength:
            truncLength = _maxActionPathLength - 3
            pos = self.path.find(os.sep, len(self.path) - truncLength)
            if pos < 0:
                pos = len(self.path) - truncLength
            self.abbrevPath = '...' + self.path[pos:]
        self.renameAction()

    def setPosNum(self, posNum):
        """Set a new position number and rename the action if necessary.

        Arguments:
            posNum -- the new position number
        """
        if posNum != self.posNum:
            self.posNum = posNum
            self.renameAction()

    def renameAction(self):
        """Rename the action based on the current path and position number.
        """
        self.action.setText('&{0:d} {1}'.format(self.posNum, self.abbrevPath))
        self.action.setStatusTip = self.path

    def pathIsValid(self):
        """Return True if the current path exists.
        """
        if self.path:
            return os.access(self.path, os.R_OK)
        return False

    def readOptionParams(self):
        """Read path names and state info from the option storage.
        """
        try:
            path = globalref.histOptions.getValue('RecentPath{:d}'.
                                                  format(self.posNum))
            if path:
                self.setPath(path)
            self.stateTime = globalref.histOptions.getValue('RecentTime{:d}'.
                                                           format(self.posNum))
            self.scrollPos = globalref.histOptions.getValue('RecentScroll{:d}'.
                                                           format(self.posNum))
            self.selectNodes = (globalref.histOptions.
                                getValue('RecentSelect{:d}'.
                                         format(self.posNum)))
            self.openNodes = globalref.histOptions.getValue('RecentOpen{:d}'.
                                                           format(self.posNum))
        except KeyError:
            return

    def writeOptionParams(self):
        """Write path names and state info to the option storage.
        """
        key = 'RecentPath{:d}'.format(self.posNum)
        while True:
            try:
                globalref.histOptions.changeValue('RecentPath{:d}'.
                                                  format(self.posNum),
                                                  self.path)
                globalref.histOptions.changeValue('RecentTime{:d}'.
                                                  format(self.posNum),
                                                  self.stateTime)
                globalref.histOptions.changeValue('RecentScroll{:d}'.
                                                  format(self.posNum),
                                                  self.scrollPos)
                globalref.histOptions.changeValue('RecentSelect{:d}'.
                                                  format(self.posNum),
                                                  self.selectNodes)
                globalref.histOptions.changeValue('RecentOpen{:d}'.
                                                  format(self.posNum),
                                                  self.openNodes)
                return
            except KeyError:
                setRecentOptionDefault(self.posNum)

    def openFile(self):
        """Open this path using the main control method.
        """
        globalref.mainControl.openFile(self.path, True)

    def recordTreeState(self, localControl):
        """Save the tree state of this item.

        Arguments:
            localControl -- the control to store
        """
        self.stateTime = int(time.time())
        treeView = localControl.currentTreeView()
        topNode = treeView.nodeAtTop()
        if topNode.parent:   # not root, so view is scrolled
            self.scrollPos = topNode.uniqueId
        else:
            self.scrollPos = ''
        self.selectNodes = ','.join([node.uniqueId for node in
                                     treeView.selectionModel().
                                     selectedNodes()])
        openNodes = [node.uniqueId for node in
                     localControl.model.root.openNodes()]
        if len(openNodes) < _maxOpenNodesStored:
            self.openNodes = ','.join(openNodes)
        else:
            self.openNodes = ''

    def restoreTreeState(self, localControl):
        """Restore the tree state of this item.

        Arguments:
            localControl -- the control to set state
        """
        fileModTime = os.stat(localControl.filePath).st_mtime
        if self.stateTime == 0 or fileModTime > self.stateTime:
            return    # file modified externally
        treeView = localControl.currentTreeView()
        if self.openNodes:
            nodes = [localControl.model.nodeIdDict.get(nodeId, None) for
                     nodeId in self.openNodes.split(',')]
            rootNode = localControl.model.root
            # should be faster if root is temporarily closed
            treeView.collapse(rootNode.index())
            for node in nodes:
                if node:
                    treeView.expand(node.index())
            treeView.expand(rootNode.index())
        if self.scrollPos:
            topNode = localControl.model.nodeIdDict.get(self.scrollPos, None)
            if topNode:
                treeView.scrollTo(topNode.index(),
                                  QtGui.QAbstractItemView.PositionAtTop)
        if self.selectNodes:
            nodes = [localControl.model.nodeIdDict.get(nodeId, None) for
                     nodeId in self.selectNodes.split(',')]
            nodes = [node for node in nodes if node]
            if nodes:
                treeView.selectionModel().selectNodes(nodes)

    def __eq__(self, other):
        """Test for equality between RecentFileItems and paths.

        Arguments:
            other -- either a RecentFileItem or a path string
        """
        try:
            otherPath = other.path
        except AttributeError:
            otherPath = other
        return os.path.normcase(self.path) == os.path.normcase(otherPath)

    def __ne__(self, other):
        """Test for inequality between RecentFileItems and paths.

        Arguments:
            other -- either a RecentFileItem or a path string
        """
        try:
            otherPath = other.path
        except AttributeError:
            otherPath = other
        return os.path.normcase(self.path) != os.path.normcase(otherPath)


class RecentFileList(list):
    """A list of recent file items.
    """
    def __init__(self):
        """Load the initial list from the options file.
        """
        super().__init__()
        self.numEntries = globalref.genOptions.getValue('RecentFiles')
        self.readItems()

    def readItems(self):
        """Read the recent items from the options file.
        """
        self[:] = []
        for num in range(self.numEntries):
            item = RecentFileItem(num + 1)
            item.readOptionParams()
            if item.pathIsValid():
                self.append(item)
        self.updatePosNumbers()

    def writeItems(self):
        """Write the recent items to the options file.
        """
        for entry in self:
            entry.writeOptionParams()
        for num in range(len(self), self.numEntries):
            try:
                globalref.histOptions.changeValue('RecentPath{:d}'.
                                                  format(num + 1), '')
            except KeyError:
                pass
        globalref.histOptions.writeFile()

    def addItem(self, path):
        """Add the given path at the start of the list.

        If the path is in the list, move it to the start,
        otherwise create a new item.
        Arguments:
            path -- the new path to search and/or create
        """
        item = RecentFileItem(1, path)
        try:
            item = self.pop(self.index(item))
        except ValueError:
            pass
        self.insert(0, item)
        self.updatePosNumbers()

    def removeItem(self, path):
        """Remove the given path name if found.

        Arguments:
            path -- the path to be removed
        """
        try:
            self.remove(RecentFileItem(1, path))
        except ValueError:
            pass
        self.updatePosNumbers()

    def saveTreeState(self, localControl):
        """Save the tree state of the item matching the localControl.

        Arguments:
            localControl -- the control to store
        """
        item = RecentFileItem(1, localControl.filePath)
        try:
            item = self[self.index(item)]
        except ValueError:
            return
        item.recordTreeState(localControl)

    def retrieveTreeState(self, localControl):
        """Restore the saved tree state of the item matching the localControl.

        Arguments:
            localControl -- the control to restore state
        """
        item = RecentFileItem(1, localControl.filePath)
        try:
            item = self[self.index(item)]
        except ValueError:
            return
        item.restoreTreeState(localControl)

    def getActions(self):
        """Return a list of actions for ech recent item.
        """
        return [item.action for item in self]

    def firstDir(self):
        """Return the first valid path from the recent items.
        """
        for item in self:
            path = os.path.dirname(item.path)
            if os.path.exists(path):
                return path + os.sep
        return ''

    def firstPath(self):
        """Return the first full path from the recent items.
        """
        if self:
            return self[0].path
        return ''

    def updatePosNumbers(self):
        """Update the item position numbers and truncate the list if req'd.
        """
        self[:] = self[:self.numEntries]
        for num, item in enumerate(self):
            item.setPosNum(num + 1)

    def updateNumEntries(self):
        """Update the maximum number of entries based on the option.
        """
        oldNumEntries = self.numEntries
        self.numEntries = globalref.genOptions.getValue('RecentFiles')
        if self.numEntries > oldNumEntries:
            for i in range(oldNumEntries, self.numEntries):
                setRecentOptionDefault(i + 1)
        elif self.numEntries < oldNumEntries:
            for i in range(self.numEntries, oldNumEntries):
                for name in ('Path', 'Time', 'Scroll', 'Select', 'Open'):
                    globalref.histOptions.removeValue('Recent{0}{1:d}'.
                                                      format(name, i + 1))
            self[:] = self[:self.numEntries]


def setRecentOptionDefaults():
    """Load correct number of default option entries.

    Must be called after general options are read but before reading history
    options or initializing the RecentFileList class.
    """
    for i in range(globalref.genOptions.getValue('RecentFiles')):
        setRecentOptionDefault(i + 1)


def setRecentOptionDefault(num):
    """Load a single default option entry.

    Arguments:
        num -- the recent number to load
    """
    options.StringOptionItem(globalref.histOptions,
                             'RecentPath{:d}'.format(num), '', True,
                             _('Recent Files'))
    options.IntOptionItem(globalref.histOptions, 'RecentTime{:d}'.format(num),
                          0, 0, None, _('Recent Files'))
    options.StringOptionItem(globalref.histOptions,
                             'RecentScroll{:d}'.format(num), '', True,
                             _('Recent Files'))
    options.StringOptionItem(globalref.histOptions,
                             'RecentSelect{:d}'.format(num), '', True,
                             _('Recent Files'))
    options.StringOptionItem(globalref.histOptions,
                             'RecentOpen{:d}'.format(num), '', True,
                             _('Recent Files'))

