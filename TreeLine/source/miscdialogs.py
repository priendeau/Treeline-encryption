#!/usr/bin/env python3

#******************************************************************************
# miscdialogs.py, provides classes for various control dialogs
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
import collections
from PyQt4 import QtCore, QtGui
import printdialogs
import undo
import options
import globalref


class RadioChoiceDialog(QtGui.QDialog):
    """Dialog for choosing between a list of text items (radio buttons).

    Dialog title, group heading, button text and return text can be set.
    """
    def __init__(self, title, heading, choiceList, parent=None):
        """Create the radio choice dialog.

        Arguments:
            title -- the window title
            heading -- the groupbox text
            choiceList -- tuples of button text and return values
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(title)
        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)

        groupBox = QtGui.QGroupBox(heading)
        topLayout.addWidget(groupBox)
        groupLayout = QtGui.QVBoxLayout(groupBox)
        self.buttonGroup = QtGui.QButtonGroup(self)
        for text, value in choiceList:
            button = QtGui.QRadioButton(text)
            button.returnValue = value
            groupLayout.addWidget(button)
            self.buttonGroup.addButton(button)
        self.buttonGroup.buttons()[0].setChecked(True)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        groupBox.setFocus()

    def addLabelBox(self, heading, text):
        """Add a group box with text above the radio button group.

        Arguments:
            heading -- the groupbox text
            text - the label text
        """
        labelBox = QtGui.QGroupBox(heading)
        self.layout().insertWidget(0, labelBox)
        labelLayout =  QtGui.QVBoxLayout(labelBox)
        label = QtGui.QLabel(text)
        labelLayout.addWidget(label)

    def selectedButton(self):
        """Return the value of the selected button.
        """
        return self.buttonGroup.checkedButton().returnValue


class FieldSelectDialog(QtGui.QDialog):
    """Dialog for selecting a sequence from a list of field names.
    """
    def __init__(self, title, heading, fieldList, parent=None):
        """Create the field select dialog.

        Arguments:
            title -- the window title
            heading -- the groupbox text
            fieldList -- the list of field names to select
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(title)
        self.selectedFields = []
        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        groupBox = QtGui.QGroupBox(heading)
        topLayout.addWidget(groupBox)
        groupLayout = QtGui.QVBoxLayout(groupBox)

        self.listView = QtGui.QTreeWidget()
        groupLayout.addWidget(self.listView)
        self.listView.setHeaderLabels(['#', _('Fields')])
        self.listView.setRootIsDecorated(False)
        self.listView.setSortingEnabled(False)
        self.listView.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        for field in fieldList:
            QtGui.QTreeWidgetItem(self.listView, ['', field])
        self.listView.resizeColumnToContents(0)
        self.listView.resizeColumnToContents(1)
        self.listView.itemSelectionChanged.connect(self.updateSelectedFields)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        self.okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        self.okButton.setEnabled(False)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.listView.setFocus()

    def updateSelectedFields(self):
        """Update the TreeView and the list of selected fields.
        """
        itemList = [self.listView.topLevelItem(i) for i in
                    range(self.listView.topLevelItemCount())]
        for item in itemList:
            if self.listView.isItemSelected(item):
                if item.text(1) not in self.selectedFields:
                    self.selectedFields.append(item.text(1))
            elif item.text(1) in self.selectedFields:
                self.selectedFields.remove(item.text(1))
        for item in itemList:
            if self.listView.isItemSelected(item):
                item.setText(0, str(self.selectedFields.index(item.text(1))
                                    + 1))
            else:
                item.setText(0, '')
        self.okButton.setEnabled(len(self.selectedFields))


class FilePropertiesDialog(QtGui.QDialog):
    """Dialog for setting file parameters like compression and encryption.
    """
    def __init__(self, localControl, parent=None):
        """Create the file properties dialog.

        Arguments:
            localControl -- a reference to the file's local control
            parent -- the parent window
        """
        super().__init__(parent)
        self.localControl = localControl
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('File Properties'))
        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)

        groupBox = QtGui.QGroupBox(_('File Storage'))
        topLayout.addWidget(groupBox)
        groupLayout = QtGui.QVBoxLayout(groupBox)
        self.compressCheck = QtGui.QCheckBox(_('&Use file compression'))
        self.compressCheck.setChecked(localControl.compressed)
        groupLayout.addWidget(self.compressCheck)
        self.encryptCheck = QtGui.QCheckBox(_('Use file &encryption'))
        self.encryptCheck.setChecked(localControl.encrypted)
        groupLayout.addWidget(self.encryptCheck)

        groupBox = QtGui.QGroupBox(_('Spell Check'))
        topLayout.addWidget(groupBox)
        groupLayout = QtGui.QHBoxLayout(groupBox)
        label = QtGui.QLabel(_('Language code or\ndictionary (optional)'))
        groupLayout.addWidget(label)
        self.spellCheckEdit = QtGui.QLineEdit()
        self.spellCheckEdit.setText(self.localControl.spellCheckLang)
        groupLayout.addWidget(self.spellCheckEdit)

        groupBox = QtGui.QGroupBox(_('Math Fields'))
        topLayout.addWidget(groupBox)
        groupLayout = QtGui.QVBoxLayout(groupBox)
        self.zeroBlanks = QtGui.QCheckBox(_('&Treat blank fields as zeros'))
        self.zeroBlanks.setChecked(localControl.model.mathZeroBlanks)
        groupLayout.addWidget(self.zeroBlanks)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def accept(self):
        """Store the results.
        """
        if (self.localControl.compressed != self.compressCheck.isChecked() or
            self.localControl.encrypted != self.encryptCheck.isChecked() or
            self.localControl.spellCheckLang != self.spellCheckEdit.text() or
            self.localControl.model.mathZeroBlanks !=
            self.zeroBlanks.isChecked()):
            undo.ParamUndo(self.localControl.model.undoList,
                           [(self.localControl, 'compressed'),
                            (self.localControl, 'encrypted'),
                            (self.localControl, 'spellCheckLang'),
                            (self.localControl.model, 'mathZeroBlanks')])
            self.localControl.compressed = self.compressCheck.isChecked()
            self.localControl.encrypted = self.encryptCheck.isChecked()
            self.localControl.spellCheckLang = self.spellCheckEdit.text()
            self.localControl.model.mathZeroBlanks = (self.zeroBlanks.
                                                      isChecked())
            super().accept()
        else:
            super().reject()


class PasswordDialog(QtGui.QDialog):
    """Dialog for password entry and optional re-entry.
    """
    remember = True
    def __init__(self, retype=True, fileLabel='', parent=None):
        """Create the password dialog.

        Arguments:
            retype -- require a 2nd password entry if True
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Encrypted File Password'))
        self.password = ''
        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        if fileLabel:
            prompt = _('Type Password for "{0}":').format(fileLabel)
        else:
            prompt = _('Type Password:')
        self.editors = [self.addEditor(prompt, topLayout)]
        self.editors[0].setFocus()
        if retype:
            self.editors.append(self.addEditor(_('Re-Type Password:'),
                                               topLayout))
            self.editors[0].returnPressed.connect(self.editors[1].setFocus)
        self.editors[-1].returnPressed.connect(self.accept)
        self.rememberCheck = QtGui.QCheckBox(_('Remember password during this '
                                               'session'))
        self.rememberCheck.setChecked(PasswordDialog.remember)
        topLayout.addWidget(self.rememberCheck)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        okButton = QtGui.QPushButton(_('&OK'))
        okButton.setAutoDefault(False)
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        cancelButton.setAutoDefault(False)
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def addEditor(self, labelText, layout):
        """Add a password editor to this dialog and return it.

        Arguments:
            labelText -- the text for the label
            layout -- the layout to append it
        """
        label = QtGui.QLabel(labelText)
        layout.addWidget(label)
        editor = QtGui.QLineEdit()
        editor.setEchoMode(QtGui.QLineEdit.Password)
        layout.addWidget(editor)
        return editor

    def accept(self):
        """Check for valid password and store the result.
        """
        self.password = self.editors[0].text()
        PasswordDialog.remember = self.rememberCheck.isChecked()
        if not self.password:
            QtGui.QMessageBox.warning(self, 'TreeLine',
                                  _('Zero-length passwords are not permitted'))
        elif len(self.editors) > 1 and self.editors[1].text() != self.password:
             QtGui.QMessageBox.warning(self, 'TreeLine',
                                       _('Re-typed password did not match'))
        else:
            super().accept()
        for editor in self.editors:
            editor.clear()
        self.editors[0].setFocus()


class TemplateFileItem:
    """Helper class to store template paths and info.
    """
    nameExp = re.compile(r'(\d+)([a-zA-Z]+?)_(.+)')
    def __init__(self, fullPath):
        """Initialize the path.

        Arguments:
            fullPath -- the full path name
        """
        self.fullPath = fullPath
        self.number = sys.maxsize
        name = os.path.splitext(os.path.basename(fullPath))[0]
        match = TemplateFileItem.nameExp.match(name)
        if match:
            num, self.langCode, self.name = match.groups()
            self.number = int(num)
        else:
            self.langCode = ''
            self.name = name
        self.displayName = self.name.replace('_', ' ')

    def sortKey(self):
        """Return a key for sorting the items by number then name.
        """
        return (self.number, self.displayName)

    def __eq__(self, other):
        """Comparison to detect equivalent items.

        Arguments:
            other -- the TemplateFileItem to compare
        """
        return (self.displayName == other.displayName and
                self.langCode == other.langCode)

    def __hash__(self):
        """Return a hash code for use in sets and dictionaries.
        """
        return hash((self.langCode, self.displayName))


class TemplateFileDialog(QtGui.QDialog):
    """Dialog for listing available template files.
    """
    def __init__(self, title, heading, searchPaths, addDefault=True,
                 parent=None):
        """Create the template dialog.

        Arguments:
            title -- the window title
            heading -- the groupbox text
            searchPaths -- list of directories with available templates
            addDefault -- if True, add a default (no path) entry
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(title)
        self.templateItems = []
        if addDefault:
            item = TemplateFileItem('')
            item.number = -1
            item.displayName = _('Default - Single Line Text')
            self.templateItems.append(item)

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        groupBox = QtGui.QGroupBox(heading)
        topLayout.addWidget(groupBox)
        boxLayout = QtGui.QVBoxLayout(groupBox)
        self.listBox = QtGui.QListWidget()
        boxLayout.addWidget(self.listBox)
        self.listBox.itemDoubleClicked.connect(self.accept)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        self.okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

        self.readTemplates(searchPaths)
        self.loadListBox()

    def readTemplates(self, searchPaths):
        """Read template file paths into the templateItems list.

        Arguments:
            searchPaths -- list of directories with available templates
        """
        templateItems = set()
        for path in searchPaths:
            for name in os.listdir(path):
                if name.endswith('.trl'):
                    templateItem = TemplateFileItem(os.path.join(path, name))
                    if templateItem not in templateItems:
                        templateItems.add(templateItem)
        availLang = set([item.langCode for item in templateItems])
        if len(availLang) > 1:
            lang = 'en'
            if globalref.lang[:2] in availLang:
                lang = globalref.lang[:2]
            templateItems = [item for item in templateItems if
                             item.langCode == lang or not item.langCode]
        self.templateItems.extend(list(templateItems))
        self.templateItems.sort(key = operator.methodcaller('sortKey'))

    def loadListBox(self):
        """Load the list box with items from the templateItems list.
        """
        self.listBox.clear()
        self.listBox.addItems([item.displayName for item in
                               self.templateItems])
        self.listBox.setCurrentRow(0)
        self.okButton.setEnabled(self.listBox.count() > 0)

    def selectedPath(self):
        """Return the path from the selected item.
        """
        item = self.templateItems[self.listBox.currentRow()]
        return item.fullPath

    def selectedName(self):
        """Return the displayed name with underscores from the selected item.
        """
        item = self.templateItems[self.listBox.currentRow()]
        return item.name


class FindFilterDialog(QtGui.QDialog):
    """Dialog for searching for text within tree titles and data.
    """
    dialogShown = QtCore.pyqtSignal(bool)
    findDialog, filterDialog = range(2)
    fullData, titlesOnly = range(2)
    keyWords, fullWords, fullPhrase, regExp = range(4)
    def __init__(self, dialogType, parent=None):
        """Initialize the find dialog.

        Arguments:
            dialogType -- either findDialog or filterDialog (button changes)
            parent -- the parent window
        """
        super().__init__(parent)
        self.dialogType = dialogType
        self.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)

        textBox = QtGui.QGroupBox(_('&Search Text'))
        topLayout.addWidget(textBox)
        textLayout = QtGui.QVBoxLayout(textBox)
        self.textEntry = QtGui.QLineEdit()
        textLayout.addWidget(self.textEntry)
        self.textEntry.textEdited.connect(self.updateAvail)

        horizLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(horizLayout)

        whatBox = QtGui.QGroupBox(_('What to Search'))
        horizLayout.addWidget(whatBox)
        whatLayout = QtGui.QVBoxLayout(whatBox)
        self.whatButtons = QtGui.QButtonGroup(self)
        button = QtGui.QRadioButton(_('Full &data'))
        self.whatButtons.addButton(button, FindFilterDialog.fullData)
        whatLayout.addWidget(button)
        button = QtGui.QRadioButton(_('&Titles only'))
        self.whatButtons.addButton(button, FindFilterDialog.titlesOnly)
        whatLayout.addWidget(button)
        self.whatButtons.button(FindFilterDialog.fullData).setChecked(True)

        howBox = QtGui.QGroupBox(_('How to Search'))
        horizLayout.addWidget(howBox)
        howLayout = QtGui.QVBoxLayout(howBox)
        self.howButtons = QtGui.QButtonGroup(self)
        button = QtGui.QRadioButton(_('&Key words'))
        self.howButtons.addButton(button, FindFilterDialog.keyWords)
        howLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Key full &words'))
        self.howButtons.addButton(button, FindFilterDialog.fullWords)
        howLayout.addWidget(button)
        button = QtGui.QRadioButton(_('F&ull phrase'))
        self.howButtons.addButton(button, FindFilterDialog.fullPhrase)
        howLayout.addWidget(button)
        button = QtGui.QRadioButton(_('&Regular expression'))
        self.howButtons.addButton(button, FindFilterDialog.regExp)
        howLayout.addWidget(button)
        self.howButtons.button(FindFilterDialog.keyWords).setChecked(True)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        if self.dialogType == FindFilterDialog.findDialog:
            self.setWindowTitle(_('Find'))
            self.previousButton = QtGui.QPushButton(_('Find &Previous'))
            ctrlLayout.addWidget(self.previousButton)
            self.previousButton.clicked.connect(self.findPrevious)
            self.nextButton = QtGui.QPushButton(_('Find &Next'))
            self.nextButton.setDefault(True)
            ctrlLayout.addWidget(self.nextButton)
            self.nextButton.clicked.connect(self.findNext)
            self.resultLabel = QtGui.QLabel()
            topLayout.addWidget(self.resultLabel)
        else:
            self.setWindowTitle(_('Filter'))
            self.filterButton = QtGui.QPushButton(_('&Filter'))
            ctrlLayout.addWidget(self.filterButton)
            self.filterButton.clicked.connect(self.startFilter)
            self.endFilterButton = QtGui.QPushButton(_('&End Filter'))
            ctrlLayout.addWidget(self.endFilterButton)
            self.endFilterButton.clicked.connect(self.endFilter)
        closeButton = QtGui.QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)
        self.updateAvail('')

    def selectAllText(self):
        """Select all line edit text to prepare for a new entry.
        """
        self.textEntry.selectAll()
        self.textEntry.setFocus()

    def updateAvail(self, text='', fileChange=False):
        """Make find buttons available if search text exists.

        Arguments:
            text -- placeholder for signal text (not used)
            fileChange -- True if window changed while dialog open
        """
        hasEntry = len(self.textEntry.text().strip()) > 0
        if self.dialogType == FindFilterDialog.findDialog:
            self.previousButton.setEnabled(hasEntry)
            self.nextButton.setEnabled(hasEntry)
            self.resultLabel.setText('')
        else:
            window = globalref.mainControl.activeControl.activeWindow
            if fileChange and window.isFiltering():
                filterView = window.treeFilterView
                self.textEntry.setText(filterView.filterStr)
                self.whatButtons.button(filterView.filterWhat).setChecked(True)
                self.howButtons.button(filterView.filterHow).setChecked(True)
            self.filterButton.setEnabled(hasEntry)
            self.endFilterButton.setEnabled(window.isFiltering())

    def find(self, forward=True):
        """Find another match in the indicated direction.

        Arguments:
            forward -- next if True, previous if False
        """
        text = self.textEntry.text()
        titlesOnly = self.whatButtons.checkedId() == (FindFilterDialog.
                                                      titlesOnly)
        control = globalref.mainControl.activeControl
        if self.howButtons.checkedId() == FindFilterDialog.regExp:
            try:
                regExp = re.compile(text)
            except re.error:
                QtGui.QMessageBox.warning(self, 'TreeLine',
                                       _('Error - invalid regular expression'))
                return
            result = control.findNodesByRegExp([regExp], titlesOnly, forward)
        elif self.howButtons.checkedId() == FindFilterDialog.fullWords:
            regExpList = []
            for word in text.lower().split():
                regExpList.append(re.compile(r'(?i)\b{}\b'.
                                             format(re.escape(word))))
            result = control.findNodesByRegExp(regExpList, titlesOnly, forward)
        elif self.howButtons.checkedId() == FindFilterDialog.keyWords:
            wordList = text.lower().split()
            result = control.findNodesByWords(wordList, titlesOnly, forward)
        else:         # full phrase
            wordList = [text.lower().strip()]
            result = control.findNodesByWords(wordList, titlesOnly, forward)
        if not result:
            self.resultLabel.setText(_('Search string "{0}" not found').
                                     format(text))

    def findPrevious(self):
        """Find the previous match.
        """
        self.find(False)

    def findNext(self):
        """Find the next match.
        """
        self.find(True)

    def startFilter(self):
        """Start filtering nodes.
        """
        if self.howButtons.checkedId() == FindFilterDialog.regExp:
            try:
                re.compile(self.textEntry.text())
            except re.error:
                QtGui.QMessageBox.warning(self, 'TreeLine',
                                       _('Error - invalid regular expression'))
                return
        window = globalref.mainControl.activeControl.activeWindow
        filterView = window.treeFilterView
        filterView.filterWhat = self.whatButtons.checkedId()
        filterView.filterHow = self.howButtons.checkedId()
        filterView.filterStr = self.textEntry.text()
        filterView.updateContents()
        window.treeStack.setCurrentWidget(filterView)
        self.updateAvail()

    def endFilter(self):
        """Stop filtering nodes.
        """
        window = globalref.mainControl.activeControl.activeWindow
        window.treeStack.setCurrentWidget(window.treeView)
        self.updateAvail()
        globalref.mainControl.currentStatusBar().clearMessage()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


class FindReplaceDialog(QtGui.QDialog):
    """Dialog for finding and replacing text in the node data.
    """
    dialogShown = QtCore.pyqtSignal(bool)
    anyMatch, fullWord, regExp = range(3)
    def __init__(self, parent=None):
        """Initialize the find and replace dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle(_('Find and Replace'))

        self.matchedNode = None
        topLayout = QtGui.QGridLayout(self)
        self.setLayout(topLayout)

        textBox = QtGui.QGroupBox(_('&Search Text'))
        topLayout.addWidget(textBox, 0, 0)
        textLayout = QtGui.QVBoxLayout(textBox)
        self.textEntry = QtGui.QLineEdit()
        textLayout.addWidget(self.textEntry)
        self.textEntry.textEdited.connect(self.updateAvail)
        self.textEntry.textEdited.connect(self.clearMatch)

        replaceBox = QtGui.QGroupBox(_('Replacement &Text'))
        topLayout.addWidget(replaceBox, 0, 1)
        replaceLayout = QtGui.QVBoxLayout(replaceBox)
        self.replaceEntry = QtGui.QLineEdit()
        replaceLayout.addWidget(self.replaceEntry)

        howBox = QtGui.QGroupBox(_('How to Search'))
        topLayout.addWidget(howBox, 1, 0, 2, 1)
        howLayout = QtGui.QVBoxLayout(howBox)
        self.howButtons = QtGui.QButtonGroup(self)
        button = QtGui.QRadioButton(_('Any &match'))
        self.howButtons.addButton(button, FindReplaceDialog.anyMatch)
        howLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Full &words'))
        self.howButtons.addButton(button, FindReplaceDialog.fullWord)
        howLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Re&gular expression'))
        self.howButtons.addButton(button, FindReplaceDialog.regExp)
        howLayout.addWidget(button)
        self.howButtons.button(FindReplaceDialog.anyMatch).setChecked(True)
        self.howButtons.buttonClicked.connect(self.clearMatch)

        typeBox = QtGui.QGroupBox(_('&Node Type'))
        topLayout.addWidget(typeBox, 1, 1)
        typeLayout = QtGui.QVBoxLayout(typeBox)
        self.typeCombo = QtGui.QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged.connect(self.loadFieldNames)

        fieldBox = QtGui.QGroupBox(_('N&ode Fields'))
        topLayout.addWidget(fieldBox, 2, 1)
        fieldLayout = QtGui.QVBoxLayout(fieldBox)
        self.fieldCombo = QtGui.QComboBox()
        fieldLayout.addWidget(self.fieldCombo)
        self.fieldCombo.currentIndexChanged.connect(self.clearMatch)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout, 3, 0, 1, 2)
        self.previousButton = QtGui.QPushButton(_('Find &Previous'))
        ctrlLayout.addWidget(self.previousButton)
        self.previousButton.clicked.connect(self.findPrevious)
        self.nextButton = QtGui.QPushButton(_('&Find Next'))
        self.nextButton.setDefault(True)
        ctrlLayout.addWidget(self.nextButton)
        self.nextButton.clicked.connect(self.findNext)
        self.replaceButton = QtGui.QPushButton(_('&Replace'))
        ctrlLayout.addWidget(self.replaceButton)
        self.replaceButton.clicked.connect(self.replace)
        self.replaceAllButton = QtGui.QPushButton(_('Replace &All'))
        ctrlLayout.addWidget(self.replaceAllButton)
        self.replaceAllButton.clicked.connect(self.replaceAll)
        closeButton = QtGui.QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)

        self.resultLabel = QtGui.QLabel()
        topLayout.addWidget(self.resultLabel, 4, 0, 1, 2)
        self.loadTypeNames()
        self.updateAvail()

    def updateAvail(self):
        """Set find & replace buttons available if search text & matches exist.
        """
        hasEntry = len(self.textEntry.text().strip()) > 0
        self.previousButton.setEnabled(hasEntry)
        self.nextButton.setEnabled(hasEntry)
        match = bool(self.matchedNode and self.matchedNode is
                     globalref.mainControl.activeControl.
                     currentSelectionModel().currentNode())
        self.replaceButton.setEnabled(match)
        self.replaceAllButton.setEnabled(match)
        self.resultLabel.setText('')

    def clearMatch(self):
        """Remove reference to matched node if search criteria changes.
        """
        self.matchedNode = None
        self.updateAvail()

    def loadTypeNames(self):
        """Load format type names into combo box.
        """
        origTypeName = self.typeCombo.currentText()
        nodeFormats = globalref.mainControl.activeControl.model.formats
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        typeNames = nodeFormats.typeNames()
        self.typeCombo.addItems([_('[All Types]')] + typeNames)
        origPos = self.typeCombo.findText(origTypeName)
        if origPos >= 0:
            self.typeCombo.setCurrentIndex(origPos)
        self.typeCombo.blockSignals(False)
        self.loadFieldNames()

    def loadFieldNames(self):
        """Load field names into combo box.
        """
        origFieldName = self.fieldCombo.currentText()
        nodeFormats = globalref.mainControl.activeControl.model.formats
        typeName = self.typeCombo.currentText()
        fieldNames = []
        if typeName.startswith('['):
            for typeName in nodeFormats.typeNames():
                for fieldName in nodeFormats[typeName].fieldNames():
                    if fieldName not in fieldNames:
                        fieldNames.append(fieldName)
        else:
            fieldNames.extend(nodeFormats[typeName].fieldNames())
        self.fieldCombo.clear()
        self.fieldCombo.addItems([_('[All Fields]')] + fieldNames)
        origPos = self.fieldCombo.findText(origFieldName)
        if origPos >= 0:
            self.fieldCombo.setCurrentIndex(origPos)
        self.matchedNode = None
        self.updateAvail()

    def findParameters(self):
        """Create search parameters based on the dialog settings.

        Return a tuple of searchText, regExpObj, typeName, and fieldName.
        """
        text = self.textEntry.text()
        searchText = ''
        regExpObj = None
        if self.howButtons.checkedId() == FindReplaceDialog.anyMatch:
            searchText = text.lower().strip()
        elif self.howButtons.checkedId() == FindReplaceDialog.fullWord:
            regExpObj = re.compile(r'(?i)\b{}\b'.format(re.escape(text)))
        else:
            regExpObj = re.compile(text)
        typeName = self.typeCombo.currentText()
        if typeName.startswith('['):
            typeName = ''
        fieldName = self.fieldCombo.currentText()
        if fieldName.startswith('['):
            fieldName = ''
        return (searchText, regExpObj, typeName, fieldName)

    def find(self, forward=True):
        """Find another match in the indicated direction.

        Arguments:
            forward -- next if True, previous if False
        """
        self.matchedNode = None
        try:
            searchText, regExpObj, typeName, fieldName = self.findParameters()
        except re.error:
            QtGui.QMessageBox.warning(self, 'TreeLine',
                                      _('Error - invalid regular expression'))
            self.updateAvail()
            return
        control = globalref.mainControl.activeControl
        if control.findNodesForReplace(searchText, regExpObj, typeName,
                                       fieldName, forward):
            self.matchedNode = control.currentSelectionModel().currentNode()
            self.updateAvail()
        else:
            self.updateAvail()
            self.resultLabel.setText(_('Search text "{0}" not found').
                                     format(self.textEntry.text()))

    def findPrevious(self):
        """Find the previous match.
        """
        self.find(False)

    def findNext(self):
        """Find the next match.
        """
        self.find(True)

    def replace(self):
        """Replace the currently found text.
        """
        searchText, regExpObj, typeName, fieldName = self.findParameters()
        replaceText = self.replaceEntry.text()
        control = globalref.mainControl.activeControl
        if control.replaceInCurrentNode(searchText, regExpObj, typeName,
                                        fieldName, replaceText):
            self.find()
        else:
            QtGui.QMessageBox.warning(self, 'TreeLine',
                                      _('Error - replacement failed'))
            self.matchedNode = None
            self.updateAvail()

    def replaceAll(self):
        """Replace all text matches.
        """
        searchText, regExpObj, typeName, fieldName = self.findParameters()
        replaceText = self.replaceEntry.text()
        control = globalref.mainControl.activeControl
        qty = control.replaceAll(searchText, regExpObj, typeName, fieldName,
                                 replaceText)
        self.matchedNode = None
        self.updateAvail()
        self.resultLabel.setText(_('Replaced {0} matches').format(qty))

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


class SortDialog(QtGui.QDialog):
    """Dialog for defining sort operations.
    """
    dialogShown = QtCore.pyqtSignal(bool)
    fullTree, selectBranch, selectChildren, selectSiblings = range(4)
    fieldSort, titleSort = range(2)
    forward, reverse = range(2)
    def __init__(self, parent=None):
        """Initialize the sort dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle(_('Sort Nodes'))

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        horizLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(horizLayout)
        whatBox = QtGui.QGroupBox(_('What to Sort'))
        horizLayout.addWidget(whatBox)
        whatLayout = QtGui.QVBoxLayout(whatBox)
        self.whatButtons = QtGui.QButtonGroup(self)
        button = QtGui.QRadioButton(_('&Entire tree'))
        self.whatButtons.addButton(button, SortDialog.fullTree)
        whatLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Selected &branches'))
        self.whatButtons.addButton(button, SortDialog.selectBranch)
        whatLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Selection\'s childre&n'))
        self.whatButtons.addButton(button, SortDialog.selectChildren)
        whatLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Selection\'s &siblings'))
        self.whatButtons.addButton(button, SortDialog.selectSiblings)
        whatLayout.addWidget(button)
        self.whatButtons.button(SortDialog.fullTree).setChecked(True)

        vertLayout =  QtGui.QVBoxLayout()
        horizLayout.addLayout(vertLayout)
        methodBox = QtGui.QGroupBox(_('Sort Method'))
        vertLayout.addWidget(methodBox)
        methodLayout = QtGui.QVBoxLayout(methodBox)
        self.methodButtons = QtGui.QButtonGroup(self)
        button = QtGui.QRadioButton(_('&Predefined Key Fields'))
        self.methodButtons.addButton(button, SortDialog.fieldSort)
        methodLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Node &Titles'))
        self.methodButtons.addButton(button, SortDialog.titleSort)
        methodLayout.addWidget(button)
        self.methodButtons.button(SortDialog.fieldSort).setChecked(True)

        directionBox = QtGui.QGroupBox(_('Sort Direction'))
        vertLayout.addWidget(directionBox)
        directionLayout =  QtGui.QVBoxLayout(directionBox)
        self.directionButtons = QtGui.QButtonGroup(self)
        button = QtGui.QRadioButton(_('&Forward'))
        self.directionButtons.addButton(button, SortDialog.forward)
        directionLayout.addWidget(button)
        button = QtGui.QRadioButton(_('&Reverse'))
        self.directionButtons.addButton(button, SortDialog.reverse)
        directionLayout.addWidget(button)
        self.directionButtons.button(SortDialog.forward).setChecked(True)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.sortAndClose)
        applyButton = QtGui.QPushButton(_('&Apply'))
        ctrlLayout.addWidget(applyButton)
        applyButton.clicked.connect(self.sortNodes)
        closeButton = QtGui.QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)
        self.updateCommandsAvail()

    def updateCommandsAvail(self):
        """Set what to sort options available based on tree selections.
        """
        selNodes = globalref.mainControl.activeControl.currentSelectionModel()
        hasChild = False
        hasSibling = False
        for node in selNodes.selectedNodes():
            if node.childList:
                hasChild = True
            if node.parent and len(node.parent.childList) > 1:
                hasSibling = True
        self.whatButtons.button(SortDialog.selectBranch).setEnabled(hasChild)
        self.whatButtons.button(SortDialog.selectChildren).setEnabled(hasChild)
        self.whatButtons.button(SortDialog.
                                selectSiblings).setEnabled(hasSibling)
        if not self.whatButtons.checkedButton().isEnabled():
            self.whatButtons.button(SortDialog.fullTree).setChecked(True)

    def sortNodes(self):
        """Perform the sorting operation.
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        control = globalref.mainControl.activeControl
        selNodes = control.currentSelectionModel().selectedNodes()
        if self.whatButtons.checkedId() == SortDialog.fullTree:
            selNodes = [control.model.root]
        elif self.whatButtons.checkedId() == SortDialog.selectSiblings:
            selNodes = [node.parent for node in selNodes if node.parent]
        if self.whatButtons.checkedId() in (SortDialog.fullTree,
                                            SortDialog.selectBranch):
            rootNodes = selNodes[:]
            selNodes = []
            for root in rootNodes:
                for node in root.descendantGen():
                    if node.childList:
                        selNodes.append(node)
        undo.ChildListUndo(control.model.undoList, selNodes)
        forward = self.directionButtons.checkedId() == SortDialog.forward
        if self.methodButtons.checkedId() == SortDialog.fieldSort:
            for node in selNodes:
                node.sortChildrenByField(False, forward)
            # reset temporary sort field storage
            for nodeFormat in control.model.formats.values():
                nodeFormat.sortFields = []
        else:
            for node in selNodes:
                node.sortChildrenByTitle(False, forward)
        control.updateAll()
        QtGui.QApplication.restoreOverrideCursor()

    def sortAndClose(self):
        """Perform the sorting operation and close the dialog.
        """
        self.sortNodes()
        self.close()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


class NumberingDialog(QtGui.QDialog):
    """Dialog for updating node nuumbering fields.
    """
    dialogShown = QtCore.pyqtSignal(bool)
    fullTree, selectBranch, selectChildren = range(3)
    ignoreNoField, restartAfterNoField, reserveNoField = range(3)
    def __init__(self, parent=None):
        """Initialize the numbering dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle(_('Update Node Numbering'))

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        whatBox = QtGui.QGroupBox(_('What to Update'))
        topLayout.addWidget(whatBox)
        whatLayout = QtGui.QVBoxLayout(whatBox)
        self.whatButtons = QtGui.QButtonGroup(self)
        button = QtGui.QRadioButton(_('&Entire tree'))
        self.whatButtons.addButton(button, NumberingDialog.fullTree)
        whatLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Selected &branches'))
        self.whatButtons.addButton(button, NumberingDialog.selectBranch)
        whatLayout.addWidget(button)
        button = QtGui.QRadioButton(_('&Selection\'s children'))
        self.whatButtons.addButton(button, NumberingDialog.selectChildren)
        whatLayout.addWidget(button)
        self.whatButtons.button(NumberingDialog.fullTree).setChecked(True)

        rootBox = QtGui.QGroupBox(_('Root Node'))
        topLayout.addWidget(rootBox)
        rootLayout = QtGui.QVBoxLayout(rootBox)
        self.rootCheck = QtGui.QCheckBox(_('Include top-level nodes'))
        rootLayout.addWidget(self.rootCheck)
        self.rootCheck.setChecked(True)

        noFieldBox = QtGui.QGroupBox(_('Handling Nodes without Numbering '
                                       'Fields'))
        topLayout.addWidget(noFieldBox)
        noFieldLayout =  QtGui.QVBoxLayout(noFieldBox)
        self.noFieldButtons = QtGui.QButtonGroup(self)
        button = QtGui.QRadioButton(_('&Ignore and skip'))
        self.noFieldButtons.addButton(button, NumberingDialog.ignoreNoField)
        noFieldLayout.addWidget(button)
        button = QtGui.QRadioButton(_('&Restart numbers for next siblings'))
        self.noFieldButtons.addButton(button,
                                      NumberingDialog.restartAfterNoField)
        noFieldLayout.addWidget(button)
        button = QtGui.QRadioButton(_('Reserve &numbers'))
        self.noFieldButtons.addButton(button, NumberingDialog.reserveNoField)
        noFieldLayout.addWidget(button)
        self.noFieldButtons.button(NumberingDialog.
                                   ignoreNoField).setChecked(True)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.numberAndClose)
        applyButton = QtGui.QPushButton(_('&Apply'))
        ctrlLayout.addWidget(applyButton)
        applyButton.clicked.connect(self.updateNumbering)
        closeButton = QtGui.QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)
        self.updateCommandsAvail()

    def updateCommandsAvail(self):
        """Set branch numbering available based on tree selections.
        """
        selNodes = globalref.mainControl.activeControl.currentSelectionModel()
        hasChild = False
        for node in selNodes.selectedNodes():
            if node.childList:
                hasChild = True
        self.whatButtons.button(NumberingDialog.
                                selectChildren).setEnabled(hasChild)
        if not self.whatButtons.checkedButton().isEnabled():
            self.whatButtons.button(NumberingDialog.fullTree).setChecked(True)

    def checkForNumberingFields(self):
        """Check that the tree formats have numbering formats.

        Return a dict of numbering field names by node format name.
        If not found, warn user.
        """
        fieldDict = (globalref.mainControl.activeControl.model.formats.
                     numberingFieldDict())
        if not fieldDict:
            QtGui.QMessageBox.warning(self, _('TreeLine Numbering'),
                             _('No numbering fields were found in data types'))
        return fieldDict

    def updateNumbering(self):
        """Perform the numbering update operation.
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        fieldDict = self.checkForNumberingFields()
        if fieldDict:
            control = globalref.mainControl.activeControl
            selNodes = control.currentSelectionModel().selectedNodes()
            if self.whatButtons.checkedId() == NumberingDialog.fullTree:
                selNodes = [control.model.root]
            undo.BranchUndo(control.model.undoList, selNodes)
            reserveNums = (self.noFieldButtons.checkedId() ==
                           NumberingDialog.reserveNoField)
            restartSetting = (self.noFieldButtons.checkedId() ==
                              NumberingDialog.restartAfterNoField)
            includeRoot = self.rootCheck.isChecked()
            if self.whatButtons.checkedId() == NumberingDialog.selectChildren:
                levelLimit = 2
            else:
                levelLimit = sys.maxsize
            startNum = [1]
            for node in selNodes:
                node.updateNumbering(fieldDict, startNum, levelLimit,
                                     includeRoot, reserveNums, restartSetting)
                if not restartSetting:
                    startNum[0] += 1
            control.updateAll()
        QtGui.QApplication.restoreOverrideCursor()

    def numberAndClose(self):
        """Perform the numbering update operation and close the dialog.
        """
        self.updateNumbering()
        self.close()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


menuNames = collections.OrderedDict([(N_('File Menu'), _('File')),
                                     (N_('Edit Menu'), _('Edit')),
                                     (N_('Node Menu'), _('Node')),
                                     (N_('Data Menu'), _('Data')),
                                     (N_('Tools Menu'), _('Tools')),
                                     (N_('View Menu'), _('View')),
                                     (N_('Window Menu'), _('Window')),
                                     (N_('Help Menu'), _('Help'))])

class CustomShortcutsDialog(QtGui.QDialog):
    """Dialog for customizing keyboard commands.
    """
    def __init__(self, allActions, parent=None):
        """Create a shortcuts selection dialog.

        Arguments:
            allActions -- dict of all actions from a window
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Keyboard Shortcuts'))
        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        scrollArea = QtGui.QScrollArea()
        topLayout.addWidget(scrollArea)
        viewport = QtGui.QWidget()
        viewLayout = QtGui.QGridLayout(viewport)
        scrollArea.setWidget(viewport)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scrollArea.setWidgetResizable(True)

        self.editors = []
        for i, keyOption in enumerate(globalref.keyboardOptions.values()):
            try:
                category = menuNames[keyOption.category]
                action = allActions[keyOption.name]
            except KeyError:
                pass
            else:
                text = '{0} > {1}'.format(category, action.toolTip())
                label = QtGui.QLabel(text)
                viewLayout.addWidget(label, i, 0)
                editor = KeyLineEdit(keyOption, action, self)
                viewLayout.addWidget(editor, i, 1)
                self.editors.append(editor)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        restoreButton = QtGui.QPushButton(_('&Restore Defaults'))
        ctrlLayout.addWidget(restoreButton)
        restoreButton.clicked.connect(self.restoreDefaults)
        ctrlLayout.addStretch(0)
        self.okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.editors[0].setFocus()

    def restoreDefaults(self):
        """Restore all default keyboard shortcuts.
        """
        for editor in self.editors:
            editor.loadDefaultKey()

    def accept(self):
        """Save any changes to options and actions before closing.
        """
        modified = False
        for editor in self.editors:
            if editor.modified:
                editor.saveChange()
                modified = True
        if modified:
            globalref.keyboardOptions.writeFile()
        super().accept()


class KeyLineEdit(QtGui.QLineEdit):
    """Line editor for keyboad sequence entry.
    """
    usedKeySet = set()
    blankText = ' ' * 8
    def __init__(self, keyOption, action, parent=None):
        """Create a key editor.

        Arguments:
            keyOption -- the KeyOptionItem for this editor
            action -- the action to update on changes
            parent -- the parent dialog
        """
        super().__init__(parent)
        self.keyOption = keyOption
        self.keyAction = action
        self.key = None
        self.modified = False
        self.setReadOnly(True)
        self.loadKey()

    def loadKey(self):
        """Load the initial key shortcut from the option.
        """
        key = self.keyOption.value
        if key:
            self.setKey(key)
        else:
            self.setText(KeyLineEdit.blankText)

    def loadDefaultKey(self):
        """Change to the default key shortcut from the option.

        Arguments:
            useDefault -- if True, load the default key
        """
        key = self.keyOption.defaultValue
        if key == self.key:
            return
        if key:
            self.setKey(key)
            self.modified = True
        else:
            self.clearKey(False)

    def setKey(self, key):
        """Set this editor to the given key and add to the used key set.

        Arguments:
            key - the QKeySequence to add
        """
        keyText = key.toString(QtGui.QKeySequence.NativeText)
        self.setText(keyText)
        self.key = key
        KeyLineEdit.usedKeySet.add(keyText)

    def clearKey(self, staySelected=True):
        """Remove any existing key.
        """
        self.setText(KeyLineEdit.blankText)
        if staySelected:
            self.selectAll()
        if self.key:
            KeyLineEdit.usedKeySet.remove(self.key.toString(QtGui.QKeySequence.
                                                            NativeText))
            self.key = None
            self.modified = True

    def saveChange(self):
        """Save any change to the option and action.
        """
        if self.modified:
            self.keyOption.setValue(self.key)
            if self.key:
                self.keyAction.setShortcut(self.key)
            else:
                self.keyAction.setShortcut(QtGui.QKeySequence())

    def keyPressEvent(self, event):
        """Capture key strokes and update the editor if valid.

        Arguments:
            event -- the key press event
        """
        if event.key() in (QtCore.Qt.Key_Shift, QtCore.Qt.Key_Control,
                           QtCore.Qt.Key_Meta, QtCore.Qt.Key_Alt,
                           QtCore.Qt.Key_AltGr, QtCore.Qt.Key_CapsLock,
                           QtCore.Qt.Key_NumLock, QtCore.Qt.Key_ScrollLock,
                           QtCore.Qt.Key_Pause, QtCore.Qt.Key_Print,
                           QtCore.Qt.Key_Cancel):
            event.ignore()
        elif event.key() in (QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Escape):
            self.clearKey()
            event.accept()
        else:
            modifier = event.modifiers()
            if modifier & QtCore.Qt.KeypadModifier:
                modifier = modifier ^ QtCore.Qt.KeypadModifier
            key = QtGui.QKeySequence(event.key() + int(modifier))
            if key != self.key:
                keyText = key.toString(QtGui.QKeySequence.NativeText)
                if keyText not in KeyLineEdit.usedKeySet:
                    if self.key:
                        KeyLineEdit.usedKeySet.remove(self.key.
                                                   toString(QtGui.QKeySequence.
                                                            NativeText))
                    self.setKey(key)
                    self.selectAll()
                    self.modified = True
                else:
                    text = _('Key {0} is already used').format(keyText)
                    QtGui.QMessageBox.warning(self.parent(), 'TreeLine', text)
            event.accept()

    def contextMenuEvent(self, event):
        """Change to a context menu with a clear command.

        Arguments:
            event -- the menu event
        """
        menu = QtGui.QMenu(self)
        menu.addAction(_('Clear &Key'), self.clearKey)
        menu.exec_(event.globalPos())

    def mousePressEvent(self, event):
        """Capture mouse clicks to avoid selection loss.

        Arguments:
            event -- the mouse event
        """
        event.accept()

    def mouseReleaseEvent(self, event):
        """Capture mouse clicks to avoid selection loss.

        Arguments:
            event -- the mouse event
        """
        event.accept()

    def mouseMoveEvent(self, event):
        """Capture mouse clicks to avoid selection loss.

        Arguments:
            event -- the mouse event
        """
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """Capture mouse clicks to avoid selection loss.

        Arguments:
            event -- the mouse event
        """
        event.accept()

    def focusInEvent(self, event):
        """Select contents when focussed.

        Arguments:
            event -- the focus event
        """
        self.selectAll()
        super().focusInEvent(event)


class CustomToolbarDialog(QtGui.QDialog):
    """Dialog for customizing toolbar buttons.
    """
    separatorString = _('--Separator--')
    def __init__(self, allActions, updateFunction, parent=None):
        """Create a toolbar buttons customization dialog.

        Arguments:
            allActions -- dict of all actions from a window
            updateFunction -- a function ref for updating window toolbars
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Customize Toolbars'))
        self.allActions = allActions
        self.updateFunction = updateFunction
        self.availableCommands = []
        self.modified = False
        self.numToolbars = 0
        self.availableCommands = []
        self.toolbarLists = []

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        gridLayout = QtGui.QGridLayout()
        topLayout.addLayout(gridLayout)

        sizeBox = QtGui.QGroupBox(_('Toolbar &Size'))
        gridLayout.addWidget(sizeBox, 0, 0, 1, 2)
        sizeLayout = QtGui.QVBoxLayout(sizeBox)
        self.sizeCombo = QtGui.QComboBox()
        sizeLayout.addWidget(self.sizeCombo)
        self.sizeCombo.addItems([_('Small Icons'), _('Large Icons')])
        self.sizeCombo.currentIndexChanged.connect(self.setModified)

        numberBox = QtGui.QGroupBox(_('Toolbar Quantity'))
        gridLayout.addWidget(numberBox, 0, 2)
        numberLayout = QtGui.QHBoxLayout(numberBox)
        self.quantitySpin = QtGui.QSpinBox()
        numberLayout.addWidget(self.quantitySpin)
        self.quantitySpin.setRange(0, 20)
        numberlabel = QtGui.QLabel(_('&Toolbars'))
        numberLayout.addWidget(numberlabel)
        numberlabel.setBuddy(self.quantitySpin)
        self.quantitySpin.valueChanged.connect(self.changeQuantity)

        availableBox = QtGui.QGroupBox(_('A&vailable Commands'))
        gridLayout.addWidget(availableBox, 1, 0)
        availableLayout = QtGui.QVBoxLayout(availableBox)
        menuCombo = QtGui.QComboBox()
        availableLayout.addWidget(menuCombo)
        menuCombo.addItems([_(name) for name in menuNames.keys()])
        menuCombo.currentIndexChanged.connect(self.updateAvailableCommands)

        self.availableListWidget = QtGui.QListWidget()
        availableLayout.addWidget(self.availableListWidget)

        buttonLayout = QtGui.QVBoxLayout()
        gridLayout.addLayout(buttonLayout, 1, 1)
        self.addButton = QtGui.QPushButton('>>')
        buttonLayout.addWidget(self.addButton)
        self.addButton.setMaximumWidth(self.addButton.sizeHint().height())
        self.addButton.clicked.connect(self.addTool)

        self.removeButton = QtGui.QPushButton('<<')
        buttonLayout.addWidget(self.removeButton)
        self.removeButton.setMaximumWidth(self.removeButton.sizeHint().
                                          height())
        self.removeButton.clicked.connect(self.removeTool)

        toolbarBox = QtGui.QGroupBox(_('Tool&bar Commands'))
        gridLayout.addWidget(toolbarBox, 1, 2)
        toolbarLayout = QtGui.QVBoxLayout(toolbarBox)
        self.toolbarCombo = QtGui.QComboBox()
        toolbarLayout.addWidget(self.toolbarCombo)
        self.toolbarCombo.currentIndexChanged.connect(self.
                                                      updateToolbarCommands)

        self.toolbarListWidget = QtGui.QListWidget()
        toolbarLayout.addWidget(self.toolbarListWidget)
        self.toolbarListWidget.currentRowChanged.connect(self.
                                                         setButtonsAvailable)

        moveLayout = QtGui.QHBoxLayout()
        toolbarLayout.addLayout(moveLayout)
        self.moveUpButton = QtGui.QPushButton(_('Move &Up'))
        moveLayout.addWidget(self.moveUpButton)
        self.moveUpButton.clicked.connect(self.moveUp)
        self.moveDownButton = QtGui.QPushButton(_('Move &Down'))
        moveLayout.addWidget(self.moveDownButton)
        self.moveDownButton.clicked.connect(self.moveDown)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        restoreButton = QtGui.QPushButton(_('&Restore Defaults'))
        ctrlLayout.addWidget(restoreButton)
        restoreButton.clicked.connect(self.restoreDefaults)
        ctrlLayout.addStretch()
        self.okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        self.applyButton = QtGui.QPushButton(_('&Apply'))
        ctrlLayout.addWidget(self.applyButton)
        self.applyButton.clicked.connect(self.applyChanges)
        self.applyButton.setEnabled(False)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

        self.updateAvailableCommands(0)
        self.loadToolbars()

    def setModified(self):
        """Set modified flag and make apply button available.
        """
        self.modified = True
        self.applyButton.setEnabled(True)

    def setButtonsAvailable(self):
        """Enable or disable buttons based on toolbar list state.
        """
        toolbarNum = numCommands = commandNum = 0
        if self.numToolbars:
            toolbarNum = self.toolbarCombo.currentIndex()
            numCommands = len(self.toolbarLists[toolbarNum])
            if self.toolbarLists[toolbarNum]:
                commandNum = self.toolbarListWidget.currentRow()
        self.addButton.setEnabled(self.numToolbars > 0)
        self.removeButton.setEnabled(self.numToolbars and numCommands)
        self.moveUpButton.setEnabled(self.numToolbars and numCommands > 1 and
                                     commandNum > 0)
        self.moveDownButton.setEnabled(self.numToolbars and numCommands > 1 and
                                       commandNum < numCommands - 1)

    def loadToolbars(self, defaultOnly=False):
        """Load all toolbar data from options.

        Arguments:
            defaultOnly -- if True, load default settings
        """
        size = globalref.toolbarOptions.getValue('ToolbarSize', defaultOnly)
        self.sizeCombo.blockSignals(True)
        if size < 24:
            self.sizeCombo.setCurrentIndex(0)
        else:
            self.sizeCombo.setCurrentIndex(1)
        self.sizeCombo.blockSignals(False)
        self.numToolbars = globalref.toolbarOptions.getValue('ToolbarQuantity',
                                                             defaultOnly)
        self.quantitySpin.blockSignals(True)
        self.quantitySpin.setValue(self.numToolbars)
        self.quantitySpin.blockSignals(False)
        self.toolbarLists = [globalref.toolbarOptions.getValue('Toolbar{0}'.
                                                               format(num),
                                                               defaultOnly).
                             split(',') for num in range(self.numToolbars)]
        self.updateToolbarCombo()

    def updateToolbarCombo(self):
        """Fill combo with toolbar numbers for current quantity.
        """
        self.toolbarCombo.clear()
        if self.numToolbars:
            self.toolbarCombo.addItems(['Toolbar {0}'.format(num + 1) for
                                        num in range(self.numToolbars)])
        else:
            self.toolbarListWidget.clear()
            self.setButtonsAvailable()

    def updateAvailableCommands(self, menuNum):
        """Fill in available command list for given menu.

        Arguments:
            menuNum -- the index of the current menu selected
        """
        menuName = list(menuNames.keys())[menuNum]
        self.availableCommands = []
        self.availableListWidget.clear()
        for option in globalref.keyboardOptions.values():
            if option.category == menuName:
                action = self.allActions[option.name]
                icon = action.icon()
                if not icon.isNull():
                    self.availableCommands.append(option.name)
                    QtGui.QListWidgetItem(icon, action.toolTip(),
                                          self.availableListWidget)
        QtGui.QListWidgetItem(CustomToolbarDialog.separatorString,
                              self.availableListWidget)
        self.availableListWidget.setCurrentRow(0)

    def updateToolbarCommands(self, toolbarNum):
        """Fill in toolbar commands for given toolbar.

        Arguments:
            toolbarNum -- the number of the toolbar to update
        """
        self.toolbarListWidget.clear()
        if self.numToolbars == 0:
            return
        for command in self.toolbarLists[toolbarNum]:
            if command:
                action = self.allActions[command]
                QtGui.QListWidgetItem(action.icon(), action.toolTip(),
                                      self.toolbarListWidget)
            else:  # separator
                QtGui.QListWidgetItem(CustomToolbarDialog.separatorString,
                                      self.toolbarListWidget)
        if self.toolbarLists[toolbarNum]:
            self.toolbarListWidget.setCurrentRow(0)
        self.setButtonsAvailable()

    def changeQuantity(self, qty):
        """Change the toolbar quantity based on a spin box signal.

        Arguments:
            qty -- the new toolbar quantity
        """
        self.numToolbars = qty
        while qty > len(self.toolbarLists):
            self.toolbarLists.append([])
        self.updateToolbarCombo()
        self.setModified()

    def addTool(self):
        """Add the selected command to the current toolbar.
        """
        toolbarNum = self.toolbarCombo.currentIndex()
        try:
            command = self.availableCommands[self.availableListWidget.
                                             currentRow()]
            action = self.allActions[command]
            item = QtGui.QListWidgetItem(action.icon(), action.toolTip())
        except IndexError:
            command = ''
            item = QtGui.QListWidgetItem(CustomToolbarDialog.separatorString)
        if self.toolbarLists[toolbarNum]:
            pos = self.toolbarListWidget.currentRow() + 1
        else:
            pos = 0
        self.toolbarLists[toolbarNum].insert(pos, command)
        self.toolbarListWidget.insertItem(pos, item)
        self.toolbarListWidget.setCurrentRow(pos)
        self.toolbarListWidget.scrollToItem(item)
        self.setModified()

    def removeTool(self):
        """Remove the selected command from the current toolbar.
        """
        toolbarNum = self.toolbarCombo.currentIndex()
        pos = self.toolbarListWidget.currentRow()
        del self.toolbarLists[toolbarNum][pos]
        self.toolbarListWidget.takeItem(pos)
        if self.toolbarLists[toolbarNum]:
            if pos == len(self.toolbarLists[toolbarNum]):
                pos -= 1
            self.toolbarListWidget.setCurrentRow(pos)
        self.setModified()

    def moveUp(self):
        """Raise the selected command.
        """
        toolbarNum = self.toolbarCombo.currentIndex()
        pos = self.toolbarListWidget.currentRow()
        command = self.toolbarLists[toolbarNum].pop(pos)
        self.toolbarLists[toolbarNum].insert(pos - 1, command)
        item = self.toolbarListWidget.takeItem(pos)
        self.toolbarListWidget.insertItem(pos - 1, item)
        self.toolbarListWidget.setCurrentRow(pos - 1)
        self.toolbarListWidget.scrollToItem(item)
        self.setModified()

    def moveDown(self):
        """Lower the selected command.
        """
        toolbarNum = self.toolbarCombo.currentIndex()
        pos = self.toolbarListWidget.currentRow()
        command = self.toolbarLists[toolbarNum].pop(pos)
        self.toolbarLists[toolbarNum].insert(pos + 1, command)
        item = self.toolbarListWidget.takeItem(pos)
        self.toolbarListWidget.insertItem(pos + 1, item)
        self.toolbarListWidget.setCurrentRow(pos + 1)
        self.toolbarListWidget.scrollToItem(item)
        self.setModified()

    def restoreDefaults(self):
        """Restore all default toolbar settings.
        """
        self.loadToolbars(True)
        self.setModified()

    def applyChanges(self):
        """Apply any changes from the dialog.
        """
        size = 16 if self.sizeCombo.currentIndex() == 0 else 32
        globalref.toolbarOptions.changeValue('ToolbarSize', size)
        globalref.toolbarOptions.changeValue('ToolbarQuantity',
                                             self.numToolbars)
        del self.toolbarLists[self.numToolbars:]
        for num, toolbarList in enumerate(self.toolbarLists):
            name = 'Toolbar{0}'.format(num)
            if name not in globalref.toolbarOptions:
                options.StringOptionItem(globalref.toolbarOptions, name, '',
                                         'Toolbar Commands')
            globalref.toolbarOptions.changeValue(name, ','.join(toolbarList))
        globalref.toolbarOptions.writeFile()
        self.modified = False
        self.applyButton.setEnabled(False)
        self.updateFunction()

    def accept(self):
        """Apply changes and close the dialog.
        """
        if self.modified:
            self.applyChanges()
        super().accept()


class CustomFontData:
    """Class to store custom font settings.

    Acts as a stand-in for PrintData class in the font page of the dialog.
    """
    def __init__(self, fontOption):
        """Initialize the font data.

        Arguments:
            fontOption -- the name of the font setting to retrieve
        """
        self.fontOption = fontOption
        self.defaultFont = QtGui.QTextDocument().defaultFont()
        self.useDefaultFont = True
        self.mainFont = QtGui.QTextDocument().defaultFont()
        fontName = globalref.miscOptions.getValue(fontOption)
        if fontName:
            self.mainFont.fromString(fontName)
            self.useDefaultFont = False

    def recordChanges(self):
        """Record the updated font info to the option settings.
        """
        if self.useDefaultFont:
            globalref.miscOptions.changeValue(self.fontOption, '')
        else:
            globalref.miscOptions.changeValue(self.fontOption,
                                              self.mainFont.toString())


class CustomFontDialog(QtGui.QDialog):
    """Dialog for selecting custom fonts.

    Uses the print setup dialog's font page for the details.
    """
    updateRequired = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        """Create a font customization dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Customize Toolbars'))

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        tabs = QtGui.QTabWidget()
        topLayout.addWidget(tabs)

        self.pages = []
        treeFontPage = printdialogs.FontPage(CustomFontData('TreeFont'), True)
        self.pages.append(treeFontPage)
        tabs.addTab(treeFontPage, _('Tree View Font'))
        outputFontPage = printdialogs.FontPage(CustomFontData('OutputFont'),
                                               True)
        self.pages.append(outputFontPage)
        tabs.addTab(outputFontPage, _('Output View Font'))
        editorFontPage = printdialogs.FontPage(CustomFontData('EditorFont'),
                                               True)
        self.pages.append(editorFontPage)
        tabs.addTab(editorFontPage, _('Editor View Font'))

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        self.okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        self.applyButton = QtGui.QPushButton(_('&Apply'))
        ctrlLayout.addWidget(self.applyButton)
        self.applyButton.clicked.connect(self.applyChanges)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def applyChanges(self):
        """Apply any changes from the dialog.
        """
        modified = False
        for page in self.pages:
            if page.saveChanges():
                page.printData.recordChanges()
                modified = True
        if modified:
            globalref.miscOptions.writeFile()
            self.updateRequired.emit()

    def accept(self):
        """Apply changes and close the dialog.
        """
        self.applyChanges()
        super().accept()


class PluginListDialog(QtGui.QDialog):
    """Dialog for listing loaded plugin modules.
    """
    def __init__(self, pluginList, parent=None):
        """Create a plugin list dialog.

        Arguments:
            pluginList -- a list of plugin descriptions to show
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('TreeLine Plugins'))

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        label = QtGui.QLabel(_('Plugin Modules Loaded'))
        topLayout.addWidget(label)
        listBox = QtGui.QListWidget()
        listBox.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        listBox.addItems(pluginList)
        topLayout.addWidget(listBox)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        self.okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
