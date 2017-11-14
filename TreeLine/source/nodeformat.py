#!/usr/bin/env python3

#******************************************************************************
# nodeformat.py, provides a class to handle node format objects
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
import collections
import os.path
import sys
import stat
import copy
import operator
import xml.sax.saxutils
if not sys.platform.startswith('win'):
    import pwd
from PyQt4 import QtCore, QtGui
import fieldformat
import conditional
import imports


defaultFieldName = _('Name')
uniqueIdFieldName = 'Node_Unique_ID'
_defaultOutputSeparator = ', '
_lineAttrRe = re.compile(r'line\d+$')
_fieldSplitRe = re.compile(r'({\*(?:\**|\?|!|&|#)[\w_\-.]+\*})')
_fieldPartRe = re.compile(r'{\*(\**|\?|!|&|#)([\w_\-.]+)\*}')
_endTagRe = re.compile(r'.*(<br[ /]*?>|<BR[ /]*?>|<hr[ /]*?>|<HR[ /]*?>)$')
_levelFieldRe = re.compile(r'[^0-9]+([0-9]+)$')

class NodeFormat:
    """Class to handle node format info
    
    Stores node field lists and line formatting.
    Provides methods to return formatted data.
    """
    def __init__(self, name, parentFormats, attrs=None, addDefaultField=False):
        """Initialize a tree node.

        Arguments:
            name -- the type name string
            parentFormats -- a ref to TreeFormats class for outside field refs
            attrs -- the attributes that define this type's format
            addDefaultField -- if true, adds a default initial field
        """
        self.name = name
        self.parentFormats = parentFormats
        self.idField = None
        if not attrs:
            attrs = {}
        self.spaceBetween = attrs.get('spacebetween', 'y').startswith('y')
        self.formatHtml = attrs.get('formathtml', '').startswith('y')
        self.useBullets = attrs.get('bullets', '').startswith('y')
        self.useTables = attrs.get('tables', '').startswith('y')
        self.childType = attrs.get('childtype', '')
        self.genericType = attrs.get('generic', '')
        self.conditional = conditional.Conditional(attrs.get('condition', ''))
        self.iconName = attrs.get('icon', '')
        self.outputSeparator = attrs.get('outputsep', _defaultOutputSeparator)
        self.savedConditionText = {}
        for key in attrs.keys():
            if key.startswith('cond-'):
                self.savedConditionText[key[5:]] = attrs[key]
        self.fieldDict = collections.OrderedDict()
        self.derivedTypes = []
        self.siblingPrefix = ''
        self.siblingSuffix = ''
        self.sortFields = []   # temporary storage while sorting
        if addDefaultField:
            self.addFieldIfNew(defaultFieldName)
            attrs['line0'] = '{{*{0}*}}'.format(defaultFieldName)
            attrs['line1'] = '{{*{0}*}}'.format(defaultFieldName)
        self.lineList = [['']]
        self.origLineList = []  # lines without bullet or table modifications
        lineNums = sorted([int(key[4:]) for key in attrs.keys()
                           if _lineAttrRe.match(key)])
        if lineNums:
            self.lineList = [[attrs['line{0}'.format(keyNum)]] for keyNum in
                             lineNums]
        if addDefaultField:
            self.updateLineParsing()
        if self.useBullets:
            self.addBullets()
        if self.useTables:
            self.addTables()

    def fields(self):
        """Return list of all fields.
        """
        return self.fieldDict.values()

    def fieldNames(self):
        """Return list of names of all fields.
        """
        return list(self.fieldDict.keys())

    def formatTitle(self, node):
        """Return a string with formatted title data.

        Arguments:
            node -- the node used to get data for fields
        """
        line = ''.join([part.outputText(node, True, self.formatHtml)
                        if hasattr(part, 'outputText') else part
                        for part in self.lineList[0]])
        return line.strip().split('\n', 1)[0]   # truncate to 1st line

    def formatOutput(self, node, plainText=False, keepBlanks=False):
        """Return a list of formatted text output lines.

        Arguments:
            node -- the node used to get data for fields
            plainText -- if True, remove HTML markup from fields and formats
            keepBlanks -- if True, keep lines with empty fields
        """
        result = []
        for lineData in self.lineList[1:]:
            line = ''
            numEmptyFields = 0
            numFullFields = 0
            for part in lineData:
                if hasattr(part, 'outputText'):
                    text = part.outputText(node, plainText, self.formatHtml)
                    if text:
                        numFullFields += 1
                    else:
                        numEmptyFields += 1
                    line += text
                else:
                    if not self.formatHtml and not plainText:
                        part = xml.sax.saxutils.escape(part)
                    elif self.formatHtml and plainText:
                        part = fieldformat.removeMarkup(part)
                    line += part
            if keepBlanks or numFullFields or not numEmptyFields:
                result.append(line)
            elif self.formatHtml and not plainText and result:
                # add ending HTML tag from skipped line back to previous line
                endTagMatch = _endTagRe.match(line)
                if endTagMatch:
                    result[-1] += endTagMatch.group(1)
        return result

    def addField(self, name, attrs=None):
        """Add a field type with its format to the field list.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        if not attrs:
            attrs = {}
        typeName = '{}Field'.format(attrs.get('type', 'Text'))
        field = getattr(fieldformat, typeName, fieldformat.TextField)(name,
                                                                      attrs)
        self.fieldDict[name] = field
        if attrs.get('idref', '').startswith('y'):
            self.idField = field
        elif not self.idField:
            self.idField = list(self.fieldDict.values())[0]

    def addFieldIfNew(self, name, attrs=None):
        """Add a field type to the field list if not already there.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        if name not in self.fieldDict:
            self.addField(name, attrs)

    def addFieldList(self, nameList, addFirstTitle=False, addToOutput=False):
        """Add text fields with names given in list.

        Also add to title and output lines if addOutput is True.
        Arguments:
            nameList -- the list of names to add
            addFirstTitle -- if True, use first field for title output format
            addToOutput -- repelace output lines with all fields if True
        """
        for name in nameList:
            self.addFieldIfNew(name)
        if addFirstTitle:
            self.changeTitleLine('{{*{0}*}}'.format(nameList[0]))
        if addToOutput:
            self.changeOutputLines(['{{*{0}*}}'.format(name) for name in
                                    nameList])

    def reorderFields(self, fieldNameList):
        """Change the order of fieldDict to match the given list.

        Arguments:
            fieldNameList -- a list of existing field names in a desired order
        """
        newFieldDict = collections.OrderedDict()
        for fieldName in fieldNameList:
            newFieldDict[fieldName] = self.fieldDict[fieldName]
        self.fieldDict = newFieldDict

    def removeField(self, field):
        """Remove all occurances of field from output lines.

        Arguments:
            field -- the field to be removed
        """
        for lineData in self.lineList:
            while field in lineData:
                lineData.remove(field)
        self.lineList = [line for line in self.lineList if line]
        while len(self.lineList) < 2:
            self.lineList.append([''])
        self.conditional.removeField(field.name)
        savedConditions = {}
        for name, text in self.savedConditionText.items():
            condition = conditional.Conditional(text, self.name)
            condition.removeField(field.name)
            if condition:
                savedConditions[name] = condition.conditionStr()
        self.savedConditionText = savedConditions

    def setInitDefaultData(self, data, overwrite=False):
        """Add initial default data from fields into supplied data dict.

        Arguments:
            data -- the data dict to modify
            overwrite -- if true, replace previous data entries
        """
        for field in self.fieldDict.values():
            text = field.getInitDefault()
            if text and (overwrite or not data.get(field.name, '')):
                data[field.name] = text

    def updateLineParsing(self):
        """Update the fields parsed in the output lines.

        Converts lines back to whole lines with embedded field names,
        then parse back to individual fields and text.
        """
        self.lineList = [self.parseLine(line) for line in self.getLines(False)]
        if self.origLineList:
            self.origLineList = [self.parseLine(line) for line in
                                 self.getLines(True)]

    def parseLine(self, text):
        """Parse text format line, return list of field types and text.

        Splits the line into field and text segments.
        Arguments:
            text -- the raw format text line to be parsed
        """
        text = ' '.join(text.split())
        segments = (part for part in _fieldSplitRe.split(text) if part)
        return [self.parseField(part) for part in segments]

    def parseField(self, text):
        """Parse text field, return field type or plain text if not a field.

        Arguments:
            text -- the raw format text (could be a field)
        """
        fieldMatch = _fieldPartRe.match(text)
        if fieldMatch:
            modifier = fieldMatch.group(1)
            fieldName = fieldMatch.group(2)
            try:
                if not modifier:
                    return self.fieldDict[fieldName]
                elif modifier[0] == '*' and modifier == '*' * len(modifier):
                    return fieldformat.AncestorLevelField(fieldName,
                                                          len(modifier))
                elif modifier == '?':
                    return fieldformat.AnyAncestorField(fieldName)
                elif modifier == '&':
                    return fieldformat.ChildListField(fieldName)
                elif modifier == '#':
                    match = _levelFieldRe.match(fieldName)
                    if match and match.group(1) != '0':
                        level = int(match.group(1))
                        return fieldformat.DescendantCountField(fieldName,
                                                                level)
                    else:
                        return text
                elif modifier == '!':
                    if fieldName == uniqueIdFieldName:
                        return fieldformat.UniqueIdField(fieldName)
                    else:      # file info field
                        return (self.parentFormats.fileInfoFormat.
                                fieldDict[fieldName])
            except KeyError:
                pass
        return text

    def getLines(self, useOriginal=True):
        """Return text list of lines with field names embedded.

        Arguments:
            useOriginal -- use original line list, wothout bullet or table mods
        """
        lines = self.lineList
        if useOriginal and self.origLineList:
            lines = self.origLineList
        lines = [''.join([part.sepName() if hasattr(part, 'sepName') else part
                          for part in line])
                 for line in lines]
        return lines if lines else ['']

    def changeTitleLine(self, text):
        """Replace the title format line.

        Arguments:
            text -- the new title format line
        """
        newLine = self.parseLine(text)
        if not newLine:
            newLine = ['']
        self.lineList[0] = newLine

    def changeOutputLines(self, lines, keepBlanks=False):
        """Replace the output format lines with given list.

        Arguments:
            lines -- a list of replacement format lines
            keepBlanks -- if False, ignore blank lines
        """
        self.lineList = self.lineList[:1]
        if not self.lineList:
            self.lineList = ['']
        for line in lines:
            newLine = self.parseLine(line)
            if keepBlanks or newLine:
                self.lineList.append(newLine)
        if self.useBullets:
            self.origLineList = self.lineList[:]
            self.addBullets()
        if self.useTables:
            self.origLineList = self.lineList[:]
            self.addTables()

    def addOutputLine(self, line):
        """Add an output format line after existing lines.

        Arguments:
            line -- the text line to add
        """
        if not self.lineList:
            self.lineList = ['']
        newLine = self.parseLine(line)
        if newLine:
            self.lineList.append(newLine)

    def xmlAttr(self):
        """Return a dictionary of this type's attributes.
        """
        attrs = {}
        for i, line in enumerate(self.getLines()):
            attrs['line{}'.format(i)] = line
        if not self.spaceBetween:
            attrs['spacebetween'] = 'n'
        if self.formatHtml:
            attrs['formathtml'] = 'y'
        if self.useBullets:
            attrs['bullets'] = 'y'
        if self.useTables:
            attrs['tables'] = 'y'
        if self.childType:
            attrs['childtype'] = self.childType
        if self.genericType:
            attrs['generic'] = self.genericType
        if self.conditional:
            attrs['condition'] = self.conditional.conditionStr()
        if self.iconName:
            attrs['icon'] = self.iconName
        if self.outputSeparator != _defaultOutputSeparator:
            attrs['outputsep'] = self.outputSeparator
        for key, text in self.savedConditionText.items():
            attrs['cond-' + key] = text
        return attrs

    def extractTitleData(self, titleString, data):
        """Modifies the data dictionary based on a title string.

        Match the title format to the string, return True if successful.
        Arguments:
            title -- the string with the new title
            data -- the data dictionary to be modified
        """
        fields = []
        pattern = ''
        extraText = ''
        for seg in self.lineList[0]:
            if hasattr(seg, 'name'):  # a field segment
                fields.append(seg)
                pattern += '(.*)'
            else:                     # a text separator
                pattern += re.escape(seg)
                extraText += seg
        match = re.match(pattern, titleString)
        if match:
            for num, field in enumerate(fields):
                text = match.group(num + 1)
                if field.useRichText:
                    text = xml.sax.saxutils.escape(text)
                data[field.name] = text
        elif not extraText.strip():
            # assign to 1st field if sep is only spaces
            data[fields[0].name] = titleString
            for field in fields[1:]:
                data[field.name] = ''
        else:
            return False
        return True

    def updateFromGeneric(self, genericType=None, formatsRef=None):
        """Update fields and field types to match a generic type.

        Does nothing if self is not a derived type.
        Must provide either the genericType or a formatsRef.
        Arguments:
            genericType -- the type to update from
            formatsRef -- the tree formats dict to update from
        """
        if not self.genericType:
            return
        if not genericType:
            genericType = formatsRef[self.genericType]
        newFields = collections.OrderedDict()
        for field in genericType.fieldDict.values():
            fieldMatch = self.fieldDict.get(field.name, None)
            if fieldMatch and field.typeName == fieldMatch.typeName:
                newFields[field.name] = fieldMatch
            else:
                newFields[field.name] = copy.deepcopy(field)
        self.fieldDict = newFields
        self.idField = self.fieldDict[genericType.idField.name]
        self.updateLineParsing()

    def addBullets(self):
        """Add bullet HTML tags to sibling prefix, suffix and output lines.
        """
        self.siblingPrefix = '<ul>'
        self.siblingSuffix = '</ul>'
        lines = self.getLines()
        if len(lines) > 1:
            lines[1] = '<li>' + lines[1]
            lines[-1] += '</li>'
        self.origLineList = self.lineList[:]
        self.lineList = lines
        self.updateLineParsing()

    def addTables(self):
        """Add table HTML tags to sibling prefix, suffix and output lines.
        """
        origLines = self.getLines()
        lines = [line for line in origLines[1:] if line]
        newLines = []
        headings = []
        for line in lines:
            head = ''
            firstPart = self.parseLine(line)[0]
            if hasattr(firstPart, 'split') and ':' in firstPart:
                head, line = line.split(':', 1)
            newLines.append(line.strip())
            headings.append(head.strip())
        self.siblingPrefix = '<table border="1" cellpadding="3">'
        if [head for head in headings if head]:
            self.siblingPrefix += '<tr>'
            for head in headings:
                self.siblingPrefix = ('{0}<th>{1}</th>'.
                                      format(self.siblingPrefix, head))
            self.siblingPrefix += '</tr>'
        self.siblingSuffix = '</table>'
        newLines = ['<td>{0}</td>'.format(line) for line in newLines]
        newLines[0] = '<tr>' + newLines[0]
        newLines[-1] += '</tr>'
        self.origLineList = self.lineList[:]
        self.lineList = newLines
        self.lineList.insert(0, origLines[0])
        self.updateLineParsing()

    def clearBulletsAndTables(self):
        """Remove any HTML tags for bullets and tables.
        """
        self.siblingPrefix = ''
        self.siblingSuffix = ''
        if self.origLineList:
            self.lineList = self.origLineList
            self.updateLineParsing()
        self.origLineList = []

    def updateDerivedTypes(self):
        """Update derived types after changes to this generic type.
        """
        for derivedType in self.derivedTypes:
            derivedType.updateFromGeneric(self)

    def findLinkField(self):
        """Return the field most likely to contain a bookmark URL.

        Return None if there are no matches.
        """
        availFields = [field for field in self.fieldDict.values() if
                       field.typeName == 'ExternalLink']
        if not availFields:
            return None
        bestFields = [field for field in availFields if
                      field.name.lower() ==
                      imports.bookmarkLinkFieldName.lower()]
        if bestFields:
            return bestFields[0]
        return availFields[0]

    def numberingFieldList(self):
        """Return a list of numbering field names.
        """
        return [field.name for field in self.fieldDict.values() if
                field.typeName == 'Numbering']

    def loadSortFields(self):
        """Add sort fields to temporarily stored list.

        Only used for efficiency while sorting.
        """
        self.sortFields = [field for field in self.fields() if
                           field.sortKeyNum > 0]
        self.sortFields.sort(key = operator.attrgetter('sortKeyNum'))
        if not self.sortFields:
            self.sortFields = [list(self.fields())[0]]


class FileInfoFormat(NodeFormat):
    """Node format class to store and update special file info fields.

    Fields used in print header/footer and in outputs of other node types.
    """
    typeName = 'INT_TL_FILE_DATA_FORM'
    fileFieldName = 'File_Name'
    pathFieldName = 'File_Path'
    sizeFieldName = 'File_Size'
    dateFieldName = 'File_Mod_Date'
    timeFieldName = 'File_Mod_Time'
    ownerFieldName = 'File_Owner'
    pageNumFieldName = 'Page_Number'
    numPagesFieldName = 'Number_of_Pages'
    def __init__(self, parentFormats):
        """Create a file info format.

        Arguments:
            parentFormats -- a ref to TreeFormats class
        """
        super().__init__(FileInfoFormat.typeName, parentFormats)
        self.fieldFormatModified = False
        self.addField(FileInfoFormat.fileFieldName)
        self.addField(FileInfoFormat.pathFieldName)
        self.addField(FileInfoFormat.sizeFieldName, {'type': 'Number'})
        self.addField(FileInfoFormat.dateFieldName, {'type': 'Date'})
        self.addField(FileInfoFormat.timeFieldName, {'type': 'Time'})
        if not sys.platform.startswith('win'):
            self.addField(FileInfoFormat.ownerFieldName)
        # page info only for print header:
        self.addField(FileInfoFormat.pageNumFieldName)
        self.fieldDict[FileInfoFormat.pageNumFieldName].showInDialog = False
        self.addField(FileInfoFormat.numPagesFieldName)
        self.fieldDict[FileInfoFormat.numPagesFieldName].showInDialog = False
        for field in self.fields():
            field.useFileInfo = True

    def updateFileInfo(self, fileName, fileInfoNode):
        """Update data of file info node.

        Arguments:
            fileName -- the TreeLine file path
            fileInfoNode -- the node to update
        """
        try:
            status = os.stat(fileName)
        except OSError:
            fileInfoNode.data = {}
            return
        fileInfoNode.data[FileInfoFormat.fileFieldName] = (os.path.
                                                           basename(fileName))
        fileInfoNode.data[FileInfoFormat.pathFieldName] = (os.path.
                                                           dirname(fileName))
        fileInfoNode.data[FileInfoFormat.sizeFieldName] = str(status[stat.
                                                                     ST_SIZE])
        modDateTime = QtCore.QDateTime()
        modDateTime.setTime_t(status[stat.ST_MTIME])
        modDateTime = modDateTime.toLocalTime()
        modDate = modDateTime.date().toString(QtCore.Qt.ISODate)
        modTime = modDateTime.time().toString()
        fileInfoNode.data[FileInfoFormat.dateFieldName] = modDate
        fileInfoNode.data[FileInfoFormat.timeFieldName] = modTime
        if not sys.platform.startswith('win'):
            try:
                owner = pwd.getpwuid(status[stat.ST_UID])[0]
            except KeyError:
                owner = repr(status[stat.ST_UID])
            fileInfoNode.data[FileInfoFormat.ownerFieldName] = owner

    def duplicateFieldFormats(self, altFileFormat):
        """Copy field format settings from alternate file format.

        Arguments:
            altFileFormat -- the file info format to copy from
        """
        for field in self.fields():
            altField = altFileFormat.fieldDict.get(field.name)
            if altField:
                if field.format != altField.format:
                    field.setFormat(altField.format)
                    self.fieldFormatModified = True
                if altField.prefix:
                    field.prefix = altField.prefix
                    self.fieldFormatModified = True
                if altField.suffix:
                    field.suffix = altField.suffix
                    self.fieldFormatModified = True


class DescendantCountFormat(NodeFormat):
    """Placeholder format for child count fields.

    Should not show up in main format type list.
    """
    countFieldName = 'Level'
    def __init__(self):
        super().__init__('CountFormat', None)
        for level in range(3):
            name = '{0}{1}'.format(DescendantCountFormat.countFieldName,
                                   level + 1)
            field = fieldformat.DescendantCountField(name, level + 1)
            self.fieldDict[name] = field
