#!/usr/bin/env python3

#******************************************************************************
# treenodelist.py, provides a class to do operations on groups of nodes
#
# TreeLine, an information storage program
# Copyright (C) 2014, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt4 import QtCore, QtGui
import undo


class TreeNodeList(list):
    """Class to do operations on groups of nodes.
    
    Stores a list of nodes.
    """
    def __init__(self, nodeList=None):
        """Initialize a tree node group.

        Arguments:
            nodeList -- the initial list of nodes
        """
        super().__init__()
        if nodeList:
            self[:] = nodeList

    def copyTree(self):
        """Copy these node branches to the clipboard.
        """
        if not self:
            return
        clip = QtGui.QApplication.clipboard()
        if clip.supportsSelection():
            titleList = []
            for node in self:
                titleList.extend(node.exportTitleText())
            clip.setText('\n'.join(titleList), QtGui.QClipboard.Selection)
        clip.setMimeData(self[0].modelRef.mimeData([node.index() for node in
                                                    self]))

    def pasteMimeData(self, mimeData):
        """Decode mime data and paste into these nodes.
        
        Returns True on success.
        Arguments:
            mimeData - the data to paste.
        """
        if not self:
            return False
        undoObj = undo.BranchFormatUndo(self[0].modelRef.undoList, self,
                                        self[0].modelRef.formats)
        for parent in self:
            if not self[0].modelRef.addMimeData(mimeData, parent):
                self[0].modelRef.undoList.removeLastUndo(undoObj)
                return False
        return True
