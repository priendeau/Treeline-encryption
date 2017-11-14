#!/usr/bin/env python3

#******************************************************************************
# treeformats.py, provides a class to store node format types and info
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import copy
import nodeformat
import conditional
import matheval


defaultTypeName = _('DEFAULT')
dummyRootTypeName = '_DUMMY__ROOT_'

class TreeFormats(dict):
    """Class to store node format types and info.
    
    Stores node formats by format name in a dictionary.
    Provides methods to change and update format data.
    """
    def __init__(self, setDefault=False):
        """Initialize the format storage.

        Arguments:
            setDefault - if true, initializes with a default format
        """
        super().__init__()
        # new names for types renamed in the config dialog (orig names as keys)
        self.typeRenameDict = {}
        # nested dict for fields renamed, keys are type name then orig field
        self.fieldRenameDict = {}
        # list of format types with unique ID ref field changes
        self.changedIdFieldTypes = set()
        # set of math field names with deleted equations, keys are type names
        self.emptiedMathDict = {}
        self.conditionalTypes = set()
        self.mathFieldRefDict = {}
        # list of math eval levels, each is a dict by type name with lists of
        # equation fields
        self.mathLevelList = []
        # for saving all-type find/filter conditionals
        self.savedConditionText = {}
        self.configModified = False
        self.fileInfoFormat = nodeformat.FileInfoFormat(self)
        if setDefault:
            self[defaultTypeName] = nodeformat.NodeFormat(defaultTypeName,
                                                          self, {}, True)
            self.updateLineParsing()

    def typeNames(self):
        """Return a sorted list of type names.
        """
        names = list(self.keys())
        names.sort()
        return names

    def updateLineParsing(self):
        """Update the fields parsed in the output lines for each format type.
        """
        for typeFormat in self.values():
            typeFormat.updateLineParsing()

    def addTypeIfMissing(self, typeFormat):
        """Add format to available types if not a duplicate.

        Arguments:
            typeFormat -- the node format to add
        """
        self.setdefault(typeFormat.name, typeFormat)

    def addDummyRootType(self):
        """Add temporary dummy root format and return it.

        Used as a root item for copying a multiple selection.
        """
        typeFormat = nodeformat.NodeFormat(dummyRootTypeName, self)
        self[dummyRootTypeName] = typeFormat
        return typeFormat

    def removeDummyRootType(self):
        """Remove the temporary dummy root format if present.
        """
        try:
            del self[dummyRootTypeName]
        except KeyError:
            pass

    def updateDerivedRefs(self):
        """Update derived type lists (in generics) & the conditional type set.
        """
        self.conditionalTypes = set()
        for typeFormat in self.values():
            typeFormat.derivedTypes = []
            if typeFormat.conditional:
                self.conditionalTypes.add(typeFormat)
                if typeFormat.genericType:
                    self.conditionalTypes.add(self[typeFormat.genericType])
        for typeFormat in self.values():
            if typeFormat.genericType:
                genericType = self[typeFormat.genericType]
                genericType.derivedTypes.append(typeFormat)
                if genericType in self.conditionalTypes:
                    self.conditionalTypes.add(typeFormat)
        for typeFormat in self.values():
            if not typeFormat.genericType and not typeFormat.derivedTypes:
                typeFormat.conditional = conditional.Conditional()
                self.conditionalTypes.discard(typeFormat)

    def updateMathFieldRefs(self):
        """Update refs used to cycle thru math field evaluations.
        """
        self.mathFieldRefDict = {}
        allRecursiveRefs = []
        recursiveRefDict = {}
        matheval.RecursiveEqnRef.recursiveRefDict = recursiveRefDict
        for typeFormat in self.values():
            for field in typeFormat.fields():
                if field.typeName == 'Math' and field.equation:
                    recursiveRef = matheval.RecursiveEqnRef(typeFormat.name,
                                                            field)
                    allRecursiveRefs.append(recursiveRef)
                    recursiveRefDict.setdefault(field.name,
                                                []).append(recursiveRef)
                    for fieldRef in field.equation.fieldRefs:
                        fieldRef.eqnNodeTypeName = typeFormat.name
                        fieldRef.eqnFieldName = field.name
                        self.mathFieldRefDict.setdefault(fieldRef.fieldName,
                                                         []).append(fieldRef)
        if not allRecursiveRefs:
            return
        for ref in allRecursiveRefs:
            ref.setPriorities()
        allRecursiveRefs.sort()
        self.mathLevelList = [{allRecursiveRefs[0].eqnTypeName:
                               [allRecursiveRefs[0]]}]
        for prevRef, currRef in zip(allRecursiveRefs, allRecursiveRefs[1:]):
            if currRef.evalSequence == prevRef.evalSequence:
                if prevRef.evalDirection == matheval.optional:
                    prevRef.evalDirection = currRef.evalDirection
                elif currRef.evalDirection == matheval.optional:
                    currRef.evalDirection = prevRef.evalDirection
                if currRef.evalDirection != prevRef.evalDirection:
                    self.mathLevelList.append({})
            else:
                self.mathLevelList.append({})
            self.mathLevelList[-1].setdefault(currRef.eqnTypeName,
                                              []).append(currRef)

    def loadAttr(self, attrs):
        """Restore attributes from the stored file.

        Arguments:
            attrs -- a dict of attributes to load
        """
        for key in attrs.keys():
            if key.startswith('glob-cond-'):
                self.savedConditionText[key[10:]] = attrs[key]

    def xmlAttr(self):
        """Return a dictionary of the formats' attributes.
        """
        attrs = {}
        for key, text in self.savedConditionText.items():
            attrs['glob-cond-' + key] = text
        return attrs

    def copyTypes(self, sourceFormats, modelRef):
        """Copy type formats from another TreeFormats instance.

        New formats are added, ones with the same name are overwritten.
        Arguments:
            sourceFormats -- the TreeFormats instance to copy from
            modelRef -- a ref to the current model
        """
        newFormats = copy.deepcopy(self)
        for sourceFormat in sourceFormats.values():
            if sourceFormat.name in newFormats:
                newFormats.changedIdFieldTypes.add(sourceFormat)
            newFormats[sourceFormat.name] = sourceFormat
        newFormats.updateDerivedRefs()
        modelRef.configDialogFormats = newFormats
        modelRef.applyConfigDialogFormats()

    def numberingFieldDict(self):
        """Return a dict of numbering field names by node format name.
        """
        result = {}
        for typeFormat in self.values():
            numberingFields = typeFormat.numberingFieldList()
            if numberingFields:
                result[typeFormat.name] = numberingFields
        return result

    def commonFields(self, nodes):
        """Return a list of field names common to all given node formats.

        Retains the field sequence from one of the types.
        Arguments:
            nodes -- the nodes to check for common fields
        """
        formats = set()
        for node in nodes:
            formats.add(node.formatName)
        firstFields = self[formats.pop()].fieldNames()
        commonFields = set(firstFields)
        for formatName in formats:
            commonFields.intersection_update(self[formatName].fieldNames())
        return [field for field in firstFields if field in commonFields]

    def savedConditions(self):
        """Return a dictionary with saved Conditonals from all type formats.
        """
        savedConditions = {}
        # all-type conditions
        for name, text in self.savedConditionText.items():
            cond = conditional.Conditional(text)
            savedConditions[name] = cond
        # specific type conditions
        for typeFormat in self.values():
            for name, text in typeFormat.savedConditionText.items():
                cond = conditional.Conditional(text, typeFormat.name)
                savedConditions[name] = cond
        return savedConditions
