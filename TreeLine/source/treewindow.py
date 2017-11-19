#!/usr/bin/env python3

#******************************************************************************
# treewindow.py, provides a class for the main window and controls
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
import base64
from PyQt4 import QtCore, QtGui
import treeview
import outputview
import titlelistview
import dataeditview
import treenode
import globalref


class TreeWindow(QtGui.QMainWindow):
    """Class override for the main window.

    Contains main window views and controls.
    """
    selectChanged = QtCore.pyqtSignal()
    nodeModified = QtCore.pyqtSignal(treenode.TreeNode)
    treeModified = QtCore.pyqtSignal()
    winActivated = QtCore.pyqtSignal(QtGui.QMainWindow)
    winClosing = QtCore.pyqtSignal(QtGui.QMainWindow)
    def __init__(self, model, allActions, parent=None):
        """Initialize the main window.

        Arguments:
            model -- the initial data model
            allActions -- a dict containing the upper level actions
            parent -- the parent window, usually None
        """
        super().__init__(parent)
        self.allActions = allActions.copy()
        self.allowCloseFlag = True
        self.toolbars = []
        self.rightTabActList = []
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAcceptDrops(True)
        self.setStatusBar(QtGui.QStatusBar())
        self.setCaption()
        self.setupActions()
        self.setupMenus()
        self.setupToolbars()
        self.restoreToolbarPosition()

        self.mainSplitter = QtGui.QSplitter()
        self.setCentralWidget(self.mainSplitter)
        self.treeStack = QtGui.QStackedWidget()
        self.mainSplitter.addWidget(self.treeStack)
        self.treeView = treeview.TreeView(model, self.allActions)
        self.treeView.shortcutEntered.connect(self.execShortcut)
        self.treeStack.addWidget(self.treeView)
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                                selectChanged)
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                              updateRightViews)
        self.treeFilterView = treeview.TreeFilterView(model, self.treeView.
                                                      selectionModel(),
                                                      self.allActions)
        self.treeFilterView.shortcutEntered.connect(self.execShortcut)
        self.treeStack.addWidget(self.treeFilterView)
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                      treeFilterView.
                                                      updateFromSelectionModel)
        self.treeStack.setCurrentWidget(self.treeView)

        self.rightTabs = QtGui.QTabWidget()
        self.mainSplitter.addWidget(self.rightTabs)
        self.rightTabs.setTabPosition(QtGui.QTabWidget.South)
        self.rightTabs.tabBar().setFocusPolicy(QtCore.Qt.NoFocus)

        self.outputSplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.rightTabs.addTab(self.outputSplitter, _('Data Output'))
        parentOutputView = outputview.OutputView(self.treeView.
                                                 selectionModel(), False)
        parentOutputView.highlighted[str].connect(self.statusBar().showMessage)
        self.outputSplitter.addWidget(parentOutputView)
        childOutputView = outputview.OutputView(self.treeView.selectionModel(),
                                                True)
        childOutputView.highlighted[str].connect(self.statusBar().showMessage)
        self.outputSplitter.addWidget(childOutputView)

        self.editorSplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.rightTabs.addTab(self.editorSplitter, _('Data Edit'))
        parentEditView = dataeditview.DataEditView(self.treeView.
                                                   selectionModel(),
                                                   self.allActions, False)
        parentEditView.nodeModified.connect(self.nodeModified)
        parentEditView.inLinkSelectMode.connect(self.treeView.
                                                toggleNoMouseSelectMode)
        parentEditView.inLinkSelectMode.connect(self.treeFilterView.
                                                toggleNoMouseSelectMode)
        parentEditView.focusOtherView.connect(self.focusNextView)
        parentEditView.shortcutEntered.connect(self.execShortcut)
        self.treeView.skippedMouseSelect.connect(parentEditView.
                                                 internalLinkSelected)
        self.treeFilterView.skippedMouseSelect.connect(parentEditView.
                                                       internalLinkSelected)
        self.editorSplitter.addWidget(parentEditView)
        childEditView = dataeditview.DataEditView(self.treeView.
                                                  selectionModel(),
                                                  self.allActions, True)
        childEditView.nodeModified.connect(self.nodeModified)
        childEditView.inLinkSelectMode.connect(self.treeView.
                                               toggleNoMouseSelectMode)
        childEditView.inLinkSelectMode.connect(self.treeFilterView.
                                               toggleNoMouseSelectMode)
        childEditView.focusOtherView.connect(self.focusNextView)
        childEditView.shortcutEntered.connect(self.execShortcut)
        self.treeView.skippedMouseSelect.connect(childEditView.
                                                 internalLinkSelected)
        self.treeFilterView.skippedMouseSelect.connect(childEditView.
                                                       internalLinkSelected)
        self.editorSplitter.addWidget(childEditView)

        self.titleSplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.rightTabs.addTab(self.titleSplitter, _('Title List'))
        parentTitleView = titlelistview.TitleListView(self.treeView.
                                                      selectionModel(), False)
        parentTitleView.nodeModified.connect(self.nodeModified)
        parentTitleView.treeModified.connect(self.treeModified)
        parentTitleView.shortcutEntered.connect(self.execShortcut)
        self.titleSplitter.addWidget(parentTitleView)
        childTitleView = titlelistview.TitleListView(self.treeView.
                                                     selectionModel(), True)
        childTitleView.nodeModified.connect(self.nodeModified)
        childTitleView.treeModified.connect(self.treeModified)
        childTitleView.shortcutEntered.connect(self.execShortcut)
        self.titleSplitter.addWidget(childTitleView)

        self.rightTabs.currentChanged.connect(self.updateRightViews)
        self.rightViewList = [parentOutputView, childOutputView,
                              parentEditView, childEditView,
                              parentTitleView, childTitleView]
        self.updateFonts()

    def updateTreeNode(self, node):
        """Update the given node in the active tree view.

        Arguments:
            node -- the node to be updated
        """
        self.treeView.update(node.index())
        self.treeView.resizeColumnToContents(0)

    def updateTree(self):
        """Update the full tree in the active tree view.
        """
        self.treeView.scheduleDelayedItemsLayout()

    def updateRightViews(self, *args, outputOnly=False):
        """Update all right-hand views (or all right-hand output views).

        Called for initial setup, selection change or data chamge.
        The views may decide not to update if hidden.
        Arguments:
            *args -- dummy arguments to collect args from signals
            outputOnly -- only update output views (not edit views)
        """
        self.rightTabActList[self.rightTabs.currentIndex()].setChecked(True)
        for view in self.rightViewList:
            if not outputOnly or isinstance(view, outputview.OutputView):
                view.updateContents()

    def refreshDataEditViews(self):
        """Refresh the data in non-selected cells in curreent data edit views.
        """
        views = [self.rightParentView(), self.rightChildView()]
        for view in views:
            if view and isinstance(view, dataeditview.DataEditView):
                view.updateUnselectedCells()

    def updateCommandsAvail(self):
        """Set window commands available based on node selections.
        """
        selNodes = self.treeView.selectionModel().selectedNodes()
        numChildren = sum([len(node.childList) for node in selNodes])
        self.allActions['ViewExpandBranch'].setEnabled(numChildren)
        self.allActions['ViewCollapseBranch'].setEnabled(numChildren)
        self.allActions['ViewPrevSelect'].setEnabled(len(self.treeView.
                                                         selectionModel().
                                                         previousNodes) > 1)
        self.allActions['ViewNextSelect'].setEnabled(len(self.treeView.
                                                         selectionModel().
                                                         nextNodes) > 0)

    def updateFonts(self):
        """Update custom fonts in views.
        """
        treeFont = QtGui.QTextDocument().defaultFont()
        treeFontName = globalref.miscOptions.getValue('TreeFont')
        if treeFontName:
            treeFont.fromString(treeFontName)
        self.treeView.setFont(treeFont)
        self.treeView.updateTreeGenOptions()
        self.treeFilterView.setFont(treeFont)
        ouputFont = QtGui.QTextDocument().defaultFont()
        ouputFontName = globalref.miscOptions.getValue('OutputFont')
        if ouputFontName:
            ouputFont.fromString(ouputFontName)
        editorFont = QtGui.QTextDocument().defaultFont()
        editorFontName = globalref.miscOptions.getValue('EditorFont')
        if editorFontName:
            editorFont.fromString(editorFontName)
        for view in self.rightViewList:
            if isinstance(view, outputview.OutputView):
                view.setFont(ouputFont)
            else:
                view.setFont(editorFont)

    def isFiltering(self):
        """Return True if tree filter view is active.
        """
        return self.treeStack.currentWidget() == self.treeFilterView

    def rightParentView(self):
        """Return the current right-hand parent view if visible (or None).
        """
        view = self.rightTabs.currentWidget().widget(0)
        if not view.isVisible() or view.height() == 0 or view.width() == 0:
            return None
        return view

    def rightChildView(self):
        """Return the current right-hand parent view if visible (or None).
        """
        view = self.rightTabs.currentWidget().widget(1)
        if not view.isVisible() or view.height() == 0 or view.width() == 0:
            return None
        return view

    def focusNextView(self, forward=True):
        """Focus the next pane in the tab focus series.

        Called by a signal from the data edit views.
        Tab sequences tended to skip views without this.
        Arguments:
            forward -- forward in tab series if True
        """
        reason = (QtCore.Qt.TabFocusReason if forward
                  else QtCore.Qt.BacktabFocusReason)
        if (self.sender().isChildView == forward or
            (forward and self.rightChildView() == None) or
            (not forward and self.rightParentView() == None)):
            self.treeStack.currentWidget().setFocus(reason)
        elif forward:
            self.rightChildView().setFocus(reason)
        else:
            self.rightParentView().setFocus(reason)

    def activateAndRaise(self):
        """Activate this window and raise it to the front.
        """
        self.activateWindow()
        self.raise_()

    def setCaption(self, filePath=''):
        """Change the window caption title based on the file name and path.

        Arguments:
            filePath - the full path to the current file
        """
        if filePath:
            caption = '{0} [{1}] - TreeLine'.format(os.path.basename(filePath),
                                                  os.path.dirname(filePath))
        else:
            caption = '- TreeLine'
        self.setWindowTitle(caption)

    def execShortcut(self, key):
        """Execute an action based on a shortcut key signal from a view.

        Arguments:
            key -- the QKeySequence shortcut
        """
        keyDict = {action.shortcut().toString(): action for action in
                   self.allActions.values()}
        try:
            action = keyDict[key.toString()]
        except KeyError:
            return
        if action.isEnabled():
            action.trigger()

    def setupActions(self):
        """Add the actions for contols at the window level.

        These actions only affect an individual window,
        they're independent in multiple windows of the same file.
        """
        winActions = {}

        viewExpandBranchAct = QtGui.QAction(_('&Expand Full Branch'), self,
                      statusTip=_('Expand all children of the selected nodes'))
        viewExpandBranchAct.triggered.connect(self.viewExpandBranch)
        winActions['ViewExpandBranch'] = viewExpandBranchAct

        viewCollapseBranchAct = QtGui.QAction(_('&Collapse Full Branch'), self,
                    statusTip=_('Collapse all children of the selected nodes'))
        viewCollapseBranchAct.triggered.connect(self.viewCollapseBranch)
        winActions['ViewCollapseBranch'] = viewCollapseBranchAct

        viewPrevSelectAct = QtGui.QAction(_('&Previous Selection'), self,
                          statusTip=_('Return to the previous tree selection'))
        viewPrevSelectAct.triggered.connect(self.viewPrevSelect)
        winActions['ViewPrevSelect'] = viewPrevSelectAct

        viewNextSelectAct = QtGui.QAction(_('&Next Selection'), self,
                       statusTip=_('Go to the next tree selection in history'))
        viewNextSelectAct.triggered.connect(self.viewNextSelect)
        winActions['ViewNextSelect'] = viewNextSelectAct

        viewRightTabGrp = QtGui.QActionGroup(self)
        viewOutputAct = QtGui.QAction(_('Show Data &Output'), viewRightTabGrp,
                                 statusTip=_('Show data output in right view'),
                                 checkable=True)
        winActions['ViewDataOutput'] = viewOutputAct

        viewEditAct = QtGui.QAction(_('Show Data &Editor'), viewRightTabGrp,
                                 statusTip=_('Show data editor in right view'),
                                 checkable=True)
        winActions['ViewDataEditor'] = viewEditAct

        viewTitleAct = QtGui.QAction(_('Show &Title List'), viewRightTabGrp,
                                  statusTip=_('Show title list in right view'),
                                  checkable=True)
        winActions['ViewTitleList'] = viewTitleAct
        self.rightTabActList = [viewOutputAct, viewEditAct, viewTitleAct]
        viewRightTabGrp.triggered.connect(self.viewRightTab)

        viewChildPaneAct = QtGui.QAction(_('&Show Child Pane'),  self,
                          statusTip=_('Toggle showing right-hand child views'),
                          checkable=True)
        viewChildPaneAct.setChecked(globalref.genOptions.
                                    getValue('ShowChildPane'))
        viewChildPaneAct.triggered.connect(self.viewShowChildPane)
        winActions['ViewShowChildPane'] = viewChildPaneAct

        viewDescendAct = QtGui.QAction(_('Show Output &Descedants'), self,
                statusTip=_('Toggle showing output view indented descendants'),
                checkable=True)
        viewDescendAct.setChecked(globalref.genOptions.
                                  getValue('ShowDescendants'))
        viewDescendAct.triggered.connect(self.viewDescendants)
        winActions['ViewShowDescend'] = viewDescendAct

        winCloseAct = QtGui.QAction(_('&Close Window'), self,
                                    statusTip=_('Close this window'))
        winCloseAct.triggered.connect(self.close)
        winActions['WinCloseWindow'] = winCloseAct

        for name, action in winActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions.getValue(name)
            if not key.isEmpty():
                action.setShortcut(key)
        self.allActions.update(winActions)

    def setupToolbars(self):
        """Add toolbars based on option settings.
        """
        for toolbar in self.toolbars:
            self.removeToolBar(toolbar)
        self.toolbars = []
        numToolbars = globalref.toolbarOptions.getValue('ToolbarQuantity')
        print("Tool-Bar quantity: {}\n".format( numToolbars ))
        iconSize = globalref.toolbarOptions.getValue('ToolbarSize')
        for num in range(numToolbars):
            name = 'Toolbar{:d}'.format(num)
            toolbar = self.addToolBar(name)
            toolbar.setObjectName(name)
            toolbar.setIconSize(QtCore.QSize(iconSize, iconSize))
            self.toolbars.append(toolbar)
            commandList = globalref.toolbarOptions.getValue(name).split(',')
            for command in commandList:
                if command:
                    try:
                        toolbar.addAction(self.allActions[command])
                    except KeyError:
                        pass
                else:
                    toolbar.addSeparator()

    def setupMenus(self):
        """Add menu items for actions.
        """
        self.fileMenu = self.menuBar().addMenu(_('&File'))
        self.fileMenu.aboutToShow.connect(self.loadRecentMenu)
        self.fileMenu.addAction(self.allActions['FileNew'])
        self.fileMenu.addAction(self.allActions['FileOpen'])
        self.fileMenu.addAction(self.allActions['FileOpenSample'])
        self.fileMenu.addAction(self.allActions['FileImport'])
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.allActions['FileSave'])
        self.fileMenu.addAction(self.allActions['FileSaveAs'])
        self.fileMenu.addAction(self.allActions['FileCompressionOpt'])
        self.fileMenu.addAction(self.allActions['FileExport'])
        self.fileMenu.addAction(self.allActions['FileProperties'])
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.allActions['FilePrintSetup'])
        self.fileMenu.addAction(self.allActions['FilePrintPreview'])
        self.fileMenu.addAction(self.allActions['FilePrint'])
        self.fileMenu.addAction(self.allActions['FilePrintPdf'])
        self.fileMenu.addSeparator()
        self.recentFileSep = self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.allActions['FileQuit'])

        editMenu = self.menuBar().addMenu(_('&Edit'))
        editMenu.addAction(self.allActions['EditUndo'])
        editMenu.addAction(self.allActions['EditRedo'])
        editMenu.addSeparator()
        editMenu.addAction(self.allActions['EditCut'])
        editMenu.addAction(self.allActions['EditCopy'])
        editMenu.addAction(self.allActions['EditPaste'])
        editMenu.addAction(self.allActions['EditPastePlain'])
        editMenu.addSeparator()
        editMenu.addAction(self.allActions['EditBoldFont'])
        editMenu.addAction(self.allActions['EditItalicFont'])
        editMenu.addAction(self.allActions['EditUnderlineFont'])
        editMenu.addSeparator()
        # add action's parent to get the sub-menu
        editMenu.addMenu(self.allActions['EditFontSize'].parent())
        # add the action to activate the shortcut key
        self.addAction(self.allActions['EditFontSize'])
        editMenu.addAction(self.allActions['EditFontColor'])
        editMenu.addSeparator()
        editMenu.addAction(self.allActions['EditExtLink'])
        editMenu.addAction(self.allActions['EditIntLink'])
        editMenu.addSeparator()
        editMenu.addAction(self.allActions['EditSelectAll'])
        editMenu.addAction(self.allActions['EditClearFormat'])

        nodeMenu = self.menuBar().addMenu(_('&Node'))
        nodeMenu.addAction(self.allActions['NodeRename'])
        nodeMenu.addSeparator()
        nodeMenu.addAction(self.allActions['NodeInsertBefore'])
        nodeMenu.addAction(self.allActions['NodeInsertAfter'])
        nodeMenu.addAction(self.allActions['NodeAddChild'])
        nodeMenu.addSeparator()
        nodeMenu.addAction(self.allActions['NodeDelete'])
        nodeMenu.addAction(self.allActions['NodeIndent'])
        nodeMenu.addAction(self.allActions['NodeUnindent'])
        nodeMenu.addSeparator()
        nodeMenu.addAction(self.allActions['NodeMoveUp'])
        nodeMenu.addAction(self.allActions['NodeMoveDown'])
        nodeMenu.addAction(self.allActions['NodeMoveFirst'])
        nodeMenu.addAction(self.allActions['NodeMoveLast'])

        dataMenu = self.menuBar().addMenu(_('&Data'))
        # add action's parent to get the sub-menu
        dataMenu.addMenu(self.allActions['DataNodeType'].parent())
        # add the action to activate the shortcut key
        self.addAction(self.allActions['DataNodeType'])
        dataMenu.addAction(self.allActions['DataConfigType'])
        dataMenu.addAction(self.allActions['DataCopyType'])
        dataMenu.addSeparator()
        dataMenu.addAction(self.allActions['DataSortNodes'])
        dataMenu.addAction(self.allActions['DataNumbering'])
        dataMenu.addSeparator()
        dataMenu.addAction(self.allActions['DataFlatCategory'])
        dataMenu.addAction(self.allActions['DataAddCategory'])
        dataMenu.addSeparator()
        dataMenu.addAction(self.allActions['DataFlatLink'])
        dataMenu.addAction(self.allActions['DataArrangeLink'])

        toolsMenu = self.menuBar().addMenu(_('&Tools'))
        toolsMenu.addAction(self.allActions['ToolsFindText'])
        toolsMenu.addAction(self.allActions['ToolsFindCondition'])
        toolsMenu.addAction(self.allActions['ToolsFindReplace'])
        toolsMenu.addSeparator()
        toolsMenu.addAction(self.allActions['ToolsFilterText'])
        toolsMenu.addAction(self.allActions['ToolsFilterCondition'])
        toolsMenu.addSeparator()
        toolsMenu.addAction(self.allActions['ToolsSpellCheck'])
        toolsMenu.addSeparator()
        toolsMenu.addAction(self.allActions['ToolsGenOptions'])
        toolsMenu.addSeparator()
        toolsMenu.addAction(self.allActions['ToolsShortcuts'])
        toolsMenu.addAction(self.allActions['ToolsToolbars'])
        toolsMenu.addAction(self.allActions['ToolsFonts'])

        viewMenu = self.menuBar().addMenu(_('&View'))
        viewMenu.addAction(self.allActions['ViewExpandBranch'])
        viewMenu.addAction(self.allActions['ViewCollapseBranch'])
        viewMenu.addSeparator()
        viewMenu.addAction(self.allActions['ViewPrevSelect'])
        viewMenu.addAction(self.allActions['ViewNextSelect'])
        viewMenu.addSeparator()
        viewMenu.addAction(self.allActions['ViewDataOutput'])
        viewMenu.addAction(self.allActions['ViewDataEditor'])
        viewMenu.addAction(self.allActions['ViewTitleList'])
        viewMenu.addSeparator()
        viewMenu.addAction(self.allActions['ViewShowChildPane'])
        viewMenu.addAction(self.allActions['ViewShowDescend'])

        self.windowMenu = self.menuBar().addMenu(_('&Window'))
        self.windowMenu.aboutToShow.connect(self.loadWindowMenu)
        self.windowMenu.addAction(self.allActions['WinNewWindow'])
        self.windowMenu.addAction(self.allActions['WinCloseWindow'])
        self.windowMenu.addSeparator()

        helpMenu = self.menuBar().addMenu(_('&Help'))
        helpMenu.addAction(self.allActions['HelpBasic'])
        helpMenu.addAction(self.allActions['HelpFull'])
        helpMenu.addSeparator()
        helpMenu.addAction(self.allActions['HelpAbout'])
        helpMenu.addAction(self.allActions['HelpPlugin'])

    def loadRecentMenu(self):
        """Load recent file items to file menu before showing.
        """
        for action in self.fileMenu.actions():
            text = action.text()
            if len(text) > 1 and text[0] == '&' and '0' <= text[1] <= '9':
                self.fileMenu.removeAction(action)
        self.fileMenu.insertActions(self.recentFileSep,
                                    globalref.mainControl.recentFiles.
                                    getActions())

    def loadWindowMenu(self):
        """Load window list items to window menu before showing.
        """
        for action in self.windowMenu.actions():
            text = action.text()
            if len(text) > 1 and text[0] == '&' and '0' <= text[1] <= '9':
                self.windowMenu.removeAction(action)
        self.windowMenu.addActions(globalref.mainControl.windowActions())

    def viewExpandBranch(self):
        """Expand all children of the selected nodes.
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.treeView.expandSelectedBranches()
        QtGui.QApplication.restoreOverrideCursor()

    def viewCollapseBranch(self):
        """Collapse all children of the selected nodes.
        """
        for node in self.treeView.selectionModel().selectedNodes():
            self.treeView.collapseBranch(node)

    def viewPrevSelect(self):
        """Return to the previous tree selection.
        """
        self.treeView.selectionModel().restorePrevSelect()

    def viewNextSelect(self):
        """Go to the next tree selection in history.
        """
        self.treeView.selectionModel().restoreNextSelect()

    def viewRightTab(self, action):
        """Show the tab in the right-hand view given by action.

        Arguments:
            action -- the action triggered in the action group
        """
        if action == self.allActions['ViewDataOutput']:
            self.rightTabs.setCurrentWidget(self.outputSplitter)
        elif action == self.allActions['ViewDataEditor']:
            self.rightTabs.setCurrentWidget(self.editorSplitter)
        else:
            self.rightTabs.setCurrentWidget(self.titleSplitter)

    def viewDescendants(self, checked):
        """Set the output view to show indented descendants if checked.

        Arguments:
            checked -- True if to be shown, False if to be hidden
        """
        self.rightViewList[1].showDescendants = checked
        self.updateRightViews()

    def viewShowChildPane(self, checked):
        """Enable or disable the display of children in a split pane.

        Arguments:
            checked -- True if to be shown, False if to be hidden
        """
        for view in self.rightViewList:
            view.hideChildView = not checked
        self.updateRightViews()

    def saveWindowGeom(self):
        """Save window geometry parameters to history options.
        """
        globalref.histOptions.changeValue('WindowXSize', self.width())
        globalref.histOptions.changeValue('WindowYSize', self.height())
        globalref.histOptions.changeValue('WindowXPos', self.geometry().x())
        globalref.histOptions.changeValue('WindowYPos', self.geometry().y())
        leftWidth, rightWidth = self.mainSplitter.sizes()
        treePercent = int(100 * leftWidth / (leftWidth + rightWidth))
        globalref.histOptions.changeValue('TreeSplitPercent', treePercent)
        upperWidth, lowerWidth = self.outputSplitter.sizes()
        outputPercent = int(100 * upperWidth / (upperWidth + lowerWidth))
        globalref.histOptions.changeValue('OutputSplitPercent', outputPercent)
        upperWidth, lowerWidth = self.editorSplitter.sizes()
        editorPercent = int(100 * upperWidth / (upperWidth + lowerWidth))
        globalref.histOptions.changeValue('EditorSplitPercent', editorPercent)
        upperWidth, lowerWidth = self.titleSplitter.sizes()
        titlePercent = int(100 * upperWidth / (upperWidth + lowerWidth))
        globalref.histOptions.changeValue('TitleSplitPercent', titlePercent)
        tabNum = self.rightTabs.currentIndex()
        globalref.histOptions.changeValue('ActiveRightView', tabNum)

    def restoreWindowGeom(self, offset=0):
        """Restore window geometry from history options.

        Arguments:
            offset -- number of pixels to offset window, down and to right
        """
        rect = QtCore.QRect(globalref.histOptions.getValue('WindowXPos'),
                            globalref.histOptions.getValue('WindowYPos'),
                            globalref.histOptions.getValue('WindowXSize'),
                            globalref.histOptions.getValue('WindowYSize'))
        if rect.x() == -1000 and rect.y() == -1000:
            # let OS position window the first time
            self.resize(rect.size())
        else:
            if offset:
                rect.adjust(offset, offset, offset, offset)
            desktop = QtGui.QApplication.desktop()
            if desktop.isVirtualDesktop():
                availRect = desktop.screen().rect()
            else:
                availRect = desktop.availableGeometry(desktop.primaryScreen())
            rect = rect.intersected(availRect)
            self.setGeometry(rect)
        treeWidth = int(self.mainSplitter.width() / 100 *
                        globalref.histOptions.getValue('TreeSplitPercent'))
        self.mainSplitter.setSizes([treeWidth,
                                    self.mainSplitter.width() - treeWidth])
        outHeight = int(self.outputSplitter.height() / 100.0 *
                        globalref.histOptions.getValue('OutputSplitPercent'))
        self.outputSplitter.setSizes([outHeight,
                                     self.outputSplitter.height() - outHeight])
        editHeight = int(self.editorSplitter.height() / 100.0 *
                         globalref.histOptions.getValue('EditorSplitPercent'))
        self.editorSplitter.setSizes([editHeight,
                                    self.editorSplitter.height() - editHeight])
        titleHeight = int(self.titleSplitter.height() / 100.0 *
                          globalref.histOptions.getValue('TitleSplitPercent'))
        self.titleSplitter.setSizes([titleHeight,
                                    self.titleSplitter.height() - titleHeight])
        self.rightTabs.setCurrentIndex(globalref.histOptions.
                                       getValue('ActiveRightView'))

    def restoreDefaultWindowSize(self):
        """Set the window size to the initial setting in history options.
        """
        self.resize(globalref.histOptions.getDefaultValue('WindowXSize'),
                    globalref.histOptions.getDefaultValue('WindowYSize'))

    def saveToolbarPosition(self):
        """Save the toolbar position to the toolbar options.
        """
        toolbarPos = base64.b64encode(self.saveState().data()).decode('ascii')
        globalref.toolbarOptions.changeValue('ToolbarPosition', toolbarPos)
        globalref.toolbarOptions.writeFile()

    def restoreToolbarPosition(self):
        """Restore the toolbar position from the toolbar options.
        """
        toolbarPos = globalref.toolbarOptions.getValue('ToolbarPosition')
        if toolbarPos:
            self.restoreState(base64.b64decode(bytes(toolbarPos, 'ascii')))

    def dragEnterEvent(self, event):
        """Accept drags of files to this window.
        
        Arguments:
            event -- the drag event object
        """
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        """Open a file dropped onto this window.
        
         Arguments:
             event -- the drop event object
        """
        fileList = event.mimeData().urls()
        if fileList:
            globalref.mainControl.openFile(fileList[0].toLocalFile(), True)

    def changeEvent(self, event):
        """Detect an activation of the main window and emit a signal.

        Arguments:
            event -- the change event object
        """
        super().changeEvent(event)
        if (event.type() == QtCore.QEvent.ActivationChange and
                  QtGui.QApplication.activeWindow() == self):
            self.winActivated.emit(self)

    def closeEvent(self, event):
        """Signal that the view is closing and close if the flag allows it.

        Also save window status if necessary.
        Arguments:
            event -- the close event object
        """
        self.winClosing.emit(self)
        if self.allowCloseFlag:
            event.accept()
        else:
            event.ignore()
