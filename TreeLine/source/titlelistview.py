#!/usr/bin/env python3

#******************************************************************************
# titlelistview.py, provides a class for the title list view
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt4 import QtCore, QtGui
import treenode
import undo
import globalref


class TitleListView(QtGui.QTextEdit):
    """Class override for the title list view.
    
    Sets view defaults and updates the content.
    """
    nodeModified = QtCore.pyqtSignal(treenode.TreeNode)
    treeModified = QtCore.pyqtSignal()
    shortcutEntered = QtCore.pyqtSignal(QtGui.QKeySequence)
    def __init__(self, selectModel, isChildView=True, parent=None):
        """Initialize the title list view.

        Arguments:
            selectModel - the tree view's selection model
            isChildView -- shows selected nodes if false, child nodes if true
            parent -- the parent main window
        """
        super().__init__(parent)
        self.selectModel = selectModel
        self.isChildView = isChildView
        self.hideChildView = not globalref.genOptions.getValue('ShowChildPane')
        self.setAcceptRichText(False)
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setTabChangesFocus(True)
        self.setUndoRedoEnabled(False)
        self.textChanged.connect(self.readChange)

    def updateContents(self):
        """Reload the view's content if the view is shown.

        Avoids update if view is not visible or has zero height or width.
        """
        selNodes = self.selectModel.selectedNodes()
        if self.isChildView and (len(selNodes) != 1 or self.hideChildView):
            self.hide()
        else:
            self.show()
        if not self.isVisible() or self.height() == 0 or self.width() == 0:
            return
        if self.isChildView:
            selNodes = selNodes[0].childList
        self.blockSignals(True)
        if selNodes:
            self.setPlainText('\n'.join(node.title() for node in selNodes))
        else:
            self.clear()
        self.blockSignals(False)

    def readChange(self):
        """Update nodes after edited by user.
        """
        textList = [' '.join(text.split()) for text in self.toPlainText().
                    split('\n') if text.strip()]
        selNodes = self.selectModel.selectedNodes()
        if self.isChildView:
            parent = selNodes[0]
            selNodes = parent.childList
        if len(selNodes) == len(textList):
            for node, text in zip(selNodes, textList):
                if node.title() != text:
                    undoObj = undo.DataUndo(node.modelRef.undoList, node, True)
                    if node.setTitle(text):
                        self.nodeModified.emit(node)
                    else:
                        node.modelRef.undoList.removeLastUndo(undoObj)
        elif self.isChildView:
            undo.BranchUndo(parent.modelRef.undoList, parent)
            parent.replaceChildren(textList)
            self.treeModified.emit()
        else:
            self.updateContents()  # remove illegal changes

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

    def focusInEvent(self, event):
        """Handle focus-in to put cursor at end for tab-based focus.

        Arguments:
            event -- the focus in event
        """
        if event.reason() in (QtCore.Qt.TabFocusReason,
                              QtCore.Qt.BacktabFocusReason):
            self.moveCursor(QtGui.QTextCursor.End)
        super().focusInEvent(event)

    def contextMenuEvent(self, event):
        """Override popup menu to remove local undo.

        Arguments:
            event -- the menu event
        """
        menu = self.createStandardContextMenu()
        menu.removeAction(menu.actions()[0])
        menu.removeAction(menu.actions()[0])
        menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        """Customize handling of return and control keys.

        Ignore return key if not in show children mode and
        emit a signal for app to handle control keys.
        Arguments:
            event -- the key press event
        """
        if (event.modifiers() == QtCore.Qt.ControlModifier and
            QtCore.Qt.Key_A <= event.key() <= QtCore.Qt.Key_Z):
            key = QtGui.QKeySequence(event.modifiers() | event.key())
            self.shortcutEntered.emit(key)
            return
        if self.isChildView or event.key() not in (QtCore.Qt.Key_Enter,
                                                    QtCore.Qt.Key_Return):
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Update view if it was collaped by splitter.
        """
        if ((event.oldSize().height() == 0 and event.size().height()) or
            (event.oldSize().width() == 0 and event.size().width())):
            self.updateContents()
        return super().resizeEvent(event)
