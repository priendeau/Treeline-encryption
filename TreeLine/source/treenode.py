#!/usr/bin/env python3

#******************************************************************************
# treenode.py, provides a class to store tree node data
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import re
import sys
import os.path
import operator
import itertools
from xml.etree import ElementTree
import globalref
import fieldformat
import nodeformat
import treeoutput
import linkref
import imports
import exports
import urltools
try:
    from __main__ import __version__
except ImportError:
    __version__ = ''

_idReplaceCharsRe = re.compile(r'[^a-zA-Z0-9_-]+')
_replaceBackrefRe = (re.compile(r'\\(\d+)'), re.compile(r'\\g<(\d+)>'))
_htmlLinkRe = re.compile(r'<a .*?href="(.+?)".*?>')
_imgLinkRe = re.compile(r'<img .*?src="(.+?)".*?>')
_exportHtmlLevel = 0     # temporary storage
_origBackrefMatch = None
_maxIdLength = 50


class TreeNode:
    """Class to store tree node data and the tree's linked structure.
    
    Stores links to the parent and lists of children and a format name string.
    Provides methods to get info on the structure and the data.
    """
    def __init__(self, parent, formatName, modelRef, attrs=None):
        """Initialize a tree node.

        Arguments:
            parent -- the parent tree node
            formatName -- a string name for this node's format info
            modelRef -- a stored ref to the model
            attrs -- a dict of stored node attributes
        """
        self.parent = parent
        self.formatName = formatName
        self.modelRef = modelRef
        if not attrs:
            attrs = {}
        self.uniqueId = attrs.get('uniqueid', '')
        self.data = {}
        self.childList = []

    def index(self):
        """Returns the index of this node in the model.
        """
        return self.modelRef.createIndex(self.row(), 0, self)

    def row(self):
        """Return the rank of this node in its parent's child list.
        """
        if self.parent:
            return self.parent.childList.index(self)
        return 0

    def numChildren(self):
        """Return number of children.
        """
        return len(self.childList)

    def nodeFormat(self):
        """Return the node format used for this node.
        """
        return self.modelRef.formats[self.formatName]

    def descendantGen(self):
        """Return a generator to step through all nodes in this branch.

        Includes self and closed nodes.
        """
        yield self
        for child in self.childList:
            for node in child.descendantGen():
                yield node

    def selectiveDescendantGen(self, openOnly=False):
        """Return a generator to step through nodes in this branch.

        Does not include the root node.
        Arguments:
            openOnly -- if True, only include children open in the current view
        """
        if not openOnly or self.isExpanded():
            for child in self.childList:
                yield child
                for node in child.selectiveDescendantGen(openOnly):
                    yield node

    def levelDescendantGen(self, includeRoot=True, maxLevel=None,
                           openOnly=False, initLevel=0):
        """Return generator with (node, level) tuples for this branch.

        Arguments:
            includeRoot -- if True, the root node is included
            maxLevel -- the max number of levels to return (no limit if none)
            openOnly -- if True, only include children open in the current view
            initLevel -- the level number to start with
        """
        if maxLevel == None:
            maxLevel = sys.maxsize
        if includeRoot:
            yield (self, initLevel)
            initLevel += 1
        if initLevel < maxLevel and (not openOnly or self.isExpanded()):
            for child in self.childList:
                for node, level in child.levelDescendantGen(True, maxLevel,
                                                            openOnly,
                                                            initLevel):
                    yield (node, level)

    def openNodes(self):
        """Return a list of all open parent nodes in this branch.
        """
        if self.childList and self.isExpanded():
            return [self] + [node for node in
                             self.selectiveDescendantGen(True) if
                             node.childList and node.isExpanded()]
        return []

    def prevSibling(self):
        """Return the nearest previous sibling or None.
        """
        if self.parent:
            pos = self.parent.childList.index(self)
            if pos > 0:
                return self.parent.childList[pos - 1]
        return None

    def nextSibling(self):
        """Return the nearest next sibling or None.
        """
        if self.parent:
            pos = self.parent.childList.index(self) + 1
            if pos < len(self.parent.childList):
                return self.parent.childList[pos]
        return None

    def nextTreeNode(self, loop=False):
        """Return the next node in the tree order.

        Return None at the end of the tree unless loop is true.
        Arguments:
            loop -- return the root node at the end of the tree if true
        """
        if self.childList:
            return self.childList[0]
        ancestor = self
        while ancestor:
            sibling = ancestor.nextSibling()
            if sibling:
                return sibling
            ancestor = ancestor.parent
        if loop:
            return self.modelRef.root
        return None

    def prevTreeNode(self, loop=False):
        """Return the previous node in the tree order.

        Return None at the root of the tree unless loop is true.
        Arguments:
            loop -- return the last node of the tree after the root if true
        """
        sibling = self.prevSibling()
        if sibling:
            return sibling.lastDescendant()
        if self.parent:
            return self.parent
        elif loop:
            return self.lastDescendant()
        return None

    def lastDescendant(self):
        """Return the last node of this node's branch (last in tree order).
        """
        node = self
        while node.childList:
            node = node.childList[-1]
        return node

    def isValid(self):
        """Return True if this node has a valid ancestry.
        """
        node = self
        while node.parent:
            node = node.parent
        return node == self.modelRef.root

    def isExpanded(self):
        """Return True if this node is expanded in the current tree view.
        """
        return globalref.mainControl.currentTreeView().isExpanded(self.index())

    def expandInView(self):
        """Expand this node in the current tree view.
        """
        globalref.mainControl.currentTreeView().expand(self.index())

    def collapseInView(self):
        """Collapse this node in the current tree view.
        """
        globalref.mainControl.currentTreeView().collapse(self.index())

    def saveExpandViewStatus(self, statusDict=None):
        """Recursively save the expand/collapse status of nodes in the branch.

        Saves by unique ID, returns dictionary.
        Arguments:
            statusDict -- a dictionary to save in
        """
        if not statusDict:
            statusDict = {}
        statusDict[self.uniqueId] = self.isExpanded()
        for node in self.childList:
            statusDict = node.saveExpandViewStatus(statusDict)
        return statusDict

    def restoreExpandViewStatus(self, statusDict):
        """Recursively restore expand/collapse status of nodes in the branch.

        Arguments:
            statusDict -- a dictionary with status by unique ID
        """
        try:
            expanded = statusDict[self.uniqueId]
            if expanded:
                self.expandInView()
            else:
                self.collapseInView()
                return
        except KeyError:
            pass
        for node in self.childList:
            node.restoreExpandViewStatus(statusDict)

    def setUniqueId(self, validate=False):
        """Add this node's unique ID to the ref dict.

        Check for format and uniqueness if not set or if validate is true.
        Arguments:
            validate -- check for format and uniqueness
        """
        if validate or not self.uniqueId:
            typeFormat = self.nodeFormat()
            self.uniqueId = typeFormat.idField.outputText(self, True,
                                                      typeFormat.formatHtml)
            self.uniqueId = adjustId(self.uniqueId)
            if self.uniqueId in self.modelRef.nodeIdDict:
                if self.uniqueId == 'id_1':
                    self.uniqueId = 'id'
                i = 1
                while (self.uniqueId + '_' + repr(i) in
                       self.modelRef.nodeIdDict):
                    i += 1
                self.uniqueId = self.uniqueId + '_' + repr(i)
        if self.uniqueId in self.modelRef.nodeIdDict:
            raise ValueError('duplicate unique ID')
        self.modelRef.nodeIdDict[self.uniqueId] = self

    def updateUniqueId(self):
        """Update and verify the unique ID and replace the ref dict entry.
        """
        if self.uniqueId:
            oldId = self.uniqueId
            self.removeUniqueId()
            self.setUniqueId(True)
            self.modelRef.linkRefCollect.renameTarget(oldId, self.uniqueId)
        else:
            self.setUniqueId(True)

    def removeUniqueId(self):
        """Remove the ref dict entry for this unique ID.
        """
        try:
            del self.modelRef.nodeIdDict[self.uniqueId]
        except KeyError:
            pass

    def treePosSortKey(self):
        """Return a sort key used to sort the selection by tree position.

        The key is a list of descendant row numbers.
        """
        nums = [self.row()]
        parent = self.parent
        while parent:
            nums.insert(0, parent.row())
            parent = parent.parent
        return nums

    def usesType(self, formatName):
        """Return True if dataType is used by self or descendants.

        Arguments:
            formatName -- the type name to search for
        """
        for node in self.descendantGen():
            if node.formatName == formatName:
                return True
        return False

    def title(self):
        """Return title info for use in a tree view.
        """
        return self.nodeFormat().formatTitle(self)

    def setTitle(self, title, updateUniqueId=True):
        """Set this node's title based on a provided string.

        Match the title format to the string, return True if successful.
        Also update the unique ID if previously set and if ID ref field changed
        Arguments:
            title -- the string with the new title
            updateUniqueId -- if True, update the unique ID if necessary
        """
        if title == self.title():
            return False
        idFieldName = self.nodeFormat().idField.name
        idData = self.data.get(idFieldName, '')
        if self.nodeFormat().extractTitleData(title, self.data):
            if updateUniqueId and (not self.uniqueId or
                                   idData != self.data.get(idFieldName, '')):
                self.updateUniqueId()
            return True
        return False

    def formatOutput(self, plainText=False, keepBlanks=False):
        """Return a list of formatted text output lines for this node.

        Arguments:
            plainText -- if True, remove HTML markup from fields and formats
            keepBlanks -- if True, keep lines with empty fields
        """
        return self.nodeFormat().formatOutput(self, plainText, keepBlanks)

    def elementXml(self, skipTypeFormats=None, addVersion=True,
                   extraFormats=True, genericFormats=None, addChildren=True):
        """Return an Element object with the XML for this branch.

        Arguments:
            skipTypeFormats -- a set of node format types not included in XML
            addVersion -- if True, add TreeLine version string
            extraFormats -- if True, includes unused format info
            genericFormats -- internal set of generic formats to be included
            addChildren -- if True, include descendant data
        """
        if skipTypeFormats == None:
            skipTypeFormats = set()
        if genericFormats == None:
            genericFormats = set()
        nodeFormat = self.nodeFormat()
        addFormat = nodeFormat not in skipTypeFormats
        element = ElementTree.Element(nodeFormat.name, {'item':'y'})
        # add line feeds to make output somewhat readable
        element.tail = '\n'
        element.text = '\n'
        if addVersion and __version__:
            element.set('tlversion', __version__)
        element.set('uniqueid', self.uniqueId)
        if addFormat:
            element.attrib.update(nodeFormat.xmlAttr())
            skipTypeFormats.add(nodeFormat)
            if nodeFormat.genericType:
                generic = self.modelRef.formats[nodeFormat.genericType]
                genericFormats.add(generic)
        for field in nodeFormat.fields():
            text = self.data.get(field.name, '')
            if text or addFormat:
                fieldElement = ElementTree.SubElement(element, field.name)
                fieldElement.tail = '\n'
                fieldElement.text = text
                linkCount = self.modelRef.linkRefCollect.linkCount(self,
                                                                   field.name)
                if linkCount:
                    fieldElement.attrib['linkcount'] = repr(linkCount)
                if addFormat:
                    fieldElement.attrib.update(field.xmlAttr())
                    if field is nodeFormat.idField:
                        fieldElement.attrib['idref'] = 'y'
        if addChildren:
            for child in self.childList:
                element.append(child.elementXml(skipTypeFormats, False, False,
                                                genericFormats))
        nodeFormats = []
        if extraFormats:   # write format info for unused formats
            nodeFormats = list(self.modelRef.formats.values())
            if self.modelRef.formats.fileInfoFormat.fieldFormatModified:
                nodeFormats.append(self.modelRef.formats.fileInfoFormat)
        elif addVersion:
            nodeFormats = list(genericFormats)
        for nodeFormat in nodeFormats:
            if nodeFormat not in skipTypeFormats:
                formatElement = ElementTree.SubElement(element,
                                                       nodeFormat.name,
                                                       {'item':'n'})
                formatElement.tail = '\n'
                formatElement.attrib.update(nodeFormat.xmlAttr())
                for field in nodeFormat.fields():
                    fieldElement = ElementTree.SubElement(formatElement,
                                                          field.name)
                    fieldElement.tail = '\n'
                    fieldElement.attrib.update(field.xmlAttr())
                    if field is nodeFormat.idField:
                        fieldElement.attrib['idref'] = 'y'
        return element

    def setInitDefaultData(self, overwrite=False):
        """Add initial default data from fields into internal data.

        Arguments:
            overwrite -- if true, replace previous data entries
        """
        self.nodeFormat().setInitDefaultData(self.data, overwrite)

    def changeDataType(self, newTypeName):
        """Change this node's data type to the given name.

        Set init default data and update the title if blank.
        Arguments:
            newTypeName -- the name of the new data type
        """
        origTitle = self.title()
        self.formatName = newTypeName
        typeFormat = self.nodeFormat()
        typeFormat.setInitDefaultData(self.data)
        if not typeFormat.formatTitle(self):
            typeFormat.extractTitleData(origTitle, self.data)
        self.updateUniqueId()

    def setConditionalType(self):
        """Set self to type based on auto conditional settings.

        Return True if type is changed.
        """
        nodeFormat = self.nodeFormat()
        if nodeFormat not in self.modelRef.formats.conditionalTypes:
            return False
        if nodeFormat.genericType:
            genericFormat = self.modelRef.formats[nodeFormat.genericType]
        else:
            genericFormat = nodeFormat
        formatList = [genericFormat] + genericFormat.derivedTypes
        formatList.remove(nodeFormat)
        formatList.insert(0, nodeFormat)   # reorder to give priority
        neutralResult = None
        newType = None
        for typeFormat in formatList:
            if typeFormat.conditional:
                if typeFormat.conditional.evaluate(self):
                    newType = typeFormat
                    break
            elif not neutralResult:
                neutralResult = typeFormat
        if not newType and neutralResult:
            newType = neutralResult
        if newType and newType is not nodeFormat:
            self.changeDataType(newType.name)
            return True
        return False

    def setDescendantConditionalTypes(self):
        """Set auto conditional types for self and all descendants.

        Return number of changes made.
        """
        if not self.modelRef.formats.conditionalTypes:
            return 0
        changes = 0
        for node in self.descendantGen():
            if node.setConditionalType():
                changes += 1
        return changes

    def setData(self, field, editorText):
        """Set the data entry for the given field to editorText.

        If the data does not match the format, sets to the raw text and
        re-raises the ValueError.
        Arguments:
            field-- the field object to be set
            editorText -- new text data from an editor
        """
        try:
            self.data[field.name] = field.storedText(editorText)
        except ValueError:
            self.data[field.name] = editorText
            raise ValueError
        if field == self.nodeFormat().idField:
            self.updateUniqueId()

    def addNewChild(self, posRefNode=None, insertBefore=True,
                    newTitle=_('New')):
        """Add a new child node with this node as the parent.

        Insert the new node near the posRefNode or at the end if no ref node.
        Return the new node.
        Arguments:
            posRefNode -- a child reference for the new node's position
            insertBefore -- insert before the ref node if True, after if False
        """
        newTypeName = self.nodeFormat().childType
        if newTypeName not in self.modelRef.formats:
            if posRefNode:
                newTypeName = posRefNode.formatName
            elif self.childList:
                newTypeName = self.childList[0].formatName
            else:
                newTypeName = self.formatName
        newNode = TreeNode(self, newTypeName, self.modelRef)
        pos = len(self.childList)
        if posRefNode:
            pos = self.childList.index(posRefNode)
            if not insertBefore:
                pos += 1
        self.childList.insert(pos, newNode)
        newNode.setInitDefaultData()
        if newTitle and not newNode.title():
            newNode.setTitle(newTitle, False)
        newNode.setUniqueId(True)
        return newNode

    def replaceChildren(self, titleList):
        """Replace child nodes with titles from a text list.

        Nodes with matches in the titleList are kept, others are added or
        deleted as required.
        Arguments:
            titleList -- the list of new child titles
        """
        newTypeName = self.nodeFormat().childType
        if newTypeName not in self.modelRef.formats:
            newTypeName = (self.childList[0].formatName if self.childList else
                           self.formatName)
        matchList = []
        remainTitles = [child.title() for child in self.childList]
        for title in titleList:
            try:
                match = self.childList.pop(remainTitles.index(title))
                matchList.append((title, match))
                remainTitles = [child.title() for child in self.childList]
            except ValueError:
                matchList.append((title, None))
        newChildList = []
        firstMiss = True
        for title, node in matchList:
            if not node:
                if (firstMiss and remainTitles and
                    remainTitles[0].startswith(title)):
                    # accept partial match on first miss for split tiles
                    node = self.childList.pop(0)
                    node.setTitle(title)
                else:
                    node = TreeNode(self, newTypeName, self.modelRef)
                    node.setTitle(title, False)
                    node.setInitDefaultData()
                    node.setUniqueId(True)
                    self.expandInView()
                firstMiss = False
            newChildList.append(node)
        for child in self.childList:
            child.parent = None
            for node in child.descendantGen():
                node.removeUniqueId()
                self.modelRef.linkRefCollect.removeNodeLinks(node)
        self.childList = newChildList

    def delete(self):
        """Remove this node from tree structure and from unique ID database.
        """
        if self.parent:
            self.parent.childList.remove(self)
            self.parent = None
        for node in self.descendantGen():
            node.removeUniqueId()
            self.modelRef.linkRefCollect.removeNodeLinks(node)

    def indent(self):
        """Make this node a child of the previous sibling.
        """
        newParent = self.prevSibling()
        if not newParent:
            return
        oldParent = self.parent
        expandDict = oldParent.saveExpandViewStatus()
        self.parent.childList.remove(self)
        newParent.childList.append(self)
        self.parent = newParent
        oldParent.restoreExpandViewStatus(expandDict)

    def unindent(self):
        """Make this node its parent's next sibling.
        """
        sibling = self.parent
        if not sibling or not sibling.parent:
            return
        expandDict = sibling.parent.saveExpandViewStatus()
        self.parent.childList.remove(self)
        pos = sibling.parent.childList.index(sibling) + 1
        sibling.parent.childList.insert(pos, self)
        self.parent = sibling.parent
        sibling.parent.restoreExpandViewStatus(expandDict)

    def wordSearch(self, wordList, titleOnly=False):
        """Return True if all words in wordlist are found in this node's data.

        Arguments:
            wordList -- a list of words or phrases to find
            titleOnly -- search only in the title text if True
        """
        dataStr = self.title().lower()
        if not titleOnly:
            # join with null char so phrase matches don't cross borders
            dataStr = '{0}\0{1}'.format(dataStr,
                                        '\0'.join(self.data.values()).lower())
        for word in wordList:
            if word not in dataStr:
                return False
        return True

    def regExpSearch(self, regExpList, titleOnly=False):
        """Return True if the regular expression is found in this node's data.

        Arguments:
            regExpList -- a list of regular expression objects to find
            titleOnly -- search only in the title text if True
        """
        dataStr = self.title()
        if not titleOnly:
            # join with null char so phrase matches don't cross borders
            dataStr = '{0}\0{1}'.format(dataStr, '\0'.join(self.data.values()))
        for regExpObj in regExpList:
            if not regExpObj.search(dataStr):
                return False
        return True

    def searchReplace(self, searchText='', regExpObj=None, skipMatches=0,
                      typeName='', fieldName='', replaceText=None,
                      replaceAll=False):
        """Find the search text in the field data and optionally replace it.

        Returns a tuple of the fieldName where found (empty string if not
        found), the node match number and the field match number.
        Returns the last match if skipMatches < 0 (not used with replace).
        Arguments:
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
            skipMatches -- number of already found matches to skip in this node
            typeName -- if given, verify that this node matches this type
            fieldName -- if given, only find matches under this type name
            replaceText -- if not None, replace a match with this string
            replaceAll -- if True, replace all matches (returns last fieldName)
        """
        if typeName and typeName != self.formatName:
            return ('', 0, 0)
        nodeFormat = self.nodeFormat()
        fields = ([nodeFormat.fieldDict[fieldName]] if fieldName
                  else nodeFormat.fields())
        matchedFieldname = ''
        findCount = 0
        prevFieldFindCount = 0
        for field in fields:
            fieldText = field.editorText(self)
            fieldFindCount = 0
            pos = 0
            while True:
                if pos >= len(fieldText):
                    break
                if searchText:
                    pos = fieldText.lower().find(searchText, pos)
                else:
                    match = regExpObj.search(fieldText, pos)
                    pos = match.start() if match else -1
                if pos < 0:
                    break
                findCount += 1
                fieldFindCount += 1
                prevFieldFindCount = fieldFindCount
                matchLen = (len(searchText) if searchText
                            else len(match.group()))
                if findCount > skipMatches:
                    matchedFieldname = field.name
                    if replaceText is not None:
                        replace = replaceText
                        if not searchText:
                            global _origBackrefMatch
                            _origBackrefMatch = match
                            for backrefRe in _replaceBackrefRe:
                                replace = backrefRe.sub(self.replaceBackref,
                                                        replace)
                        fieldText = (fieldText[:pos] + replace +
                                     fieldText[pos + matchLen:])
                        try:
                            self.setData(field, fieldText)
                        except ValueError:
                            pass
                    if not replaceAll and skipMatches >= 0:
                        return (field.name, findCount, fieldFindCount)
                pos += matchLen
        if not matchedFieldname:
            findCount = prevFieldFindCount = 0
        return (matchedFieldname, findCount, prevFieldFindCount)

    @staticmethod
    def replaceBackref(match):
        """Return the re match group from _origBackrefMatch for replacement.

        Used for reg exp backreference replacement.
        Arguments:
            match -- the backref match in the replacement string
        """
        return _origBackrefMatch.group(int(match.group(1)))

    def fieldSortKey(self, level=0):
        """Return a key used to sort by key fields.

        Arguments:
            level -- the sort key depth level for the current sort stage
        """
        nodeFormat = self.nodeFormat()
        if len(nodeFormat.sortFields) > level:
            return nodeFormat.sortFields[level].sortKey(self)
        return ('',)

    def sortChildrenByField(self, recursive=True, forward=True):
        """Sort child nodes by predefined field keys.

        Arguments:
            recursive -- continue to sort recursively if true
            forward -- reverse the sort if false
        """
        formats = set([child.nodeFormat() for child in self.childList])
        maxDepth = 0
        directions = []
        for nodeFormat in formats:
            if not nodeFormat.sortFields:
                nodeFormat.loadSortFields()
            maxDepth = max(maxDepth, len(nodeFormat.sortFields))
            newDirections = [field.sortKeyForward for field in
                             nodeFormat.sortFields]
            directions = [sum(i) for i in itertools.zip_longest(directions,
                                                                newDirections,
                                                                fillvalue=
                                                                False)]
        if forward:
            directions = [bool(direct) for direct in directions]
        else:
            directions = [not bool(direct) for direct in directions]
        for level in range(maxDepth, 0, -1):
            self.childList.sort(key = operator.methodcaller('fieldSortKey',
                                                            level - 1),
                                reverse = not directions[level - 1])
        if recursive:
            for child in self.childList:
                child.sortChildrenByField(True, forward)

    def titleSortKey(self):
        """Return a key used to sort by titles.
        """
        return self.title().lower()

    def sortChildrenByTitle(self, recursive=True, forward=True):
        """Sort child nodes by titles.

        Arguments:
            recursive -- continue to sort recursively if true
            forward -- reverse the sort if false
        """
        self.childList.sort(key = operator.methodcaller('titleSortKey'),
                            reverse = not forward)
        if recursive:
            for child in self.childList:
                child.sortChildrenByTitle(True, forward)

    def loadChildLevels(self, textLevelList, initLevel=0):
        """Recursively add children from a list of text titles and levels.

        Return True on success, False if data levels are not valid.
        Arguments:
            textLevelList -- list of tuples with title text and level
            initLevel -- the level of this node in the structure
        """
        while textLevelList:
            text, level = textLevelList[0]
            if level == initLevel + 1:
                del textLevelList[0]
                child = TreeNode(self, self.formatName, self.modelRef)
                child.setTitle(text)
                self.childList.append(child)
                if not child.loadChildLevels(textLevelList, level):
                    return False
            else:
                return 0 < level <= initLevel
        return True

    def updateNodeMathFields(self):
        """Recalculate math fields that depend on this node and so on.

        Return True if any data was changed.
        """
        changed = False
        for field in self.nodeFormat().fields():
            for fieldRef in (self.modelRef.formats.mathFieldRefDict.
                             get(field.name, [])):
                for node in fieldRef.dependentEqnNodes(self):
                    if node.recalcMathField(fieldRef.eqnFieldName):
                        changed = True
        return changed

    def recalcMathField(self, eqnFieldName):
        """Recalculate a math field, if changed, recalc depending math fields.

        Return True if any data was changed.
        Arguments:
            eqnFieldName -- the equation field in this node to update
        """
        changed = False
        oldValue = self.data.get(eqnFieldName, '')
        newValue = (self.nodeFormat().fieldDict[eqnFieldName].
                    equationValue(self))
        if newValue != oldValue:
            self.data[eqnFieldName] = newValue
            changed = True
            for fieldRef in (self.modelRef.formats.mathFieldRefDict.
                             get(eqnFieldName, [])):
                for node in fieldRef.dependentEqnNodes(self):
                    node.recalcMathField(fieldRef.eqnFieldName)
        return changed

    def updateNumbering(self, fieldDict, currentSequence, levelLimit,
                        includeRoot=True, reserveNums=True,
                        restartSetting=False):
        """Add auto incremented numbering to fields by type in the dict.

        Arguments:
            fieldDict -- numbering field name lists stored by type name
            currentSequence -- a list of int for the current numbering sequence
            levelLimit -- the number of child levels to include
            includeRoot -- if Ture, number the current node
            reserveNums -- if true, increment number even without num field
            restartSetting -- if true, restart numbering after a no-field gap
        """
        childSequence = currentSequence[:]
        if includeRoot:
            for fieldName in fieldDict.get(self.formatName, []):
                self.data[fieldName] = '.'.join((repr(num) for num in
                                                 currentSequence))
            if self.formatName in fieldDict or reserveNums:
                childSequence += [1]
        if levelLimit > 0:
            for child in self.childList:
                child.updateNumbering(fieldDict, childSequence, levelLimit - 1,
                                      True, reserveNums, restartSetting)
                if child.formatName in fieldDict or reserveNums:
                    childSequence[-1] += 1
                if restartSetting and child.formatName not in fieldDict:
                    childSequence[-1] = 1

    def flatChildCategory(self, origFormats):
        """Collapse descendant nodes by merging fields.

        Overwrites data in any fields with the same name.
        Arguments:
            origFormats -- copy of tree formats before any changes
        """
        self.childList = [node for node in self.selectiveDescendantGen() if
                          not node.childList]
        for node in self.childList:
            oldParent = node.parent
            while oldParent != self:
                for field in origFormats[oldParent.formatName].fields():
                    data = oldParent.data.get(field.name, '')
                    if data:
                        node.data[field.name] = data
                    node.nodeFormat().addFieldIfNew(field.name,
                                                    field.xmlAttr())
                oldParent.removeUniqueId()
                oldParent = oldParent.parent
            node.parent = self

    def addChildCategory(self, catList):
        """Insert category nodes above children.

        Arguments:
            catList -- the field names to add to the new level
        """
        newFormat = None
        catSet = set(catList)
        similarFormats = [nodeFormat for nodeFormat in
                          self.modelRef.formats.values() if
                          catSet.issubset(set(nodeFormat.fieldNames()))]
        if similarFormats:
            similarFormat = min(similarFormats, key=lambda f: len(f.fieldDict))
            if len(similarFormat.fieldDict) < len(self.childList[0].
                                                  nodeFormat().fieldDict):
                newFormat = similarFormat
        if not newFormat:
            newFormatName = '{0}_TYPE'.format(catList[0].upper())
            num = 1
            while newFormatName in self.modelRef.formats:
                newFormatName = '{0}_TYPE_{1}'.format(catList[0].upper(), num)
                num += 1
            newFormat = nodeformat.NodeFormat(newFormatName,
                                              self.modelRef.formats)
            newFormat.addFieldList(catList, True, True)
            self.modelRef.formats[newFormatName] = newFormat
        newParents = []
        for child in self.childList:
            newParent = child.findEqualFields(catList, newParents)
            if not newParent:
                newParent = TreeNode(self, newFormat.name, self.modelRef)
                for field in catList:
                    data = child.data.get(field, '')
                    if data:
                        newParent.data[field] = data
                newParent.setUniqueId(True)
                newParents.append(newParent)
            newParent.childList.append(child)
            child.parent = newParent
        self.childList = newParents

    def findEqualFields(self, fieldNames, nodes):
        """Return first node in nodes with same data in fieldNames as self.

        Arguments:
            fieldNames -- the list of fields to check
            nodes -- the nodes to search for a match
        """
        for node in nodes:
            for field in fieldNames:
                if self.data.get(field, '') != node.data.get(field, ''):
                    break
            else:   # this for loop didn't hit break, so we have a match
                return node

    def flatChildLink(self, newFieldName):
        """Collapse descendant nodes by adding parent links.

        Arguments:
            newFieldName -- the new link field name
        """
        self.childList = [node for node in self.selectiveDescendantGen()]
        for node in self.childList:
            node.nodeFormat().addField(newFieldName, {'type': 'InternalLink'})
            linkField = node.nodeFormat().fieldDict[newFieldName]
            node.data[newFieldName] = linkField.storedText(node.parent.
                                                           uniqueId)
            node.childList = []
            node.parent = self

    def arrangeByLink(self, linkField):
        """Place descendant nodes under parents found in link fields.

        Arguments:
            linkField -- the field name for the parent links
        """
        descendList = [node for node in self.selectiveDescendantGen()]
        for node in descendList:
            node.childList = []
        self.childList = []
        for node in descendList:
            parentNode = None
            linkMatch = linkref.intLinkRegExp.search(node.data.get(linkField,
                                                                   ''))
            if linkMatch:
                parentId = linkMatch.group(1)
                parentNode = self.modelRef.nodeIdDict.get(parentId, None)
            if not parentNode:
                parentNode = self
            node.parent = parentNode
            parentNode.childList.append(node)

    def exportTitleText(self, level=0, openOnly=False):
        """Return a list of tabbed title lines for this node and descendants.

        Arguments:
            level -- indicates the indent level needed
            openOnly -- if True, only include children open in the current view
        """
        textList = ['\t' * level + self.title()]
        if not openOnly or self.isExpanded():
            for child in self.childList:
                textList.extend(child.exportTitleText(level + 1, openOnly))
        return textList

    def exportHtmlPage(self, level=0):
        """Write web pages with navigation for this node and descendents.

        Arguments:
            level -- indicates the depth and how far up the css file is
        """
        lines = ['<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 '
                 'Transitional//EN">', '<html>', '<head>',
                 '<meta http-equiv="Content-Type" content="text/html; '
                 'charset=utf-8">',
                 '<link rel="stylesheet" type="text/css" '
                 'href="{0}default.css" />'.format('../' * level),
                 '<title>{0}</title>'.format(self.title()),
                 '</head>', '<body>', '<div id="sidebar">']
        uncleList = (self.parent.parent.childList if level > 1 else
                     [self.parent])
        for uncle in uncleList:
            if uncle:
                lines.append('&bull; <a href="../{0}.html">{1}</a><br />'.
                             format(uncle.uniqueId, uncle.title()))
            if uncle is self.parent:
                siblingList = (self.parent.childList if level > 0 else
                               [self])
                if siblingList:
                    lines.append('<div>')
                    for sibling in siblingList:
                        if sibling is self:
                            lines.append('&bull; <b>{0}</b><br />'.
                                         format(self.title()))
                            if self.childList:
                                lines.append('<div>')
                                for child in self.childList:
                                    lines.append('&bull; <a href="{0}/{1}'
                                                 '.html">{2}</a><br />'.
                                                 format(self.uniqueId,
                                                        child.uniqueId,
                                                        child.title()))
                                lines.append('</div>')
                        else:
                            lines.append('&bull; <a href="{0}.html">{1}</a>'
                                         '<br />'.
                                         format(sibling.uniqueId,
                                                sibling.title()))
                    lines.append('</div>')
        lines.extend(['</div>', '<div id="content">'])
        outputGroup = treeoutput.OutputGroup([self])
        outputGroup.addSiblingPrefixes()
        outputLines = outputGroup.getLines()
        newLines = []
        global _exportHtmlLevel
        _exportHtmlLevel = level
        for line in outputLines:
            line = _htmlLinkRe.sub(self.localLinkReplace, line)
            line = _imgLinkRe.sub(self.localLinkReplace, line)
            newLines.append(line)
        outputLines = newLines
        for linkSet in (self.modelRef.linkRefCollect.nodeRefDict.
                        get(self, {}).values()):
            nodePath = ''
            nodeParent = self.parent
            while nodeParent:
                nodePath = os.path.join(nodeParent.uniqueId, nodePath)
                nodeParent = nodeParent.parent
            for linkRef in linkSet:
                targetNode = self.modelRef.nodeIdDict[linkRef.targetId]
                targetPath = targetNode.uniqueId + '.html'
                targetParent = targetNode.parent
                while targetParent:
                    targetPath = os.path.join(targetParent.uniqueId,
                                              targetPath)
                    targetParent = targetParent.parent
                targetPath = os.path.relpath(targetPath, nodePath)
                newLines = []
                for line in outputLines:
                    newLines.append(re.sub(r'<a href="#{0}">'.
                                           format(targetNode.uniqueId),
                                           '<a href="{0}">'.format(targetPath),
                                           line))
                outputLines = newLines
        lines.extend(outputLines)
        lines.extend(['</div>', '</body>', '</html>'])
        fileName = self.uniqueId + '.html'
        with open(fileName, 'w', encoding='utf-8') as f:
            f.writelines([(line + '\n') for line in lines])
        if self.childList:
            if not os.access(self.uniqueId, os.R_OK):
                os.mkdir(self.uniqueId, 0o755)
            os.chdir(self.uniqueId)
            for child in self.childList:
                child.exportHtmlPage(level + 1)
            os.chdir('..')

    @staticmethod
    def localLinkReplace(match):
        """Replace a local link address with one pointing up several levels.

        Return the modified match string.
        Arguments:
            match -- the link match object
        """
        path = match.group(1)
        fullmatch = match.group(0)
        if (urltools.isRelative(path) and path[0] != '#' and
            not path.startswith('data:')):
            fullmatch = fullmatch.replace(path,
                                          '../' * _exportHtmlLevel + path)
        return fullmatch

    def exportHtmlTable(self, parentTitle=None, level=1):
        """Write web pages with tables for child data to nested directories.

        Arguments:
            parentTitle -- the title of the parent page, used in a go-up link
            level -- the depth and how far up local links should point
        """
        if not self.childList:
            return
        if not os.access(self.uniqueId, os.R_OK):
            os.mkdir(self.uniqueId, 0o755)
        os.chdir(self.uniqueId)
        title = self.title()
        lines = ['<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 '
                 'Transitional//EN">', '<html>', '<head>',
                 '<meta http-equiv="Content-Type" content="text/html; '
                 'charset=utf-8">', '<title>{0}</title>'.format(title),
                 '</head>', '<body>']
        if exports.ExportDialog.addHeader:
            headerText = (globalref.mainControl.activeControl.printData.
                          formatHeaderFooter(True))
            if headerText:
                lines.append(headerText)
        lines.append('<h1 align="center">{0}</h1>'.format(title))
        if parentTitle:
            lines.append('<p align="center">{0}<a href="../index.html">{1}'
                         '</a></p>'.format('Parent: ', parentTitle))
        lines.extend(['<table cellpadding="10">', '<tr>'])
        lines.extend(['<th><u>{0}</u></th>'.format(name) for name in
                      self.childList[0].nodeFormat().fieldNames()])
        lines.append('</tr><tr>')
        nodePath = self.uniqueId   # used for internal link relative paths
        nodeParent = self.parent
        while nodeParent:
            nodePath = os.path.join(nodeParent.uniqueId, nodePath)
            nodeParent = nodeParent.parent
        for child in self.childList:
            cellList = [field.outputText(child, False, True) for field in
                        child.nodeFormat().fields()]
            newList = []
            global _exportHtmlLevel
            _exportHtmlLevel = level
            for cell in cellList:
                cell = _htmlLinkRe.sub(self.localLinkReplace, cell)
                cell = _imgLinkRe.sub(self.localLinkReplace, cell)
                newList.append(cell)
            cellList = newList
            if child.childList:
                cellList[0] = ('<a href="{0}/index.html">{1}</a>'.
                               format(child.uniqueId, cellList[0]))
            if child.uniqueId in self.modelRef.linkRefCollect.targetIdDict:
                cellList[0] = '<a id="{0}" />{1}'.format(child.uniqueId,
                                                         cellList[0])
            for linkSet in (self.modelRef.linkRefCollect.nodeRefDict.
                            get(child, {}).values()):
                for linkRef in linkSet:
                    targetNode = self.modelRef.nodeIdDict[linkRef.targetId]
                    targetPath = 'index.html#{0}'.format(targetNode.uniqueId)
                    targetParent = targetNode.parent
                    while targetParent:
                        targetPath = os.path.join(targetParent.uniqueId,
                                                  targetPath)
                        targetParent = targetParent.parent
                    targetPath = os.path.relpath(targetPath, nodePath)
                    fieldNum = (child.nodeFormat().fieldNames().
                                index(linkRef.fieldName))
                    cellList[fieldNum] = re.sub(r'<a href="#{0}">'.
                                                format(targetNode.uniqueId),
                                                '<a href="{0}">'.
                                                format(targetPath),
                                                cellList[fieldNum])
            lines.extend(['<td>{0}</td>'.format(cell) for cell in cellList])
            lines.append('</tr><tr>')
        lines.extend(['</tr>', '</table>'])
        if exports.ExportDialog.addHeader:
            footerText = (globalref.mainControl.activeControl.printData.
                          formatHeaderFooter(False))
            if footerText:
                lines.append(footerText)
        lines.extend(['</body>', '</html>'])
        with open('index.html', 'w', encoding='utf-8') as f:
            f.writelines([(line + '\n') for line in lines])
        for child in self.childList:
            child.exportHtmlTable(title, level + 1)
        os.chdir('..')

    def exportGenericXml(self, addChildren=True):
        """Return an ElementTree element with generic XML from this branch.

        Called recursively for children if addChildren is True.
        Arguments:
            addChildren -- add branch if True
        """
        nodeFormat = self.nodeFormat()
        element = ElementTree.Element(nodeFormat.name)
        element.tail = '\n'
        for fieldName in nodeFormat.fieldNames():
            text = self.data.get(fieldName, '')
            if text and fieldName != imports.genericXmlTextFieldName:
                element.set(fieldName, text)
        if imports.genericXmlTextFieldName in nodeFormat.fieldDict:
            text = self.data.get(imports.genericXmlTextFieldName, '')
            if text:
                element.text = text
        if addChildren and self.childList:
            if not text:
                element.text = '\n'
            for child in self.childList:
                element.append(child.exportGenericXml())
        return element

    def exportOdf(self, parentElem, addChildren=True, level=1, maxLevel=1):
        """Add heading and text elements to the parent element tree element.

        Called recursively for children if addChildren is True.
        Returns the maximum indent level used for this branch.
        Arguments:
            parentElem -- the parent element tree element to add to
            addChildren -- add branch if True
            level -- the current tree indent level
            maxLevel -- the previous max indent level
        """
        headElem = exports.addOdfElement('text:h', parentElem,
                                         {'text:outline-level':
                                          '{0}'.format(level),
                                          'text:style-name':
                                          'Heading_20_{0}'.format(level)})
        headElem.text = self.title()
        output = self.formatOutput(True)
        if output and output[0] == self.title():
            del output[0]      # remove first line if same as title
        for line in output:
            textElem = exports.addOdfElement('text:p', parentElem,
                                             {'text:outline-level':
                                              '{0}'.format(level),
                                              'text:style-name':
                                              'Text_20_body'})
            textElem.text = line
        if addChildren and self.childList:
            for child in self.childList:
                childlevel = child.exportOdf(parentElem, True, level + 1,
                                             maxLevel)
                maxLevel = max(childlevel, maxLevel)
        else:
            maxLevel = max(level, maxLevel)
        return maxLevel

    def exportHtmlBookmarks(self, addChildren=True):
        """Return a text list ith descendant bookmarks in Mozilla format.

        Called recursively for children if addChildren is True.
        Arguments:
            addChildren -- add branch if True
        """
        title = self.title()
        if not self.childList:
            nodeFormat = self.nodeFormat()
            field = nodeFormat.findLinkField()
            if field:
                linkMatch = fieldformat.linkRegExp.search(self.data.
                                                          get(field.name, ''))
                if linkMatch:
                    link = linkMatch.group(1)
                    return ['<dt><a href="{0}">{1}</a>'.format(link, title)]
            elif (len(nodeFormat.fieldDict) == 1 and not
                  self.data.get(nodeFormat.fieldNames()[0], '')):
                return ['<hr>']
        result = ['<dt><h3>{0}</h3>'.format(title)]
        if addChildren:
            result.append('<dl><p>')
            for child in self.childList:
                result.extend(child.exportHtmlBookmarks())
            result.append('</dl><p>')
        return result

    def exportXbel(self, addChildren=True):
        """Return an ElementTree element with XBEL bookmarks from this branch.

        Called recursively for children if addChildren is True.
        Arguments:
            addChildren -- add branch if True
        """
        titleElem = ElementTree.Element('title')
        titleElem.text = self.title()
        if not self.childList:
            nodeFormat = self.nodeFormat()
            field = nodeFormat.findLinkField()
            if field:
                linkMatch = fieldformat.linkRegExp.search(self.data.
                                                          get(field.name, ''))
                if linkMatch:
                    link = linkMatch.group(1)
                    element = ElementTree.Element('bookmark', {'href': link})
                    element.append(titleElem)
                    element.tail = '\n'
                    return element
            elif (len(nodeFormat.fieldDict) == 1 and not
                  self.data.get(nodeFormat.fieldNames()[0], '')):
                element = ElementTree.Element('separator')
                element.tail = '\n'
                return element
        element = ElementTree.Element('folder')
        element.append(titleElem)
        element.tail = '\n'
        if addChildren:
            for child in self.childList:
                element.append(child.exportXbel())
        return element


####  Utility Functions  ####

def adjustId(uniqueId):
    """Adjust unique ID string by shortening and replacing illegal characters.

    Arguments:
        uniqueId -- the ID to adjust
    """
    # shorten to first line
    uniqueId = uniqueId.strip().split('\n', 1)[0]
    # shorten to max length
    if len(uniqueId) > _maxIdLength:
        pos = uniqueId.rfind(' ', _maxIdLength // 2, _maxIdLength + 1)
        if pos < 0:
            pos = _maxIdLength
        uniqueId = uniqueId[:pos]
    uniqueId = uniqueId.replace(' ', '_')
    # use lower case only (html links are not case sensitive)
    uniqueId = uniqueId.lower()
    # only alphanumerics, underscores and dashes OK in HTML IDs
    uniqueId = _idReplaceCharsRe.sub('', uniqueId)
    if not uniqueId:
        uniqueId = 'id_1'
    # HTML IDs must begin with a letter
    elif not 'a' <= uniqueId[0].lower() <= 'z':
        uniqueId = 'id_' + uniqueId
    return uniqueId
