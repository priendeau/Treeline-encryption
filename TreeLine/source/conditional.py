#!/usr/bin/env python3

#******************************************************************************
# conditional.py, provides a class to store field comparison functions
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
from PyQt4 import QtCore, QtGui
import treeformats
import configdialog
import undo
import globalref

_operators = ['==', '<', '<=', '>', '>=', '!=', N_('starts with'),
              N_('ends with'), N_('contains'), N_('True'), N_('False')]
_functions = {'==': '__eq__', '<': '__lt__', '<=': '__le__',
              '>': '__gt__', '>=': '__ge__', '!=': '__ne__',
              'starts with': 'startswith', 'ends with': 'endswith',
              'contains': 'contains', 'True': 'true', 'False': 'false'}
_boolOper = [N_('and'), N_('or')]
_allTypeEntry = _('[All Types]')
_parseRe = re.compile(r'((?:and)|(?:or)) (\S+) (.+?) '
                      r'(?:(?<!\\)"|(?<=\\\\)")(.*?)(?:(?<!\\)"|(?<=\\\\)")')


class Conditional:
    """Stores and evaluates a conditional comparison for field data.
    """
    def __init__(self, conditionStr='', nodeFormatName=''):
        """Initialize the condition object.

        Accepts a string in the following format:
        'fieldname == "value" and otherFieldName > "othervalue"'
        Arguments:
            conditionStr -- the condition string to set
            nodeFormatName -- if name is set, restricts matches to type family
        """
        self.conditionLines = []
        conditionStr = 'and ' + conditionStr
        for boolOper, fieldName, oper, value in _parseRe.findall(conditionStr):
            value = value.replace('\\"', '"').replace('\\\\', '\\')
            self.conditionLines.append(ConditionLine(boolOper, fieldName,
                                                     oper, value))
        self.origNodeFormatName = nodeFormatName
        self.nodeFormatNames = set()
        if nodeFormatName:
            self.nodeFormatNames.add(nodeFormatName)
            nodeFormats = globalref.mainControl.activeControl.model.formats
            for nodeType in nodeFormats[nodeFormatName].derivedTypes:
                self.nodeFormatNames.add(nodeType.name)

    def evaluate(self, node):
        """Evaluate this condition and return True or False.

        Arguments:
            node -- the node to check for a field match
        """
        if (self.nodeFormatNames and
            node.formatName not in self.nodeFormatNames):
            return False
        result = True
        for conditon in self.conditionLines:
            result = conditon.evaluate(node, result)
        return result

    def conditionStr(self):
        """Return the condition string for this condition set.
        """
        return ' '.join([cond.conditionStr() for cond in
                         self.conditionLines])[4:]

    def renameFields(self, oldName, newName):
        """Rename the any fields found in condition lines.

        Arguments:
            oldName -- the previous field name
            newName -- the updated field name
        """
        for condition in self.conditionLines:
            if condition.fieldName == oldName:
                condition.fieldName = newName

    def removeField(self, fieldname):
        """Remove conditional lines referencing the given field.

        Arguments:
            fieldname -- the field name to be removed
        """
        for condition in self.conditionLines[:]:
            if condition.fieldName == fieldname:
                self.conditionLines.remove(condition)

    def __len__(self):
        """Return the number of conditions for truth testing.
        """
        return len(self.conditionLines)


class ConditionLine:
    """Stores & evaluates a portion of a conditional comparison.
    """
    def __init__(self, boolOper, fieldName, oper, value):
        """Initialize the condition line.

        Arguments:
            boolOper -- a string for combining previous lines ('and' or 'or')
            fieldName -- the field name to evaluate
            oper -- the operator string
            value -- the string for comparison
        """
        self.boolOper = boolOper
        self.fieldName = fieldName
        self.oper = oper
        self.value = value

    def evaluate(self, node, prevResult=True):
        """Evaluate this line and return True or False.

        Arguments:
            node -- the node to check for a field match
            prevResult -- the result to combine with the boolOper
        """
        try:
            field = node.nodeFormat().fieldDict[self.fieldName]
        except KeyError:
            if self.boolOper == 'and':
                return False
            return prevResult
        dataStr = field.compareValue(node)
        value = field.adjustedCompareValue(self.value)
        try:
            func = getattr(dataStr, _functions[self.oper])
        except AttributeError:
            dataStr = StringOps(dataStr)
            func = getattr(dataStr, _functions[self.oper])
            value = str(value)
        if self.boolOper == 'and':
            return prevResult and func(value)
        else:
            return prevResult or func(value)

    def conditionStr(self):
        """Return the text line for this condition.
        """
        value = self.value.replace('\\', '\\\\').replace('"', '\\"')
        return '{0} {1} {2} "{3}"'.format(self.boolOper, self.fieldName,
                                          self.oper, value)


class StringOps(str):
    """A string class with extra comparison functions.
    """
    def __new__(cls, initStr=''):
        """Return the str object.

        Arguments:
            initStr -- the initial string value
        """
        return str.__new__(cls, initStr)

    def contains(self, substr):
        """Return True if self contains substr.

        Arguments:
            substr -- the substring to check
        """
        return self.find(substr) != -1

    def true(self, other=''):
        """Always return True.

        Arguments:
            other -- unused placeholder
        """
        return True

    def false(self, other=''):
        """Always return False.

        Arguments:
            other -- unused placeholder
        """
        return False


class ConditionDialog(QtGui.QDialog):
    """Dialog for defining field condition tests.

    Used for defining conditional types (modal), for finding by condition
    (nonmodal) and for filtering by condition (nonmodal).
    """
    dialogShown = QtCore.pyqtSignal(bool)
    typeDialog, findDialog, filterDialog = range(3)
    def __init__(self, dialogType, caption, nodeFormat=None, parent=None):
        """Create the conditional dialog.

        Arguments:
            dialogType -- either typeDialog, findDialog or filterDialog
            caption -- the window title for this dialog
            nodeFormat -- the current node format for the typeDialog
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.setWindowTitle(caption)
        self.dialogType = dialogType
        self.ruleList = []
        self.combiningBoxes = []
        self.typeCombo = None
        self.resultLabel = None
        self.endFilterButton = None
        self.fieldNames = []
        if nodeFormat:
            self.fieldNames = nodeFormat.fieldNames()
        topLayout = QtGui.QVBoxLayout(self)

        if dialogType == ConditionDialog.typeDialog:
            self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                                QtCore.Qt.WindowSystemMenuHint)
        else:
            self.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
            self.setWindowFlags(QtCore.Qt.Window |
                                QtCore.Qt.WindowStaysOnTopHint)
            typeBox = QtGui.QGroupBox(_('Node Type'))
            topLayout.addWidget(typeBox)
            typeLayout = QtGui.QVBoxLayout(typeBox)
            self.typeCombo = QtGui.QComboBox()
            typeLayout.addWidget(self.typeCombo)
            self.typeCombo.currentIndexChanged.connect(self.updateDataType)

        self.mainLayout = QtGui.QVBoxLayout()
        topLayout.addLayout(self.mainLayout)

        upCtrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(upCtrlLayout)
        upCtrlLayout.addStretch()
        addButton = QtGui.QPushButton(_('&Add New Rule'))
        upCtrlLayout.addWidget(addButton)
        addButton.clicked.connect(self.addNewRule)
        self.removeButton = QtGui.QPushButton(_('&Remove Rule'))
        upCtrlLayout.addWidget(self.removeButton)
        self.removeButton.clicked.connect(self.removeRule)

        if dialogType == ConditionDialog.typeDialog:
            okButton = QtGui.QPushButton(_('&OK'))
            upCtrlLayout.addWidget(okButton)
            okButton.clicked.connect(self.accept)
            cancelButton = QtGui.QPushButton(_('&Cancel'))
            upCtrlLayout.addWidget(cancelButton)
            cancelButton.clicked.connect(self.reject)
        else:
            self.removeButton.setEnabled(False)
            self.retrieveButton = QtGui.QPushButton(_('R&etrieve Rules...'))
            upCtrlLayout.addWidget(self.retrieveButton)
            self.retrieveButton.clicked.connect(self.retrieveRules)
            saveButton = QtGui.QPushButton(_('&Save Rules...'))
            upCtrlLayout.addWidget(saveButton)
            saveButton.clicked.connect(self.saveRules)

            lowCtrlLayout = QtGui.QHBoxLayout()
            topLayout.addLayout(lowCtrlLayout)
            lowCtrlLayout.addStretch()
            if dialogType == ConditionDialog.findDialog:
                previousButton = QtGui.QPushButton(_('Find &Previous'))
                lowCtrlLayout.addWidget(previousButton)
                previousButton.clicked.connect(self.findPrevious)
                nextButton = QtGui.QPushButton(_('Find &Next'))
                nextButton.setDefault(True)
                lowCtrlLayout.addWidget(nextButton)
                nextButton.clicked.connect(self.findNext)
                self.resultLabel = QtGui.QLabel()
                topLayout.addWidget(self.resultLabel)
            else:
                filterButton = QtGui.QPushButton(_('&Filter'))
                lowCtrlLayout.addWidget(filterButton)
                filterButton.clicked.connect(self.startFilter)
                self.endFilterButton = QtGui.QPushButton(_('&End Filter'))
                lowCtrlLayout.addWidget(self.endFilterButton)
                self.endFilterButton.setEnabled(False)
                self.endFilterButton.clicked.connect(self.endFilter)
            closeButton = QtGui.QPushButton(_('&Close'))
            lowCtrlLayout.addWidget(closeButton)
            closeButton.clicked.connect(self.close)
            origTypeName = nodeFormat.name if nodeFormat else ''
            self.loadTypeNames(origTypeName)
        self.ruleList.append(ConditionRule(1, self.fieldNames))
        self.mainLayout.addWidget(self.ruleList[0])

    def addNewRule(self, checked=False, combineBool='and'):
        """Add a new empty rule to the dialog.

        Arguments:
            checked -- unused placekeeper variable for signal
            combineBool -- the boolean op for combining with the previous rule
        """
        if self.ruleList:
            boolBox = QtGui.QComboBox()
            boolBox.setEditable(False)
            self.combiningBoxes.append(boolBox)
            boolBox.addItems([_(op) for op in _boolOper])
            if combineBool != 'and':
                boolBox.setCurrentIndex(1)
            self.mainLayout.insertWidget(len(self.ruleList) * 2 - 1, boolBox,
                                        0, QtCore.Qt.AlignHCenter)
        rule = ConditionRule(len(self.ruleList) + 1, self.fieldNames)
        self.ruleList.append(rule)
        self.mainLayout.insertWidget(len(self.ruleList) * 2 - 2, rule)
        self.removeButton.setEnabled(True)

    def removeRule(self):
        """Remove the last rule from the dialog.
        """
        if self.ruleList:
            if self.combiningBoxes:
                self.combiningBoxes[-1].hide()
                del self.combiningBoxes[-1]
            self.ruleList[-1].hide()
            del self.ruleList[-1]
            if self.dialogType == ConditionDialog.typeDialog:
                self.removeButton.setEnabled(len(self.ruleList) > 0)
            else:
                self.removeButton.setEnabled(len(self.ruleList) > 1)

    def clearRules(self):
        """Remove all rules from the dialog and add default rule.
        """
        for box in self.combiningBoxes:
            box.hide()
        for rule in self.ruleList:
            rule.hide()
        self.combiningBoxes = []
        self.ruleList = [ConditionRule(1, self.fieldNames)]
        self.mainLayout.insertWidget(0, self.ruleList[0])
        self.removeButton.setEnabled(True)

    def setCondition(self, conditional, typeName=''):
        """Set rule values to match the given conditional.

        Arguments:
            conditional -- the Conditional class to match
            typeName -- an optional type name used with some dialog types
        """
        if self.typeCombo:
            if typeName:
                self.typeCombo.setCurrentIndex(self.typeCombo.
                                               findText(typeName))
            else:
                self.typeCombo.setCurrentIndex(0)
        while len(self.ruleList) > 1:
            self.removeRule()
        if conditional:
            self.ruleList[0].setCondition(conditional.conditionLines[0])
        for conditionLine in conditional.conditionLines[1:]:
            self.addNewRule(combineBool=conditionLine.boolOper)
            self.ruleList[-1].setCondition(conditionLine)

    def conditional(self):
        """Return a Conditional instance for the current settings.
        """
        combineBools = [0] + [boolBox.currentIndex() for boolBox in
                              self.combiningBoxes]
        typeName = self.typeCombo.currentText() if self.typeCombo else ''
        if typeName == _allTypeEntry:
            typeName = ''
        conditional = Conditional('', typeName)
        for boolIndex, rule in zip(combineBools, self.ruleList):
            condition = rule.conditionLine()
            if boolIndex != 0:
                condition.boolOper = 'or'
            conditional.conditionLines.append(condition)
        return conditional

    def loadTypeNames(self, origTypeName=''):
        """Load format type names into combo box.

        Arguments:
            origTypeName -- a starting type name if given
        """
        if not origTypeName:
            origTypeName = self.typeCombo.currentText()
        nodeFormats = globalref.mainControl.activeControl.model.formats
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItem(_allTypeEntry)
        typeNames = nodeFormats.typeNames()
        self.typeCombo.addItems(typeNames)
        if origTypeName and origTypeName != _allTypeEntry:
            try:
                self.typeCombo.setCurrentIndex(typeNames.index(origTypeName)
                                               + 1)
            except ValueError:
                if self.endFilterButton and self.endFilterButton.isEnabled():
                    self.endFilter()
                self.clearRules()
        self.typeCombo.blockSignals(False)
        self.retrieveButton.setEnabled(len(nodeFormats.savedConditions()) > 0)
        self.updateDataType()

    def updateDataType(self):
        """Update the node format based on a data type change.
        """
        typeName = self.typeCombo.currentText()
        if not typeName:
            return
        nodeFormats = globalref.mainControl.activeControl.model.formats
        if typeName == _allTypeEntry:
            fieldNameSet = set()
            for typeFormat in nodeFormats.values():
                fieldNameSet.update(typeFormat.fieldNames())
            self.fieldNames = sorted(list(fieldNameSet))
        else:
            self.fieldNames = nodeFormats[typeName].fieldNames()
        for rule in self.ruleList:
            currentField = rule.conditionLine().fieldName
            if currentField not in self.fieldNames:
                if self.endFilterButton and self.endFilterButton.isEnabled():
                    self.endFilter()
                self.clearRules()
                break
            rule.reloadFieldBox(self.fieldNames, currentField)

    def updateFilterControls(self):
        """Set filter button status based on active window changes.
        """
        window = globalref.mainControl.activeControl.activeWindow
        if window.isFiltering():
            filterView = window.treeFilterView
            conditional = filterView.conditionalFilter
            self.setCondition(conditional, conditional.origNodeFormatName)
            self.endFilterButton.setEnabled(True)
        else:
            self.endFilterButton.setEnabled(False)

    def retrieveRules(self):
        """Show a menu to retrieve stored rules.
        """
        modelRef = globalref.mainControl.activeControl.model
        nodeFormats = modelRef.formats
        savedRules = nodeFormats.savedConditions()
        ruleNames = sorted(list(savedRules.keys()))
        dlg = RuleRetrieveDialog(ruleNames, self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            if dlg.selectedRule:
                conditional = savedRules[dlg.selectedRule]
                self.setCondition(conditional, conditional.origNodeFormatName)
            if dlg.removedRules:
                undo.FormatUndo(modelRef.undoList, nodeFormats,
                                treeformats.TreeFormats())
                for ruleName in dlg.removedRules:
                    conditional = savedRules[ruleName]
                    if conditional.origNodeFormatName:
                        typeFormat = nodeFormats[conditional.
                                                 origNodeFormatName]
                        del typeFormat.savedConditionText[ruleName]
                    else:
                        del nodeFormats.savedConditionText[ruleName]
                self.retrieveButton.setEnabled(len(nodeFormats.
                                                   savedConditions()) > 0)
                globalref.mainControl.activeControl.setModified()

    def saveRules(self):
        """Prompt for a name for storing these rules.
        """
        modelRef = globalref.mainControl.activeControl.model
        nodeFormats = modelRef.formats
        usedNames = set(nodeFormats.savedConditions().keys())
        dlg = configdialog.NameEntryDialog(_('Save Rules'),
                                           _('Enter a descriptive name'), '',
                                           '', usedNames, self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            undo.FormatUndo(modelRef.undoList, nodeFormats,
                            treeformats.TreeFormats())
            typeName = self.typeCombo.currentText()
            if typeName == _allTypeEntry:
                nodeFormat = nodeFormats
            else:
                nodeFormat = nodeFormats[typeName]
            nodeFormat.savedConditionText[dlg.text] = (self.conditional().
                                                       conditionStr())
            self.retrieveButton.setEnabled(True)
            globalref.mainControl.activeControl.setModified()

    def find(self, forward=True):
        """Find another match in the indicated direction.

        Arguments:
            forward -- next if True, previous if False
        """
        self.resultLabel.setText('')
        conditional = self.conditional()
        control = globalref.mainControl.activeControl
        if not control.findNodesByCondition(conditional, forward):
            self.resultLabel.setText(_('No conditional matches were found'))

    def findPrevious(self):
        """Find the previous match.
        """
        self.find(False)

    def  findNext(self):
        """Find the next match.
        """
        self.find(True)

    def startFilter(self):
        """Start filtering nodes.
        """
        window = globalref.mainControl.activeControl.activeWindow
        filterView = window.treeFilterView
        filterView.conditionalFilter = self.conditional()
        filterView.updateContents()
        window.treeStack.setCurrentWidget(filterView)
        self.endFilterButton.setEnabled(True)

    def endFilter(self):
        """Stop filtering nodes.
        """
        window = globalref.mainControl.activeControl.activeWindow
        window.treeStack.setCurrentWidget(window.treeView)
        self.endFilterButton.setEnabled(False)
        globalref.mainControl.currentStatusBar().clearMessage()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


class ConditionRule(QtGui.QGroupBox):
    """Group boxes for conditional rules in the ConditionDialog.
    """
    def __init__(self, num, fieldNames, parent=None):
        """Create the conditional rule group box.

        Arguments:
            num -- the sequence number for the title
            fieldNames -- a list of available field names
            parent -- the parent dialog
        """
        super().__init__(parent)
        self.fieldNames = fieldNames
        self.setTitle(_('Rule {0}').format(num))
        layout = QtGui.QHBoxLayout(self)
        self.fieldBox = QtGui.QComboBox()
        self.fieldBox.setEditable(False)
        self.fieldBox.addItems(fieldNames)
        layout.addWidget(self.fieldBox)

        self.operBox = QtGui.QComboBox()
        self.operBox.setEditable(False)
        self.operBox.addItems([_(op) for op in _operators])
        layout.addWidget(self.operBox)
        self.operBox.currentIndexChanged.connect(self.changeOper)

        self.editor = QtGui.QLineEdit()
        layout.addWidget(self.editor)
        self.fieldBox.setFocus()

    def reloadFieldBox(self, fieldNames, currentField=''):
        """Load the field combo box with a new field list.

        Arguments:
            fieldNames -- list of field names to add
            currentField -- a field name to make current if given
        """
        self.fieldNames = fieldNames
        self.fieldBox.clear()
        self.fieldBox.addItems(fieldNames)
        if currentField:
            fieldNum = fieldNames.index(currentField)
            self.fieldBox.setCurrentIndex(fieldNum)
        self.changeOper()

    def setCondition(self, conditionLine):
        """Set values to match the given condition.

        Arguments:
            conditionLine -- the ConditionLine to match
        """
        fieldNum = self.fieldNames.index(conditionLine.fieldName)
        self.fieldBox.setCurrentIndex(fieldNum)
        operNum = _operators.index(conditionLine.oper)
        self.operBox.setCurrentIndex(operNum)
        self.editor.setText(conditionLine.value)

    def conditionLine(self):
        """Return a conditionLine for the current settings.
        """
        operTransDict = dict([(_(name), name) for name in _operators])
        oper = operTransDict[self.operBox.currentText()]
        return ConditionLine('and', self.fieldBox.currentText(), oper,
                             self.editor.text())

    def changeOper(self):
        """Set the field available based on an operator change.
        """
        realOp = self.operBox.currentText() not in (_(op) for op in
                                                       ('True', 'False'))
        self.editor.setEnabled(realOp)
        if (not realOp and
            self.parent().typeCombo.currentText() == _allTypeEntry):
            realOp = True
        self.fieldBox.setEnabled(realOp)


class RuleRetrieveDialog(QtGui.QDialog):
    """Dialog to select saved conditional rules for retrieval or removal.
    """
    def __init__(self, ruleNames, parent=None):
        """Initialize the rule retrieval dialog.

        Arguments:
            ruleNames -- a list of rulenames to show
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.ruleNames = ruleNames
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Retrieve Rules'))
        self.selectedRule = ''
        self.removedRules = []

        topLayout = QtGui.QVBoxLayout(self)
        label = QtGui.QLabel(_('Select rule set to retrieve:'))
        topLayout.addWidget(label)
        self.listBox = QtGui.QListWidget()
        topLayout.addWidget(self.listBox)
        self.listBox.addItems(ruleNames)
        self.listBox.setCurrentRow (0)
        self.listBox.itemDoubleClicked.connect(self.accept)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        removeButton = QtGui.QPushButton(_('Remove Rule'))
        ctrlLayout.addWidget(removeButton)
        removeButton.clicked.connect(self.removeRule)
        ctrlLayout.addStretch()
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def removeRule(self):
        """Remove the currently selected rule.
        """
        currentItem = self.listBox.currentItem()
        if currentItem:
            self.removedRules.append(currentItem.text())
            self.listBox.takeItem(self.listBox.currentRow())

    def accept(self):
        """Recored results before closing.
        """
        currentItem = self.listBox.currentItem()
        if currentItem:
            self.selectedRule = currentItem.text()
        return super().accept()
