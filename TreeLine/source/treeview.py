#!/usr/bin/env python3

#******************************************************************************
# treeview.py, provides a class for the indented tree view
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
import treeselection
import miscdialogs
import globalref


class TreeView(QtGui.QTreeView):
    """Class override for the indented tree view.
    
    Sets view defaults and links with document for content.
    """
    skippedMouseSelect = QtCore.pyqtSignal(treenode.TreeNode)
    shortcutEntered = QtCore.pyqtSignal(QtGui.QKeySequence)
    def __init__(self, model, allActions, parent=None):
        """Initialize the tree view.

        Arguments:
            model -- the initial model for view data
            allActions -- a dictionary of control actions for popup menus
            parent -- the parent main window
        """
        super().__init__(parent)
        self.setModel(model)
        self.allActions = allActions
        self.menu = None
        self.noMouseSelectMode = False
        self.setSelectionModel(treeselection.TreeSelection(model, self))
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.header().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.setHeaderHidden(True)
        self.setItemDelegate(TreeEditDelegate(self))
        self.updateTreeGenOptions()
        self.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setDropIndicatorShown(True)
        self.setUniformRowHeights(True)
        self.selectionModel().selectNode(model.root)
        self.expand(model.root.index())

    def updateTreeGenOptions(self):
        """Set the tree to match the current general options.
        """
        if globalref.genOptions.getValue('ClickRename'):
            self.setEditTriggers(QtGui.QAbstractItemView.SelectedClicked)
        else:
            self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        dragAvail = globalref.genOptions.getValue('DragTree')
        self.setDragEnabled(dragAvail)
        self.setAcceptDrops(dragAvail)
        self.setIndentation(globalref.genOptions.getValue('IndentOffset') *
                            self.fontInfo().pixelSize())

    def showTypeMenu(self, menu):
        """Show a popup menu for setting the item type.
        """
        index = self.selectionModel().currentIndex()
        self.scrollTo(index)
        rect = self.visualRect(index)
        pt = self.mapToGlobal(QtCore.QPoint(rect.center().x(), rect.bottom()))
        menu.popup(pt)

    def expandSelectedBranches(self):
        """Set all nodes in the selected branches to expanded.

        Uses expandAll() if root is selected.
        Otherwise it collapses root temporarily to avoid extreme slowness.
        """
        selectNodes = self.selectionModel().selectedNodes()
        rootNode = self.model().root
        if rootNode in selectNodes:
            self.expandAll()
        else:
            self.collapse(rootNode.index())
            for node in selectNodes:
                self.expandBranch(node)
            self.expand(rootNode.index())

    def expandBranch(self, parentNode):
        """Recursively expand all nodes in the branch.

        This goes very slowly if root is not temporarily collapsed first in
        expandSelectedBranches().
        Arguments:
            parentNode -- the top of the branch to expand
        """
        self.expand(parentNode.index())
        for node in parentNode.childList:
            if node.childList:
                self.expandBranch(node)

    def collapseBranch(self, parentNode):
        """Recursively collapse all nodes in the branch.

        Arguments:
            parentNode -- the top of the branch to collapse
        """
        self.collapse(parentNode.index())
        for node in parentNode.childList:
            if node.childList:
                self.collapseBranch(node)

    def endEditing(self):
        """Stop the editing of any item being renamed.
        """
        self.closePersistentEditor(self.selectionModel().currentIndex())

    def contextMenu(self):
        """Return the context menu, creating it if necessary.
        """
        if not self.menu:
            self.menu = QtGui.QMenu(self)
            self.menu.addAction(self.allActions['EditCut'])
            self.menu.addAction(self.allActions['EditCopy'])
            self.menu.addAction(self.allActions['EditPaste'])
            self.menu.addAction(self.allActions['NodeRename'])
            self.menu.addSeparator()
            self.menu.addAction(self.allActions['NodeInsertBefore'])
            self.menu.addAction(self.allActions['NodeInsertAfter'])
            self.menu.addAction(self.allActions['NodeAddChild'])
            self.menu.addSeparator()
            self.menu.addAction(self.allActions['NodeDelete'])
            self.menu.addAction(self.allActions['NodeIndent'])
            self.menu.addAction(self.allActions['NodeUnindent'])
            self.menu.addSeparator()
            self.menu.addAction(self.allActions['NodeMoveUp'])
            self.menu.addAction(self.allActions['NodeMoveDown'])
            self.menu.addSeparator()
            self.menu.addMenu(self.allActions['DataNodeType'].parent())
        return self.menu

    def contextMenuEvent(self, event):
        """Show popup context menu on mouse click or menu key.

        Arguments:
            event -- the context menu event
        """
        if event.reason() == QtGui.QContextMenuEvent.Mouse:
            clickedItem = self.indexAt(event.pos()).internalPointer()
            if not clickedItem:
                event.ignore()
                return
            if clickedItem not in self.selectionModel().selectedNodes():
                self.selectionModel().selectNode(clickedItem)
            pos = event.globalPos()
        else:       # shown for menu key or other reason
            selectList = self.selectionModel().selectedNodes()
            if not selectList:
                event.ignore()
                return
            currentNode = self.selectionModel().currentNode()
            if currentNode in selectList:
                selectList.insert(0, currentNode)
            posList = []
            for node in selectList:
                rect = self.visualRect(node.index())
                pt = QtCore.QPoint(rect.center().x(), rect.bottom())
                if self.rect().contains(pt):
                    posList.append(pt)
            if not posList:
                self.scrollTo(selectList[0].index())
                rect = self.visualRect(selectList[0].index())
                posList = [QtCore.QPoint(rect.center().x(), rect.bottom())]
            pos = self.mapToGlobal(posList[0])
        self.contextMenu().popup(pos)
        event.accept()

    def scrollTo(self, index, hint=QtGui.QAbstractItemView.EnsureVisible):
        """Scroll the view to make node at index visible.

        Overriden to stop autoScroll from horizontally jumping when selecting
        nodes.
        Arguments:
            index -- the node to be made visible
            hint -- where the visible item should be
        """
        horizPos = self.horizontalScrollBar().value()
        super().scrollTo(index, hint)
        self.horizontalScrollBar().setValue(horizPos)

    def nodeAtTop(self):
        """Return the node at the top of the view as currently scrolled.
        """
        return self.indexAt(QtCore.QPoint(0, 0)).internalPointer()

    def dropEvent(self, event):
        """Event handler for view drop actions.

        Selects parent node at destination and avoids node removal after
        invalid moves.
        Arguments:
            event -- the drop event
        """
        clickedNode = self.indexAt(event.pos()).internalPointer()
        if clickedNode:
            super().dropEvent(event)
            self.expand(clickedNode.index())
            self.selectionModel().selectNode(clickedNode)
        else:
            # avoid removal of "moved" items
            event.setDropAction(QtCore.Qt.CopyAction)
            event.ignore()

    def toggleNoMouseSelectMode(self, active=True):
        """Set noMouseSelectMode to active or inactive.

        noMouseSelectMode will not change selection on mouse click,
        it will just signal the clicked node for use in links, etc.
        Arguments:
            active -- if True, activate noMouseSelectMode
        """
        self.noMouseSelectMode = active

    def mousePressEvent(self, event):
        """Skip unselecting click on blank spaces and if in noMouseSelectMode.

        If in noMouseSelectMode, signal which node is under the mouse.
        Arguments:
            event -- the mouse click event
        """
        clickedNode = self.indexAt(event.pos()).internalPointer()
        if not clickedNode:
            event.ignore()
            return
        if self.noMouseSelectMode:
            self.skippedMouseSelect.emit(clickedNode)
            event.ignore()
            return
        super().mousePressEvent(event)


class TreeEditDelegate(QtGui.QStyledItemDelegate):
    """Class override for editing tree items to capture shortcut keys.
    """
    def __init__(self, parent=None):
        """Initialize the delegate class.

        Arguments:
            parent -- the parent view
        """
        super().__init__(parent)

    def createEditor(self, parent, styleOption, modelIndex):
        """Return a new text editor for an item.

        Arguments:
            parent -- the parent widget for the editor
            styleOption -- the data for styles and geometry
            modelIndex -- the index of the item to be edited
        """
        editor = super().createEditor(parent, styleOption, modelIndex)
        return editor

    def eventFilter(self, editor, event):
        """Override to handle shortcut control keys.

        Arguments:
            editor -- the editor that Qt installed a filter on
            event -- the key press event
        """
        if (event.type() == QtCore.QEvent.KeyPress and
            event.modifiers() == QtCore.Qt.ControlModifier and
            QtCore.Qt.Key_A <= event.key() <= QtCore.Qt.Key_Z):
            key = QtGui.QKeySequence(event.modifiers() | event.key())
            self.parent().shortcutEntered.emit(key)
            return True
        return super().eventFilter(editor, event)


class TreeFilterViewItem(QtGui.QListWidgetItem):
    """Item container for the flat list of filtered nodes.
    """
    def __init__(self, node, viewParent=None):
        """Initialize the list view item.

        Arguments:
            node -- the node item to reference for content
            viewParent -- the parent list view
        """
        super().__init__(viewParent)
        self.node = node
        self.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable |
                      QtCore.Qt.ItemIsEnabled)
        self.update()

    def update(self):
        """Update title and icon from the stored node.
        """
        self.setText(self.node.title())
        if globalref.genOptions.getValue('ShowTreeIcons'):
            self.setIcon(globalref.treeIcons.getIcon(self.node.nodeFormat().
                                                     iconName, True))


class TreeFilterView(QtGui.QListWidget):
    """View to show flat list of filtered nodes.
    """
    skippedMouseSelect = QtCore.pyqtSignal(treenode.TreeNode)
    shortcutEntered = QtCore.pyqtSignal(QtGui.QKeySequence)
    def __init__(self, model, selectionModel, allActions, parent=None):
        """Initialize the list view.

        Arguments:
            model -- the initial model for view data
            selectionModel -- the selection model for this view
            allActions -- a dictionary of control actions for popup menus
            parent -- the parent main window
        """
        super().__init__(parent)
        self.model = model
        self.selectionModel = selectionModel
        self.allActions = allActions
        self.menu = None
        self.noMouseSelectMode = False
        self.drivingSelectionChange = False
        self.conditionalFilter = None
        self.filterWhat = miscdialogs.FindFilterDialog.fullData
        self.filterHow = miscdialogs.FindFilterDialog.keyWords
        self.filterStr = ''
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setItemDelegate(TreeEditDelegate(self))
        if globalref.genOptions.getValue('ClickRename'):
            self.setEditTriggers(QtGui.QAbstractItemView.SelectedClicked)
        else:
            self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.itemSelectionChanged.connect(self.updateSelectionModel)
        self.itemChanged.connect(self.changeTitle)

    def updateItem(self, node):
        """Update the item corresponding to the given node.

        Arguments:
            node -- the node to be updated
        """
        for row in range(self.count()):
            if self.item(row).node == node:
                self.blockSignals(True)
                self.item(row).update()
                self.blockSignals(False)
                return

    def updateContents(self):
        """Update filtered contents from current model and filter criteria.
        """
        if self.conditionalFilter:
            self.conditionalUpdate()
            return
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        if self.filterHow == miscdialogs.FindFilterDialog.regExp:
            criteria = [re.compile(self.filterStr)]
            useRegExpFilter = True
        elif self.filterHow == miscdialogs.FindFilterDialog.fullWords:
            criteria = []
            for word in self.filterStr.lower().split():
                criteria.append(re.compile(r'(?i)\b{}\b'.
                                           format(re.escape(word))))
            useRegExpFilter = True
        elif self.filterHow == miscdialogs.FindFilterDialog.keyWords:
            criteria = self.filterStr.lower().split()
            useRegExpFilter = False
        else:         # full phrase
            criteria = [self.filterStr.lower().strip()]
            useRegExpFilter = False
        titlesOnly = self.filterWhat == miscdialogs.FindFilterDialog.titlesOnly
        self.blockSignals(True)
        self.clear()
        if useRegExpFilter:
            for node in self.model.root.descendantGen():
                if node.regExpSearch(criteria, titlesOnly):
                    item = TreeFilterViewItem(node, self)
        else:
            for node in self.model.root.descendantGen():
                if node.wordSearch(criteria, titlesOnly):
                    item = TreeFilterViewItem(node, self)
        self.blockSignals(False)
        self.selectItems(self.selectionModel.selectedNodes(), True)
        if self.count() and not self.selectedItems():
            self.item(0).setSelected(True)
        message = _('Filtering by "{0}", found {1} nodes').format(self.
                                                                  filterStr,
                                                                  self.count())
        globalref.mainControl.currentStatusBar().showMessage(message)
        QtGui.QApplication.restoreOverrideCursor()

    def conditionalUpdate(self):
        """Update filtered contents from model and conditional criteria.
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.blockSignals(True)
        self.clear()
        for node in self.model.root.descendantGen():
            if self.conditionalFilter.evaluate(node):
                item = TreeFilterViewItem(node, self)
        self.blockSignals(False)
        self.selectItems(self.selectionModel.selectedNodes(), True)
        if self.count() and not self.selectedItems():
            self.item(0).setSelected(True)
        message = _('Conditional filtering, found {0} nodes').format(self.
                                                                     count())
        globalref.mainControl.currentStatusBar().showMessage(message)
        QtGui.QApplication.restoreOverrideCursor()

    def selectItems(self, nodes, signalModel=False):
        """Select items matching given nodes if in filtered view.

        Arguments:
            nodes -- the node list to select
            signalModel -- signal to update the tree selection model if True
        """
        selectNodes = set(nodes)
        if not signalModel:
            self.blockSignals(True)
        for item in self.selectedItems():
            item.setSelected(False)
        for row in range(self.count()):
            if self.item(row).node in selectNodes:
                self.item(row).setSelected(True)
                self.setCurrentItem(self.item(row))
        if not signalModel:
            self.blockSignals(False)

    def updateFromSelectionModel(self):
        """Select items selected in the tree selection model.

        Called from a signal that the tree selection model is changing.
        """
        if self.count() and not self.drivingSelectionChange:
            self.selectItems(self.selectionModel.selectedNodes())

    def updateSelectionModel(self):
        """Change the selection model based on a filter list selection signal.
        """
        self.drivingSelectionChange = True
        self.selectionModel.selectNodes([item.node for item in
                                         self.selectedItems()])
        self.drivingSelectionChange = False

    def changeTitle(self, item):
        """Update the node title in the model based on an edit signal.

        Reset to the node text if invalid.
        Arguments:
            item -- the filter view item that changed
        """
        if not self.model.setData(item.node.index(), item.text()):
            self.blockSignals(True)
            item.setText(item.node.title())
            self.blockSignals(False)

    def nextPrevNode(self, node, forward=True):
        """Return the next or previous node in this filter list view.

        Wraps around ends.  Return None if view doesn't have node.
        Arguments:
            node -- the starting node
            forward -- next if True, previous if False
        """
        for row in range(self.count()):
            if self.item(row).node == node:
                if forward:
                    row += 1
                    if row >= self.count():
                        row = 0
                else:
                    row -= 1
                    if row < 0:
                        row = self.count() - 1
                return self.item(row).node
        return None

    def contextMenu(self):
        """Return the context menu, creating it if necessary.
        """
        if not self.menu:
            self.menu = QtGui.QMenu(self)
            self.menu.addAction(self.allActions['EditCut'])
            self.menu.addAction(self.allActions['EditCopy'])
            self.menu.addAction(self.allActions['NodeRename'])
            self.menu.addSeparator()
            self.menu.addAction(self.allActions['NodeDelete'])
            self.menu.addSeparator()
            self.menu.addMenu(self.allActions['DataNodeType'].parent())
        return self.menu

    def contextMenuEvent(self, event):
        """Show popup context menu on mouse click or menu key.

        Arguments:
            event -- the context menu event
        """
        if event.reason() == QtGui.QContextMenuEvent.Mouse:
            clickedItem = self.itemAt(event.pos())
            if not clickedItem:
                event.ignore()
                return
            if clickedItem.node not in self.selectionModel.selectedNodes():
                self.selectionModel().selectNode(clickedItem.node)
            pos = event.globalPos()
        else:       # shown for menu key or other reason
            selectList = self.selectedItems()
            if not selectList:
                event.ignore()
                return
            currentItem = self.currentItem()
            if currentItem in selectList:
                selectList.insert(0, currentItem)
            posList = []
            for item in selectList:
                rect = self.visualItemRect(item)
                pt = QtCore.QPoint(rect.center().x(), rect.bottom())
                if self.rect().contains(pt):
                    posList.append(pt)
            if not posList:
                self.scrollTo(self.indexFromItem(selectList[0]))
                rect = self.visualItemRect(selectList[0])
                posList = [QtCore.QPoint(rect.center().x(), rect.bottom())]
            pos = self.mapToGlobal(posList[0])
        self.contextMenu().popup(pos)
        event.accept()

    def toggleNoMouseSelectMode(self, active=True):
        """Set noMouseSelectMode to active or inactive.

        noMouseSelectMode will not change selection on mouse click,
        it will just signal the clicked node for use in links, etc.
        Arguments:
            active -- if True, activate noMouseSelectMode
        """
        self.noMouseSelectMode = active

    def mousePressEvent(self, event):
        """Skip unselecting click on blank spaces.

        Arguments:
            event -- the mouse click event
        """
        clickedItem = self.itemAt(event.pos())
        if not clickedItem:
            event.ignore()
            return
        if self.noMouseSelectMode:
            self.skippedMouseSelect.emit(clickedItem.node)
            event.ignore()
            return
        super().mousePressEvent(event)
