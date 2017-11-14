#!/usr/bin/env python3

#******************************************************************************
# imports.py, provides classes for a file import dialog and import functions
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
import re
import collections
import zipfile
import html.parser
from xml.etree import ElementTree
from PyQt4 import QtCore, QtGui
import miscdialogs
import treenode
import treemodel
import nodeformat
import treeformats
import globalref


methods = collections.OrderedDict()
methods.update([(_('&Tab indented text, one node per line'),
                 'importTabbedText'),
                (_('Tab delimited text table with header &row'),
                 'importTableText'),
                (_('Plain text, one node per &line (CR delimited)'),
                 'importTextLines'),
                (_('Plain text &paragraphs (blank line delimited)'),
                 'importTextPara'),
                (_('Treepad &file (text nodes only)'), 'importTreePad'),
                (_('&Generic XML (non-TreeLine file)'), 'importXml'),
                (_('Open &Document (ODF) outline'), 'importOdfText'),
                (_('&HTML bookmarks (Mozilla Format)'), 'importMozilla'),
                (_('&XML bookmarks (XBEL format)'), 'importXbel')])
fileFilters = {'importTabbedText': 'txt', 'importTableText': 'txt',
               'importTextLines': 'txt', 'importTextPara': 'txt',
               'importTreePad': 'hjt',
               'importXml': 'xml',
               'importOdfText': 'odt',
               'importMozilla': 'html',
               'importXbel': 'xml'}
bookmarkFolderTypeName = _('FOLDER')
bookmarkLinkTypeName = _('BOOKMARK')
bookmarkSeparatorTypeName = _('SEPARATOR')
bookmarkLinkFieldName = _('Link')
textFieldName = _('Text')
genericXmlTextFieldName = 'Element_Data'
htmlUnescapeDict = {'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"'}


class ImportControl:
    """Control file imports of alt file types.
    """
    def __init__(self, filePath=''):
        """Initialize the import control object.

        Arguments:
            filePath -- the file to import from if give, otherwise prompt user
        """
        self.filePath = filePath
        self.errorMessage = ''

    def interactiveImport(self, addWarning=False):
        """Prompt the user for import type & proceed with import.

        Return the model if import is successful, otherwise None
        Arguments:
            addWarning - if True, add non-valid file warning to dialog
        """
        dialog = miscdialogs.RadioChoiceDialog(_('Import File'),
                                               _('Choose Import Method'),
                                               methods.items(),
                                               QtGui.QApplication.
                                               activeWindow())
        if addWarning:
            fileName = os.path.basename(self.filePath)
            dialog.addLabelBox(_('Invalid File'),
                               _('"{0}" is not a valid TreeLine file.\n\n'
                                 'Use an import filter?').format(fileName))
        if dialog.exec_() != QtGui.QDialog.Accepted:
            return None
        method = dialog.selectedButton()
        if not self.filePath:
            filters = ';;'.join((globalref.fileFilters[fileFilters[method]],
                                 globalref.fileFilters['all']))
            defaultFilePath = globalref.mainControl.defaultFilePath(True)
            self.filePath = QtGui.QFileDialog.getOpenFileName(QtGui.
                                                   QApplication.activeWindow(),
                                                   _('TreeLine - Import File'),
                                                   defaultFilePath, filters)
            if not self.filePath:
                return None
        self.errorMessage = ''
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            model = getattr(self, method)()
            QtGui.QApplication.restoreOverrideCursor()
        except IOError:
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                      'TreeLine',
                                      _('Error - could not read file {0}').
                                      format(self.filePath))
            return None
        if not model:
            message = _('Error - improper format in {0}').format(self.filePath)
            if self.errorMessage:
                message = '{0}\n{1}'.format(message, self.errorMessage)
                self.errorMessage = ''
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                      'TreeLine', message)
        return model

    def importTabbedText(self):
        """Import a file with tabbed title structure.

        Return the model if import is successful, otherwise None
        """
        textLevelList = []
        with open(self.filePath, 'r',
                  encoding=globalref.localTextEncoding) as f:
            for line in f:
                text = line.strip()
                if text:
                    level = line.count('\t', 0, len(line) - len(line.lstrip()))
                    textLevelList.append((text, level))
        if textLevelList:
            if len([item for item in textLevelList if item[1] == 0]) > 1:
                textLevelList = [(text, level + 1) for text, level in
                                 textLevelList]
                textLevelList.insert(0, (treemodel.defaultRootName, 0))
            model = treemodel.TreeModel(True)
            text, level = textLevelList.pop(0)
            if level == 0:
                model.root.setTitle(text)
                if model.root.loadChildLevels(textLevelList):
                    return model
        return None

    def importTableText(self):
        """Import a file with a tab-delimited table with header row.

        Return the model if import is successful, otherwise None.
        """
        model = treemodel.TreeModel(True)
        typeName = _('TABLE')
        tableFormat = nodeformat.NodeFormat(typeName, model.formats)
        model.formats.addTypeIfMissing(tableFormat)
        with open(self.filePath, 'r',
                  encoding=globalref.localTextEncoding) as f:
            headings = [self.correctFieldName(name) for name in 
                        f.readline().split('\t')]
            tableFormat.addFieldList(headings, True, True)
            lineNum = 1
            for line in f:
                lineNum += 1
                if line.strip():
                    entries = line.split('\t')
                    node = treenode.TreeNode(model.root, typeName, model)
                    model.root.childList.append(node)
                    try:
                        for heading in headings:
                            node.data[heading] = entries.pop(0)
                    except IndexError:
                        pass    # fewer entries than headings is OK
                    if entries:
                        self.errorMessage = (_('Too many entries on Line {0}').
                                             format(lineNum))
                        return None   # abort if too few headings
                    node.setUniqueId(True)
        return model

    @staticmethod
    def correctFieldName(name):
        """Return the field name with any illegal characters removed.

        Arguments:
            name -- the name to modify
        """
        name = re.sub(r'[^\w_\-.]', '_', name.strip())
        if not name:
            return 'X'
        if not name[0].isalpha() or name[:3].lower() == 'xml':
            name = 'X' + name
        return name

    def importTextLines(self):
        """Import a text file, creating one node per line.

        Return the model if import is successful, otherwise None.
        """
        model = treemodel.TreeModel(True)
        with open(self.filePath, 'r',
                  encoding=globalref.localTextEncoding) as f:
            for line in f:
                line = line.strip()
                if line:
                    node = treenode.TreeNode(model.root, model.root.formatName,
                                             model)
                    model.root.childList.append(node)
                    node.data[nodeformat.defaultFieldName] = line
                    node.setUniqueId(True)
        return model

    def importTextPara(self):
        """Import a text file, creating one node per paragraph.

        Blank line delimited.
        Return the model if import is successful, otherwise None.
        """
        model = treemodel.TreeModel(True)
        with open(self.filePath, 'r',
                  encoding=globalref.localTextEncoding) as f:
            text = f.read()
        paraList = text.split('\n\n')
        for para in paraList:
            para = para.strip()
            if para:
                node = treenode.TreeNode(model.root, model.root.formatName,
                                         model)
                model.root.childList.append(node)
                node.data[nodeformat.defaultFieldName] = para
                node.setUniqueId(True)
        return model

    def importTreePad(self):
        """Import a Treepad file, text nodes only.

        Return the model if import is successful, otherwise None.
        """
        model = treemodel.TreeModel(True)
        tpFormat = model.formats[treeformats.defaultTypeName]
        tpFormat.addFieldList([textFieldName], False, True)
        tpFormat.fieldDict[textFieldName].changeType('SpacedText')
        with open(self.filePath, 'r',
                  encoding=globalref.localTextEncoding) as f:
            textList = f.read().split('<end node> 5P9i0s8y19Z')
        nodeList = []
        for text in textList:
            text = text.strip()
            if text:
                try:
                    text = text.split('<node>', 1)[1].lstrip()
                    lines = text.split('\n')
                    title = lines[0]
                    level = int(lines[1])
                    lines = lines[2:]
                except (ValueError, IndexError):
                    return None
                node =  treenode.TreeNode(None, tpFormat.name, model)
                node.data[nodeformat.defaultFieldName] = title
                node.data[textFieldName] = '\n'.join(lines)
                node.level = level
                node.setUniqueId(True)
                nodeList.append(node)
        parentList = []
        for node in nodeList:
            if node.level != 0:
                parentList = parentList[:node.level]
                node.parent = parentList[-1]
                parentList[-1].childList.append(node)
            parentList.append(node)
        model.root = nodeList[0]
        return model

    def importXml(self):
        """Import a non-treeline generic XML file.

        Return the model if import is successful, otherwise None.
        """
        model = treemodel.TreeModel()
        tree = ElementTree.ElementTree()
        try:
            tree.parse(self.filePath)
            self.loadXmlNode(tree.getroot(), model, None)
        except ElementTree.ParseError:
            return None
        for elemFormat in model.formats.values():  # fix formats if required
            if not elemFormat.getLines()[0]:
                elemFormat.changeTitleLine(elemFormat.name)
                for fieldName in elemFormat.fieldNames():
                    elemFormat.addOutputLine('{0}="{{*{1}*}}"'.
                                             format(fieldName, fieldName))
            if not elemFormat.fieldDict:
                elemFormat.addField(genericXmlTextFieldName)
        if model.root:
            for node in model.root.descendantGen():
                node.updateUniqueId()
            return model
        return None

    def loadXmlNode(self, element, model, parent=None):
        """Recursively load a generic XML ElementTree node and its children.

        Arguments:
            element -- an XML ElementTree node
            model -- a ref to the TreeLine model
            parent -- the parent TreeNode (None for the root node only)
        """
        elemFormat = model.formats.get(element.tag, None)
        if not elemFormat:
            elemFormat = nodeformat.NodeFormat(element.tag, model.formats)
            model.formats[element.tag] = elemFormat
        node = treenode.TreeNode(parent, elemFormat.name, model)
        if parent:
            parent.childList.append(node)
        elif model.root:
            raise ElementTree.ParseError  # invalid with two roots
        else:
            model.root = node
        if element.text and element.text.strip():
            if genericXmlTextFieldName not in elemFormat.fieldDict:
                elemFormat.addFieldList([genericXmlTextFieldName], True, True)
            node.setTitle(element.text.strip())
        for key, value in element.items():
            elemFormat.addFieldIfNew(key)
            node.data[key] = value
        for child in element:
            self.loadXmlNode(child, model, node)

    def importOdfText(self):
        """Import an ODF format text file outline.

        Return the model if import is successful, otherwise None.
        """
        model = treemodel.TreeModel(True)
        odfFormat = model.formats[treeformats.defaultTypeName]
        odfFormat.addField(textFieldName)
        odfFormat.changeOutputLines(['<b>{{*{0}*}}</b>'.
                                     format(nodeformat.defaultFieldName),
                                     '{{*{0}*}}'.format(textFieldName)])
        odfFormat.formatHtml = True
        try:
            with zipfile.ZipFile(self.filePath, 'r') as f:
                text = f.read('content.xml')
        except (zipfile.BadZipFile, KeyError):
            return None
        try:
            rootElement = ElementTree.fromstring(text)
        except ElementTree.ParseError:
            return None
        nameSpace = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
        headerTag = '{0}h'.format(nameSpace)
        paraTag = '{0}p'.format(nameSpace)
        numRegExp = re.compile(r'.*?(\d+)$')
        currentNode = model.root
        currentLevel = 0
        for elem in rootElement.iter():
            if elem.tag == headerTag:
                style = elem.get('{0}style-name'.format(nameSpace), '')
                try:
                    level = int(numRegExp.match(style).group(1))
                except AttributeError:
                    return None
                if level < 1 or level > currentLevel + 1:
                    return None
                while(currentLevel >= level):
                    currentNode = currentNode.parent
                    currentLevel -= 1
                node = treenode.TreeNode(currentNode, odfFormat.name, model)
                currentNode.childList.append(node)
                node.data[nodeformat.defaultFieldName] = ''.join(elem.
                                                                itertext())
                node.setUniqueId(True)
                currentNode = node
                currentLevel = level
            elif elem.tag == paraTag:
                text = ''.join(elem.itertext())
                origText = currentNode.data.get(textFieldName, '')
                if origText:
                    text = '{0}<br />{1}'.format(origText, text)
                node.data[textFieldName] = text
        return model

    def createBookmarkFormat(self):
        """Return a set of node formats for bookmark imports.
        """
        treeFormats = treeformats.TreeFormats()
        folderFormat = nodeformat.NodeFormat(bookmarkFolderTypeName,
                                             treeFormats, addDefaultField=True)
        folderFormat.iconName = 'folder_3'
        treeFormats[folderFormat.name] = folderFormat
        linkFormat = nodeformat.NodeFormat(bookmarkLinkTypeName, treeFormats,
                                           addDefaultField=True)
        linkFormat.addField(bookmarkLinkFieldName, {'type': 'ExternalLink'})
        linkFormat.addOutputLine('{{*{0}*}}'.format(bookmarkLinkFieldName))
        linkFormat.iconName = 'bookmark'
        treeFormats[linkFormat.name] = linkFormat
        sepFormat = nodeformat.NodeFormat(bookmarkSeparatorTypeName,
                                          treeFormats, {'formathtml': 'y'},
                                          True)
        sepFormat.changeTitleLine('------------------')
        sepFormat.changeOutputLines(['<hr>'])
        treeFormats[sepFormat.name] = sepFormat
        return treeFormats

    def importMozilla(self):
        """Import an HTML mozilla-format bookmark file.

        Return the model if import is successful, otherwise None.
        """
        model = treemodel.TreeModel()
        model.formats = self.createBookmarkFormat()
        with open(self.filePath, 'r', encoding='utf-8') as f:
            text = f.read()
        try:
            handler = HtmlBookmarkHandler(model)
            handler.feed(text)
            handler.close()
        except html.parser.HTMLParseError:
            return None
        return model

    def importXbel(self):
        """Import an XBEL format bookmark file.

        Return the model if import is successful, otherwise None.
        """
        model = treemodel.TreeModel()
        model.formats = self.createBookmarkFormat()
        tree = ElementTree.ElementTree()
        try:
            tree.parse(self.filePath)
        except ElementTree.ParseError:
            return None
        self.loadXbelNode(tree.getroot(), model, None)
        if model.root:
            return model
        return None

    def loadXbelNode(self, element, model, parent=None):
        """Recursively load an XBEL ElementTree node and its children.

        Arguments:
            element -- an XBEL ElementTree node
            model -- a ref to the TreeLine model
            parent  -- the parent TreeNode (None for the root node only)
        """
        if element.tag in ('xbel', 'folder'):
            node = treenode.TreeNode(parent, bookmarkFolderTypeName, model)
            if parent:
                parent.childList.append(node)
            else:
                model.root = node
            for child in element:
                self.loadXbelNode(child, model, node)
        elif element.tag == 'bookmark':
            node = treenode.TreeNode(parent, bookmarkLinkTypeName, model)
            parent.childList.append(node)
            link = element.get('href').strip()
            if link:
                node.data[bookmarkLinkFieldName] = ('<a href="{0}">{1}</a>'.
                                                    format(link, link))
            for child in element:
                self.loadXbelNode(child, model, node)
        elif element.tag == 'title':
            parent.setTitle(element.text)
        elif element.tag == 'separator':
            node = treenode.TreeNode(parent, bookmarkSeparatorTypeName, model)
            parent.childList.append(node)
            node.setUniqueId(True)
        else:   # unsupported tags
            pass


class HtmlBookmarkHandler(html.parser.HTMLParser):
    """Handler to parse HTML mozilla bookmark format.
    """
    def __init__(self, model):
        """Initialize the HTML parser object.

        Arguments:
            model -- a reference to the tree model
        """
        super().__init__()
        self.model = model
        self.model.root = treenode.TreeNode(None, bookmarkFolderTypeName,
                                            self.model)
        self.model.root.data[nodeformat.defaultFieldName] = _('Bookmarks')
        self.currentNode = self.model.root
        self.currentParent = None
        self.text = ''

    def handle_starttag(self, tag, attrs):
        """Called by the reader at each open tag.
        
        Arguments:
            tag -- the tag label
            attrs -- any tag attributes
        """
        if tag == 'dt' or tag == 'h1':      # start any entry
            self.text = ''
        elif tag == 'dl':    # start indent
            self.currentParent = self.currentNode
            self.currentNode = None
        elif tag == 'h3':    # start folder
            if not self.currentParent:
                raise html.parser.HTMLParseError
            self.currentNode = treenode.TreeNode(self.currentParent,
                                                 bookmarkFolderTypeName,
                                                 self.model)
            self.currentParent.childList.append(self.currentNode)
        elif tag == 'a':     # start link
            if not self.currentParent:
                raise html.parser.HTMLParseError
            self.currentNode = treenode.TreeNode(self.currentParent,
                                                 bookmarkLinkTypeName,
                                                 self.model)
            self.currentParent.childList.append(self.currentNode)
            for name, value in attrs:
                if name == 'href':
                    link = '<a href="{0}">{0}</a>'.format(value)
                    self.currentNode.data[bookmarkLinkFieldName] = link
        elif tag == 'hr':     # separator
            if not self.currentParent:
                raise html.parser.HTMLParseError
            node = treenode.TreeNode(self.currentParent,
                                     bookmarkSeparatorTypeName, self.model)
            node.setUniqueId(True)
            self.currentParent.childList.append(node)
            self.currentNode = None

    def handle_endtag(self, tag):
        """Called by the reader at each end tag.
        
        Arguments:
            tag -- the tag label
        """
        if tag == 'dl':      # end indented section
            self.currentParent = self.currentParent.parent
            self.currentNode = None
        elif tag == 'h3' or tag == 'a':    # end folder or link
            if not self.currentNode:
                raise html.parser.HTMLParseError
            self.currentNode.data[nodeformat.defaultFieldName] = self.text
            self.currentNode.updateUniqueId()
        elif tag == 'h1':    # end main title
            self.model.root.data[nodeformat.defaultFieldName] = self.text
            self.currentNode.updateUniqueId()

    def handle_data(self, data):
        """Called by the reader to process text.
        
        Arguments:
            data -- the new text
        """
        self.text += data

    def handle_entityref(self, name):
        """Convert escaped entity ref to char.
        
        Arguments:
            name -- the name of the escaped entity
        """
        self.text += htmlUnescapeDict.get(name, '')
