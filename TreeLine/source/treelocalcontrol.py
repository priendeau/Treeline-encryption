#!/usr/bin/env python3

#******************************************************************************
# treelocalcontrol.py, provides a class for the main tree commands
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
import io
import sys
import gzip
import bz2 
import zlib
from xml.etree import ElementTree
from PyQt4 import QtCore, QtGui
import treemaincontrol
import treemodel
import treewindow
import treeopener
import printdata
import miscdialogs
import configdialog
import matheval
import undo
import p3
import exports
import spellcheck
import globalref


class TreeLocalControl(QtCore.QObject):
    """Class to handle controls local to a model/view combination.
    
    Provides methods for all local controls and stores a model & windows.
    """
    controlActivated = QtCore.pyqtSignal(QtCore.QObject)
    controlClosed = QtCore.pyqtSignal(QtCore.QObject)
    def __init__(self, allActions, filePath='', model=None, parent=None):
        """Initialize the local tree controls.
        
        Use an imported model if given or open the file if path is given.
        Always creates a new window.
        Arguments:
            allActions -- a dict containing the upper level actions
            filePath -- the file path or file object to open, if given
            model -- an imported model file, if given
            parent -- a parent object if given
        """
        super().__init__(parent)
        self.printData = printdata.PrintData(self)
        self.spellCheckLang = ''
        self.CompressionType = ''
        self.allActions = allActions.copy()
        self.setupActions()
        if hasattr(filePath, 'name'):
            self.filePath = filePath.name
        else:
            self.filePath = filePath
        if model:
            self.model = model
        elif filePath:
            opener = treeopener.TreeOpener()
            self.model = opener.readFile(filePath)
            self.printData.restoreXmlAttrs(opener.rootAttr)
            self.spellCheckLang = opener.rootAttr.get('spellchk', '')
            self.model.mathZeroBlanks = (opener.rootAttr.
                                         get('zeroblanks', 'y').
                                         startswith('y'))
            if opener.duplicateIdList:
                msg = _('Warning: duplicate Unique IDs found.\n')
                if len(opener.duplicateIdList) > 10:
                    msg += _('Many Unique IDs were re-assigned.\n')
                else:
                    msg += _('The following IDs were re-assigned:\n\t')
                    msg += '\n\t'.join(opener.duplicateIdList)
                msg += _('\nInternal link targets could be affected.')
                QtGui.QMessageBox.warning(None, 'TreeLine', msg)
        else:
            self.model = treemodel.TreeModel(True)
        self.model.allModified.connect(self.updateAll)
        self.model.nodeTitleModified.connect(self.updateRightViews)
        self.model.formats.fileInfoFormat.updateFileInfo(self.filePath,
                                                       self.model.fileInfoNode)
        self.modified           = False
        self.imported           = False
        self.compressed         = False
        self.encrypted          = False
        self.compression_type   = "Normal"
        self.encryption_Type    = "Normal"
        self.windowList         = []
        self.activeWindow       = None
        self.findReplaceNodeRef = (None, 0)
        QtGui.QApplication.clipboard().dataChanged.connect(self.
                                                           updatePasteAvail)
        self.updatePasteAvail()
        self.model.undoList = undo.UndoRedoList(self.allActions['EditUndo'],
                                                self)
        self.model.redoList = undo.UndoRedoList(self.allActions['EditRedo'],
                                                self)
        self.model.undoList.altListRef = self.model.redoList
        self.model.redoList.altListRef = self.model.undoList
        self.autoSaveTimer = QtCore.QTimer(self)
        self.autoSaveTimer.timeout.connect(self.autoSave)
        self.windowNew()

    def updateTreeNode(self, node, setModified=True):
        """Update the given node in all tree views.

        Arguments:
            node -- the node to be updated
            setModified -- if True, set the modified flag for this file
        """
        if node.setConditionalType():
            self.activeWindow.updateRightViews(outputOnly=True)
        if node.updateNodeMathFields():
            self.activeWindow.updateRightViews(outputOnly=True)
            if globalref.genOptions.getValue('ShowMath'):
                self.activeWindow.refreshDataEditViews()
        for window in self.windowList:
            window.updateTreeNode(node)
            if window != self.activeWindow:
                window.updateRightViews()
            if window.isFiltering():
                window.treeFilterView.updateItem(node)
        pluginInterface = globalref.mainControl.pluginInterface
        if pluginInterface:
            pluginInterface.execCallback(pluginInterface.dataChangeCallbacks,
                                         node)
        if setModified:
            self.setModified()

    def updateTree(self, setModified=True):
        """Update the full tree in all tree views and set the modified flag.

        Arguments:
            setModified -- if True, set the modified flag for this file
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        typeChanges = self.model.root.setDescendantConditionalTypes()
        self.updateAllMathFields()
        for window in self.windowList:
            window.updateTree()
            if window != self.activeWindow or typeChanges:
                window.updateRightViews()
            if window.isFiltering():
                window.treeFilterView.updateContents()
        if setModified:
            self.setModified()
        QtGui.QApplication.restoreOverrideCursor()

    def updateRightViews(self, setModified=False):
        """Update the right-hand view in all windows.

        Arguments:
            setModified -- if True, set the modified flag for this file
        """
        for window in self.windowList:
            window.updateRightViews()
        if setModified:
            self.setModified()

    def updateAll(self, setModified=True):
        """Update the full tree, right-hand views and set the modified flag.

        Arguments:
            setModified -- if True, set the modified flag for this file
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.model.root.setDescendantConditionalTypes()
        self.updateAllMathFields()
        if (globalref.mainControl.findConditionDialog and
            globalref.mainControl.findConditionDialog.isVisible()):
            globalref.mainControl.findConditionDialog.loadTypeNames()
        if (globalref.mainControl.findReplaceDialog and
            globalref.mainControl.findReplaceDialog.isVisible()):
            globalref.mainControl.findReplaceDialog.loadTypeNames()
        if (globalref.mainControl.filterConditionDialog and
            globalref.mainControl.filterConditionDialog.isVisible()):
            globalref.mainControl.filterConditionDialog.loadTypeNames()
        for window in self.windowList:
            window.updateTree()
            if window.isFiltering():
                window.treeFilterView.updateContents()
            window.updateRightViews()
        self.updateCommandsAvail()
        if setModified:
            self.setModified()
        QtGui.QApplication.restoreOverrideCursor()

    def updateCommandsAvail(self):
        """Set commands available based on node selections.
        """
        selNodes = self.currentSelectionModel().selectedNodes()
        notRoot = len(selNodes) and self.model.root not in selNodes
        hasGrandParent = (notRoot and None not in
                          [node.parent.parent for node in selNodes])
        hasPrevSibling = (len(selNodes) and None not in
                          [node.prevSibling() for node in selNodes])
        hasNextSibling = (len(selNodes) and None not in
                          [node.nextSibling() for node in selNodes])
        hasChildren = (len(selNodes) and 0 not in
                       [len(node.childList) for node in selNodes])
        self.allActions['NodeRename'].setEnabled(len(selNodes) == 1)
        self.allActions['NodeInsertBefore'].setEnabled(notRoot)
        self.allActions['NodeInsertAfter'].setEnabled(notRoot)
        self.allActions['NodeAddChild'].setEnabled(len(selNodes))
        self.allActions['NodeDelete'].setEnabled(notRoot)
        self.allActions['NodeIndent'].setEnabled(hasPrevSibling)
        self.allActions['NodeUnindent'].setEnabled(hasGrandParent)
        self.allActions['NodeMoveUp'].setEnabled(hasPrevSibling)
        self.allActions['NodeMoveDown'].setEnabled(hasNextSibling)
        self.allActions['NodeMoveFirst'].setEnabled(hasPrevSibling)
        self.allActions['NodeMoveLast'].setEnabled(hasNextSibling)
        self.allActions['DataNodeType'].setEnabled(len(selNodes))
        self.allActions['DataAddCategory'].setEnabled(hasChildren)
        self.allActions['DataFlatCategory'].setEnabled(hasChildren)
        if self.activeWindow.isFiltering():
            self.allActions['NodeInsertBefore'].setEnabled(False)
            self.allActions['NodeInsertAfter'].setEnabled(False)
            self.allActions['NodeAddChild'].setEnabled(False)
            self.allActions['NodeIndent'].setEnabled(False)
            self.allActions['NodeUnindent'].setEnabled(False)
            self.allActions['NodeMoveUp'].setEnabled(False)
            self.allActions['NodeMoveDown'].setEnabled(False)
            self.allActions['NodeMoveFirst'].setEnabled(False)
            self.allActions['NodeMoveLast'].setEnabled(False)
        if (globalref.mainControl.sortDialog and
            globalref.mainControl.sortDialog.isVisible()):
            globalref.mainControl.sortDialog.updateCommandsAvail()
        if (globalref.mainControl.numberingDialog and
            globalref.mainControl.numberingDialog.isVisible()):
            globalref.mainControl.numberingDialog.updateCommandsAvail()
        if (globalref.mainControl.findReplaceDialog and
            globalref.mainControl.findReplaceDialog.isVisible()):
            globalref.mainControl.findReplaceDialog.updateAvail()
        self.activeWindow.updateCommandsAvail()
        pluginInterface = globalref.mainControl.pluginInterface
        if pluginInterface:
            pluginInterface.execCallback(pluginInterface.selectChangeCallbacks)

    def updatePasteAvail(self):
        """Set paste available based on a signal.
        """
        mime = QtGui.QApplication.clipboard().mimeData()
        self.allActions['EditPaste'].setEnabled(len(mime.data('text/xml') or
                                                    mime.data('text/plain'))
                                                > 0)
        focusWidget = QtGui.QApplication.focusWidget()
        if hasattr(focusWidget, 'pastePlain'):
            focusWidget.updateActions()

    def updateWindowCaptions(self):
        """Update the caption for all windows.
        """
        for window in self.windowList:
            window.setCaption(self.filePath)

    def updateAllMathFields(self):
        """Recalculate all math fields in the entire tree.
        """
        for eqnRefDict in self.model.formats.mathLevelList:
            if list(eqnRefDict.values())[0][0].evalDirection != (matheval.
                                                                 upward):
                for node in self.model.root.descendantGen():
                    for eqnRef in eqnRefDict.get(node.formatName, []):
                        node.data[eqnRef.eqnField.name] = (eqnRef.eqnField.
                                                           equationValue(node))
            else:
                node = self.model.root.lastDescendant()
                while node:
                    for eqnRef in eqnRefDict.get(node.formatName, []):
                        node.data[eqnRef.eqnField.name] = (eqnRef.eqnField.
                                                           equationValue(node))
                    node = node.prevTreeNode()

    def currentSelectionModel(self):
        """Return the current tree's selection model.
        """
        return self.activeWindow.treeView.selectionModel()

    def currentTreeView(self):
        """Return the current left-hand tree view.
        """
        return self.activeWindow.treeView

    def setActiveWin(self, window):
        """When a window is activated, stores it and emits a signal.

        Arguments:
            window -- the new active window
        """
        self.activeWindow = window
        self.controlActivated.emit(self)
        self.updateCommandsAvail()
        filterTextDialog = globalref.mainControl.filterTextDialog
        if filterTextDialog and filterTextDialog.isVisible():
            filterTextDialog.updateAvail('', True)
        filterConditionDialog = globalref.mainControl.filterConditionDialog
        if filterConditionDialog and filterConditionDialog.isVisible():
            filterConditionDialog.updateFilterControls()

    def windowActions(self, startNum=1, active=False):
        """Return a list of window menu actions to select this file's windows.

        Arguments:
            startNum -- where to start numbering the action names
            active -- if True, activate the current active window
        """
        actions = []
        maxActionPathLength = 30
        abbrevPath = self.filePath
        if len(self.filePath) > maxActionPathLength:
            truncLength = maxActionPathLength - 3
            pos = self.filePath.find(os.sep, len(self.filePath) - truncLength)
            if pos < 0:
                pos = len(self.filePath) - truncLength
            abbrevPath = '...' + self.filePath[pos:]
        for window in self.windowList:
            action = QtGui.QAction('&{0:d} {1}'.format(startNum, abbrevPath),
                                   self, statusTip=self.filePath,
                                   checkable=True)
            action.triggered.connect(window.activateAndRaise)
            if active and window == self.activeWindow:
                action.setChecked(True)
            actions.append(action)
            startNum += 1
        return actions

    def autoSave(self):
        """Save a backup file if appropriate.

        Called from the timer.
        """
        if self.filePath and not self.imported:
            self.fileSave(True)

    def resetAutoSave(self):
        """Start or stop the auto-save timer based on file modified status.

        Also delete old autosave files if file becomes unmodified.
        """
        self.autoSaveTimer.stop()
        minutes = globalref.genOptions.getValue('AutoSaveMinutes')
        if minutes and self.modified:
            self.autoSaveTimer.start(60000 * minutes)
        else:
            self.deleteAutoSaveFile()

    def deleteAutoSaveFile(self):
        """Delete an auto save file if it exists.
        """
        filePath = self.filePath + '~'
        if self.filePath and os.path.exists(filePath):
            try:
                os.remove(filePath)
            except OSError:
                QtGui.QMessageBox.warning(self.activeWindow, 'TreeLine',
                                  _('Error - could not delete backup file {}').
                                  format(filePath))

    def checkWindowClose(self, window):
        """Check for modified files and delete ref when a window is closing.

        Arguments:
            window -- the window being closed
        """
        if len(self.windowList) > 1:
            self.windowList.remove(window)
            window.allowCloseFlag = True
            # keep ref until Qt window can fully close
            self.oldWindow = window
        elif self.promptModifiedOk():
            window.allowCloseFlag = True
            self.controlClosed.emit(self)
        else:
            window.allowCloseFlag = False

    def promptModifiedOk(self):
        """Ask for save if doc modified, return True if OK to continue.

        Save this doc if directed.
        Return True if not modified or if saved or if discarded.
        Return False on cancel.
        """
        if not self.modified or len(self.windowList) > 1:
            return True
        promptText = (_('Save changes to {}?').format(self.filePath) if
                      self.filePath else _('Save changes?'))
        ans = QtGui.QMessageBox.information(self.activeWindow, 'TreeLine',
                                            promptText,
                                            QtGui.QMessageBox.Save |
                                            QtGui.QMessageBox.Discard |
                                            QtGui.QMessageBox.Cancel, 
                                            QtGui.QMessageBox.Save)
        if ans == QtGui.QMessageBox.Save:
            self.fileSave()
        elif ans == QtGui.QMessageBox.Cancel:
            return False
        else:      # discard
            self.setModified(False)
        return True

    def closeWindows(self):
        """Close this control's windows prior to quiting the application.
        """
        for window in self.windowList:
            window.close()

    def setModified(self, modified=True):
        """Set the modified flag on this file and update commands available.
        """
        if modified != self.modified:
            self.modified = modified
            self.allActions['FileSave'].setEnabled(modified)
            self.resetAutoSave()
        pluginInterface = globalref.mainControl.pluginInterface
        if pluginInterface and modified:
            pluginInterface.execCallback(pluginInterface.fileModCallbacks)

    def setupActions(self):
        """Add the actions for contols at the local level.

        These actions affect an individual file, possibly in multiple windows.
        """
        localActions = {}

        fileSaveAct = QtGui.QAction(_('&Save'), self, toolTip=_('Save File'),
                                    statusTip=_('Save the current file'))
        fileSaveAct.setEnabled(False)
        fileSaveAct.triggered.connect(self.fileSave)
        localActions['FileSave'] = fileSaveAct

        fileSaveAsAct = QtGui.QAction(_('Save &As...'), self,
                                  statusTip=_('Save the file with a new name'))
        fileSaveAsAct.triggered.connect(self.fileSaveAs)
        localActions['FileSaveAs'] = fileSaveAsAct

        # Option added to specify a specific 
        # compression option. 
        fileCprOptAct = QtGui.QAction(_('File &Compression Options...'), self,
                                  statusTip=_('change type of compression, encryption'))
        fileCprOptAct.triggered.connect(self.fileCompressionOption)
        localActions['FileCompressionOpt'] = fileCprOptAct
        # End of addition . 

        fileExportAct = QtGui.QAction(_('&Export...'), self,
                       statusTip=_('Export the file in various other formats'))
        fileExportAct.triggered.connect(self.fileExport)
        localActions['FileExport'] = fileExportAct

        filePropertiesAct = QtGui.QAction(_('Prop&erties...'), self,
            statusTip=_('Set file parameters like compression and encryption'))
        
        filePropertiesAct.triggered.connect(self.fileProperties)
        localActions['FileProperties'] = filePropertiesAct

        filePrintSetupAct = QtGui.QAction(_('P&rint Setup...'), self,
              statusTip=_('Set margins, page size and other printing options'))
        filePrintSetupAct.triggered.connect(self.printData.printSetup)
        localActions['FilePrintSetup'] = filePrintSetupAct

        filePrintPreviewAct = QtGui.QAction(_('Print Pre&view...'), self,
                             statusTip=_('Show a preview of printing results'))
        filePrintPreviewAct.triggered.connect(self.printData.printPreview)
        localActions['FilePrintPreview'] = filePrintPreviewAct

        filePrintAct = QtGui.QAction(_('&Print...'), self,
                     statusTip=_('Print tree output based on current options'))
        filePrintAct.triggered.connect(self.printData.filePrint)
        localActions['FilePrint'] = filePrintAct

        filePrintPdfAct = QtGui.QAction(_('Print &to PDF...'), self,
                    statusTip=_('Export to PDF with current printing options'))
        filePrintPdfAct.triggered.connect(self.printData.filePrintPdf)
        localActions['FilePrintPdf'] = filePrintPdfAct

        editUndoAct = QtGui.QAction(_('&Undo'), self,
                                    statusTip=_('Undo the previous action'))
        editUndoAct.triggered.connect(self.editUndo)
        localActions['EditUndo'] = editUndoAct

        editRedoAct = QtGui.QAction(_('&Redo'), self,
                                    statusTip=_('Redo the previous undo'))
        editRedoAct.triggered.connect(self.editRedo)
        localActions['EditRedo'] = editRedoAct

        editCutAct = QtGui.QAction(_('Cu&t'), self,
                        statusTip=_('Cut the branch or text to the clipboard'))
        editCutAct.triggered.connect(self.editCut)
        localActions['EditCut'] = editCutAct

        editCopyAct = QtGui.QAction(_('&Copy'), self,
                       statusTip=_('Copy the branch or text to the clipboard'))
        editCopyAct.triggered.connect(self.editCopy)
        localActions['EditCopy'] = editCopyAct

        editPasteAct = QtGui.QAction(_('&Paste'), self,
                         statusTip=_('Paste nodes or text from the clipboard'))
        editPasteAct.triggered.connect(self.editPaste)
        localActions['EditPaste'] = editPasteAct

        editPastePlainAct = QtGui.QAction(_('P&aste Plain Text'), self,
                    statusTip=_('Paste non-formatted text from the clipboard'))
        editPastePlainAct.setEnabled(False)
        localActions['EditPastePlain'] = editPastePlainAct

        editBoldAct = QtGui.QAction(_('&Bold Font'), self,
                       statusTip=_('Set the current or selected font to bold'),
                          checkable=True)
        editBoldAct.setEnabled(False)
        localActions['EditBoldFont'] = editBoldAct

        editItalicAct = QtGui.QAction(_('&Italic Font'), self,
                     statusTip=_('Set the current or selected font to italic'),
                        checkable=True)
        editItalicAct.setEnabled(False)
        localActions['EditItalicFont'] = editItalicAct

        editUnderlineAct = QtGui.QAction(_('U&nderline Font'), self,
                  statusTip=_('Set the current or selected font to underline'),
                     checkable=True)
        editUnderlineAct.setEnabled(False)
        localActions['EditUnderlineFont'] = editUnderlineAct

        title = _('&Font Size')
        key = globalref.keyboardOptions.getValue('EditFontSize')
        if not key.isEmpty():
            title = '{0}  ({1})'.format(title, key.toString())
        self.fontSizeSubMenu = QtGui.QMenu(title,
                       statusTip=_('Set size of the current or selected text'))
        sizeActions = QtGui.QActionGroup(self)
        for size in (_('Small'), _('Default'), _('Large'), _('Larger'),
                     _('Largest')):
            action = QtGui.QAction(size, sizeActions)
            action.setCheckable(True)
        self.fontSizeSubMenu.addActions(sizeActions.actions())
        self.fontSizeSubMenu.setEnabled(False)
        fontSizeContextMenuAct = QtGui.QAction(_('Set Font Size'),
                                               self.fontSizeSubMenu)
        localActions['EditFontSize'] = fontSizeContextMenuAct

        editColorAct =  QtGui.QAction(_('Font C&olor...'), self,
                  statusTip=_('Set the color of the current or selected text'))
        editColorAct.setEnabled(False)
        localActions['EditFontColor'] = editColorAct

        editExtLinkAct = QtGui.QAction(_('&External Link...'), self,
                              statusTip=_('Add or modify an extrnal web link'))
        editExtLinkAct.setEnabled(False)
        localActions['EditExtLink'] = editExtLinkAct

        editIntLinkAct = QtGui.QAction(_('Internal &Link...'), self,
                            statusTip=_('Add or modify an internal node link'))
        editIntLinkAct.setEnabled(False)
        localActions['EditIntLink'] = editIntLinkAct

        editClearFormatAct =  QtGui.QAction(_('Clear For&matting'), self,
                      statusTip=_('Clear current or selected text formatting'))
        editClearFormatAct.setEnabled(False)
        localActions['EditClearFormat'] = editClearFormatAct

        nodeRenameAct = QtGui.QAction(_('&Rename'), self,
                            statusTip=_('Rename the current tree entry title'))
        nodeRenameAct.triggered.connect(self.nodeRename)
        localActions['NodeRename'] = nodeRenameAct

        nodeInBeforeAct = QtGui.QAction(_('Insert Sibling &Before'), self,
                            statusTip=_('Insert new sibling before selection'))
        nodeInBeforeAct.triggered.connect(self.nodeInBefore)
        localActions['NodeInsertBefore'] = nodeInBeforeAct

        nodeInAfterAct = QtGui.QAction(_('Insert Sibling &After'), self,
                            statusTip=_('Insert new sibling after selection'))
        nodeInAfterAct.triggered.connect(self.nodeInAfter)
        localActions['NodeInsertAfter'] = nodeInAfterAct

        nodeAddChildAct = QtGui.QAction(_('Add &Child'), self,
                               statusTip=_('Add new child to selected parent'))
        nodeAddChildAct.triggered.connect(self.nodeAddChild)
        localActions['NodeAddChild'] = nodeAddChildAct

        nodeDeleteAct = QtGui.QAction(_('&Delete Node'), self,
                                      statusTip=_('Delete the selected nodes'))
        nodeDeleteAct.triggered.connect(self.nodeDelete)
        localActions['NodeDelete'] = nodeDeleteAct

        nodeIndentAct = QtGui.QAction(_('&Indent Node'), self,
                                      statusTip=_('Indent the selected nodes'))
        nodeIndentAct.triggered.connect(self.nodeIndent)
        localActions['NodeIndent'] = nodeIndentAct

        nodeUnindentAct = QtGui.QAction(_('&Unindent Node'), self,
                                    statusTip=_('Unindent the selected nodes'))
        nodeUnindentAct.triggered.connect(self.nodeUnindent)
        localActions['NodeUnindent'] = nodeUnindentAct

        nodeMoveUpAct = QtGui.QAction(_('&Move Up'), self,
                                      statusTip=_('Move the selected nodes up'))
        nodeMoveUpAct.triggered.connect(self.nodeMoveUp)
        localActions['NodeMoveUp'] = nodeMoveUpAct

        nodeMoveDownAct = QtGui.QAction(_('M&ove Down'), self,
                                   statusTip=_('Move the selected nodes down'))
        nodeMoveDownAct.triggered.connect(self.nodeMoveDown)
        localActions['NodeMoveDown'] = nodeMoveDownAct

        nodeMoveFirstAct = QtGui.QAction(_('Move &First'), self,
               statusTip=_('Move the selected nodes to be the first children'))
        nodeMoveFirstAct.triggered.connect(self.nodeMoveFirst)
        localActions['NodeMoveFirst'] = nodeMoveFirstAct

        nodeMoveLastAct = QtGui.QAction(_('Move &Last'), self,
                statusTip=_('Move the selected nodes to be the last children'))
        nodeMoveLastAct.triggered.connect(self.nodeMoveLast)
        localActions['NodeMoveLast'] = nodeMoveLastAct

        title = _('&Set Node Type')
        key = globalref.keyboardOptions.getValue('DataNodeType')
        if not key.isEmpty():
            title = '{0}  ({1})'.format(title, key.toString())
        self.typeSubMenu = QtGui.QMenu(title,
                           statusTip=_('Set the node type for selected nodes'))
        self.typeSubMenu.aboutToShow.connect(self.loadTypeSubMenu)
        self.typeSubMenu.triggered.connect(self.dataSetType)
        typeContextMenuAct = QtGui.QAction(_('Set Node Type'), self.typeSubMenu)
        typeContextMenuAct.triggered.connect(self.showTypeContextMenu)
        localActions['DataNodeType'] = typeContextMenuAct

        dataCopyTypeAct = QtGui.QAction(_('Copy Types from &File...'), self,
              statusTip=_('Copy the configuration from another TreeLine file'))
        dataCopyTypeAct.triggered.connect(self.dataCopyType)
        localActions['DataCopyType'] = dataCopyTypeAct

        dataFlatCatAct = QtGui.QAction(_('Flatten &by Category'), self,
                         statusTip=_('Collapse descendants by merging fields'))
        dataFlatCatAct.triggered.connect(self.dataFlatCategory)
        localActions['DataFlatCategory'] = dataFlatCatAct

        dataAddCatAct = QtGui.QAction(_('Add Category &Level...'), self,
                           statusTip=_('Insert category nodes above children'))
        dataAddCatAct.triggered.connect(self.dataAddCategory)
        localActions['DataAddCategory'] = dataAddCatAct

        dataFlatLinkAct = QtGui.QAction(_('Flatten b&y Link...'), self,
                   statusTip=_('Collapse descendants and insert parent links'))
        dataFlatLinkAct.triggered.connect(self.dataFlatLink)
        localActions['DataFlatLink'] = dataFlatLinkAct

        dataArrangeLinkAct = QtGui.QAction(_('&Arrange by Link...'), self,
                         statusTip=_('Arrange descendants using parent links'))
        dataArrangeLinkAct.triggered.connect(self.dataArrangeLink)
        localActions['DataArrangeLink'] = dataArrangeLinkAct

        toolsSpellCheckAct = QtGui.QAction(_('&Spell Check...'), self,
                             statusTip=_('Spell check the tree\')s text data'))
        toolsSpellCheckAct.triggered.connect(self.toolsSpellCheck)
        localActions['ToolsSpellCheck'] = toolsSpellCheckAct

        winNewAct = QtGui.QAction(_('&New Window'), self,
                            statusTip=_('Open a new window for the same file'))
        winNewAct.triggered.connect(self.windowNew)
        localActions['WinNewWindow'] = winNewAct

        for name, action in localActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions.getValue(name)
            if not key.isEmpty():
                action.setShortcut(key)
        self.allActions.update(localActions)

    def fileSave(self, backupFile=False):
        """Save the currently active file.

        Arguments:
            backupFile -- if True, write auto-save backup file instead
        """
        if not self.filePath or self.imported:
            self.fileSaveAs()
            return
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        saveFilePath = self.filePath
        if backupFile:
            saveFilePath += '~'
        rootElement = self.model.root.elementXml()
        rootElement.attrib.update(self.model.formats.xmlAttr())
        rootElement.attrib.update(self.printData.xmlAttr())
        if self.spellCheckLang:
            rootElement.set('spellchk', self.spellCheckLang)
        if not self.model.mathZeroBlanks:
            rootElement.set('zeroblanks', 'n')
        elementTree = ElementTree.ElementTree(rootElement)
        try:
            # use binary for regular files to avoid newline translation
            fileIO = io.BytesIO()
            elementTree.write(fileIO, 'utf-8', True)
            data = fileIO.getvalue()
            fileIO.close()
            if self.compressed:
                data = gzip.compress(data)
            if self.encrypted:
                password = (globalref.mainControl.passwords.
                            get(self.filePath, ''))
                if not password:
                    QtGui.QApplication.restoreOverrideCursor()
                    dialog = miscdialogs.PasswordDialog(True, '',
                                                        self.activeWindow)
                    if dialog.exec_() != QtGui.QDialog.Accepted:
                        return
                    QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                    password = dialog.password
                    if miscdialogs.PasswordDialog.remember:
                        globalref.mainControl.passwords[self.
                                                       filePath] = password
                data = (treemaincontrol.encryptPrefix +
                        p3.p3_encrypt(data, password.encode()))
            with open(saveFilePath, 'wb') as f:
                f.write(data)
        except IOError:
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(self.activeWindow, 'TreeLine',
                                      _('Error - could not write to {}').
                                      format(saveFilePath))
        else:
            QtGui.QApplication.restoreOverrideCursor()
            if not backupFile:
                self.model.formats.fileInfoFormat.updateFileInfo(self.filePath,
                                                       self.model.fileInfoNode)
                self.setModified(False)
                self.imported = False
                self.activeWindow.statusBar().showMessage(_('File saved'),
                                                          3000)
                pluginInterface = globalref.mainControl.pluginInterface
                if pluginInterface:
                    pluginInterface.execCallback(pluginInterface.
                                                 fileSaveCallbacks)

    def fileSaveAs(self):
        """Prompt for a new file name and save the file.
        """
        oldFilePath = self.filePath
        oldModifiedFlag = self.modified
        oldImportFlag = self.imported
        self.modified = True
        self.imported = False
        filters = ';;'.join((globalref.fileFilters['trl'],
                             globalref.fileFilters['trlgz'],
                             globalref.fileFilters['trl.gz'],
                             globalref.fileFilters['trl.enc'],
                             globalref.fileFilters['trl.bz2'],
                             globalref.fileFilters['trl.enc.bz2'],
                             globalref.fileFilters['trl.enc.gz']))
        if self.encrypted:
            initFilter = globalref.fileFilters['trl.enc']
        elif self.compressed:
            initFilter = globalref.fileFilters['trl.gz']
        else:
            initFilter = globalref.fileFilters['trl']
        defaultFilePath = globalref.mainControl.defaultFilePath()
        defaultFilePath = os.path.splitext(defaultFilePath)[0] + '.trl'
        self.filePath, selectFilter = (QtGui.QFileDialog.
                                 getSaveFileNameAndFilter(self.activeWindow,
                                                       _('TreeLine - Save As'),
                                                       defaultFilePath,
                                                       filters, initFilter))
        if self.filePath:
            if not os.path.splitext(self.filePath)[1]:
                self.filePath += '.trl'
            if selectFilter != initFilter:
                self.compressed = (selectFilter ==
                                   globalref.fileFilters['trl.gz'])
                self.encrypted = (selectFilter ==
                                  globalref.fileFilters['trl.enc'])
            self.fileSave()
            if not self.modified:
                globalref.mainControl.recentFiles.addItem(self.filePath)
                self.updateWindowCaptions()
                return
        self.filePath = oldFilePath
        self.modified = oldModifiedFlag
        self.imported = oldImportFlag

    def fileExport(self):
        """Export the file in various other formats.
        """
        self.currentSelectionModel().sortSelection()
        exportControl = exports.ExportControl(self.model.root,
                                              self.currentSelectionModel().
                                              selectedNodes(),
                                              globalref.mainControl.
                                              defaultFilePath())
        try:
            exportControl.interactiveExport()
        except IOError:
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(self.activeWindow, 'TreeLine',
                                      _('Error - could not write to file'))
    def fileCompressionOption(self):
        """Show dialog to set compression / encryption information .
        """
        dialog = miscdialogs.FileMediaFormatDialog(self, self.activeWindow)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            self.setModified()
            


    def fileProperties(self):
        """Show dialog to set file parameters like compression and encryption.
        """
        origZeroBlanks = self.model.mathZeroBlanks
        dialog = miscdialogs.FilePropertiesDialog(self, self.activeWindow)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            self.setModified()
            if self.model.mathZeroBlanks != origZeroBlanks:
                self.updateAll(False)

    def editUndo(self):
        """Undo the previous action and update the views.
        """
        self.model.undoList.undo()
        self.updateAll(False)

    def editRedo(self):
        """Redo the previous undo and update the views.
        """
        self.model.redoList.undo()
        self.updateAll(False)

    def editCut(self):
        """Cut the branch or text to the clipboard.
        """
        widget = QtGui.QApplication.focusWidget()
        try:
            if widget.hasSelectedText():
                widget.cut()
                return
        except AttributeError:
            pass
        self.currentSelectionModel().selectedNodes().copyTree()
        self.nodeDelete()

    def editCopy(self):
        """Copy the branch or text to the clipboard.

        Copy from any selection in non-focused output view, or copy from
        any focused editor, or copy from tree.
        """
        splitter = self.activeWindow.rightTabs.currentWidget()
        if splitter == self.activeWindow.outputSplitter:
            for view in splitter.children():
                try:
                    if view.hasSelectedText():
                        view.copy()
                        return
                except AttributeError:
                    pass
        widget = QtGui.QApplication.focusWidget()
        try:
            if widget.hasSelectedText():
                widget.copy()
                return
        except AttributeError:
            pass
        self.currentSelectionModel().selectedNodes().copyTree()

    def editPaste(self):
        """Paste nodes or text from the clipboard.
        """
        if self.activeWindow.treeView.hasFocus():
            if (self.currentSelectionModel().selectedNodes().
                pasteMimeData(QtGui.QApplication.clipboard().mimeData())):
                for node in self.currentSelectionModel().selectedNodes():
                    node.expandInView()
                self.updateAll()
        else:
            widget = QtGui.QApplication.focusWidget()
            try:
                widget.paste()
            except AttributeError:
                pass

    def nodeRename(self):
        """Start the rename editor in the selected tree node.
        """
        if self.activeWindow.isFiltering():
            self.activeWindow.treeFilterView.editItem(self.activeWindow.
                                                      treeFilterView.
                                                      currentItem())
        else:
            self.activeWindow.treeView.endEditing()
            self.activeWindow.treeView.edit(self.currentSelectionModel().
                                            currentIndex())

    def nodeInBefore(self):
        """Insert new sibling before selection.
        """
        self.activeWindow.treeView.endEditing()
        undo.ChildListUndo(self.model.undoList, [node.parent for node in
                                                 self.currentSelectionModel().
                                                 selectedNodes()])
        newNodes = []
        for node in self.currentSelectionModel().selectedNodes():
            newNodes.append(node.parent.addNewChild(node, True))
        if globalref.genOptions.getValue('RenameNewNodes'):
            self.currentSelectionModel().selectNodes(newNodes, False)
            if len(newNodes) == 1:
                self.updateAll()
                self.activeWindow.treeView.edit(newNodes[0].index())
                return
        self.updateAll()

    def nodeInAfter(self):
        """Insert new sibling after selection.
        """
        self.activeWindow.treeView.endEditing()
        undo.ChildListUndo(self.model.undoList, [node.parent for node in
                                                 self.currentSelectionModel().
                                                 selectedNodes()])
        newNodes = []
        for node in self.currentSelectionModel().selectedNodes():
            newNodes.append(node.parent.addNewChild(node, False))
        if globalref.genOptions.getValue('RenameNewNodes'):
            self.currentSelectionModel().selectNodes(newNodes, False)
            if len(newNodes) == 1:
                self.updateAll()
                self.activeWindow.treeView.edit(newNodes[0].index())
                return
        self.updateAll()

    def nodeAddChild(self):
        """Add new child to selected parent.
        """
        self.activeWindow.treeView.endEditing()
        undo.ChildListUndo(self.model.undoList, self.currentSelectionModel().
                           selectedNodes())
        newNodes = []
        for node in self.currentSelectionModel().selectedNodes():
            newNodes.append(node.addNewChild())
            node.expandInView()
        if globalref.genOptions.getValue('RenameNewNodes'):
            self.currentSelectionModel().selectNodes(newNodes, False)
            if len(newNodes) == 1:
                self.updateAll()
                self.activeWindow.treeView.edit(newNodes[0].index())
                return
        self.updateAll()

    def nodeDelete(self):
        """Delete the selected nodes.
        """
        selNodes = self.currentSelectionModel().selectedNodes()
        if not selNodes or self.model.root in selNodes:
            return
        # gather next selected node in increasing order of desirability
        nextSel = [node.parent for node in selNodes]
        undo.ChildListUndo(self.model.undoList, nextSel)
        nextSel.extend([node.prevSibling() for node in selNodes])
        nextSel.extend([node.nextSibling() for node in selNodes])
        while not nextSel[-1] or nextSel[-1] in selNodes:
            del nextSel[-1]
        for node in selNodes:
            node.delete()
        self.currentSelectionModel().selectNode(nextSel[-1], False)
        self.updateAll()

    def nodeIndent(self):
        """Indent the selected nodes.
        """
        self.currentSelectionModel().sortSelection()
        selNodes = self.currentSelectionModel().selectedNodes()
        parentList = [node.parent for node in selNodes]
        siblingList = [node.prevSibling() for node in selNodes]
        undo.ChildListUndo(self.model.undoList, parentList + siblingList)
        for node in selNodes:
            node.indent()
            node.parent.expandInView()
        self.currentSelectionModel().selectNodes(selNodes, False)
        self.updateAll()

    def nodeUnindent(self):
        """Unindent the selected nodes.
        """
        self.currentSelectionModel().sortSelection()
        selNodes = self.currentSelectionModel().selectedNodes()
        parentList = [node.parent for node in selNodes]
        grandParentList = [node.parent for node in parentList]
        undo.ChildListUndo(self.model.undoList, parentList + grandParentList)
        for node in reversed(selNodes):
            node.unindent()
        self.currentSelectionModel().selectNodes(selNodes, False)
        self.updateAll()

    def nodeMoveUp(self):
        """Move the selected nodes upward in the sibling list.
        """
        self.currentSelectionModel().sortSelection()
        selNodes = self.currentSelectionModel().selectedNodes()
        undo.ChildListUndo(self.model.undoList,
                           [node.parent for node in selNodes])
        for node in selNodes:
            pos = node.parent.childList.index(node)
            del node.parent.childList[pos]
            node.parent.childList.insert(pos - 1, node)
        self.currentSelectionModel().selectNodes(selNodes, False)
        self.updateAll()

    def nodeMoveDown(self):
        """Move the selected nodes downward in the sibling list.
        """
        self.currentSelectionModel().sortSelection()
        selNodes = self.currentSelectionModel().selectedNodes()
        undo.ChildListUndo(self.model.undoList,
                           [node.parent for node in selNodes])
        for node in reversed(selNodes):
            pos = node.parent.childList.index(node)
            del node.parent.childList[pos]
            node.parent.childList.insert(pos + 1, node)
        self.currentSelectionModel().selectNodes(selNodes, False)
        self.updateAll()

    def nodeMoveFirst(self):
        """Move the selected nodes to be the first children.
        """
        self.currentSelectionModel().sortSelection()
        selNodes = self.currentSelectionModel().selectedNodes()
        undo.ChildListUndo(self.model.undoList,
                           [node.parent for node in selNodes])
        for node in reversed(selNodes):
            node.parent.childList.remove(node)
            node.parent.childList.insert(0, node)
        self.currentSelectionModel().selectNodes(selNodes, False)
        self.updateAll()

    def nodeMoveLast(self):
        """Move the selected nodes to be the last children.
        """
        self.currentSelectionModel().sortSelection()
        selNodes = self.currentSelectionModel().selectedNodes()
        undo.ChildListUndo(self.model.undoList,
                           [node.parent for node in selNodes])
        for node in selNodes:
            node.parent.childList.remove(node)
            node.parent.childList.append(node)
        self.currentSelectionModel().selectNodes(selNodes, False)
        self.updateAll()

    def dataSetType(self, action):
        """Change the type of selected nodes based on a menu selection.

        Arguments:
            action -- the menu action containing the new type name
        """
        newType = action.toolTip()   # gives menu name without the accelerator
        nodes = [node for node in self.currentSelectionModel().selectedNodes()
                 if node.formatName != newType]
        if nodes:
            undo.TypeUndo(self.model.undoList, nodes)
            for node in nodes:
                node.changeDataType(newType)
                self.updateTreeNode(node)
        self.updateAll()

    def loadTypeSubMenu(self):
        """Update type select submenu with type names and check marks.
        """
        selectTypes = {node.formatName for node in
                       self.currentSelectionModel().selectedNodes()}
        typeNames = self.model.formats.typeNames()
        self.typeSubMenu.clear()
        usedShortcuts = []
        for name in typeNames:
            shortcutPos = 0
            try:
                while [shortcutPos] in usedShortcuts:
                    shortcutPos += 1
                usedShortcuts.append(name[shortcutPos])
                text = '{0}&{1}'.format(name[:shortcutPos], name[shortcutPos:])
            except IndexError:
                text = name
            action = self.typeSubMenu.addAction(text)
            action.setCheckable(True)
            if name in selectTypes:
                action.setChecked(True)

    def showTypeContextMenu(self):
        """Show a type set menu at the current tree view item.
        """
        self.activeWindow.treeView.showTypeMenu(self.typeSubMenu)

    def dataCopyType(self):
        """Copy the configuration from another TreeLine file.
        """
        filters = ';;'.join((globalref.fileFilters['trl'],
                             globalref.fileFilters['trlgz'],
                             globalref.fileFilters['trlenc'],
                             globalref.fileFilters['all']))
        fileName = QtGui.QFileDialog.getOpenFileName(self.activeWindow,
                                   _('TreeLine - Open Configuration File'),
                                   globalref.mainControl.defaultFilePath(True),
                                   filters)
        if not fileName:
            return
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        tmpModel = None
        try:
            opener = treeopener.TreeOpener()
            tmpModel = opener.readFile(fileName)
            QtGui.QApplication.restoreOverrideCursor()
        except IOError:
            pass
        except treeopener.ParseError:
            QtGui.QApplication.restoreOverrideCursor()
            compressed = False
            encrypted = False
            fileObj = open(fileName, 'rb')
            # decompress before decrypt to support TreeLine 1.4 and earlier
            fileObj, compressed = (globalref.mainControl.
                                   decompressFile(fileName, fileObj))
            fileObj, encrypted = globalref.mainControl.decryptFile(fileName,
                                                                   fileObj)
            if fileObj:
                if encrypted and not compressed:
                    fileObj, compressed = (globalref.mainControl.
                                           decompressFile(fileName, fileObj))
                if compressed or encrypted:
                    try:
                        QtGui.QApplication.setOverrideCursor(QtCore.Qt.
                                                             WaitCursor)
                        tmpModel = opener.readFile(fileObj)
                    except (treeopener.ParseError, zlib.error):
                        pass
                fileObj.close()
        if not tmpModel:
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(self.activeWindow, 'TreeLine',
                                      _('Error - could not read file {0}').
                                      format(fileName))
            return
        self.model.formats.copyTypes(tmpModel.formats, self.model)
        QtGui.QApplication.restoreOverrideCursor()
        pluginInterface = globalref.mainControl.pluginInterface
        if pluginInterface:
            pluginInterface.execCallback(pluginInterface.formatChangeCallbacks)

    def dataFlatCategory(self):
        """Collapse descendant nodes by merging fields.

        Overwrites data in any fields with the same name.
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        selectList = self.currentSelectionModel().uniqueBranches()
        undo.BranchFormatUndo(self.model.undoList, selectList,
                              self.model.formats)
        origFormats = self.model.undoList[-1].treeFormats
        for node in selectList:
            node.flatChildCategory(origFormats)
        self.updateAll()
        dialog = globalref.mainControl.configDialog
        if dialog and dialog.isVisible():
            dialog.reset()
        QtGui.QApplication.restoreOverrideCursor()

    def dataAddCategory(self):
        """Insert category nodes above children.
        """
        selectList = self.currentSelectionModel().uniqueBranches()
        children = []
        for node in selectList:
            children.extend(node.childList)
        fieldList = self.model.formats.commonFields(children)
        if not fieldList:
            QtGui.QMessageBox.warning(self.activeWindow, 'TreeLine',
                                      _('Cannot expand without common fields'))
            return
        dialog = miscdialogs.FieldSelectDialog(_('Category Fields'),
                                              _('Select fields for new level'),
                                              fieldList, self.activeWindow)
        if dialog.exec_() != QtGui.QDialog.Accepted:
            return
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        undo.BranchFormatUndo(self.model.undoList, selectList,
                              self.model.formats)
        for node in selectList:
            node.addChildCategory(dialog.selectedFields)
        self.updateAll()
        dialog = globalref.mainControl.configDialog
        if dialog and dialog.isVisible():
            dialog.reset()
        QtGui.QApplication.restoreOverrideCursor()

    def dataFlatLink(self):
        """Collapse descendants and insert parent links.
        """
        dialog = configdialog.NameEntryDialog(_('Flatten by Link'),
                                              _('Enter a new field name for '
                                              'parent links'), '', '', [],
                                              self.activeWindow)
        if dialog.exec_() != QtGui.QDialog.Accepted:
            return
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        newFieldName = dialog.text
        selectList = self.currentSelectionModel().uniqueBranches()
        undo.BranchFormatUndo(self.model.undoList, selectList,
                              self.model.formats)
        for node in selectList:
            node.flatChildLink(newFieldName)
        self.updateAll()
        dialog = globalref.mainControl.configDialog
        if dialog and dialog.isVisible():
            dialog.reset()
        QtGui.QApplication.restoreOverrideCursor()

    def dataArrangeLink(self):
        """Arrange nodes using parent links.
        """
        selectList = self.currentSelectionModel().uniqueBranches()
        children = []
        for node in selectList:
            children.extend(node.childList)
        fieldList = self.model.formats.commonFields(children)
        if not fieldList:
            QtGui.QMessageBox.warning(self.activeWindow, 'TreeLine',
                                      _('Cannot expand without common fields'))
            return
        linkField, ok = QtGui.QInputDialog.getItem(self.activeWindow,
                                                   _('Link Field'),
                                                   _('Select field with links '
                                                   'to parents'), fieldList,
                                                   0, False)
        if not ok:
            return
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        undo.BranchUndo(self.model.undoList, selectList)
        for node in selectList:
            node.arrangeByLink(linkField)
        self.updateAll()
        QtGui.QApplication.restoreOverrideCursor()

    def findNodesByWords(self, wordList, titlesOnly=False, forward=True):
        """Search for and select nodes that match the word list criteria.

        Called from the text find dialog.
        Returns True if found, otherwise False.
        Arguments:
            wordList -- a list of words or phrases to find
            titleOnly -- search only in the title text if True
            forward -- next if True, previous if False
        """
        currentNode = self.currentSelectionModel().currentNode()
        node = currentNode
        while True:
            if self.activeWindow.isFiltering():
                node = self.activeWindow.treeFilterView.nextPrevNode(node,
                                                                     forward)
            else:
                if forward:
                    node = node.nextTreeNode(True)
                else:
                    node = node.prevTreeNode(True)
            if node is currentNode:
                return False
            if node.wordSearch(wordList, titlesOnly):
                self.currentSelectionModel().selectNode(node, True, True)
                rightView = self.activeWindow.rightParentView()
                if rightView:
                    rightView.highlightSearch(wordList=wordList)
                return True

    def findNodesByRegExp(self, regExpList, titlesOnly=False, forward=True):
        """Search for and select nodes that match the regular exp criteria.

        Called from the text find dialog.
        Returns True if found, otherwise False.
        Arguments:
            regExpList -- a list of regular expression objects
            titleOnly -- search only in the title text if True
            forward -- next if True, previous if False
        """
        currentNode = self.currentSelectionModel().currentNode()
        node = currentNode
        while True:
            if forward:
                node = node.nextTreeNode(True)
            else:
                node = node.prevTreeNode(True)
            if node is currentNode:
                return False
            if node.regExpSearch(regExpList, titlesOnly):
                self.currentSelectionModel().selectNode(node, True, True)
                rightView = self.activeWindow.rightParentView()
                if rightView:
                    rightView.highlightSearch(regExpList=regExpList)
                return True

    def findNodesForReplace(self, searchText='', regExpObj=None, typeName='',
                            fieldName='', forward=True):
        """Search for & select nodes that match the criteria prior to replace.

        Called from the find replace dialog.
        Returns True if found, otherwise False.
        Arguments:
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
            typeName -- if given, verify that this node matches this type
            fieldName -- if given, only find matches under this type name
            forward -- next if True, previous if False
        """
        currentNode = self.currentSelectionModel().currentNode()
        lastFoundNode, currentNumMatches = self.findReplaceNodeRef
        numMatches = currentNumMatches
        if lastFoundNode is not currentNode:
            numMatches = 0
        node = currentNode
        if not forward:
            if numMatches == 0:
                numMatches = -1   # find last one if backward
            elif numMatches == 1:
                numMatches = sys.maxsize   # no match if on first one
            else:
                numMatches -= 2
        while True:
            matchedField, numMatches, fieldPos = node.searchReplace(searchText,
                                                                    regExpObj,
                                                                    numMatches,
                                                                    typeName,
                                                                    fieldName)
            if matchedField:
                fieldNum = node.nodeFormat().fieldNames().index(matchedField)
                self.currentSelectionModel().selectNode(node, True, True)
                self.activeWindow.rightTabs.setCurrentWidget(self.activeWindow.
                                                             editorSplitter)
                dataView = self.activeWindow.rightParentView()
                if dataView:
                    dataView.highlightMatch(searchText, regExpObj, fieldNum,
                                            fieldPos - 1)
                self.findReplaceNodeRef = (node, numMatches)
                return True
            if self.activeWindow.isFiltering():
                node = self.activeWindow.treeFilterView.nextPrevNode(node,
                                                                     forward)
            else:
                if forward:
                    node = node.nextTreeNode(True)
                else:
                    node = node.prevTreeNode(True)
            if node is currentNode and currentNumMatches == 0:
                self.findReplaceNodeRef = (None, 0)
                return False
            numMatches = 0 if forward else -1

    def replaceInCurrentNode(self, searchText='', regExpObj=None, typeName='',
                             fieldName='', replaceText=None):
        """Replace the current match in the current node.

        Called from the find replace dialog.
        Returns True if replaced, otherwise False.
        Arguments:
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
            typeName -- if given, verify that this node matches this type
            fieldName -- if given, only find matches under this type name
            replaceText -- if not None, replace a match with this string
        """
        node = self.currentSelectionModel().currentNode()
        lastFoundNode, numMatches = self.findReplaceNodeRef
        if numMatches > 0:
            numMatches -= 1
        if lastFoundNode is not node:
            numMatches = 0
        dataUndo = undo.DataUndo(self.model.undoList, node)
        matchedField, num1, num2 = node.searchReplace(searchText, regExpObj,
                                                      numMatches, typeName,
                                                      fieldName, replaceText)
        if ((searchText and searchText in replaceText) or
            (regExpObj and r'\g<0>' in replaceText) or
            (regExpObj and regExpObj.pattern.startswith('(') and
             regExpObj.pattern.endswith(')') and r'\1' in replaceText)):
            numMatches += 1    # check for recursive matches
        self.findReplaceNodeRef = (node, numMatches)
        if matchedField:
            self.updateRightViews(True)
            return True
        self.model.undoList.removeLastUndo(dataUndo)
        return False

    def replaceAll(self, searchText='', regExpObj=None, typeName='',
                   fieldName='', replaceText=None):
        """Replace all matches in all nodes.

        Called from the find replace dialog.
        Returns number of matches replaced.
        Arguments:
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
            typeName -- if given, verify that this node matches this type
            fieldName -- if given, only find matches under this type name
            replaceText -- if not None, replace a match with this string
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        dataUndo = undo.BranchUndo(self.model.undoList, self.model.root)
        totalMatches = 0
        for node in self.model.root.descendantGen():
            field, matchQty, num = node.searchReplace(searchText, regExpObj,
                                                      0, typeName, fieldName,
                                                      replaceText, True)
            totalMatches += matchQty
        self.findReplaceNodeRef = (None, 0)
        if totalMatches > 0:
            self.updateAll(True)
        else:
            self.model.undoList.removeLastUndo(dataUndo)
        QtGui.QApplication.restoreOverrideCursor()
        return totalMatches

    def findNodesByCondition(self, conditional, forward=True):
        """Search for and select nodes that match the regular exp criteria.

        Called from the conditional find dialog.
        Returns True if found, otherwise False.
        Arguments:
            conditional -- the Conditional object to be evaluated
            forward -- next if True, previous if False
        """
        currentNode = self.currentSelectionModel().currentNode()
        node = currentNode
        while True:
            if forward:
                node = node.nextTreeNode(True)
            else:
                node = node.prevTreeNode(True)
            if node is currentNode:
                return False
            if conditional.evaluate(node):
                self.currentSelectionModel().selectNode(node, True, True)
                return True

    def toolsSpellCheck(self):
        """Spell check the tree text data.
        """
        try:
            spellCheckOp = spellcheck.SpellCheckOperation(self)
        except spellcheck.SpellCheckError:
            return
        spellCheckOp.spellCheck()

    def windowNew(self):
        """Open a new window for this file.
        """
        window = treewindow.TreeWindow(self.model, self.allActions)
        window.selectChanged.connect(self.updateCommandsAvail)
        window.nodeModified.connect(self.updateTreeNode)
        window.treeModified.connect(self.updateTree)
        window.winActivated.connect(self.setActiveWin)
        window.winClosing.connect(self.checkWindowClose)
        self.windowList.append(window)
        self.updateWindowCaptions()
        oldControl = globalref.mainControl.activeControl
        if not oldControl:
            if globalref.genOptions.getValue('SaveWindowGeom'):
                # restore window geometry for first window
                window.restoreWindowGeom()
        elif (globalref.genOptions.getValue('OpenNewWindow') or
              len(self.windowList) > 1):
            # cascade additional windows
            oldControl.activeWindow.saveWindowGeom()
            window.restoreWindowGeom(30)
        else:
            # close old window for single-window operation
            oldControl.activeWindow.saveWindowGeom()
            oldControl.activeWindow.close()
            window.restoreWindowGeom()
        self.activeWindow = window
        window.show()
        window.updateRightViews()
        pluginInterface = globalref.mainControl.pluginInterface
        if pluginInterface and oldControl == self:
            pluginInterface.execCallback(pluginInterface.newWindowCallbacks)
