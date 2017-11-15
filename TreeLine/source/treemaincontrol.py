#!/usr/bin/env python3

#******************************************************************************
# treemaincontrol.py, provides a class for global tree commands
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import sys
import os.path
import io
import gzip
import zlib
from PyQt4 import QtCore, QtGui, QtNetwork
import globalref
import options
import optiondefaults
import recentfiles
import treelocalcontrol
import treeopener
import plugininterface
import p3
import configdialog
import miscdialogs
import conditional
import imports
import icondict
import helpview
try:
    from __main__ import __version__, __author__
except ImportError:
    __version__ = ''
    __author__ = ''
try:
    from __main__ import docPath, iconPath, templatePath, samplePath
except ImportError:
    docPath = None
    iconPath = None
    templatePath = None
    samplePath = None

encryptPrefix = b'>>TL+enc'


class TreeMainControl(QtCore.QObject):
    """Class to handle all global controls.
    
    Provides methods for all controls and stores local control objects.
    """
    def __init__(self, filePaths, parent=None):
        """Initialize the main tree controls

        Arguments:
            filePaths -- a list of files to open
            parent -- the parent QObject if given
        """
        super().__init__(parent)
        self.localControls = []
        self.activeControl = None
        self.pluginInterface = None
        self.pluginInstances = []
        self.pluginDescriptions = []
        self.configDialog = None
        self.sortDialog = None
        self.numberingDialog = None
        self.findTextDialog = None
        self.findConditionDialog = None
        self.findReplaceDialog = None
        self.filterTextDialog = None
        self.filterConditionDialog = None
        self.basicHelpView = None
        self.serverSocket = None
        self.passwords = {}
        globalref.mainControl = self
        try:
            # check for existing TreeLine session
            socket = QtNetwork.QLocalSocket()
            socket.connectToServer('treeline2-session',
                                   QtCore.QIODevice.WriteOnly)
            # if found, send files to open and exit TreeLine
            if socket.waitForConnected(1000):
                socket.write(bytes(repr(filePaths), 'utf-8'))
                if socket.waitForBytesWritten(1000):
                    socket.close()
                    sys.exit(0)
            # start local server to listen for attempt to start new session
            self.serverSocket = QtNetwork.QLocalServer()
            self.serverSocket.listen('treeline2-session')
            self.serverSocket.newConnection.connect(self.getSocket)
        except AttributeError:
            print(_('Warning:  Could not create local socket'))
        mainVersion = '.'.join(__version__.split('.')[:2])
        globalref.genOptions = options.Options('general', 'TreeLine',
                                               mainVersion, 'bellz')
        optiondefaults.setGenOptionDefaults(globalref.genOptions)
        globalref.miscOptions  = options.Options('misc')
        optiondefaults.setMiscOptionDefaults(globalref.miscOptions)
        globalref.histOptions = options.Options('history')
        optiondefaults.setHistOptionDefaults(globalref.histOptions)
        globalref.toolbarOptions = options.Options('toolbar')
        optiondefaults.setToolbarOptionDefaults(globalref.toolbarOptions)
        globalref.keyboardOptions = options.Options('keyboard')
        optiondefaults.setKeyboardOptionDefaults(globalref.keyboardOptions)
        try:
            globalref.genOptions.readFile()
            globalref.miscOptions.readFile()
            recentfiles.setRecentOptionDefaults()
            globalref.histOptions.readFile()
            globalref.toolbarOptions.readFile()
            globalref.keyboardOptions.readFile()
        except IOError:
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                'TreeLine',
                                _('Error - could not write config file to {}').
                                format(options.Options.basePath))
        iconPathList = self.findResourcePaths('icons', iconPath)
        globalref.toolIcons = icondict.IconDict([os.path.join(path, 'toolbar')
                                                 for path in iconPathList],
                                                ['', '32x32', '16x16'])
        globalref.toolIcons.loadAllIcons()
        windowIcon = globalref.toolIcons.getIcon('treelogo')
        if windowIcon:
            QtGui.QApplication.setWindowIcon(windowIcon)
        globalref.treeIcons = icondict.IconDict(iconPathList, ['', 'tree'])
        self.recentFiles = recentfiles.RecentFileList()
        if globalref.genOptions.getValue('AutoFileOpen') and not filePaths:
            recentPath = self.recentFiles.firstPath()
            if recentPath:
                filePaths = [recentPath]
        self.allActions = {}
        self.setupActions()
        QtGui.qApp.focusChanged.connect(self.updateActionsAvail)
        if filePaths:
            for path in filePaths:
                self.openFile(path)
        else:
            self.createLocalControl()
        self.setupPlugins()

    def getSocket(self):
        """Open a socket from an attempt to open a second Treeline instance.

        Opens the file (or raise and focus if open) in this instance.
        """
        socket = self.serverSocket.nextPendingConnection()
        if socket and socket.waitForReadyRead(1000):
            data = str(socket.readAll(), 'utf-8')
            if data.startswith('[') and data.endswith(']'):
                filePaths = eval(data)
                if filePaths:
                    for path in filePaths:
                        self.openFile(path)
                else:
                    self.activeControl.activeWindow.activateAndRaise()

    def findResourcePaths(self, resourceName, preferredPath=None):
        """Return a list of potential non-empty paths for the resource name.

        List includes preferred, module and user option paths.
        Arguments:
            resourceName -- the typical name of the resource directory
            preferredPath -- add this as the first path if given
        """
        modPath = os.path.abspath(sys.path[0])
        pathList = [os.path.join(options.Options.basePath, resourceName),
                    os.path.join(modPath, '..', resourceName),
                    os.path.join(modPath, resourceName)]
        if preferredPath:
            pathList.insert(1, preferredPath)
        return [path for path in pathList if os.path.exists(path) and
                os.listdir(path)]

    def findResourceFile(self, fileName, resourceName, preferredPath=None):
        """Return a full path to a resource file.

        Add a language code before the extension if it exists.
        Arguments:
            fileName -- the name of the file to find
            resourceName -- the typical name of the resource directory
            preferredPath -- search this path first if given
        """
        fileList = [fileName]
        if globalref.lang and globalref.lang != 'C':
            fileList[0:0] = [fileName.replace('.', '_{0}.'.
                                              format(globalref.lang)),
                             fileName.replace('.', '_{0}.'.
                                              format(globalref.lang[:2]))]
        for fileName in fileList:
            for path in self.findResourcePaths(resourceName, preferredPath):
                if os.access(os.path.join(path, fileName), os.R_OK):
                    return os.path.join(path, fileName)
        return ''

    def updateAllViews(self):
        """Update the views associated with all local controls.
        """
        for control in self.localControls:
            control.updateAll(False)

    def defaultFilePath(self, dirOnly=False):
        """Return a reasonable default file path.

        Used for open, save-as, import and export.
        Arguments:
            dirOnly -- if True, do not include basename of file
        """
        filePath = ''
        if  self.activeControl:
            filePath = self.activeControl.filePath
        if not filePath:
            filePath = self.recentFiles.firstDir()
            if not filePath:
                 filePath = os.path.expanduser('~')
                 if filePath == '~':
                     filePath = ''
        if dirOnly:
            filePath = os.path.dirname(filePath)
        return filePath

    def openFile(self, path, checkModified=False, importOnFail=True):
        """Open the file given by path if not already open.

        If already open in a different window, focus and raise the window.
        Arguments:
            path -- the name of the file path to read
            checkModified -- if True, prompt user about current modified file
            importOnFail -- if True, prompts for import on non-TreeLine files
        """
        path = os.path.abspath(path)
        match = [control for control in self.localControls if 
                 os.path.normcase(control.filePath) == os.path.normcase(path)]
        if match and self.activeControl not in match:
            control = match[0]
            control.activeWindow.activateAndRaise()
            self.updateLocalControlRef(control)
        elif (not checkModified or
              globalref.genOptions.getValue('OpenNewWindow') or
              self.activeControl.promptModifiedOk()):
            if not self.checkAutoSave(path):
                if not self.localControls:
                    self.createLocalControl()
                    return
            try:
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                self.createLocalControl(path)
                self.recentFiles.addItem(path)
                if globalref.genOptions.getValue('SaveTreeStates'):
                    self.recentFiles.retrieveTreeState(self.activeControl)
                QtGui.QApplication.restoreOverrideCursor()
                if self.pluginInterface:
                    self.pluginInterface.execCallback(self.pluginInterface.
                                                      fileOpenCallbacks)
            except IOError:
                QtGui.QApplication.restoreOverrideCursor()
                QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                         'TreeLine',
                                         _('Error - could not read file {0}').
                                         format(path))
                self.recentFiles.removeItem(path)
            except treeopener.ParseError:
                QtGui.QApplication.restoreOverrideCursor()
                compressed = False
                encrypted = False
                compress_type = 'normal'
                encryption_type = 'normal'
                
                fileObj = open(path, 'rb')
                # decompress before decrypt to support TreeLine 1.4 and earlier
                fileObj, compressed = self.decompressFile(path, fileObj)
                fileObj, encrypted = self.decryptFile(path, fileObj)
                if not fileObj:
                    if not self.localControls:
                        self.createLocalControl()
                        QtGui.QApplication.restoreOverrideCursor()
                        return
                if encrypted and not compressed:
                    fileObj, compressed = self.decompressFile(path, fileObj)
                if compressed or encrypted:
                    try:
                        QtGui.QApplication.setOverrideCursor(QtCore.Qt.
                                                             WaitCursor)
                        self.createLocalControl(fileObj)
                        self.recentFiles.addItem(path)
                        if globalref.genOptions.getValue('SaveTreeStates'):
                            self.recentFiles.retrieveTreeState(self.
                                                               activeControl)
                        self.activeControl.compressed = compressed
                        self.activeControl.encrypted = encrypted
                        QtGui.QApplication.restoreOverrideCursor()
                        if self.pluginInterface:
                            self.pluginInterface.execCallback(self.
                                                              pluginInterface.
                                                             fileOpenCallbacks)
                    except (treeopener.ParseError, zlib.error):
                        QtGui.QApplication.restoreOverrideCursor()
                        QtGui.QMessageBox.warning(QtGui.QApplication.
                                                  activeWindow(),
                                                  'TreeLine',
                                                  _('Error - {0} is not a '
                                                  'valid TreeLine file').
                                                  format(path))
                    fileObj.close()
                else:
                    fileObj.close()
                    if importOnFail:
                        importControl = imports.ImportControl(path)
                        model = importControl.interactiveImport(True)
                        if model:
                            self.createLocalControl(importControl.filePath,
                                                    model)
                            self.activeControl.imported = True
            if not self.localControls:
                self.createLocalControl()

    def decompressFile(self, path, fileObj):
        """Check for compression and decompress the fileObj if needed.

        Return a tuple of the file object and True if it was compressed.
        Arguments:
            path -- the path name for reference
            fileObj -- the file object to check and decompress
        """
        prefix = fileObj.read(2)
        fileObj.seek(0)
        if prefix != b'\037\213':
            return (fileObj, False)
        fileObj = gzip.GzipFile(fileobj=fileObj)
        fileObj.name = path
        return (fileObj, True)

    def decryptFile(self, path, fileObj):
        """Check for encryption and decrypt the fileObj if needed.

        Return a tuple of the file object and True if it was encrypted.
        Return None for the file object if the user cancels.
        Arguments:
            path -- the path name for reference
            fileObj -- the file object to check and decrypt
        """
        if fileObj.read(len(encryptPrefix)) != encryptPrefix:
            fileObj.seek(0)
            return (fileObj, False)
        while True:
            password = self.passwords.get(path, '')
            if not password:
                dialog = miscdialogs.PasswordDialog(False,
                                                    os.path.basename(path),
                                                    QtGui.QApplication.
                                                    activeWindow())
                if dialog.exec_() != QtGui.QDialog.Accepted:
                    fileObj.close()
                    return (None, True)
                password = dialog.password
                if miscdialogs.PasswordDialog.remember:
                    self.passwords[path] = password
            try:
                text = p3.p3_decrypt(fileObj.read(), password.encode())
                fileIO = io.BytesIO(text)
                fileIO.name = path
                return (fileIO, True)
            except p3.CryptError:
                try:
                    del self.passwords[path]
                except KeyError:
                    pass

    def checkAutoSave(self, filePath):
        """Check for presence of auto save file & prompt user.

        Return True if OK to contimue, False if aborting.
        Arguments:
            filePath -- the base path name to search for a backup
        """
        if not globalref.genOptions.getValue('AutoSaveMinutes'):
            return True
        basePath = filePath
        filePath = filePath + '~'
        if not os.access(filePath, os.R_OK):
            return True
        msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Information, 'TreeLine',
                                _('Backup file "{}" exists.\nA previous '
                                  'session may have crashed').format(filePath),
                                QtGui.QMessageBox.NoButton,
                                QtGui.QApplication.activeWindow())
        restoreButton = msgBox.addButton(_('&Restore Backup'),
                                         QtGui.QMessageBox.ApplyRole)
        deleteButton = msgBox.addButton(_('&Delete Backup'),
                                        QtGui.QMessageBox.DestructiveRole)
        cancelButton = msgBox.addButton(_('&Cancel File Open'),
                                        QtGui.QMessageBox.RejectRole)
        msgBox.exec_()
        if msgBox.clickedButton() == restoreButton:
            self.openFile(filePath)
            if self.activeControl.filePath != filePath:
                return False
            try:
                os.remove(basePath)
                os.rename(filePath, basePath)
            except OSError:
                QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                  'TreeLine',
                                  _('Error - could not rename "{0}" to "{1}"').
                                     format(filePath, basePath))
                return False
            self.activeControl.filePath = basePath
            self.activeControl.updateWindowCaptions()
        elif msgBox.clickedButton() == deleteButton:
            try:
                os.remove(filePath)
            except OSError:
                QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                  'TreeLine',
                                  _('Error - could not remove backup file {}').
                                  format(filePath))
        else:   # cancel button
            return False
        return True

    def createLocalControl(self, path='', model=None):
        """Create a new local control object and add it to the list.

        Use an imported model if given or open the file if path is given.
        Arguments:
            path -- the path for the control to open
            model -- the imported model to use
        """
        localControl = treelocalcontrol.TreeLocalControl(self.allActions, path,
                                                         model)
        localControl.controlActivated.connect(self.updateLocalControlRef)
        localControl.controlClosed.connect(self.removeLocalControlRef)
        self.localControls.append(localControl)
        
        ### Adding compress_type and encryption_type control
        ### to allow extension of encryption and compression. 
        #for DataCodec in ['compress_type','encryption_type'] :
        # if hasattr( self.localControls, DataCodec ) != True :
        #  self.localControls[DataCodec] = 'normal'
          #setattr( self.localControls, DataCodec, 'normal' ) 
        
        self.updateLocalControlRef(localControl)
        if self.pluginInterface:
            if not path and not model:
                self.pluginInterface.execCallback(self.pluginInterface.
                                                  fileNewCallbacks)
            self.pluginInterface.execCallback(self.pluginInterface.
                                              newWindowCallbacks)

    def updateLocalControlRef(self, localControl):
        """Set the given local control as active.

        Called by signal from a window becoming active.
        Also updates non-modal dialogs.
        Arguments:
            localControl -- the new active local control
        """
        if localControl != self.activeControl:
            self.activeControl = localControl
            if self.configDialog and self.configDialog.isVisible():
                self.configDialog.setRefs(self.activeControl.model,
                                          self.activeControl.
                                          currentSelectionModel())
            if self.sortDialog and self.sortDialog.isVisible():
                self.sortDialog.updateCommandsAvail()
            if self.numberingDialog and self.numberingDialog.isVisible():
                self.numberingDialog.updateCommandsAvail()
            if (self.findConditionDialog and
                self.findConditionDialog.isVisible()):
                self.findConditionDialog.loadTypeNames()
            if self.findReplaceDialog and self.findReplaceDialog.isVisible():
                self.findReplaceDialog.loadTypeNames()
            if (self.filterConditionDialog and
                self.filterConditionDialog.isVisible()):
                self.filterConditionDialog.loadTypeNames()

    def removeLocalControlRef(self, localControl):
        """Remove ref to local control based on a closing signal.

        Also do application exit clean ups if last control closing.
        Arguments:
            localControl -- the local control that is closing
        """
        self.localControls.remove(localControl)
        if globalref.genOptions.getValue('SaveTreeStates'):
            self.recentFiles.saveTreeState(localControl)
        if not self.localControls:
            if globalref.genOptions.getValue('SaveWindowGeom'):
                localControl.windowList[0].saveWindowGeom()
            self.recentFiles.writeItems()
            localControl.windowList[0].saveToolbarPosition()

    def currentTreeView(self):
        """Return the current left-hand tree view.
        """
        return self.activeControl.currentTreeView()

    def currentStatusBar(self):
        """Return the status bar from the current main window.
        """
        return self.activeControl.activeWindow.statusBar()

    def windowActions(self):
        """Return a list of window menu actions from each local control.
        """
        actions = []
        for control in self.localControls:
            actions.extend(control.windowActions(len(actions) + 1,
                                                control == self.activeControl))
        return actions

    def updateActionsAvail(self, oldWidget, newWidget):
        """Update command availability based on focus changes.

        Arguments:
            oldWidget -- the previously focused widget
            newWidget -- the newly focused widget
        """
        self.allActions['EditSelectAll'].setEnabled(hasattr(newWidget,
                                                            'selectAll') and
                                                    not hasattr(newWidget,
                                                               'editTriggers'))

    def setupPlugins(self):
        """Load and initialize any available plugin modules.
        """
        self.pluginInterface = plugininterface.PluginInterface()
        pluginNames = set()
        for pluginPath in self.findResourcePaths('plugins'):
            names = [name[:-3] for name in os.listdir(pluginPath) if
                     name.endswith('.py')]
            if names:
                pluginNames.update(names)
                sys.path.insert(1, pluginPath)
        errorList = []
        for name in sorted(pluginNames):
            try:
                module = __import__(name)
                if not hasattr(module, 'main'):
                    raise ImportError
                self.pluginInstances.append(module.main(self.pluginInterface))
                descript = module.__doc__.strip().split('\n', 1)[0].strip()
                if not descript:
                    descript = name
                self.pluginDescriptions.append(descript)
            except ImportError:
                errorList.append(name)
        if not self.pluginInstances:
            self.pluginInterface = None
        if errorList:
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                               'TreeLine',
                               _('Warning - could not load plugin module {0}').
                               format(', '.join(errorList)))


    def setupActions(self):
        """Add the actions for contols at the global level.
        """
        fileNewAct = QtGui.QAction(_('&New...'), self, toolTip=_('New File'),
                                   statusTip=_('Start a new file'))
        fileNewAct.triggered.connect(self.fileNew)
        self.allActions['FileNew'] = fileNewAct

        fileOpenAct = QtGui.QAction(_('&Open...'), self,
                                    toolTip=_('Open File'),
                                    statusTip=_('Open a file from disk'))
        fileOpenAct.triggered.connect(self.fileOpen)
        self.allActions['FileOpen'] = fileOpenAct

        fileSampleAct = QtGui.QAction(_('Open Sa&mple...'), self,
                                      toolTip=_('Open Sample'),
                                      statusTip=_('Open a sample file'))
        fileSampleAct.triggered.connect(self.fileOpenSample)
        self.allActions['FileOpenSample'] = fileSampleAct

        fileImportAct = QtGui.QAction(_('&Import...'), self,
                                      statusTip=_('Open a non-TreeLine file'))
        fileImportAct.triggered.connect(self.fileImport)
        self.allActions['FileImport'] = fileImportAct

        fileQuitAct = QtGui.QAction(_('&Quit'), self,
                                    statusTip=_('Exit the application'))
        fileQuitAct.triggered.connect(self.fileQuit)
        self.allActions['FileQuit'] = fileQuitAct

        editSelectAllAct =  QtGui.QAction(_('&Select All'), self,
                                   statusTip=_('Select all text in an editor'))
        editSelectAllAct.setEnabled(False)
        editSelectAllAct.triggered.connect(self.editSelectAll)
        self.allActions['EditSelectAll'] = editSelectAllAct

        dataConfigAct = QtGui.QAction(_('&Configure Data Types...'), self,
                       statusTip=_('Modify data types, fields & output lines'),
                       checkable=True)
        dataConfigAct.triggered.connect(self.dataConfigDlg)
        self.allActions['DataConfigType'] = dataConfigAct

        dataSortAct = QtGui.QAction(_('Sor&t Nodes...'), self,
                                    statusTip=_('Define node sort operations'),
                                    checkable=True)
        dataSortAct.triggered.connect(self.dataSortDialog)
        self.allActions['DataSortNodes'] = dataSortAct

        dataNumberingAct = QtGui.QAction(_('Update &Numbering...'), self,
                                   statusTip=_('Update node numbering fields'),
                                   checkable=True)
        dataNumberingAct.triggered.connect(self.dataNumberingDialog)
        self.allActions['DataNumbering'] = dataNumberingAct

        toolsFindTextAct = QtGui.QAction(_('&Find Text...'), self,
                                statusTip=_('Find text in node titles & data'),
                                checkable=True)
        toolsFindTextAct.triggered.connect(self.toolsFindTextDialog)
        self.allActions['ToolsFindText'] = toolsFindTextAct

        toolsFindConditionAct = QtGui.QAction(_('&Conditional Find...'), self,
                             statusTip=_('Use field conditions to find nodes'),
                             checkable=True)
        toolsFindConditionAct.triggered.connect(self.toolsFindConditionDialog)
        self.allActions['ToolsFindCondition'] = toolsFindConditionAct

        toolsFindReplaceAct = QtGui.QAction(_('Find and &Replace...'), self,
                              statusTip=_('Replace text strings in node data'),
                              checkable=True)
        toolsFindReplaceAct.triggered.connect(self.toolsFindReplaceDialog)
        self.allActions['ToolsFindReplace'] = toolsFindReplaceAct

        toolsFilterTextAct = QtGui.QAction(_('&Text Filter...'), self,
                         statusTip=_('Filter nodes to only show text matches'),
                         checkable=True)
        toolsFilterTextAct.triggered.connect(self.toolsFilterTextDialog)
        self.allActions['ToolsFilterText'] = toolsFilterTextAct

        toolsFilterConditionAct = QtGui.QAction(_('C&onditional Filter...'),
                           self,
                           statusTip=_('Use field conditions to filter nodes'),
                           checkable=True)
        toolsFilterConditionAct.triggered.connect(self.
                                                  toolsFilterConditionDialog)
        self.allActions['ToolsFilterCondition'] = toolsFilterConditionAct

        toolsGenOptionsAct = QtGui.QAction(_('&General Options...'), self,
                             statusTip=_('Set user preferences for all files'))
        toolsGenOptionsAct.triggered.connect(self.toolsGenOptions)
        self.allActions['ToolsGenOptions'] = toolsGenOptionsAct

        toolsShortcutAct = QtGui.QAction(_('Set &Keyboard Shortcuts...'), self,
                                    statusTip=_('Customize keyboard commands'))
        toolsShortcutAct.triggered.connect(self.toolsCustomShortcuts)
        self.allActions['ToolsShortcuts'] = toolsShortcutAct

        toolsToolbarAct = QtGui.QAction(_('C&ustomize Toolbars...'), self,
                                     statusTip=_('Customize toolbar buttons'))
        toolsToolbarAct.triggered.connect(self.toolsCustomToolbars)
        self.allActions['ToolsToolbars'] = toolsToolbarAct

        toolsFontsAct = QtGui.QAction(_('Customize Fo&nts...'), self,
                               statusTip=_('Customize fonts in various views'))
        toolsFontsAct.triggered.connect(self.toolsCustomFonts)
        self.allActions['ToolsFonts'] = toolsFontsAct

        helpBasicAct = QtGui.QAction(_('&Basic Usage...'), self,
                               statusTip=_('Display basic usage instructions'))
        helpBasicAct.triggered.connect(self.helpViewBasic)
        self.allActions['HelpBasic'] = helpBasicAct

        helpFullAct = QtGui.QAction(_('&Full Documentation...'), self,
                   statusTip=_('Open a TreeLine file with full documentation'))
        helpFullAct.triggered.connect(self.helpViewFull)
        self.allActions['HelpFull'] = helpFullAct

        helpAboutAct = QtGui.QAction(_('&About TreeLine...'), self,
                        statusTip=_('Display version info about this program'))
        helpAboutAct.triggered.connect(self.helpAbout)
        self.allActions['HelpAbout'] = helpAboutAct

        helpPluginAct = QtGui.QAction(_('&About &Plugins...'), self,
                                     statusTip=_('Show loaded plugin modules'))
        helpPluginAct.triggered.connect(self.helpPlugin)
        self.allActions['HelpPlugin'] = helpPluginAct

        for name, action in self.allActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions.getValue(name)
            if not key.isEmpty():
                action.setShortcut(key)

    def fileNew(self):
        """Start a new blank file.
        """
        if (globalref.genOptions.getValue('OpenNewWindow') or
            self.activeControl.promptModifiedOk()):
            searchPaths = self.findResourcePaths('templates', templatePath)
            if searchPaths:
                dialog = miscdialogs.TemplateFileDialog(_('New File'),
                                                        _('&Select Template'),
                                                        searchPaths)
                if dialog.exec_() == QtGui.QDialog.Accepted:
                    self.createLocalControl(dialog.selectedPath())
                    self.activeControl.filePath = ''
                    self.activeControl.updateWindowCaptions()
            else:
                self.createLocalControl()

    def fileOpen(self):
        """Prompt for a filename and open it.
        """
        if (globalref.genOptions.getValue('OpenNewWindow') or
            self.activeControl.promptModifiedOk()):
            filters = ';;'.join((globalref.fileFilters['trl'],
                                 globalref.fileFilters['trlgz'],
                                 globalref.fileFilters['trlenc'],
                                 globalref.fileFilters['all']))
            fileName = QtGui.QFileDialog.getOpenFileName(QtGui.QApplication.
                                                   activeWindow(),
                                                   _('TreeLine - Open File'),
                                                   self.defaultFilePath(True),
                                                   filters)
            if fileName:
                self.openFile(fileName)

    def fileOpenSample(self):
        """Open a sample file from the doc directories.
        """
        if (globalref.genOptions.getValue('OpenNewWindow') or
            self.activeControl.promptModifiedOk()):
            searchPaths = self.findResourcePaths('samples', samplePath)
            dialog = miscdialogs.TemplateFileDialog(_('Open Sample File'),
                                                    _('&Select Sample'),
                                                    searchPaths, False)
            if dialog.exec_() == QtGui.QDialog.Accepted:
                self.createLocalControl(dialog.selectedPath())
                name = dialog.selectedName() + '.trl'
                self.activeControl.filePath = name
                self.activeControl.updateWindowCaptions()
                self.activeControl.imported = True

    def fileImport(self):
        """Prompt for an import type, then a file to import.
        """
        importControl = imports.ImportControl()
        model = importControl.interactiveImport()
        if model:
            self.createLocalControl(importControl.filePath, model)
            self.activeControl.imported = True

    def fileQuit(self):
        """Close all windows to exit the applications.
        """
        for control in self.localControls[:]:
            control.closeWindows()

    def editSelectAll(self):
        """Select all text in any currently focused editor.
        """
        try:
            QtGui.QApplication.focusWidget().selectAll()
        except AttributeError:
            pass

    def dataConfigDlg(self, show):
        """Show or hide the non-modal data config dialog.

        Arguments:
            show -- true if dialog should be shown, false to hide it
        """
        if show:
            if not self.configDialog:
                self.configDialog = configdialog.ConfigDialog()
                dataConfigAct = self.allActions['DataConfigType']
                self.configDialog.dialogShown.connect(dataConfigAct.setChecked)
            self.configDialog.setRefs(self.activeControl.model,
                                      self.activeControl.
                                      currentSelectionModel(), True)
            self.configDialog.show()
        else:
            self.configDialog.close()

    def dataSortDialog(self, show):
        """Show or hide the non-modal data sort nodes dialog.

        Arguments:
            show -- true if dialog should be shown, false to hide it
        """
        if show:
            if not self.sortDialog:
                self.sortDialog = miscdialogs.SortDialog()
                dataSortAct = self.allActions['DataSortNodes']
                self.sortDialog.dialogShown.connect(dataSortAct.setChecked)
            self.sortDialog.show()
        else:
            self.sortDialog.close()

    def dataNumberingDialog(self, show):
        """Show or hide the non-modal update node numbering dialog.

        Arguments:
            show -- true if dialog should be shown, false to hide it
        """
        if show:
            if not self.numberingDialog:
                self.numberingDialog = miscdialogs.NumberingDialog()
                dataNumberingAct = self.allActions['DataNumbering']
                self.numberingDialog.dialogShown.connect(dataNumberingAct.
                                                         setChecked)
            self.numberingDialog.show()
            if not self.numberingDialog.checkForNumberingFields():
                self.numberingDialog.close()
        else:
            self.numberingDialog.close()

    def toolsFindTextDialog(self, show):
        """Show or hide the non-modal find text dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.findTextDialog:
                self.findTextDialog = (miscdialogs.
                                   FindFilterDialog(miscdialogs.
                                                    FindFilterDialog.
                                                    findDialog))
                toolsFindTextAct = self.allActions['ToolsFindText']
                self.findTextDialog.dialogShown.connect(toolsFindTextAct.
                                                        setChecked)
            self.findTextDialog.selectAllText()
            self.findTextDialog.show()
        else:
            self.findTextDialog.close()

    def toolsFindConditionDialog(self, show):
        """Show or hide the non-modal conditional find dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.findConditionDialog:
                dialogType = conditional.ConditionDialog.findDialog
                self.findConditionDialog = (conditional.
                                            ConditionDialog(dialogType,
                                                        _('Conditional Find')))
                toolsFindConditionAct = self.allActions['ToolsFindCondition']
                (self.findConditionDialog.dialogShown.
                 connect(toolsFindConditionAct.setChecked))
            else:
                self.findConditionDialog.loadTypeNames()
            self.findConditionDialog.show()
        else:
            self.findConditionDialog.close()

    def toolsFindReplaceDialog(self, show):
        """Show or hide the non-modal find and replace text dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.findReplaceDialog:
                self.findReplaceDialog = miscdialogs.FindReplaceDialog()
                toolsFindReplaceAct = self.allActions['ToolsFindReplace']
                self.findReplaceDialog.dialogShown.connect(toolsFindReplaceAct.
                                                           setChecked)
            else:
                self.findReplaceDialog.loadTypeNames()
            self.findReplaceDialog.show()
        else:
            self.findReplaceDialog.close()

    def toolsFilterTextDialog(self, show):
        """Show or hide the non-modal filter text dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.filterTextDialog:
                self.filterTextDialog = (miscdialogs.
                                     FindFilterDialog(miscdialogs.
                                                      FindFilterDialog.
                                                      filterDialog))
                toolsFilterTextAct = self.allActions['ToolsFilterText']
                self.filterTextDialog.dialogShown.connect(toolsFilterTextAct.
                                                          setChecked)
            self.filterTextDialog.selectAllText()
            self.filterTextDialog.show()
        else:
            self.filterTextDialog.close()

    def toolsFilterConditionDialog(self, show):
        """Show or hide the non-modal conditional filter dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.filterConditionDialog:
                dialogType = conditional.ConditionDialog.filterDialog
                self.filterConditionDialog = (conditional.
                                              ConditionDialog(dialogType,
                                                      _('Conditional Filter')))
                toolsFilterConditionAct = (self.
                                        allActions[_('ToolsFilterCondition')])
                (self.filterConditionDialog.dialogShown.
                 connect(toolsFilterConditionAct.setChecked))
            else:
                self.filterConditionDialog.loadTypeNames()
            self.filterConditionDialog.show()
        else:
            self.filterConditionDialog.close()

    def toolsGenOptions(self):
        """Set general user preferences for all files.
        """
        oldAutoSaveMinutes = globalref.genOptions.getValue('AutoSaveMinutes')
        dialog = options.OptionDialog(globalref.genOptions,
                                      QtGui.QApplication.activeWindow())
        dialog.setWindowTitle(_('General Options'))
        if (dialog.exec_() == QtGui.QDialog.Accepted and
            globalref.genOptions.modified):
            globalref.genOptions.writeFile()
            self.recentFiles.updateNumEntries()
            autoSaveMinutes = globalref.genOptions.getValue('AutoSaveMinutes')
            for control in self.localControls:
                for window in control.windowList:
                    window.treeView.updateTreeGenOptions()
                if autoSaveMinutes != oldAutoSaveMinutes:
                    control.resetAutoSave()
            self.updateAllViews()

    def toolsCustomShortcuts(self):
        """Show dialog to customize keyboard commands.
        """
        actions = self.activeControl.activeWindow.allActions
        dialog = miscdialogs.CustomShortcutsDialog(actions, QtGui.QApplication.
                                                   activeWindow())
        dialog.exec_()

    def toolsCustomToolbars(self):
        """Show dialog to customize toolbar buttons.
        """
        actions = self.activeControl.activeWindow.allActions
        dialog = miscdialogs.CustomToolbarDialog(actions, self.updateToolbars,
                                                 QtGui.QApplication.
                                                 activeWindow())
        dialog.exec_()

    def updateToolbars(self):
        """Update toolbars after changes in custom toolbar dialog.
        """
        for control in self.localControls:
            for window in control.windowList:
                window.setupToolbars()

    def toolsCustomFonts(self):
        """Show dialog to customize fonts in various views.
        """
        dialog = miscdialogs.CustomFontDialog(QtGui.QApplication.
                                              activeWindow())
        dialog.updateRequired.connect(self.updateCustomFonts)
        dialog.exec_()

    def updateCustomFonts(self):
        """Update fonts in all windows based on a dialog signal.
        """
        for control in self.localControls:
            for window in control.windowList:
                window.updateFonts()
            control.printData.setDefaultFont()
        self.updateAllViews()

    def helpViewBasic(self):
        """Display basic usage instructions.
        """
        if not self.basicHelpView:
            path = self.findResourceFile('basichelp.html', 'doc', docPath)
            if not path:
                QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                        'TreeLine',
                                        _('Error - basic help file not found'))
                return
            self.basicHelpView = helpview.HelpView(path,
                                                   _('TreeLine Basic Usage'),
                                                   globalref.toolIcons)
        self.basicHelpView.show()

    def helpViewFull(self):
        """Open a TreeLine file with full documentation.
        """
        path = self.findResourceFile('documentation.trl', 'doc', docPath)
        if not path:
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                     'TreeLine',
                                     _('Error - documentation file not found'))
            return
        newWindowSetting = globalref.genOptions.getValue('OpenNewWindow')
        if not newWindowSetting:
            globalref.genOptions.changeValue('OpenNewWindow', True)
        self.createLocalControl(path)
        self.activeControl.filePath = 'documentation.trl'
        self.activeControl.updateWindowCaptions()
        self.activeControl.imported = True
        win = self.activeControl.activeWindow
        win.rightTabs.setCurrentWidget(win.outputSplitter)
        if not newWindowSetting:
            globalref.genOptions.changeValue('OpenNewWindow', False)

    def helpAbout(self):
        """ Display version info about this program.
        """
        QtGui.QMessageBox.about(QtGui.QApplication.activeWindow(), 'TreeLine',
                                _('TreeLine, Version {0}\nby {1}').
                                format(__version__, __author__))

    def helpPlugin(self):
        """Show dialog with loaded plugin modules.
        """
        dialog = miscdialogs.PluginListDialog(self.pluginDescriptions,
                                              QtGui.QApplication.
                                              activeWindow())
        dialog.exec_()
