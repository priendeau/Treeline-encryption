#!/usr/bin/env python3

#******************************************************************************
# outputview.py, provides a class for the data output view
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import os.path
from PyQt4 import QtCore, QtGui
import treenode
import treeoutput
import urltools
import dataeditors
import globalref


class OutputView(QtGui.QTextBrowser):
    """Class override for the data output view.
    
    Sets view defaults and updates the content.
    """
    def __init__(self, selectModel, isChildView=True, parent=None):
        """Initialize the output view.

        Arguments:
            selectModel - the tree view's selection model
            isChildView -- shows selected nodes if false, child nodes if true
            parent -- the parent main window
        """
        super().__init__(parent)
        self.selectModel = selectModel
        self.isChildView = isChildView
        self.hideChildView = not globalref.genOptions.getValue('ShowChildPane')
        self.showDescendants = globalref.genOptions.getValue('ShowDescendants')
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def updateContents(self):
        """Reload the view's content if the view is shown.

        Avoids update if view is not visible or has zero height or width.
        """
        selNodes = self.selectModel.selectedNodes()
        if self.isChildView and (len(selNodes) != 1 or self.hideChildView or
                                 not selNodes[0].childList):
            self.hide()
        else:
            self.show()
        if not self.isVisible() or self.height() == 0 or self.width() == 0:
            return
        if not selNodes:
            self.setHtml('')
            return
        if self.isChildView:
            if self.showDescendants:
                outputGroup = treeoutput.OutputGroup(selNodes, False, True)
                if outputGroup.hasPrefixes():
                    outputGroup.combineAllSiblings()
                outputGroup.addBlanksBetween()
                outputGroup.addAbsoluteIndents()
            else:
                outputGroup = treeoutput.OutputGroup(selNodes[0].childList)
                outputGroup.addBlanksBetween()
                outputGroup.addSiblingPrefixes()
        else:
            outputGroup = treeoutput.OutputGroup(selNodes)
            outputGroup.addBlanksBetween()
            outputGroup.addSiblingPrefixes()
        self.setHtml('\n'.join(outputGroup.getLines()))
        self.setSearchPaths([globalref.mainControl.defaultFilePath(True)])

    def setSource(self, url):
        """Called when a user clicks on a URL link.

        Selects an internal link or opens an external browser.
        Arguments:
            url -- the QUrl that is clicked
        """
        name = url.toString()
        if name.startswith('#'):
            if not self.selectModel.selectNodeById(name[1:]):
                super().setSource(url)
        else:
            if urltools.isRelative(name):    # check for relative path
                defaultPath = globalref.mainControl.defaultFilePath(True)
                name = urltools.toAbsolute(name, defaultPath)
            dataeditors.openExtUrl(name)

    def hasSelectedText(self):
        """Return True if text is selected.
        """
        return self.textCursor().hasSelection()

    def highlightSearch(self, wordList=None, regExpList=None):
        """Highlight any found search terms.

        Arguments:
            wordList -- list of words to highlight
            regExpList -- a list of regular expression objects to highlight
        """
        backColor = self.palette().brush(QtGui.QPalette.Active,
                                         QtGui.QPalette.Highlight)
        foreColor = self.palette().brush(QtGui.QPalette.Active,
                                         QtGui.QPalette.HighlightedText)
        if wordList is None:
            wordList = []
        if regExpList is None:
            regExpList = []
        for regExp in regExpList:
            for match in regExp.finditer(self.toPlainText()):
                matchText = match.group()
                if matchText not in wordList:
                    wordList.append(matchText)
        selections = []
        for word in wordList:
            while self.find(word):
                extraSel = QtGui.QTextEdit.ExtraSelection()
                extraSel.cursor = self.textCursor()
                extraSel.format.setBackground(backColor)
                extraSel.format.setForeground(foreColor)
                selections.append(extraSel)
        cursor = QtGui.QTextCursor(self.document())
        self.setTextCursor(cursor)  # reset main cursor/selection
        self.setExtraSelections(selections)

    def contextMenuEvent(self, event):
        """Add a popup menu for select all and copy actions.

        Arguments:
            event -- the menu event
        """
        menu = self.createStandardContextMenu()
        menu.removeAction(menu.actions()[1]) #remove copy link location
        menu.exec_(event.globalPos())

    def resizeEvent(self, event):
        """Update view if was collaped by splitter.
        """
        if ((event.oldSize().height() == 0 and event.size().height()) or
            (event.oldSize().width() == 0 and event.size().width())):
            self.updateContents()
        return super().resizeEvent(event)
