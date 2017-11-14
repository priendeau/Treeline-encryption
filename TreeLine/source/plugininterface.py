#!/usr/bin/env python3

#******************************************************************************
# plugininterface.py, provides an interface class for plugin extension modules
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************


"""Plugin Interface Rules

   Plugins are python files located in a plugins directory, either one created
   by the TreeLine installer or one in the user's config file location.

   Plugins must define a function named "main" that takes an instance of the
   PluginInterface class as its only argument.  The function should initialize
   the plugin.  It is called after the TreeLine GUI is initialized and an
   initial file (new or automatic) is loaded.  The return value of the
   function is stored by TreeLine to avoid garbage collection of the
   reference.

   There should be a module doc string defined by the plugin.  The first line
   is used as the plugin listing in Help->About Plugins.  It should contain the
   plugin name and a very brief description.

   To avoid problems with plugins breaking when TreeLine is revised, the plugin
   API is restricted to the methods of the PluginInterface class.  References
   from within the method code and elsewhere in TreeLine code should not be
   used.  Exceptions to this rule include certain data members of node objects
   (childList, parent and data).  Of course, if a method returns a Qt object,
   the normal Qt API is available.

   There are methods that setup callback functions for various TreeLine
   operations.  The functions are called when various actions are taken
   in TreeLine.

   Note that the plugins are initialized after TreeLine has fully initiallized
   and the first file (new or auomatically opened) has been loaded.  This
   allows plugins to access the full TreeLine interface when initializing, but
   it means that callback functions (new window, new file amd open file) are
   not invoked for the first file.

   Plugins used with windows binary installations are limited to the Python
   modules that are used somewhere in TreeLine itself.  No other modules are
   available, with the exception of urllib which is specifically included in
   the binary for plugin use.
"""

import sys
import os.path
import io
import tempfile
from xml.etree import ElementTree
from PyQt4 import QtCore, QtGui
import treeoutput
import nodeformat
import fieldformat
import treeopener
import dataeditview
import exports
import options
import globalref


class PluginInterface():
    """Defines the available interface for the plugins.
    """
    def __init__(self):
        """Initialize the interface.
        """
        self.dataChangeCallbacks = []    # internal use only
        self.formatChangeCallbacks = []  # internal use only
        self.selectChangeCallbacks = []  # internal use only
        self.newWindowCallbacks = []     # internal use only
        self.fileModCallbacks = []       # internal use only
        self.fileNewCallbacks = []       # internal use only
        self.fileOpenCallbacks = []      # internal use only
        self.fileSaveCallbacks = []      # internal use only

    def mainControl(self):
        """Return the main control object.

        Can be used as a presistent parent QObject for new actions.
        """
        return globalref.mainControl 

    def pluginPath(self):
        """Return the path of this plugin's directory.
        """
        try:
            frame = sys._getframe(1)
            fileName = frame.f_code.co_filename
        finally:
            del frame
        return os.path.dirname(fileName)

    def getLanguage(self):
        """Return language code used by TreeLine for translations.
        """
        return globalref.lang


    #**************************************************************************
    #  Node Interfaces:
    #**************************************************************************

    def getCurrentNode(self):
        """Return a reference to the currently active node in the tree view.
        """
        return (globalref.mainControl.activeControl.currentSelectionModel().
                currentNode())

    def getSelectedNodes(self):
        """Return a list of currently selected nodes.
        """
        return (globalref.mainControl.activeControl.currentSelectionModel().
                selectedNodes())

    def changeSelection(self, newSelectList):
        """Clear the current selection and select the nodes in the given list.

        Also updates the right-view after the change.
        Arguments:
            newSelectList -- a list of nodes to be selected
        """
        (globalref.mainControl.activeControl.currentSelectionModel().
         selectNodes(newSelectList))

    def getRootNode(self):
        """Return a reference to the root node.
        """
        return globalref.mainControl.activeControl.model.root

    def getNodeChildList(self, node):
        """Return a list of the given node's child nodes.

        This is provided for completeness, node.childList may be used directly.
        Arguments:
            node -- the given parent node
        """
        return node.childList

    def getNodeParent(self, node):
        """Return the given node's parent node.

        This is provided for completeness, node.parent may be used directly.
        Arguments:
            node -- the given child node
        """
        return node.parent

    def getNodeDescendantList(self, node):
        """Return a list of the given node and all descendant nodes.

        Arguments:
            node -- the given parent node
        """
        return list(node.descendantGen())

    def addChildNode(self, parent, text='New'):
        """Add new child node at the end of the current child list.

        Returns the new node.
        Arguments:
            parent -- the parent node
            text -- the new node's title text
        """
        return parent.addNewChild(newTitle=text)

    def insertSibling(self, siblingNode, text='New', inAfter=False):
        """Add new sibling before or after sibling - return new item.

        Arguments:
            siblingNode -- the node adjacent to the new node
            text -- the new node's title text
            inAfter -- insert after the sibling if True
        """
        return siblingNode.parent.addNewChild(siblingNode, not inAfter, text)

    def setNodeOpenClosed(self, node, setOpen=True):
        """Open children in tree if open is True, close children if False.

        Arguments:
            node -- the parent node
            setOpen -- expand if True, collapse if False
        """
        view = globalref.mainControl.activeControl.activeWindow.treeView
        if setOpen:
            view.expand(node.index())
        else:
            view.collapse(node.index())

    def setBranchOpenClosed(self, node, setOpen=True):
        """Open all chhildren in tree if open True, close children if False.

        Arguments:
            node -- the parent node
            setOpen -- expand if True, collapse if False
        """
        view = globalref.mainControl.activeControl.activeWindow.treeView
        if setOpen:
            view.expandBranch(node)
        else:
            view.collapseBranch(node)

    def getNodeDataDict(self, node):
        """Return the given node's data dictionary.

        This is provided for completeness, node.data may be used directly.
        Arguments:
            node -- the given node
        """
        return node.data

    def getNodeUniqueId(self, node):
        """Return the given node's unique ID string.

        Arguments:
            node -- the given node
        """
        return node.uniqueId

    def updateUniqueId(self, node):
        """Update the node's unique ID string based on data or format changes.

        Arguments:
            node -- the given node
        """
        node.setUniqueId(True)

    def getNodeByUniqueId(self, uniqueId):
        """Return the node matching the given unique ID.

        Raises KeyError if no matching ID is found.
        Arguments:
            uniqueId -- the unique ID string to find
        """
        return globalref.mainControl.activeControl.model.nodeIdDict[uniqueId]

    def getNodeTitle(self, node):
        """Return the formatted text for the node's title in the tree view.

        Arguments:
            node -- the given node
        """
        return node.title()

    def setNodeTitle(self, node, titleText):
        """Set this node's title based on a provided string.

        Modifies the field data used in the title format.
        Returns True if successful, False otherwise.
        Arguments:
            node -- the given node
            titleText -- the new title string
        """
        return node.setTitle(titleText)

    def getNodeOutput(self, node, lineSep='<br />\n'):
        """Return the formatted HTML text for the node's output.

        Arguments:
            node -- the given node
            lineSep -- separator for text lines
        """
        return lineSep.join(node.formatOutput())

    def getChildNodeOutput(self, node):
        """Return the formatted HTML text for the node children's output.

        Arguments:
            node -- the given parent node
        """
        outputGroup = treeoutput.OutputGroup(node.childList)
        outputGroup.addBlanksBetween()
        outputGroup.addAbsoluteIndents()
        return '\n'.join(outputGroup.getLines())

    def getFieldOutput(self, node, fieldName):
        """Return formatted text for the given fieldName data.

        Arguments:
            node -- the given node
            fieldName -- the field name with the data
        """
        nodeFormat = node.nodeFormat()
        try:
            field = nodeFormat.fieldDict[fieldName]
            return field.outputText(node, False, nodeFormat.formatHtml)
        except KeyError:
            return ''

    def getNodeFormatName(self, node):
        """Return the format type name for the given node.

        Arguments:
            node -- the given node
        """
        return node.formatName

    def setNodeFormat(self, node, formatName):
        """Set the given node to the given node format type.

        Arguments:
            node -- the given node
            formatName -- the given type format name
        """
        node.changeDataType(formatName)

    def setDataChangeCallback(self, callbackFunc):
        """Set callback function called when a node's dict data is changed.

        The callbackFunc must take one argument: the node being changed.
        Arguments:
            callbackFunc -- the function to be called
        """
        self.dataChangeCallbacks.append(callbackFunc)


    #**************************************************************************
    #  Format Interfaces:
    #**************************************************************************

    def getNodeFormatNames(self):
        """Return text list of available node format names.
        """
        return (globalref.mainControl.activeControl.model.formats.
                typeNames())

    def newNodeFormat(self, formatName, defaultFieldName='Name'):
        """Create a new node format and add it to the available tree formats.

        The format name must only contain characters [a-zA-Z0-9_.-].
        If defaultFieldName, a text field is created and added to the title
        line and the first output line.
        Arguments:
            formatName -- the new format name
            defaultFieldName -- if defined, a text field is created and added
        """
        treeFormats = globalref.mainControl.activeControl.model.formats
        newFormat = nodeformat.NodeFormat(formatName, treeFormats)
        if defaultFieldName:
            newFormat.addFieldIfNew(defaultFieldName)
            newFormat.lineList = ['{{*{0}*}}'.format(defaultFieldName)] * 2
            newFormat.updateLineParsing()
        treeFormats[formatName] = newFormat

    def copyFileFormat(self, fileRef):
        """Copy the configuration from another TreeLine file,

        If fileRef is a file-like object, fileRef.name must be defined.
        Returns True/False on success/failure.
        Arguments:
            fileRef -- either a file path string or a file-like object
        """
        try:
            opener = treeopener.TreeOpener()
            tmpModel = opener.readFile(fileName)
        except (IOError, treeopener.ParseError):
            return False
        model = globalref.mainControl.activeControl.model
        model.formats.copyTypes(tmpModel.formats, model)
        return True

    def getFormatIconName(self, formatName):
        """Return the node format's currently set icon name.

        A default setting will return an empty string,
        blank will return 'NoIcon'.
        Arguments:
            formatName -- the given format name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        return nodeFormat.iconName

    def setFormatIconName(self, formatName, iconName):
        """Set the node format's icon to iconName.

        An empty string will get the default icon, use 'NoIcon' to get a blank.
        Arguments:
            formatName -- the given format nam
            iconName -- the new icon name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        nodeFormat.iconName = iconName

    def addTreeIcon(self, name, image):
        """Add an icon to those available for use in the tree.

        The icon data can be in any image format supported by Qt.
        If the name matches one already loaded, the earlier one is replaced.
        Arguments:
            name -- the new icon name
            image -- the image data
        """
        icon = QtGui.QIcon()
        pixmap = QtGui.QPixmap(image)
        if not pixmap.isNull():
            icon.addPixmap(pixmap)
            globalref.treeIcons[name] = icon

    def getTitleLineFormat(self, formatName):
        """Return the format's title formatting line with field names embedded.

        Arguments:
            formatName -- the given format name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        return nodeFormat.getLines()[0]

    def setTitleLineFormat(self, formatName, newLine):
        """Set the node format's title formatting line to newLine.

        Arguments:
            formatName -- the given format name
            newLine -- the line to set
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        nodeFormat.changeTitleLine(newLine)
        nodeFormat.updateLineParsing()

    def getOutputFormatLines(self, formatName):
        """Return a list of output formatting lines with field names embedded.

        Arguments:
            formatName -- the given format name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        return nodeFormat.getLines()[0]

    def setOutputFormatLines(self, formatName, lineList):
        """Set the node format's output formatting lines to lineList.

        Arguments:
            formatName -- the given format name
            lineList -- a list of lines to set
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        nodeFormat.changeOutputLines(lineList)
        nodeFormat.updateLineParsing()

    def getFormatSpaceBetween(self, formatName):
        """Return True if the type is set to add a space between nodes.

        Arguments:
            formatName -- the given format name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        return nodeFormat.spaceBetween

    def setFormatSpaceBetween(self, formatName, spaceBetween=True):
        """Change the type space between node setting.

        Arguments:
            formatName -- the given format name
            spaceBetween -- True for spaces between nodes, False otherwise
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        nodeFormat.spaceBetween = spaceBetween

    def getFormatHtmlProp(self, formatName):
        """Return True if the type uses HTML in formats, False for plain text.

        Arguments:
            formatName -- the given format name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        return nodeFormat.formatHtml

    def setFormatHtmlProp(self, formatName, htmlProp=True):
        """Change the format HTML handling of the given type.

        Arguments:
            formatName -- the given format name
            htmlProp -- True for HTML in formats, False for plain text
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        nodeFormat.formatHtml = htmlProp

    def getFormatFieldNames(self, formatName):
        """Return a list of the node format's field names.

        Arguments:
            formatName -- the given format name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        return nodeFormat.fieldNames()

    def addNewFormatField(self, formatName, fieldName, fieldType='Text'):
        """Add a new field to the node format.
        
        Type should be one of: Text, HtmlText, OneLineText, SpacedText,
        Number, Math, Numbering, Boolean, Date, Time, Choice, AutoChoice,
        Combination, AutoCombination, ExternalLink, InternalLink, Picture,
        RegularExpression.
        Arguments:
            formatName -- the given format name
            fieldName -- the new field name
            fieldType -- the new field type
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        nodeFormat.addField(fieldName, {'type': fieldType})

    def getFormatFieldType(self, formatName, fieldName):
        """Return the type string of the given field in the given format.

        Arguments:
            formatName -- the given format name
            fieldName -- the given field name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        field = nodeFormat.fieldDict[fieldName]
        return field.typeName

    def changeFormatFieldType(self, formatName, fieldName, newFieldType):
        """Change the type of the given field in the given format.

        Field type should be one of: Text, HtmlText, OneLineText, SpacedText,
        Number, Math, Numbering, Boolean, Date, Time, Choice, AutoChoice,
        Combination, AutoCombination, ExternalLink, InternalLink, Picture,
        RegularExpression.
        Arguments:
            formatName -- the given format name
            fieldName -- the given field name
            newFieldType -- the new field type name string
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        field = nodeFormat.fieldDict[fieldName]
        field.changeType(newFieldType)

    def registerNewFieldType(self, fieldTypeClass):
        """Make a new field type class available.

        The new class should be derived from an existing filed class (see
        getFieldClass method, below).
        The class name must end in 'Field' and it must have a typeName
        attribute that is the name without the 'Field' ending.
        Arguments:
            fieldTypeClass -- the new field type class
        """
        fieldformat.fieldTypes.append(fieldTypeClass.typeName)
        setattr(fieldformat, fieldTypeClass.__name__, fieldTypeClass)

    def getFieldClass(self, fieldTypeName):
        """Return the class associated with the given field type name.

        The returned class can be used as a base class for new field types.
        Field type should be one of: Text, HtmlText, OneLineText, SpacedText,
        Number, Math, Numbering, Boolean, Date, Time, Choice, AutoChoice,
        Combination, AutoCombination, ExternalLink, InternalLink, Picture,
        RegularExpression.
        Arguments:
            fieldTypeName -- the field type name string
        """
        fieldTypeName = '{}Field'.format(fieldTypeName)
        return getattr(fieldformat, fieldTypeName)

    def getFormatFieldFormat(self, formatName, fieldName):
        """Return the format code string of the given field.

        Arguments:
            formatName -- the given format name
            fieldName -- the given field name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        field = nodeFormat.fieldDict[fieldName]
        return field.format

    def setFormatFieldFormat(self, formatName, fieldName, newFieldFormat):
        """Change the format code string of the given field.

        Arguments:
            formatName -- the given format name
            fieldName -- the given field name
            newFieldFormat -- the new field formatting string
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        field = nodeFormat.fieldDict[fieldName]
        field.setFormat(newFieldFormat)

    def getFormatFieldExtraText(self, formatName, fieldName):
        """Return a tuple of the prefix and suffix text of the given field.

        Arguments:
            formatName -- the given format name
            fieldName -- the given field name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        field = nodeFormat.fieldDict[fieldName]
        return (field.prefix, field.suffix)

    def setFormatFieldExtraText(self, formatName, fieldName, newPrefix='',
                                newSuffix=''):
        """Set the format prefix and suffix text of the given field.

        Arguments:
            formatName -- the given format name
            fieldName -- the given field name
            newPrefix -- a new prefix (blank for none)
            newSuffix -- a new suffix (blank for none)
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        field = nodeFormat.fieldDict[fieldName]
        field.prefix = newPrefix
        field.suffix = newSuffix

    def getFormatFieldNumLines(self, formatName, fieldName):
        """Return the number of lines set for the given field.

        Arguments:
            formatName -- the given format name
            fieldName -- the given field name
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        field = nodeFormat.fieldDict[fieldName]
        return field.numLines

    def setFormatFieldNumLines(self, formatName, fieldName, numLines):
        """Set the number of lines set for the given field.

        Arguments:
            formatName -- the given format name
            fieldName -- the given field name
            numLines -- the new number of lines
        """
        nodeFormat = (globalref.mainControl.activeControl.model.
                      formats[formatName])
        field = nodeFormat.fieldDict[fieldName]
        field.numLines = numLines

    def setFormatChangeCallback(self, callbackFunc):
        """Set callback function called when the data format is modified.

        The callbackFunc must take no arguments.
        Arguments:
            callbackFunc -- the function to be called
        """
        self.formatChangeCallbacks.append(callbackFunc)


    #**************************************************************************
    #   View Interfaces:
    #**************************************************************************

    def updateViews(self):
        """Refresh all tree and right-hand views using current data.
        """
        globalref.mainControl.activeControl.updateAll(False)

    def updateRightViews(self):
        """Refresh all right-hand views using current data.
        """
        globalref.mainControl.activeControl.updateRightViews()

    def updateTreeNode(self, node):
        """Update the given node in all tree views.

        Arguments:
            node -- the node to be updated
        """
        globalref.mainControl.activeControl.updateTreeNode(node, False)

    def getActiveWindow(self):
        """Return the currently active main window.

        Can be used as a QWidet parent.
        """
        return globalref.mainControl.activeControl.activeWindow

    def getActiveEditView(self):
        """Return the active editor in the Data Editor right-hand view.

        Returns None if something else has the focus.
        """
        widget = QtGui.QApplication.focusWidget()
        if (hasattr(widget, 'paste') and
            isinstance(widget.parent().parent(), dataeditview.DataEditView)):
            return widget
        return None

    def insertEditViewText(self, text, usePlainText=True):
        """Inserts text in the active Data Editor right-hand editor.

        Does nothing if something else has the focus.
        Arguments:
            usePlainText -- insert as formatted HTML if False
        """
        editor = self.getActiveEditView()
        if editor:
            if hasattr(editor, 'lineEdit'):
                editor.lineEdit().insert(text)
            elif usePlainText:
                editor.insertPlainText(text)
            else:
                editor.insertHtml(text)

    def setSelectChangeCallback(self, callbackFunc):
        """Set callback function called when the tree selection is changed.

        The callbackFunc must take no arguments.
        Arguments:
            callbackFunc -- the function to be called
        """
        self.selectChangeCallbacks.append(callbackFunc)

    def setNewWindowCallback(self, callbackFunc):
        """Set callback function called when a new main window is created.

        The callbackFunc must take no arguments.
        Arguments:
            callbackFunc -- the function to be called
        """
        self.newWindowCallbacks.append(callbackFunc)


    #**************************************************************************
    #   File Interfaces:
    #**************************************************************************

    def openFile(self, fileRef, checkModified=True, importOnFail=True):
        """Open file given by fileRef interactively.

        Uses QMessageBox to inform user of issues/failures.
        If fileRef is a  file-like object, fileRef.name must be defined.
        Arguments:
            fileRef -- either a file path string or a file-like object
            checkModified -- if True, prompt user about current modified file
            importOnFail -- if True, prompts for import on non-TreeLine files
        """
        if hasattr(fileRef, 'read'):
            fd, fileName = tempfile.mkstemp(text=True)
            os.write(fd, fileRef.read())
            os.close(fd)
            fileRef.close()
        else:
            fileName = fileRef
        globalref.mainControl.openFile(fileName, checkModified, importOnFail)
        if hasattr(fileRef, 'read'):
            os.remove(fileName)
            globalref.mainControl.activeControl.filePath = fileRef.name
            globalref.mainControl.activeControl.updateWindowCaptions()
            globalref.mainControl.recentFiles.removeItem(fileName)

    def readFile(self, fileRef):
        """Open TreeLine file given by fileRef non-interactively.

        Returns True/False on success/failure.
        Does not work with compressed or encrypted files.
        If fileRef is a  file-like object, fileRef.name must be defined.
        Arguments:
            fileRef -- either a file path string or a file-like object
        """
        try:
            globalref.mainControl.createLocalControl(fileRef)
            return True
        except (treeopener.ParseError, IOError):
            return False

    def newFile(self):
        """Start a new file interactively.

        Prompts user for template to be used.
        """
        globalref.mainControl.fileNew()

    def createFile(self):
        """Start a new file non-interactively.

        Uses the default single-line template.
        """
        globalref.mainControl.createLocalControl()

    def saveFile(self):
        """Save TreeLine file interactively.

        Uses QMessageBox for possible password prompts or failures.
        """
        globalref.mainControl.activeControl.fileSave()

    def writeFile(self, fileRef):
        """Save TreeLine file to fileRef non-interactively.

        Returns True/False on success/failure.
        Does not compress or encrypt files.
        If fileRef is a  file-like object, fileRef.name must be defined.
        Arguments:
            fileRef -- either a file path string or a file-like object
        """
        rootElement = globalref.mainControl.model.root.elementXml()
        rootElement.attrib.update(globalref.mainControl.model.formats.
                                  xmlAttr())
        rootElement.attrib.update(globalref.mainControl.printData.xmlAttr())
        if globalref.mainControl.spellCheckLang:
            rootElement.set('spellchk', globalref.mainControl.spellCheckLang)
        if not globalref.mainControl.model.mathZeroBlanks:
            rootElement.set('zeroblanks', 'n')
        elementTree = ElementTree.ElementTree(rootElement)
        try:
            # use binary for regular files to avoid newline translation
            fileIO = io.BytesIO()
            elementTree.write(fileIO, 'utf-8', True)
            data = fileIO.getvalue()
            fileIO.close()
            if hasattr(fileRef, 'write'):
                fileRef.write(data)
            else:
                with open(saveFilePath, 'wb') as f:
                    f.write(data)
            return True
        except IOError:
            return False

    def getFileFilters(self):
        """Return a dictionary of all available file filters.

        See globalref.py file for the key values.
        """
        return globalref.fileFilters

    def getCurrentFileName(self):
        """Return the currently open file path.
        """
        return globalref.mainControl.activeControl.filePath

    def getDocModified(self):
        """Return True if the current document is marked as modified.
        """
        return globalref.mainControl.activeControl.modified

    def setDocModified(self, value=True):
        """Set the document status to modified or unmodified.

        Also updates command availablility.
        Arguments:
            value -- if True sets to modified, if False sets to unmodified
        """
        globalref.mainControl.activeControl.setModified(value)

    def fileExport(self):
        """Interactive export of data to html,xml, etc. via dialog.
        """
        globalref.mainControl.activeControl.fileExport()

    def exportHtmlSingle(self, filePath, includeRoot=True, openOnly=False,
                         addHeader=False, numColumns=1):
        """Export selected branches to single-page HTML.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
            includeRoot -- if True, include the root of the selection
            openOnly -- if True, do not include collapsed nodes
            addHeader -- if True, include the print header in the export
            numColumns -- the number of columns in the exported page
        """
        exports.ExportDialog.includeRoot = includeRoot
        exports.ExportDialog.openOnly = openOnly
        exports.ExportDialog.addHeader = addHeader
        exports.ExportDialog.numColumns = numColumns
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportHtmlSingle(filePath)
        except IOError:
            return False

    def exportHtmlNavSingle(self, filePath, includeRoot=True, openOnly=False,
                            addHeader=False, navPaneLevels=1):
        """Export selected branches to single-page HTML with a navigation pane.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
            includeRoot -- if True, include the root of the selection
            openOnly -- if True, do not include collapsed nodes
            addHeader -- if True, include the print header in the export
            numColumns -- the number of columns in the exported page
        """
        exports.ExportDialog.includeRoot = includeRoot
        exports.ExportDialog.openOnly = openOnly
        exports.ExportDialog.addHeader = addHeader
        exports.ExportDialog.navPaneLevels = navPaneLevels
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportHtmlNavSingle(filePath)
        except IOError:
            return False

    def exportHtmlPages(self, filePath):
        """Export selected branches to multiple web pages with navigation pane.

        Return True on successful export.
        Arguments:
            filePath -- the directory path to export to
        """
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportHtmlPages(filePath)
        except IOError:
            return False

    def exportHtmlTables(self, filePath, addHeader=False):
        """Export selected branches to multiple web page tables.

        Return True on successful export.
        Arguments:
            filePath -- the directory path to export to
            addHeader -- if True, include the print header in the export
        """
        exports.ExportDialog.addHeader = addHeader
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportHtmlTables(filePath)
        except IOError:
            return False

    def exportTextTitles(self, filePath, includeRoot=True, openOnly=False):
        """Export selected branches to tabbed title text.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
            includeRoot -- if True, include the root of the selection
            openOnly -- if True, do not include collapsed nodes
        """
        exports.ExportDialog.includeRoot = includeRoot
        exports.ExportDialog.openOnly = openOnly
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportTextTitles(filePath)
        except IOError:
            return False

    def exportTextPlain(self, filePath, includeRoot=True, openOnly=False):
        """Export selected branches to unformatted output text.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
            includeRoot -- if True, include the root of the selection
            openOnly -- if True, do not include collapsed nodes
        """
        exports.ExportDialog.includeRoot = includeRoot
        exports.ExportDialog.openOnly = openOnly
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportTextPlain(filePath)
        except IOError:
            return False

    def exportTextTables(self, filePath):
        """Export the children of the selection to a tab delimited text table.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
        """
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportTextTables(filePath)
        except IOError:
            return False

    def exportXmlGeneric(self, filePath):
        """Export selected branches to generic XML.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
        """
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportXmlGeneric(filePath)
        except IOError:
            return False

    def exportXmlSubtree(self, filePath):
        """Export selected branches to a TreeLine subtree.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
        """
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportXmlSubtree(filePath)
        except IOError:
            return False

    def exportOdfText(self, filePath):
        """Export selected branches to an ODF text file.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
        """
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportOdfText(filePath)
        except IOError:
            return False

    def exportBookmarksHtml(self, filePath):
        """Export selected branches to HTML format bookmarks.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
        """
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportBookmarksHtml(filePath)
        except IOError:
            return False

    def exportBookmarksXbel(self, filePath):
        """Export selected branches to XBEL format bookmarks.

        Return True on successful export.
        Arguments:
            filePath -- the path and filename to export to
        """
        exports.ExportDialog.exportWhat = exports.ExportDialog.selectBranch
        localControl = globalref.mainControl.activeControl
        exportControl = exports.ExportControl(localControl.model.root,
                          localControl.currentSelectionModel().selectedNodes(),
                          globalref.mainControl.defaultFilePath())
        try:
            return exportControl.exportBookmarksXbel(filePath)
        except IOError:
            return False

    def setFileModCallback(self, callbackFunc):
        """Set callback function called when anything modifies file data.

        The callbackFunc must take no arguments.
        Arguments:
            callbackFunc -- the function to be called
        """
        self.fileModCallbacks.append(callbackFunc)

    def setFileNewCallback(self, callbackFunc):
        """Set callback function to be called after a new file is started.

        The callbackFunc must take no arguments.
        Arguments:
            callbackFunc -- the function to be called
        """
        self.fileNewCallbacks.append(callbackFunc)

    def setFileOpenCallback(self, callbackFunc):
        """Set callback function to be called after opening a TreeLine file.

        The callbackFunc must take no arguments.
        Arguments:
            callbackFunc -- the function to be called
        """
        self.fileOpenCallbacks.append(callbackFunc)

    def setFileSaveCallback(self, callbackFunc):
        """Set callback function to be called after a file is saved.

        The callbackFunc must take no arguments.
        Arguments:
            callbackFunc -- the function to be called
        """
        self.fileSaveCallbacks.append(callbackFunc)


    #**************************************************************************
    #   Menu Interfaces:
    #**************************************************************************

    def execMenuAction(self, actionName):
        """Execute the action associated with the given menu item.

        Names can be found in the keyboard option section of optiondefaults.py.
        Raises an IndexError if the name is not valid.
        Does nothing if the action is not enabled.
        Arguments:
            actionName -- the name of the menu action
        """
        action = (globalref.mainControl.activeControl.activeWindow.
                  allActions[actionName])
        if action.isEnabled():
            action.trigger()

    def getMenuBar(self):
        """Return the main window's top menu bar (QMenuBar).
        """
        return globalref.mainControl.activeControl.activeWindow.menuBar()

    def getPulldownMenu(self, index):
        """Return top pulldown menu (QMenu) at position index.

        Raise IndexError if index is not valid.
        Arguments:
            index -- the menu number
        """
        return self.getMenuBar().actions()[index].menu()

    def addActionCustomize(self, action, menuName):
        """Adds action to the custom key shortcuts and custom toolbar dialogs.

        This does not add it to a menu (use insertAction(...) on a QMenu).
        The action should already have its default shortcut (if any) set.
        The action must have an icon set for it to show in the toolbr dialog.
        Arguments:
            action -- the QAction being added
            menuName -- top level menu (must be one of 'File', 'Edit', etc.)
        """
        indexName = action.toolTip().replace(' ', '')
        menuName = menuName + ' Menu'
        try:
            key = globalref.keyboardOptions.getValue(indexName)
        except KeyError:
            key = None
        if key:
            action.setShortcut(key)
        options.KeyOptionItem(globalref.keyboardOptions, indexName,
                              action.shortcut().toString(), menuName)
        globalref.mainControl.allActions[indexName] = action
        for control in globalref.mainControl.localControls:
            control.allActions[indexName] = action
            for window in control.windowList:
                window.allActions[indexName] = action
                window.setupToolbars()


    #**************************************************************************
    #   General Options:
    #**************************************************************************

    def getOptionValue(self, name):
        """Return the value of a general option item.

        See the setGenOptionDefaults function in the optiondefaults.py file
        for available name values.
        Raises a KeyError if the name is incorrect.
        Arguments:
            name -- the key name for the option
        """
        return globalref.genOptions.getValue(name)

    def changeOptionValue(self, name, value):
        """Set the name of an existing option to the given value.

        Returns True if changed, False if value is the same or not permitted.
        See the setGenOptionDefaults function in the optiondefaults.py file
        for available name values.
        Raises a KeyError if the name is incorrect.
        Arguments:
            name -- the key name for the option
            value -- a value or a string defining the value
        """
        return globalref.genOptions.changeValue(name, value)


    #**************************************************************************
    #  Internal methods (not for plugin use):
    #**************************************************************************

    def execCallback(self, funcList, *args):
        """Call functions in funcList with given args if any.

        Arguments:
            funcList -- the stored callback function list
            *args -- the callback argumants
        """
        for func in funcList:
            func(*args)
