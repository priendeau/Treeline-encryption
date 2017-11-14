#!/usr/bin/env python3

#******************************************************************************
# treeopener.py, provides a class to open and import tree data
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from xml.etree import ElementTree
import xml.sax.saxutils
import os
import sys
import treemodel
import treenode
import nodeformat
import urltools


class TreeOpener:
    """Class to open or import tree data files
    
    Creates a new model and provides methods for file open/import.
    """
    def __init__(self):
        """Initialize a TreeOpenFile object.
        """
        self.model = treemodel.TreeModel()
        self.rootAttr = {}
        self.duplicateIdList = []

    def readFile(self, filePath):
        """Open the given TreeLine file and return the resulting model.
        
        Arguments:
            filePath -- file path or file object to open
        """
        tree = ElementTree.ElementTree()
        try:
            tree.parse(filePath)
        except ElementTree.ParseError:
            raise ParseError(_('Invalid XML file'))
        if not tree.getroot().get('item') == 'y':
            raise ParseError(_('Bad elememnt - not a valid TreeLine file'))
        version = tree.getroot().get('tlversion', '').split('.')
        try:
            version = [int(i) for i in version]
        except ValueError:
            version = []
        self.rootAttr = tree.getroot().attrib
        self.model.formats.loadAttr(self.rootAttr)
        self.loadNode(tree.getroot(), None)
        self.model.formats.updateLineParsing()
        if version < [1, 9]:
            self.convertOldFormats()
            self.convertOldNodes()
        if nodeformat.FileInfoFormat.typeName in self.model.formats:
            altFormat = self.model.formats[nodeformat.FileInfoFormat.typeName]
            self.model.formats.fileInfoFormat.duplicateFieldFormats(altFormat)
            del self.model.formats[nodeformat.FileInfoFormat.typeName]
        self.model.formats.updateDerivedRefs()
        self.model.formats.updateMathFieldRefs()
        return self.model

    def loadNode(self, element, parent=None):
        """Recursively load an ElementTree node and its children.
        
        Arguments:
            element -- an ElementTree node
            parent  -- the parent TreeNode (None for the root node only)
        """
        try:
            typeFormat = self.model.formats[element.tag]
        except KeyError:
            typeFormat = nodeformat.NodeFormat(element.tag, self.model.formats,
                                               element.attrib)
            self.model.formats[element.tag] = typeFormat
        if element.get('item') == 'y':
            node = treenode.TreeNode(parent, element.tag, self.model,
                                     element.attrib)
            if parent:
                parent.childList.append(node)
            else:
                self.model.root = node
        else:     # bare format (no nodes)
            node = None
        for child in element:
            if child.get('item') and node:
                self.loadNode(child, node)
            else:
                if node and child.text:
                    node.data[child.tag] = child.text
                    if child.get('linkcount'):
                        self.model.linkRefCollect.searchForLinks(node,
                                                                 child.tag)
                typeFormat.addFieldIfNew(child.tag, child.attrib)
        if node and typeFormat.fieldDict:
            try:
                node.setUniqueId()
            except ValueError:
                oldId = node.uniqueId
                node.setUniqueId(True)
                self.duplicateIdList.append('{0} -> {1}'.format(oldId,
                                                                node.uniqueId))

    def convertOldFormats(self):
        """Convert node and field formats from old TreeLine versions.

        Set node parameters from old file formats, change date & time formats,
        set ID ref field.
        """
        oldSpaceBetween = not self.rootAttr.get('nospace', '').startswith('y')
        oldFormatHtml = not self.rootAttr.get('nohtml', '').startswith('y')
        for nodeFormat in self.model.formats.values():
            nodeFormat.spaceBetween = oldSpaceBetween
            nodeFormat.formatHtml = oldFormatHtml
            for field in nodeFormat.fields():
                if field.oldRef:
                    nodeFormat.idField = field
                if field.typeName == 'Date':
                    field.format = field.format.replace('w', 'd')
                    field.format = field.format.replace('m', 'M')
                elif field.typeName == 'Time':
                    field.format = field.format.replace('M', 'm')
                    field.format = field.format.replace('s', 'z')
                    field.format = field.format.replace('S', 's')
                    field.format = field.format.replace('AA', 'AP')
                    field.format = field.format.replace('aa', 'ap')
                elif field.oldTypeName and field.oldTypeName in ('URL', 'Path',
                                                                 'ExecuteLink',
                                                                 'Email'):
                    field.changeType('ExternalLink')

    def convertOldNodes(self):
        """Convert node data from old TreeLine versions to match new formats.

        Fix escaping of special characters.
        """
        for node in self.model.root.descendantGen():
            for field in node.nodeFormat().fields():
                text = node.data.get(field.name, '')
                if text:
                    if field.typeName == 'Text' and not field.oldHasHtml:
                        text = text.strip()
                        text = xml.sax.saxutils.escape(text)
                        text = text.replace('\n', '<br />\n')
                        node.data[field.name] = text
                    elif (field.typeName == 'ExternalLink' and
                          field.oldTypeName):
                        dispName = node.data.get(field.oldLinkAltField, '')
                        if not dispName:
                            dispName = text
                        if field.oldTypeName == 'URL':
                            if not urltools.extractScheme(text):
                                text = urltools.replaceScheme('http', text)
                        elif field.oldTypeName == 'Path':
                            text = urltools.replaceScheme('file', text)
                        elif field.oldTypeName == 'ExecuteLink':
                            if urltools.isRelative(text):
                                fullPath = which(text)
                                if fullPath:
                                    text = fullPath
                            text = urltools.replaceScheme('file', text)
                        elif field.oldTypeName == 'Email':
                            text = urltools.replaceScheme('mailto', text)
                        node.data[field.name] = ('<a href="{0}">{1}</a>'.
                                                 format(text, dispName))
                    elif field.typeName == 'InternalLink':
                        uniqueId = treenode.adjustId(text)
                        dispName = node.data.get(field.oldLinkAltField, '')
                        if not dispName:
                            dispName = uniqueId
                        node.data[field.name] = ('<a href="#{0}">{1}</a>'.
                                                 format(uniqueId, dispName))
                    elif field.typeName == 'Picture':
                        node.data[field.name] = ('<img src="{0}" />'.
                                                 format(text))
            if node.nodeFormat().fields():   # skip for dummy root
                node.updateUniqueId()


class ParseError(Exception):
    """Exception raised when the file is not a valid format.
    """
    pass


def which(fileName):
    """Return the full path if the fileName is found somewhere in the PATH.

    If not found, return an empty string.
    Similar to the Linux which command.
    Arguments:
        fileName -- the name to search for
    """
    extList = ['']
    if sys.platform.startswith('win'):
        extList.extend(os.getenv('PATHEXT', '').split(os.pathsep))
    for path in os.get_exec_path():
        for ext in extList:
            fullPath = os.path.join(path, fileName + ext)
            if os.access(fullPath, os.X_OK):
                return fullPath
    return ''
