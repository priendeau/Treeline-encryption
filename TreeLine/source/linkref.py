#!/usr/bin/env python3

#******************************************************************************
# linkref.py, provides a class to store and update internal link references
#
# TreeLine, an information storage program
# Copyright (C) 2011, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import re

intLinkRegExp = re.compile(r'<a [^>]*href="#([^"]+)"[^>]*>.*?</a>',
                           re.I | re.S)


class LinkRefItem:
    """Class to store node, field and target info for a single internal link.
    """
    def __init__(self, nodeRef, fieldName, targetId):
        """Initialize the link info object.

        Arguments:
            nodeRef -- the node with this link in a field
            fieldName -- the field with theis link
            targetId -- the unique ID of the target node
        """
        self.nodeRef = nodeRef
        self.fieldName = fieldName
        self.targetId = targetId


class LinkRefCollection:
    """Class to store and retrieve the link info for a tree model.
    """
    def __init__(self):
        """Initialize the collection.

        The targetIdDict is used to find sets of link ref items by target ID,
        nodeRefDict finds sets of them by node and a nested field name dict.
        """
        self.targetIdDict = {}
        self.nodeRefDict = {}

    def addLink(self, nodeRef, fieldName, targetId):
        """Add a new link ref object.

        Arguments:
            nodeRef -- the node with this link in a field
            fieldName -- the field with this link
            targetId -- the unique ID of the target node
        """
        link = LinkRefItem(nodeRef, fieldName, targetId)
        linksByTarget = self.targetIdDict.setdefault(targetId, set())
        linksByTarget.add(link)
        fieldDict = self.nodeRefDict.setdefault(nodeRef, {})
        linksByField = fieldDict.setdefault(fieldName, set())
        linksByField.add(link)

    def searchForLinks(self, nodeRef, fieldName):
        """Add or update link ref objects for this field.

        Arguments:
            nodeRef -- the node with this link in a field
            fieldName -- the field with theis link
        """
        self.removeFieldLinks(nodeRef, fieldName)
        for match in intLinkRegExp.finditer(nodeRef.data[fieldName]):
            self.addLink(nodeRef, fieldName, match.group(1))

    def removeFieldLinks(self, nodeRef, fieldName):
        """Remove all link ref objects for this field.

        Arguments:
            nodeRef -- the node with this link in a field
            fieldName -- the field with theis link
        """
        fieldDict = self.nodeRefDict.setdefault(nodeRef, {})
        linkSet = fieldDict.setdefault(fieldName, set())
        for link in linkSet:
            linksByTarget = self.targetIdDict[link.targetId]
            linksByTarget.remove(link)
            if not linksByTarget:
                del self.targetIdDict[link.targetId]
        del fieldDict[fieldName]
        if not fieldDict:
            del self.nodeRefDict[nodeRef]

    def removeNodeLinks(self, nodeRef):
        """Remove link ref objects for all fields of this node.

        Arguments:
            nodeRef -- the node with this link in a field
        """
        fieldDict = self.nodeRefDict.setdefault(nodeRef, {})
        for linkSet in fieldDict.values():
            for link in linkSet:
                linksByTarget = self.targetIdDict[link.targetId]
                linksByTarget.remove(link)
                if not linksByTarget:
                    del self.targetIdDict[link.targetId]
        del self.nodeRefDict[nodeRef]

    def linkCount(self, nodeRef, fieldName):
        """Return the number of links stored for the given field.

        Arguments:
            nodeRef -- the node with this link in a field
            fieldName -- the field with this link
        """
        fieldDict = self.nodeRefDict.get(nodeRef, {})
        linkSet = fieldDict.get(fieldName, set())
        return len(linkSet)

    def renameTarget(self, oldTarget, newTarget):
        """Rename all link ref objects that point to a target.

        Arguments:
            oldTarget -- the original target name
            newTarget -- the new target name
        """
        links = self.targetIdDict.get(oldTarget, None)
        if links:
            linkRegExp = re.compile(r'<a [^>]*href="#{}"[^>]*>(.*?)</a>'.
                                    format(oldTarget), re.I | re.S)
            for link in links:
                link.targetId = newTarget
                link.nodeRef.data[link.fieldName] = \
                      linkRegExp.sub(r'<a href="#{}">\1</a>'.format(newTarget),
                                     link.nodeRef.data[link.fieldName])
            del self.targetIdDict[oldTarget]
            self.targetIdDict[newTarget] = links
