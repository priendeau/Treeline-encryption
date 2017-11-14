#!/usr/bin/env python3

#******************************************************************************
# configdialog.py, provides classes for the type configuration dialog
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
import copy
import operator
from PyQt4 import QtCore, QtGui
import nodeformat
import fieldformat
import icondict
import conditional
import matheval
import globalref


class ConfigDialog(QtGui.QDialog):
    """Class override for the main config dialog
    
    Contains the tabbed pages that handle the actual settings.
    """
    dialogShown = QtCore.pyqtSignal(bool)
    modelRef = None
    formatsRef = None
    currentTypeName = ''
    currentFieldName = ''
    def __init__(self, parent=None):
        """Initialize the config dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(_('Configure Data Types'))
        self.prevPage = None
        self.selectionModel = None

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)

        self.tabs = QtGui.QTabWidget()
        topLayout.addWidget(self.tabs)
        typeListPage = TypeListPage(self)
        self.tabs.addTab(typeListPage, _('T&ype List'))
        typeConfigPage = TypeConfigPage(self)
        self.tabs.addTab(typeConfigPage, _('Typ&e Config'))
        fieldListPage = FieldListPage(self)
        self.tabs.addTab(fieldListPage, _('Field &List'))
        fieldConfigPage = FieldConfigPage(self)
        self.tabs.addTab(fieldConfigPage, _('&Field Config'))
        outputPage = OutputPage(self)
        self.tabs.addTab(outputPage, _('O&utput'))
        self.tabs.currentChanged.connect(self.updatePage)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        self.advancedButton = QtGui.QPushButton(_('&Show Advanced'))
        ctrlLayout.addWidget(self.advancedButton)
        self.advancedButton.setCheckable(True)
        self.advancedButton.clicked.connect(self.toggleAdavanced)
        ctrlLayout.addStretch()
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.applyAndClose)
        self.applyButton = QtGui.QPushButton(_('&Apply'))
        ctrlLayout.addWidget(self.applyButton)
        self.applyButton.clicked.connect(self.applyChanges)
        self.resetButton = QtGui.QPushButton(_('&Reset'))
        ctrlLayout.addWidget(self.resetButton)
        self.resetButton.clicked.connect(self.reset)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.resetAndClose)

    def setRefs(self, modelRef, selectionModel, resetSelect=False):
        """Set refs to model and formats, then update dialog data.

        Sets current type to current node's type if resetSelect or if invalid.
        Sets current field to first field if resetSelect or if invalid.
        Arguments:
            modelRef - a reference to the model and formats
            selectionModel - holds node selection for initial selections
            resetSelect -- if True, forces reset of current selections
        """
        ConfigDialog.modelRef = modelRef
        ConfigDialog.formatsRef = modelRef.getConfigDialogFormats()
        self.selectionModel = selectionModel
        self.updateSelections(resetSelect)
        self.setModified(modified=False)
        self.prevPage = None
        self.updatePage()

    def updateSelections(self, forceUpdate=False):
        """Sets current type & current field if invalid or forceUpdate is True.

        Arguments:
            forceUpdate -- if True, forces reset of current selections
        """
        if forceUpdate or (ConfigDialog.currentTypeName not in
                           ConfigDialog.formatsRef):
            ConfigDialog.currentTypeName = (self.selectionModel.currentNode().
                                            formatName)
        if forceUpdate or (ConfigDialog.currentFieldName not in
                           ConfigDialog.formatsRef[ConfigDialog.
                           currentTypeName].fieldNames()):
            ConfigDialog.currentFieldName = (ConfigDialog.
                                             formatsRef[ConfigDialog.
                                                        currentTypeName].
                                             fieldNames()[0])

    def updatePage(self):
        """Update new page and advanced button state when changing tabs.
        """
        if self.prevPage:
            self.prevPage.readChanges()
        page = self.tabs.currentWidget()
        self.advancedButton.setEnabled(len(page.advancedWidgets))
        page.toggleAdvanced(self.advancedButton.isChecked())
        page.updateContent()
        self.prevPage = page

    def setModified(self, dummyArg=None, modified=True):
        """Set the format to a modified status and update the controls.

        Arguments:
            dummyArg -- placeholder for unused signal arguments
            modified -- set to modified if True
        """
        ConfigDialog.formatsRef.configModified = modified
        self.applyButton.setEnabled(modified)
        self.resetButton.setEnabled(modified)

    def toggleAdavanced(self, show):
        """Toggle the display of advanced widgets in the sub-dialogs.

        Arguments:
            show -- show if true, hide if false
        """
        if show:
            self.advancedButton.setText(_('&Hide Advanced'))
        else:
            self.advancedButton.setText(_('&Show Advanced'))
        page = self.tabs.currentWidget()
        page.toggleAdvanced(show)

    def reset(self):
        """Set the formats back to original settings.
        """
        ConfigDialog.formatsRef = (ConfigDialog.modelRef.
                                   getConfigDialogFormats(True))
        self.updateSelections()
        self.setModified(modified=False)
        self.prevPage = None
        self.updatePage()

    def applyChanges(self):
        """Apply copied format changes to the main format.

        Return False if there is a circular math reference.
        """
        self.tabs.currentWidget().readChanges()
        if ConfigDialog.formatsRef.configModified:
            try:
                ConfigDialog.modelRef.applyConfigDialogFormats()
            except matheval.CircularMathError:
                QtGui.QMessageBox.warning(self, 'TreeLine',
                       _('Error - circular reference in math field equations'))
                return False
            ConfigDialog.formatsRef = (ConfigDialog.modelRef.
                                       getConfigDialogFormats())
            self.setModified(modified=False)
            pluginInterface = globalref.mainControl.pluginInterface
            if pluginInterface:
                pluginInterface.execCallback(pluginInterface.
                                             formatChangeCallbacks)
        return True

    def applyAndClose(self):
        """Apply copied format changes to the main format and close the dialog.
        """
        if self.applyChanges():
            self.close()

    def resetAndClose(self):
        """Set the formats back to original settings and close the dialog.
        """
        self.reset()
        self.close()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


class ConfigPage(QtGui.QWidget):
    """Abstract base class for config dialog tabbed pages.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.mainDialogRef = parent
        self.advancedWidgets = []

    def updateContent(self):
        """Update page contents from current format settings.

        Base class does nothing.
        """
        pass

    def readChanges(self):
        """Make changes to the format for each widget.

        Base class does nothing.
        """
        pass

    def changeCurrentType(self, typeName):
        """Change the current format type based on a signal from lists.

        Arguments:
            typeName -- the name of the new current type
        """
        self.readChanges()
        ConfigDialog.currentTypeName = typeName
        ConfigDialog.currentFieldName = (ConfigDialog.formatsRef[typeName].
                                         fieldNames()[0])
        self.updateContent()

    def changeCurrentField(self, fieldName):
        """Change the current format field based on a signal from lists.

        Arguments:
            fieldName -- the name of the new current field
        """
        self.readChanges()
        ConfigDialog.currentFieldName = fieldName
        self.updateContent()

    def toggleAdvanced(self, show=True):
        """Toggle the display state of advanced widgets.
        
        Arguments:
            show -- show if true, hide if false
        """
        for widget in self.advancedWidgets:
            widget.setVisible(show)


class TypeListPage(ConfigPage):
    """Config dialog page with an editable list of node types.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        topLayout = QtGui.QVBoxLayout(self)
        box = QtGui.QGroupBox(_('Add or Remove Data Types'))
        topLayout.addWidget(box)
        horizLayout = QtGui.QHBoxLayout(box)
        self.listBox = QtGui.QListWidget()
        horizLayout.addWidget(self.listBox)
        self.listBox.currentTextChanged.connect(self.changeCurrentType)

        buttonLayout = QtGui.QVBoxLayout()
        horizLayout.addLayout(buttonLayout)
        newButton = QtGui.QPushButton(_('&New Type...'))
        buttonLayout.addWidget(newButton)
        newButton.clicked.connect(self.newType)
        copyButton = QtGui.QPushButton(_('Co&py Type...'))
        buttonLayout.addWidget(copyButton)
        copyButton.clicked.connect(self.copyType)
        renameButton = QtGui.QPushButton(_('Rena&me Type...'))
        buttonLayout.addWidget(renameButton)
        renameButton.clicked.connect(self.renameType)
        deleteButton = QtGui.QPushButton(_('&Delete Type'))
        buttonLayout.addWidget(deleteButton)
        deleteButton.clicked.connect(self.deleteType)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        names = ConfigDialog.formatsRef.typeNames()
        self.listBox.blockSignals(True)
        self.listBox.clear()
        self.listBox.addItems(names)
        self.listBox.setCurrentRow(names.index(ConfigDialog.currentTypeName))
        self.listBox.blockSignals(False)

    def newType(self):
        """Create a new type based on button signal.
        """
        dlg = NameEntryDialog(_('Add Type'), _('Enter new type name:'), '', '',
                              ConfigDialog.formatsRef.typeNames(), self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            newFormat = nodeformat.NodeFormat(dlg.text,
                                              ConfigDialog.formatsRef, {},
                                              True)
            ConfigDialog.formatsRef[dlg.text] = newFormat
            ConfigDialog.currentTypeName = dlg.text
            ConfigDialog.currentFieldName = newFormat.fieldNames()[0]
            self.updateContent()
            self.mainDialogRef.setModified()

    def copyType(self):
        """Copy selected type based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dlg = NameEntryDialog(_('Copy Type'), _('Enter new type name:'),
                              ConfigDialog.currentTypeName,
                              _('&Derive from original'),
                              ConfigDialog.formatsRef.typeNames(), self)
        if currentFormat.genericType:
            dlg.extraCheckBox.setEnabled(False)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            newFormat = copy.deepcopy(currentFormat)
            newFormat.name = dlg.text
            ConfigDialog.formatsRef[dlg.text] = newFormat
            ConfigDialog.currentTypeName = dlg.text
            if dlg.extraChecked:
                newFormat.genericType = currentFormat.name
            ConfigDialog.formatsRef.updateDerivedRefs()
            self.updateContent()
            self.mainDialogRef.setModified()

    def renameType(self):
        """Rename the selected type based on button signal.
        """
        oldName = ConfigDialog.currentTypeName
        dlg = NameEntryDialog(_('Rename Type'),
                              _('Rename from {} to:').format(oldName), oldName,
                              '', ConfigDialog.formatsRef.typeNames(), self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            currentType = ConfigDialog.formatsRef[oldName]
            currentType.name = dlg.text
            del ConfigDialog.formatsRef[oldName]
            ConfigDialog.formatsRef[dlg.text] = currentType
            # reverse the rename dict - find original name (multiple renames)
            reverseDict = {}
            for old, new in ConfigDialog.formatsRef.typeRenameDict.items():
                reverseDict[new] = old
            origName = reverseDict.get(oldName, oldName)
            ConfigDialog.formatsRef.typeRenameDict[origName] = dlg.text
            if oldName in ConfigDialog.formatsRef.fieldRenameDict:
                ConfigDialog.formatsRef.fieldRenameDict[dlg.text] = \
                        ConfigDialog.formatsRef.fieldRenameDict[oldName]
                del ConfigDialog.formatsRef.fieldRenameDict[oldName]
            for nodeType in ConfigDialog.formatsRef.values():
                if nodeType.childType == oldName:
                    nodeType.childType = dlg.text
                if nodeType.genericType == oldName:
                    nodeType.genericType = dlg.text
            ConfigDialog.currentTypeName = dlg.text
            self.updateContent()
            self.mainDialogRef.setModified()

    def deleteType(self):
        """Delete the selected type based on button signal.
        """
        if ConfigDialog.modelRef.root.usesType(ConfigDialog.currentTypeName):
            QtGui.QMessageBox.warning(self, 'TreeLine',
                              _('Cannot delete data type being used by nodes'))
            return
        del ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        for nodeType in ConfigDialog.formatsRef.values():
            if nodeType.childType == ConfigDialog.currentTypeName:
                nodeType.childType = ''
            if nodeType.genericType == ConfigDialog.currentTypeName:
                nodeType.genericType = ''
                nodeType.conditional = conditional.Conditional()
        ConfigDialog.formatsRef.updateDerivedRefs()
        ConfigDialog.currentTypeName = ConfigDialog.formatsRef.typeNames()[0]
        ConfigDialog.currentFieldName = ConfigDialog.formatsRef[ConfigDialog.
                                               currentTypeName].fieldNames()[0]
        self.updateContent()
        self.mainDialogRef.setModified()


_noTypeSetName = _('[None]', 'no type set')

class TypeConfigPage(ConfigPage):
    """Config dialog page to change parmaters of a node type.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        topLayout = QtGui.QGridLayout(self)
        typeBox = QtGui.QGroupBox(_('&Data Type'))
        topLayout.addWidget(typeBox, 0, 0)
        typeLayout = QtGui.QVBoxLayout(typeBox)
        self.typeCombo = QtGui.QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged[str].connect(self.changeCurrentType)

        childBox = QtGui.QGroupBox(_('Default Child &Type'))
        topLayout.addWidget(childBox, 0, 1)
        childLayout = QtGui.QVBoxLayout(childBox)
        self.childCombo = QtGui.QComboBox()
        childLayout.addWidget(self.childCombo)
        self.childCombo.currentIndexChanged.connect(self.mainDialogRef.
                                                    setModified)

        iconBox = QtGui.QGroupBox(_('Icon'))
        topLayout.addWidget(iconBox, 1, 1)
        iconLayout = QtGui.QHBoxLayout(iconBox)
        self.iconImage = QtGui.QLabel()
        iconLayout.addWidget(self.iconImage)
        self.iconImage.setAlignment(QtCore.Qt.AlignCenter)
        iconButton = QtGui.QPushButton(_('Change &Icon'))
        iconLayout.addWidget(iconButton)
        iconButton.clicked.connect(self.changeIcon)

        optionsBox = QtGui.QGroupBox(_('Output Options'))
        topLayout.addWidget(optionsBox, 1, 0, 2, 1)
        optionsLayout =  QtGui.QVBoxLayout(optionsBox)
        self.blanksButton = QtGui.QCheckBox(_('Add &blank lines between '
                                              'nodes'))
        optionsLayout.addWidget(self.blanksButton)
        self.blanksButton.toggled.connect(self.mainDialogRef.setModified)
        self.htmlButton = QtGui.QCheckBox(_('Allow &HTML rich text in format'))
        optionsLayout.addWidget(self.htmlButton)
        self.htmlButton.toggled.connect(self.mainDialogRef.setModified)
        self.bulletButton = QtGui.QCheckBox(_('Add text bullet&s'))
        optionsLayout.addWidget(self.bulletButton)
        self.bulletButton.toggled.connect(self.changeUseBullets)
        self.tableButton = QtGui.QCheckBox(_('Use a table for field &data'))
        optionsLayout.addWidget(self.tableButton)
        self.tableButton.toggled.connect(self.changeUseTable)

        # advanced widgets
        outputSepBox = QtGui.QGroupBox(_('Combination && Child List Output '
                                         '&Separator'))
        topLayout.addWidget(outputSepBox, 2, 1)
        self.advancedWidgets.append(outputSepBox)
        outputSepLayout = QtGui.QVBoxLayout(outputSepBox)
        self.outputSepEdit = QtGui.QLineEdit()
        outputSepLayout.addWidget(self.outputSepEdit)
        sizePolicy = self.outputSepEdit.sizePolicy()
        sizePolicy.setHorizontalPolicy(QtGui.QSizePolicy.Preferred)
        self.outputSepEdit.setSizePolicy(sizePolicy)
        self.outputSepEdit.textEdited.connect(self.mainDialogRef.setModified)

        idFieldBox = QtGui.QGroupBox(_('Uni&que ID Reference Field'))
        topLayout.addWidget(idFieldBox, 3, 0)
        self.advancedWidgets.append(idFieldBox)
        idFieldLayout = QtGui.QVBoxLayout(idFieldBox)
        self.idFieldCombo = QtGui.QComboBox()
        idFieldLayout.addWidget(self.idFieldCombo)
        self.idFieldCombo.currentIndexChanged.connect(self.mainDialogRef.
                                                      setModified)

        genericBox = QtGui.QGroupBox(_('Derived from &Generic Type'))
        topLayout.addWidget(genericBox, 3, 1)
        self.advancedWidgets.append(genericBox)
        genericLayout = QtGui.QVBoxLayout(genericBox)
        self.genericCombo = QtGui.QComboBox()
        genericLayout.addWidget(self.genericCombo)
        self.genericCombo.currentIndexChanged.connect(self.setGenericIdRef)
        self.genericCombo.currentIndexChanged.connect(self.mainDialogRef.
                                                      setModified)

        conditionBox = QtGui.QGroupBox(_('Automatic Types'))
        topLayout.addWidget(conditionBox, 4, 1)
        self.advancedWidgets.append(conditionBox)
        conditionLayout = QtGui.QVBoxLayout(conditionBox)
        self.conditionButton = QtGui.QPushButton()
        conditionLayout.addWidget(self.conditionButton)
        self.conditionButton.clicked.connect(self.showConditionDialog)

        topLayout.setRowStretch(5, 1)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        typeNames = ConfigDialog.formatsRef.typeNames()
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItems(typeNames)
        self.typeCombo.setCurrentIndex(typeNames.index(ConfigDialog.
                                                       currentTypeName))
        self.typeCombo.blockSignals(False)

        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        self.childCombo.blockSignals(True)
        self.childCombo.clear()
        self.childCombo.addItem(_noTypeSetName)
        self.childCombo.addItems(typeNames)
        try:
            childItem = typeNames.index(currentFormat.childType) + 1
        except ValueError:
            childItem = 0
        self.childCombo.setCurrentIndex(childItem)
        self.childCombo.blockSignals(False)

        icon = globalref.treeIcons.getIcon(currentFormat.iconName, True)
        if icon:
            self.iconImage.setPixmap(icon.pixmap(16, 16))
        else:
            self.iconImage.setText(_('None'))

        self.blanksButton.blockSignals(True)
        self.blanksButton.setChecked(currentFormat.spaceBetween)
        self.blanksButton.blockSignals(False)

        self.htmlButton.blockSignals(True)
        self.htmlButton.setChecked(currentFormat.formatHtml)
        self.htmlButton.blockSignals(False)

        self.bulletButton.blockSignals(True)
        self.bulletButton.setChecked(currentFormat.useBullets)
        self.bulletButton.blockSignals(False)

        self.tableButton.blockSignals(True)
        self.tableButton.setChecked(currentFormat.useTables)
        self.tableButton.blockSignals(False)

        self.htmlButton.setEnabled(not currentFormat.useBullets and
                                   not currentFormat.useTables)

        self.outputSepEdit.setText(currentFormat.outputSeparator)

        self.idFieldCombo.blockSignals(True)
        self.idFieldCombo.clear()
        self.idFieldCombo.addItems(currentFormat.fieldNames())
        self.idFieldCombo.setCurrentIndex(currentFormat.fieldNames().
                                          index(currentFormat.idField.name))
        self.idFieldCombo.blockSignals(False)
        self.idFieldCombo.setEnabled(not currentFormat.genericType)

        self.genericCombo.blockSignals(True)
        self.genericCombo.clear()
        self.genericCombo.addItem(_noTypeSetName)
        typeNames = [name for name in typeNames if
                     name != ConfigDialog.currentTypeName]
        self.genericCombo.addItems(typeNames)
        try:
            generic = typeNames.index(currentFormat.genericType) + 1
        except ValueError:
            generic = 0
        self.genericCombo.setCurrentIndex(generic)
        self.genericCombo.blockSignals(False)
        self.setConditionAvail()

    def changeIcon(self):
        """Show the change icon dialog based on a button press.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dlg = IconSelectDialog(currentFormat, self)
        if (dlg.exec_() == QtGui.QDialog.Accepted and
            dlg.currentIconName != currentFormat.iconName):
            currentFormat.iconName = dlg.currentIconName
            self.mainDialogRef.setModified()
            self.updateContent()

    def changeUseBullets(self, checked=True):
        """Change setting to use bullets for output.

        Does not allow bullets and table to both be checked, and
        automatically checks use HTML.
        Arguments:
            checked -- True if bullets are selected
        """
        if checked:
            self.tableButton.setChecked(False)
            self.htmlButton.setChecked(True)
        self.htmlButton.setEnabled(not checked)
        self.mainDialogRef.setModified()

    def changeUseTable(self, checked=True):
        """Change setting to use tables for output.

        Does not allow bullets and table to both be checked, and
        automatically checks use HTML.
        Arguments:
            checked -- True if tables are selected
        """
        if checked:
            self.bulletButton.setChecked(False)
            self.htmlButton.setChecked(True)
        self.htmlButton.setEnabled(not checked)
        self.mainDialogRef.setModified()

    def setGenericIdRef(self):
        """Update the unique ID combobox based on a generic type change.
        """
        genericType = self.genericCombo.currentText()
        if genericType == _noTypeSetName:
            typeFormat =  ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
            self.idFieldCombo.setEnabled(True)
        else:
            typeFormat =  ConfigDialog.formatsRef[genericType]
            self.idFieldCombo.setEnabled(False)
        self.idFieldCombo.blockSignals(True)
        self.idFieldCombo.clear()
        self.idFieldCombo.addItems(typeFormat.fieldNames())
        self.idFieldCombo.setCurrentIndex(typeFormat.fieldNames().
                                          index(typeFormat.idField.name))
        self.idFieldCombo.blockSignals(False)
        self.setConditionAvail()

    def setConditionAvail(self):
        """Enable conditional button if generic or dervived type.

        Set button text based on presence of conditions.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        if self.genericCombo.currentIndex() > 0 or currentFormat.derivedTypes:
            self.conditionButton.setEnabled(True)
            if currentFormat.conditional:
                self.conditionButton.setText(_('Modify Co&nditional Types'))
                return
        else:
            self.conditionButton.setEnabled(False)
        self.conditionButton.setText(_('Create Co&nditional Types'))

    def showConditionDialog(self):
        """Show the dialog to create or modify conditional types.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dialog = conditional.ConditionDialog(conditional.ConditionDialog.
                                             typeDialog,
                                             _('Set Types Conditionally'),
                                             currentFormat)
        if currentFormat.conditional:
            dialog.setCondition(currentFormat.conditional)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            currentFormat.conditional = dialog.conditional()
            ConfigDialog.formatsRef.updateDerivedRefs()
            self.mainDialogRef.setModified()
            self.updateContent()

    def readChanges(self):
        """Make changes to the format for each widget.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        currentFormat.childType = self.childCombo.currentText()
        if currentFormat.childType == _noTypeSetName:
            currentFormat.childType = ''
        currentFormat.outputSeparator = self.outputSepEdit.text()
        oldIdField = currentFormat.idField
        prevGenericType = currentFormat.genericType
        currentFormat.genericType = self.genericCombo.currentText()
        if currentFormat.genericType == _noTypeSetName:
            currentFormat.genericType = ''
        if currentFormat.genericType != prevGenericType:
            ConfigDialog.formatsRef.updateDerivedRefs()
            currentFormat.updateFromGeneric(formatsRef=ConfigDialog.formatsRef)
        currentFormat.spaceBetween = self.blanksButton.isChecked()
        currentFormat.formatHtml = self.htmlButton.isChecked()
        useBullets = self.bulletButton.isChecked()
        useTables = self.tableButton.isChecked()
        if (useBullets != currentFormat.useBullets or
            useTables != currentFormat.useTables):
            currentFormat.useBullets = useBullets
            currentFormat.useTables = useTables
            if useBullets:
                currentFormat.addBullets()
            elif useTables:
                currentFormat.addTables()
            else:
                currentFormat.clearBulletsAndTables()
        currentFormat.idField = currentFormat.fieldDict[self.idFieldCombo.
                                                        currentText()]
        if currentFormat.idField != oldIdField:
            currentFormat.updateDerivedTypes()
            ConfigDialog.formatsRef.changedIdFieldTypes.add(currentFormat)


class FieldListPage(ConfigPage):
    """Config dialog page with an editable list of fields.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        topLayout = QtGui.QVBoxLayout(self)
        typeBox = QtGui.QGroupBox(_('&Data Type'))
        topLayout.addWidget(typeBox)
        typeLayout = QtGui.QVBoxLayout(typeBox)
        self.typeCombo = QtGui.QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged[str].connect(self.changeCurrentType)

        fieldBox = QtGui.QGroupBox(_('Modify &Field List'))
        topLayout.addWidget(fieldBox)
        horizLayout = QtGui.QHBoxLayout(fieldBox)
        self.fieldListBox = QtGui.QTreeWidget()
        horizLayout.addWidget(self.fieldListBox)
        self.fieldListBox.setRootIsDecorated(False)
        self.fieldListBox.setColumnCount(3)
        self.fieldListBox.setHeaderLabels([_('Name'), _('Type'),
                                           _('Sort Key')])
        self.fieldListBox.currentItemChanged.connect(self.changeField)

        buttonLayout = QtGui.QVBoxLayout()
        horizLayout.addLayout(buttonLayout)
        self.upButton = QtGui.QPushButton(_('Move U&p'))
        buttonLayout.addWidget(self.upButton)
        self.upButton.clicked.connect(self.moveUp)
        self.downButton = QtGui.QPushButton(_('Move Do&wn'))
        buttonLayout.addWidget(self.downButton)
        self.downButton.clicked.connect(self.moveDown)
        self.newButton = QtGui.QPushButton(_('&New Field...'))
        buttonLayout.addWidget(self.newButton)
        self.newButton.clicked.connect(self.newField)
        self.renameButton = QtGui.QPushButton(_('Rena&me Field...'))
        buttonLayout.addWidget(self.renameButton)
        self.renameButton.clicked.connect(self.renameField)
        self.deleteButton = QtGui.QPushButton(_('Dele&te Field'))
        buttonLayout.addWidget(self.deleteButton)
        self.deleteButton.clicked.connect(self.deleteField)
        sortKeyButton = QtGui.QPushButton(_('Sort &Keys...'))
        buttonLayout.addWidget(sortKeyButton)
        sortKeyButton.clicked.connect(self.defineSortKeys)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        typeNames = ConfigDialog.formatsRef.typeNames()
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItems(typeNames)
        self.typeCombo.setCurrentIndex(typeNames.index(ConfigDialog.
                                                       currentTypeName))
        self.typeCombo.blockSignals(False)

        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        sortFields = [field for field in currentFormat.fields() if
                      field.sortKeyNum > 0]
        sortFields.sort(key = operator.attrgetter('sortKeyNum'))
        if not sortFields:
            sortFields = [list(currentFormat.fields())[0]]
        self.fieldListBox.blockSignals(True)
        self.fieldListBox.clear()
        for field in currentFormat.fields():
            try:
                sortKey = repr(sortFields.index(field) + 1)
                sortDir = _('fwd') if field.sortKeyForward else _('rev')
                sortKey = '{0} ({1})'.format(sortKey, sortDir)
            except ValueError:
                sortKey = ''
            QtGui.QTreeWidgetItem(self.fieldListBox,
                                  [field.name, _(field.typeName), sortKey])
        selectNum = currentFormat.fieldNames().index(ConfigDialog.
                                                     currentFieldName)
        selectItem = self.fieldListBox.topLevelItem(selectNum)
        self.fieldListBox.setCurrentItem(selectItem)
        self.fieldListBox.setItemSelected(selectItem, True)
        width = self.fieldListBox.viewport().width()
        self.fieldListBox.setColumnWidth(0, width // 2.5)
        self.fieldListBox.setColumnWidth(1, width // 2.5)
        self.fieldListBox.setColumnWidth(2, width // 5)
        self.fieldListBox.blockSignals(False)
        num = currentFormat.fieldNames().index(ConfigDialog.currentFieldName)
        self.upButton.setEnabled(num > 0 and not  currentFormat.genericType)
        self.downButton.setEnabled(num < len(currentFormat.fieldDict) - 1 and
                                   not currentFormat.genericType)
        self.newButton.setEnabled(not currentFormat.genericType)
        self.renameButton.setEnabled(not currentFormat.genericType)
        self.deleteButton.setEnabled(len(currentFormat.fieldDict) > 1 and
                                     not currentFormat.genericType)

    def changeField(self, currentItem, prevItem):
        """Change the current format field based on a tree widget signal.

        Arguments:
            currentItem -- the new current tree widget item
            prevItem -- the old current tree widget item
        """
        self.changeCurrentField(currentItem.text(0))

    def moveUp(self):
        """Move field upward in the list based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        fieldList = currentFormat.fieldNames()
        num = fieldList.index(ConfigDialog.currentFieldName)
        if num > 0:
            fieldList[num-1], fieldList[num] = fieldList[num], fieldList[num-1]
            currentFormat.reorderFields(fieldList)
            currentFormat.updateDerivedTypes()
            self.updateContent()
            self.mainDialogRef.setModified()

    def moveDown(self):
        """Move field downward in the list based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        fieldList = currentFormat.fieldNames()
        num = fieldList.index(ConfigDialog.currentFieldName)
        if num < len(fieldList) - 1:
            fieldList[num], fieldList[num+1] = fieldList[num+1], fieldList[num]
            currentFormat.reorderFields(fieldList)
            currentFormat.updateDerivedTypes()
            self.updateContent()
            self.mainDialogRef.setModified()

    def newField(self):
        """Create and add a new field based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dlg = NameEntryDialog(_('Add Field'), _('Enter new field name:'), '',
                              '', currentFormat.fieldNames(), self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            currentFormat.addField(dlg.text)
            ConfigDialog.currentFieldName = dlg.text
            currentFormat.updateDerivedTypes()
            self.updateContent()
            self.mainDialogRef.setModified()

    def renameField(self):
        """Prompt for new name and rename field based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        fieldList = currentFormat.fieldNames()
        oldName = ConfigDialog.currentFieldName
        dlg = NameEntryDialog(_('Rename Field'),
                              _('Rename from {} to:').format(oldName), oldName,
                              '', fieldList, self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            num = fieldList.index(oldName)
            fieldList[num] = dlg.text
            for nodeFormat in [currentFormat] + currentFormat.derivedTypes:
                field = nodeFormat.fieldDict[oldName]
                field.name = dlg.text
                nodeFormat.fieldDict[field.name] = field
                nodeFormat.reorderFields(fieldList)
                nodeFormat.conditional.renameFields(oldName, field.name)
                savedConditions = {}
                for name, text in nodeFormat.savedConditionText.items():
                    condition = conditional.Conditional(text, nodeFormat.name)
                    condition.renameFields(oldName, field.name)
                    savedConditions[name] = condition.conditionStr()
                nodeFormat.savedConditionText = savedConditions
                renameDict = (ConfigDialog.formatsRef.fieldRenameDict.
                              setdefault(nodeFormat.name, {}))
                # reverse rename dict - find original name (multiple renames)
                reverseDict = {}
                for old, new in renameDict.items():
                    reverseDict[new] = old
                origName = reverseDict.get(oldName, oldName)
                renameDict[origName] = dlg.text
            ConfigDialog.currentFieldName = dlg.text
            self.updateContent()
            self.mainDialogRef.setModified()

    def deleteField(self):
        """Delete field based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        num = currentFormat.fieldNames().index(ConfigDialog.currentFieldName)
        for nodeFormat in [currentFormat] + currentFormat.derivedTypes:
            field = nodeFormat.fieldDict[ConfigDialog.currentFieldName]
            nodeFormat.removeField(field)
            del nodeFormat.fieldDict[ConfigDialog.currentFieldName]
            if nodeFormat.idField == field:
                nodeFormat.idField = list(nodeFormat.fieldDict.values())[0]
                ConfigDialog.formatsRef.changedIdFieldTypes.add(nodeFormat)
        if num > 0:
            num -= 1
        ConfigDialog.currentFieldName = currentFormat.fieldNames()[num]
        ConfigDialog.formatsRef.updateDerivedRefs()
        self.updateContent()
        self.mainDialogRef.setModified()

    def defineSortKeys(self):
        """Show a dialog to change sort key fields and directions.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dlg = SortKeyDialog(currentFormat.fieldDict, self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            self.updateContent()
            self.mainDialogRef.setModified()


_fileInfoFormatName = _('File Info Reference')

class FieldConfigPage(ConfigPage):
    """Config dialog page to change parmaters of a field.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.currentFileInfoField = ''

        topLayout = QtGui.QGridLayout(self)
        typeBox = QtGui.QGroupBox(_('&Data Type'))
        topLayout.addWidget(typeBox, 0, 0)
        typeLayout = QtGui.QVBoxLayout(typeBox)
        self.typeCombo = QtGui.QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged[str].connect(self.changeCurrentType)

        fieldBox = QtGui.QGroupBox(_('F&ield'))
        topLayout.addWidget(fieldBox, 0, 1)
        fieldLayout = QtGui.QVBoxLayout(fieldBox)
        self.fieldCombo = QtGui.QComboBox()
        fieldLayout.addWidget(self.fieldCombo)
        self.fieldCombo.currentIndexChanged[str].connect(self.
                                                         changeCurrentField)

        fieldTypeBox = QtGui.QGroupBox(_('&Field Type'))
        topLayout.addWidget(fieldTypeBox, 1, 0)
        fieldTypeLayout = QtGui.QVBoxLayout(fieldTypeBox)
        self.fieldTypeCombo = QtGui.QComboBox()
        fieldTypeLayout.addWidget(self.fieldTypeCombo)
        self.fieldTypeCombo.addItems([_(name) for name in
                                      fieldformat.fieldTypes])
        self.fieldTypeCombo.currentIndexChanged.connect(self.changeFieldType)

        self.formatBox = QtGui.QGroupBox(_('Outpu&t Format'))
        topLayout.addWidget(self.formatBox, 1, 1)
        formatLayout = QtGui.QHBoxLayout(self.formatBox)
        self.formatEdit = QtGui.QLineEdit()
        formatLayout.addWidget(self.formatEdit)
        self.formatEdit.textEdited.connect(self.mainDialogRef.setModified)
        self.helpButton = QtGui.QPushButton(_('Format &Help'))
        formatLayout.addWidget(self.helpButton)
        self.helpButton.clicked.connect(self.formatHelp)

        extraBox = QtGui.QGroupBox(_('Extra Text'))
        topLayout.addWidget(extraBox, 2, 0, 2, 1)
        extraLayout = QtGui.QVBoxLayout(extraBox)
        extraLayout.setSpacing(0)
        prefixLabel = QtGui.QLabel(_('&Prefix'))
        extraLayout.addWidget(prefixLabel)
        self.prefixEdit = QtGui.QLineEdit()
        extraLayout.addWidget(self.prefixEdit)
        prefixLabel.setBuddy(self.prefixEdit)
        self.prefixEdit.textEdited.connect(self.mainDialogRef.setModified)
        extraLayout.addSpacing(8)
        suffixLabel = QtGui.QLabel(_('Suffi&x'))
        extraLayout.addWidget(suffixLabel)
        self.suffixEdit = QtGui.QLineEdit()
        extraLayout.addWidget(self.suffixEdit)
        suffixLabel.setBuddy(self.suffixEdit)
        self.suffixEdit.textEdited.connect(self.mainDialogRef.setModified)

        defaultBox = QtGui.QGroupBox(_('Default &Value for New Nodes'))
        topLayout.addWidget(defaultBox, 2, 1)
        defaultLayout = QtGui.QVBoxLayout(defaultBox)
        self.defaultCombo = QtGui.QComboBox()
        defaultLayout.addWidget(self.defaultCombo)
        self.defaultCombo.setEditable(True)
        self.defaultCombo.editTextChanged.connect(self.mainDialogRef.
                                                  setModified)

        self.heightBox = QtGui.QGroupBox(_('Editor Height'))
        topLayout.addWidget(self.heightBox, 3, 1)
        heightLayout = QtGui.QHBoxLayout(self.heightBox)
        heightLabel = QtGui.QLabel(_('Num&ber of text lines'))
        heightLayout.addWidget(heightLabel)
        self.heightCtrl = QtGui.QSpinBox()
        heightLayout.addWidget(self.heightCtrl)
        self.heightCtrl.setMinimum(1)
        self.heightCtrl.setMaximum(999)
        heightLabel.setBuddy(self.heightCtrl)
        self.heightCtrl.valueChanged.connect(self.mainDialogRef.setModified)

        self.equationBox = QtGui.QGroupBox(_('Math Equation'))
        topLayout.addWidget(self.equationBox, 4, 0, 1, 2)
        equationLayout = QtGui.QHBoxLayout(self.equationBox)
        self.equationViewer = QtGui.QLineEdit()
        equationLayout.addWidget(self.equationViewer)
        self.equationViewer.setReadOnly(True)
        equationButton = QtGui.QPushButton(_('Define Equation'))
        equationLayout.addWidget(equationButton)
        equationButton.clicked.connect(self.defineMathEquation)

        topLayout.setRowStretch(5, 1)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        typeNames = ConfigDialog.formatsRef.typeNames()
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItems(typeNames)
        self.typeCombo.addItem(_fileInfoFormatName)
        if self.currentFileInfoField:
            self.typeCombo.setCurrentIndex(len(typeNames))
        else:
            self.typeCombo.setCurrentIndex(typeNames.index(ConfigDialog.
                                                           currentTypeName))
        self.typeCombo.blockSignals(False)

        currentFormat, currentField = self.currentFormatAndField()
        self.fieldCombo.blockSignals(True)
        self.fieldCombo.clear()
        self.fieldCombo.addItems(currentFormat.fieldNames())
        selectNum = currentFormat.fieldNames().index(currentField.name)
        self.fieldCombo.setCurrentIndex(selectNum)
        self.fieldCombo.blockSignals(False)

        self.fieldTypeCombo.blockSignals(True)
        selectNum = fieldformat.fieldTypes.index(currentField.typeName)
        self.fieldTypeCombo.setCurrentIndex(selectNum)
        self.fieldTypeCombo.blockSignals(False)
        self.fieldTypeCombo.setEnabled(not self.currentFileInfoField and
                                       not currentFormat.genericType)

        self.formatBox.setEnabled(currentField.defaultFormat != '')
        if (hasattr(currentField, 'resultType') and
            currentField.resultType == fieldformat.textResult):
            self.formatBox.setEnabled(False)
        self.formatEdit.setText(currentField.format)

        self.prefixEdit.setText(currentField.prefix)
        self.suffixEdit.setText(currentField.suffix)

        self.defaultCombo.blockSignals(True)
        self.defaultCombo.clear()
        self.defaultCombo.addItem(currentField.getEditorInitDefault())
        self.defaultCombo.addItems(currentField.initDefaultChoices())
        self.defaultCombo.setCurrentIndex(0)
        self.defaultCombo.blockSignals(False)
        self.defaultCombo.setEnabled(not self.currentFileInfoField)

        self.heightCtrl.blockSignals(True)
        self.heightCtrl.setValue(currentField.numLines)
        self.heightCtrl.blockSignals(False)
        self.heightBox.setEnabled(not self.currentFileInfoField and
                                  issubclass(currentField.editorClass,
                                             QtGui.QTextEdit))

        if currentField.typeName == 'Math':
            self.equationBox.show()
            eqnText = currentField.equationText()
            self.equationViewer.setText(eqnText)
        else:
            self.equationBox.hide()

    def currentFormatAndField(self):
        """Return a tuple of the current format and field.

        Adjusts for a current file info field.
        """
        if self.currentFileInfoField:
            currentFormat = ConfigDialog.formatsRef.fileInfoFormat
            fieldName = self.currentFileInfoField
        else:
            currentFormat = ConfigDialog.formatsRef[ConfigDialog.
                                                    currentTypeName]
            fieldName = ConfigDialog.currentFieldName
        currentField = currentFormat.fieldDict[fieldName]
        return (currentFormat, currentField)

    def changeCurrentType(self, typeName):
        """Change the current format type based on a signal from lists.

        Arguments:
            typeName -- the name of the new current type
        """
        self.readChanges()
        if typeName == _fileInfoFormatName:
            self.currentFileInfoField = (ConfigDialog.formatsRef.
                                         fileInfoFormat.fieldNames()[0])
        else:
            ConfigDialog.currentTypeName = typeName
            ConfigDialog.currentFieldName = (ConfigDialog.formatsRef[typeName].
                                             fieldNames()[0])
            self.currentFileInfoField = ''
        self.updateContent()

    def changeCurrentField(self, fieldName):
        """Change the current format field based on a signal from lists.

        Arguments:
            fieldName -- the name of the new current field
        """
        self.readChanges()
        if self.currentFileInfoField:
            self.currentFileInfoField = fieldName
        else:
            ConfigDialog.currentFieldName = fieldName
        self.updateContent()

    def changeFieldType(self):
        """Change the field type based on a combo box signal.
        """
        self.readChanges()   # preserve previous changes
        currentFormat, currentField = self.currentFormatAndField()
        selectNum = self.fieldTypeCombo.currentIndex()
        fieldTypeName = fieldformat.fieldTypes[selectNum]
        currentField.changeType(fieldTypeName)
        currentFormat.updateDerivedTypes()
        self.updateContent()
        self.mainDialogRef.setModified()

    def defineMathEquation(self):
        """Show the dialog to define an equation for a Math field.
        """
        currentFormat, currentField = self.currentFormatAndField()
        prevEqnText = currentField.equationText()
        prevResultType = currentField.resultType
        dlg = MathEquationDialog(currentFormat, currentField, self)
        if (dlg.exec_() == QtGui.QDialog.Accepted and
            (currentField.equationText() != prevEqnText or
             currentField.resultType != prevResultType)):
            self.mainDialogRef.setModified()
            self.updateContent()

    def formatHelp(self):
        """Provide a format help menu based on a button signal.
        """
        currentFormat, currentField = self.currentFormatAndField()
        menu = QtGui.QMenu(self)
        self.formatHelpDict = {}
        for descript, key in currentField.getFormatHelpMenuList():
            if descript:
                self.formatHelpDict[descript] = key
                menu.addAction(descript)
            else:
                menu.addSeparator()
        menu.popup(self.helpButton.
                   mapToGlobal(QtCore.QPoint(0, self.helpButton.height())))
        menu.triggered.connect(self.insertFormat)

    def insertFormat(self, action):
        """Insert format text from help menu into edit box.

        Arguments:
            action -- the action from the help menu
        """
        self.formatEdit.insert(self.formatHelpDict[action.text()])

    def readChanges(self):
        """Make changes to the format for each widget.
        """
        currentFormat, currentField = self.currentFormatAndField()
        if self.formatEdit.text() != currentField.format:
            try:
                currentField.setFormat(self.formatEdit.text())
                if self.currentFileInfoField:
                    currentFormat.fieldFormatModified = True
            except ValueError:
                self.formatEdit.setText(currentField.format)
        currentField.prefix = self.prefixEdit.text()
        currentField.suffix = self.suffixEdit.text()
        if self.currentFileInfoField and (currentField.prefix or
                                          currentField.suffix):
            currentFormat.fieldFormatModified = True
        try:
            currentField.setInitDefault(self.defaultCombo.currentText())
        except ValueError:
            self.defaultCombo.blockSignals(True)
            self.defaultCombo.setEditText(currentField.getEditorInitDefault())
            self.defaultCombo.blockSignals(False)
        currentField.numLines = self.heightCtrl.value()


_refLevelList = ['No Other Reference', 'File Info Reference',
                 'Any Ancestor Reference', 'Parent Reference',
                 'Grandparent Reference', 'Great Grandparent Reference',
                 'Child Reference', 'Child Count']
# _refLevelFlags  correspond to _refLevelList
_refLevelFlags = ['', '!', '?', '*', '**', '***', '&', '#']
fieldPattern = re.compile('{\*.*?\*}')

class  OutputPage(ConfigPage):
    """Config dialog page to define the node output strings.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.refLevelFlag = ''
        self.refLevelType = None

        topLayout = QtGui.QGridLayout(self)
        typeBox = QtGui.QGroupBox(_('&Data Type'))
        topLayout.addWidget(typeBox, 0, 0)
        typeLayout = QtGui.QVBoxLayout(typeBox)
        self.typeCombo = QtGui.QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged[str].connect(self.changeCurrentType)

        fieldBox = QtGui.QGroupBox(_('F&ield List'))
        topLayout.addWidget(fieldBox, 1, 0, 2, 1)
        boxLayout = QtGui.QVBoxLayout(fieldBox)
        self.fieldListBox = QtGui.QTreeWidget()
        boxLayout.addWidget(self.fieldListBox)
        self.fieldListBox.setRootIsDecorated(False)
        self.fieldListBox.setColumnCount(2)
        self.fieldListBox.setHeaderLabels([_('Name'), _('Type')])
        self.fieldListBox.currentItemChanged.connect(self.changeField)

        titleButtonLayout = QtGui.QVBoxLayout()
        topLayout.addLayout(titleButtonLayout, 1, 1)
        self.toTitleButton = QtGui.QPushButton('>>')
        titleButtonLayout.addWidget(self.toTitleButton)
        self.toTitleButton.setMaximumWidth(self.toTitleButton.
                                           sizeHint().height())
        self.toTitleButton.clicked.connect(self.fieldToTitle)
        self.delTitleButton = QtGui.QPushButton('<<')
        titleButtonLayout.addWidget(self.delTitleButton)
        self.delTitleButton.setMaximumWidth(self.delTitleButton.
                                            sizeHint().height())
        self.delTitleButton.clicked.connect(self.delTitleField)

        titleBox = QtGui.QGroupBox(_('&Title Format'))
        topLayout.addWidget(titleBox, 1, 2)
        titleLayout = QtGui.QVBoxLayout(titleBox)
        self.titleEdit = TitleEdit()
        titleLayout.addWidget(self.titleEdit)
        self.titleEdit.cursorPositionChanged.connect(self.
                                                     setControlAvailability)
        self.titleEdit.textEdited.connect(self.mainDialogRef.setModified)

        outputButtonLayout = QtGui.QVBoxLayout()
        topLayout.addLayout(outputButtonLayout, 2, 1)
        self.toOutputButton = QtGui.QPushButton('>>')
        outputButtonLayout.addWidget(self.toOutputButton)
        self.toOutputButton.setMaximumWidth(self.toOutputButton.
                                            sizeHint().height())
        self.toOutputButton.clicked.connect(self.fieldToOutput)
        self.delOutputButton = QtGui.QPushButton('<<')
        outputButtonLayout.addWidget(self.delOutputButton)
        self.delOutputButton.setMaximumWidth(self.delOutputButton.
                                             sizeHint().height())
        self.delOutputButton.clicked.connect(self.delOutputField)

        outputBox = QtGui.QGroupBox(_('Out&put Format'))
        topLayout.addWidget(outputBox, 2, 2)
        outputLayout = QtGui.QVBoxLayout(outputBox)
        self.outputEdit = QtGui.QTextEdit()
        self.outputEdit.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        outputLayout.addWidget(self.outputEdit)
        self.outputEdit.setTabChangesFocus(True)
        self.outputEdit.cursorPositionChanged.connect(self.
                                                      setControlAvailability)
        self.outputEdit.textChanged.connect(self.mainDialogRef.setModified)

        # advanced widgets
        otherBox = QtGui.QGroupBox(_('Other Field References'))
        topLayout.addWidget(otherBox, 0, 2)
        self.advancedWidgets.append(otherBox)
        otherLayout = QtGui.QHBoxLayout(otherBox)
        levelLayout =  QtGui.QVBoxLayout()
        otherLayout.addLayout(levelLayout)
        levelLayout.setSpacing(0)
        levelLabel = QtGui.QLabel(_('Reference Le&vel'))
        levelLayout.addWidget(levelLabel)
        levelCombo = QtGui.QComboBox()
        levelLayout.addWidget(levelCombo)
        levelLabel.setBuddy(levelCombo)
        levelCombo.addItems(_refLevelList)
        levelCombo.currentIndexChanged.connect(self.changeRefLevel)
        refTypeLayout = QtGui.QVBoxLayout()
        otherLayout.addLayout(refTypeLayout)
        refTypeLayout.setSpacing(0)
        refTypeLabel = QtGui.QLabel(_('Refere&nce Type'))
        refTypeLayout.addWidget(refTypeLabel)
        self.refTypeCombo = QtGui.QComboBox()
        refTypeLayout.addWidget(self.refTypeCombo)
        refTypeLabel.setBuddy(self.refTypeCombo)
        self.refTypeCombo.currentIndexChanged.connect(self.changeRefType)

        topLayout.setRowStretch(1, 1)
        topLayout.setRowStretch(2, 1)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        typeNames = ConfigDialog.formatsRef.typeNames()
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItems(typeNames)
        self.typeCombo.setCurrentIndex(typeNames.index(ConfigDialog.
                                                       currentTypeName))
        self.typeCombo.blockSignals(False)

        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        self.updateFieldList()
        lines = currentFormat.getLines()
        self.titleEdit.blockSignals(True)
        self.titleEdit.setText(lines[0])
        self.titleEdit.end(False)
        self.titleEdit.blockSignals(False)
        self.outputEdit.blockSignals(True)
        self.outputEdit.setPlainText('\n'.join(lines[1:]))
        cursor = self.outputEdit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.outputEdit.setTextCursor(cursor)
        self.outputEdit.blockSignals(False)

        self.refTypeCombo.blockSignals(True)
        self.refTypeCombo.clear()
        self.refTypeCombo.addItems(typeNames)
        refLevelType = (self.refLevelType if self.refLevelType else
                        ConfigDialog.currentTypeName)
        try:
            self.refTypeCombo.setCurrentIndex(typeNames.index(refLevelType))
        except ValueError:   # type no longer exists
            self.refLevelType = ConfigDialog.currentTypeName
            self.refTypeCombo.setCurrentIndex(typeNames.index(self.
                                                              refLevelType))
        self.refTypeCombo.blockSignals(False)
        self.setControlAvailability()

    def updateFieldList(self):
        """Reload the field list box.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        if not self.refLevelFlag:
            activeFormat = currentFormat
        elif self.refLevelFlag == '!':
            activeFormat = ConfigDialog.formatsRef.fileInfoFormat
        elif self.refLevelFlag == '#':
            activeFormat = nodeformat.DescendantCountFormat()
        else:
            try:
                activeFormat = ConfigDialog.formatsRef[self.refLevelType]
            except ValueError:
                self.refLevelType = ConfigDialog.currentTypeName
                activeFormat = currentFormat
        self.fieldListBox.blockSignals(True)
        self.fieldListBox.clear()
        for field in activeFormat.fields():
            if field.showInDialog:
                QtGui.QTreeWidgetItem(self.fieldListBox,
                                      [field.name, field.typeName])
        if self.refLevelFlag == '!':
            QtGui.QTreeWidgetItem(self.fieldListBox,
                                  [nodeformat.uniqueIdFieldName, 'Text'])
        selectList = self.fieldListBox.findItems(ConfigDialog.currentFieldName,
                                                 QtCore.Qt.MatchFixedString |
                                                 QtCore.Qt.MatchCaseSensitive)
        selectItem = (selectList[0] if selectList else
                      self.fieldListBox.topLevelItem(0))
        self.fieldListBox.setCurrentItem(selectItem)
        self.fieldListBox.setItemSelected(selectItem, True)
        self.fieldListBox.setColumnWidth(0, self.fieldListBox.width() // 2)
        self.fieldListBox.blockSignals(False)

    def changeField(self, currentItem, prevItem):
        """Change the current format field based on a tree widget signal.

        Not set if a special field ref level is active.
        Arguments:
            currentItem -- the new current tree widget item
            prevItem -- the old current tree widget item
        """
        if not self.refLevelFlag:
            ConfigDialog.currentFieldName = currentItem.text(0)

    def setControlAvailability(self):
        """Set controls available based on text cursor movements.
        """
        cursorInTitleField = self.isCursorInTitleField()
        self.toTitleButton.setEnabled(cursorInTitleField == None)
        self.delTitleButton.setEnabled(cursorInTitleField == True)
        cursorInOutputField = self.isCursorInOutputField()
        self.toOutputButton.setEnabled(cursorInOutputField == None)
        self.delOutputButton.setEnabled(cursorInOutputField == True)
        self.refTypeCombo.setEnabled(self.refLevelFlag not in ('', '!', '#'))

    def fieldToTitle(self):
        """Add selected field to cursor pos in title editor.
        """
        self.titleEdit.insert(self.currentFieldSepName())
        self.titleEdit.setFocus()

    def delTitleField(self):
        """Remove field from cursor pos in title editor.
        """
        if self.isCursorInTitleField(True):
            self.titleEdit.insert('')

    def fieldToOutput(self):
        """Add selected field to cursor pos in output editor.
        """
        self.outputEdit.insertPlainText(self.currentFieldSepName())
        self.outputEdit.setFocus()

    def delOutputField(self):
        """Remove field from cursor pos in output editor.
        """
        if self.isCursorInOutputField(True):
            self.outputEdit.insertPlainText('')

    def currentFieldSepName(self):
        """Return current field name with proper separators.

        Adjusts for special field ref levels.
        """
        return '{{*{0}{1}*}}'.format(self.refLevelFlag,
                                     self.fieldListBox.currentItem().text(0))

    def isCursorInTitleField(self, selectField=False):
        """Return True if a field pattern encloses the cursor/selection.

        Return False if the selection overlaps a field.
        Return None if there is no field at the cursor.
        Arguments:
            selectField -- select the entire field pattern if True.
        """
        cursorPos = self.titleEdit.cursorPosition()
        selectStart = self.titleEdit.selectionStart()
        if selectStart < 0:
            selectStart = cursorPos
        elif selectStart == cursorPos:   # backward selection
            cursorPos += len(self.titleEdit.selectedText())
        fieldPos = self.fieldPosAtCursor(selectStart, cursorPos,
                                         self.titleEdit.text())
        if not fieldPos:
            return None
        start, end = fieldPos
        if start == None or end == None:
            return False
        if selectField:
            self.titleEdit.setSelection(start, end - start)
        return True

    def isCursorInOutputField(self, selectField=False):
        """Return True if a field pattern encloses the cursor/selection.

        Return False if the selection overlaps a field.
        Return None if there is no field at the cursor.
        Arguments:
            selectField -- select the entire field pattern if True.
        """
        outputCursor = self.outputEdit.textCursor()
        selectStart = outputCursor.anchor()
        cursorPos = outputCursor.position()
        block = outputCursor.block()
        blockStart = block.position()
        if selectStart < blockStart or (selectStart > blockStart +
                                        block.length()):
            return False      # multi-line selection
        fieldPos = self.fieldPosAtCursor(selectStart - blockStart,
                                         cursorPos - blockStart, block.text())
        if not fieldPos:
            return None
        start, end = fieldPos
        if start == None or end == None:
            return False
        if selectField:
            outputCursor.setPosition(start + blockStart)
            outputCursor.setPosition(end + blockStart,
                                     QtGui.QTextCursor.KeepAnchor)
            self.outputEdit.setTextCursor(outputCursor)
        return True

    def fieldPosAtCursor(self, anchorPos, cursorPos, textLine):
        """Find the position of the field pattern that encloses the selection.

        Return a tuple of (start, end) positions of the field if found.
        Return (start, None) or (None, end) if the selection overlaps.
        Return None if no field is found.
        Arguments:
            anchorPos -- the selection start
            cursorPos -- the selection end
            textLine -- the text to search
        """
        for match in fieldPattern.finditer(textLine):
            start = (match.start() if match.start() < anchorPos < match.end()
                     else None)
            end = (match.end() if match.start() < cursorPos < match.end()
                   else None)
            if start != None or end != None:
                return (start, end)
        return None

    def changeRefLevel(self, num):
        """Change other field ref level based on a combobox signal.

        Arguments:
            num -- the combobox index selected
        """
        self.refLevelFlag = _refLevelFlags[num]
        if self.refLevelFlag in ('', '!', '#'):
            self.refLevelType = None
        elif not self.refLevelType:
            self.refLevelType = ConfigDialog.currentTypeName
        self.updateFieldList()
        self.setControlAvailability()

    def changeRefType(self, num):
        """Change the other field ref level type based on a combobox signal.

        Arguments:
            num -- the combobox index selected
        """
        self.refLevelType = ConfigDialog.formatsRef.typeNames()[num]
        self.updateFieldList()
        self.setControlAvailability()

    def readChanges(self):
        """Make changes to the format for each widget.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        currentFormat.changeTitleLine(self.titleEdit.text())
        currentFormat.changeOutputLines(self.outputEdit.toPlainText().strip().
                                        split('\n'),
                                        not currentFormat.formatHtml)


class TitleEdit(QtGui.QLineEdit):
    """LineEdit that avoids changing the selection on focus changes.
    """
    focusIn = QtCore.pyqtSignal(QtGui.QWidget)
    def __init__(self, parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent dialog
        """
        super().__init__(parent)

    def focusInEvent(self, event):
        """Override to keep selection & cursor position.

        Arguments:
            event -- the focus event
        """
        cursorPos = self.cursorPosition()
        selectStart = self.selectionStart()
        if selectStart == cursorPos:
            selectStart = cursorPos + len(self.selectedText())
        super().focusInEvent(event)
        self.setCursorPosition(cursorPos)
        if selectStart >= 0:
            self.setSelection(selectStart, cursorPos - selectStart)
        self.focusIn.emit(self)

    def focusOutEvent(self, event):
        """Override to keep selection & cursor position.

        Arguments:
            event -- the focus event
        """
        cursorPos = self.cursorPosition()
        selectStart = self.selectionStart()
        if selectStart == cursorPos:
            selectStart = cursorPos + len(self.selectedText())
        super().focusOutEvent(event)
        self.setCursorPosition(cursorPos)
        if selectStart >= 0:
            self.setSelection(selectStart, cursorPos - selectStart)


_illegalRe = re.compile(r'[^\w_\-.]')

class NameEntryDialog(QtGui.QDialog):
    """Dialog to handle user entry of a type or field name.

    Restricts entry to alpha-numerics, underscores, dashes and periods.
    """
    def __init__(self, caption, labelText, defaultText='', addCheckBox = '',
                 badText=None, parent=None):
        """Initialize the name entry class.

        Arguments:
            caption -- the window title
            labelText -- text for a descriptive lable
            defaultText -- initial text
            addCheckBox -- the label for an extra check box if needed
            badText -- a set or list of other illegal strings
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.badText = set()
        if badText:
            self.badText = badText
        self.text = ''
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(caption)
        topLayout = QtGui.QVBoxLayout(self)
        label = QtGui.QLabel(labelText)
        topLayout.addWidget(label)
        self.entry = QtGui.QLineEdit(defaultText)
        topLayout.addWidget(self.entry)
        self.entry.setFocus()
        self.entry.returnPressed.connect(self.accept)

        self.extraChecked = False
        if addCheckBox:
            self.extraCheckBox = QtGui.QCheckBox(addCheckBox)
            topLayout.addWidget(self.extraCheckBox)
        else:
            self.extraCheckBox = None

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def accept(self):
        """Check for acceptable string before closing.
        """
        self.text = self.entry.text().strip()
        if not self.text:
            error = _('The name cannot be empty')
        elif not self.text[0].isalpha():
            error = _('The name must start with a letter')
        elif self.text[:3].lower() == 'xml':
            error = _('The name cannot start with "xml"')
        elif ' ' in self.text:
            error = _('The name cannot contain spaces')
        elif _illegalRe.search(self.text):
            badChars = set(_illegalRe.findall(self.text))
            error = (_('The following characters are not allowed: {}').
                     format(''.join(badChars)))
        elif self.text in self.badText:
            error = _('The name was already used')
        else:
            if self.extraCheckBox:
                self.extraChecked = self.extraCheckBox.isChecked()
            return super().accept()
        QtGui.QMessageBox.warning(self, 'TreeLine', error)


class IconSelectDialog(QtGui.QDialog):
    """Dialog for selecting icons for a format type.
    """
    dialogSize = ()
    dialogPos = ()
    def __init__(self, nodeFormat, parent=None):
        """Create the icon select dialog.

        Arguments:
            nodeFormat -- the current node format to be set
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.currentIconName = nodeFormat.iconName
        if (not self.currentIconName or
            self.currentIconName not in globalref.treeIcons):
            self.currentIconName = icondict.defaultName
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Set Data Type Icon'))
        topLayout = QtGui.QVBoxLayout(self)
        self.iconView = QtGui.QListWidget()
        self.iconView.setViewMode(QtGui.QListView.ListMode)
        self.iconView.setMovement(QtGui.QListView.Static)
        self.iconView.setResizeMode(QtGui.QListView.Adjust)
        self.iconView.setWrapping(True)
        self.iconView.setGridSize(QtCore.QSize(112, 32))
        topLayout.addWidget(self.iconView)
        self.iconView.itemDoubleClicked.connect(self.accept)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        clearButton = QtGui.QPushButton(_('Clear &Select'))
        ctrlLayout.addWidget(clearButton)
        clearButton.clicked.connect(self.iconView.clearSelection)
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        if IconSelectDialog.dialogSize:
            self.resize(IconSelectDialog.dialogSize[0],
                        IconSelectDialog.dialogSize[1])
            self.move(IconSelectDialog.dialogPos[0],
                      IconSelectDialog.dialogPos[1])
        self.loadIcons()

    def loadIcons(self):
        """Load icons from the icon dict source.
        """
        if not globalref.treeIcons.allLoaded:
            globalref.treeIcons.loadAllIcons()
        for name, icon in globalref.treeIcons.items():
            if icon:
                item = QtGui.QListWidgetItem(icon, name, self.iconView)
                if name == self.currentIconName:
                    self.iconView.setCurrentItem(item)
        self.iconView.sortItems()
        selectedItem = self.iconView.currentItem()
        if selectedItem:
            self.iconView.scrollToItem(selectedItem,
                                      QtGui.QAbstractItemView.PositionAtCenter)

    def saveSize(self):
        """Record dialog size at close.
        """
        IconSelectDialog.dialogSize = (self.width(), self.height())
        IconSelectDialog.dialogPos = (self.x(), self.y())

    def accept(self):
        """Save changes before closing.
        """
        selectedItems = self.iconView.selectedItems()
        if selectedItems:
            self.currentIconName = selectedItems[0].text()
            if self.currentIconName == icondict.defaultName:
                self.currentIconName = ''
        else:
            self.currentIconName = icondict.noneName
        self.saveSize()
        super().accept()

    def reject(self):
        """Save dialog size before closing.
        """
        self.saveSize()
        super().reject()


class SortKeyDialog(QtGui.QDialog):
    """Dialog for defining sort key fields and directions.
    """
    directionNameDict = {True: _('forward'), False: _('reverse')}
    directionVarDict = dict([(name, boolVal) for boolVal, name in
                             directionNameDict.items()])
    def __init__(self, fieldDict, parent=None):
        """Create the sort key dialog.

        Arguments:
            fieldDict -- a dict of field names and values
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.fieldDict = fieldDict
        self.numChanges = 0
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Sort Key Fields'))
        topLayout = QtGui.QVBoxLayout(self)
        horizLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(horizLayout)
        fieldBox = QtGui.QGroupBox(_('Available &Fields'))
        horizLayout.addWidget(fieldBox)
        boxLayout = QtGui.QVBoxLayout(fieldBox)
        self.fieldListBox = QtGui.QTreeWidget()
        boxLayout.addWidget(self.fieldListBox)
        self.fieldListBox.setRootIsDecorated(False)
        self.fieldListBox.setColumnCount(2)
        self.fieldListBox.setHeaderLabels([_('Name'), _('Type')])

        midButtonLayout = QtGui.QVBoxLayout()
        horizLayout.addLayout(midButtonLayout)
        self.addFieldButton = QtGui.QPushButton('>>')
        midButtonLayout.addWidget(self.addFieldButton)
        self.addFieldButton.setMaximumWidth(self.addFieldButton.
                                            sizeHint().height())
        self.addFieldButton.clicked.connect(self.addField)
        self.removeFieldButton = QtGui.QPushButton('<<')
        midButtonLayout.addWidget(self.removeFieldButton)
        self.removeFieldButton.setMaximumWidth(self.removeFieldButton.
                                               sizeHint().height())
        self.removeFieldButton.clicked.connect(self.removeField)

        sortBox = QtGui.QGroupBox(_('&Sort Criteria'))
        horizLayout.addWidget(sortBox)
        boxLayout = QtGui.QVBoxLayout(sortBox)
        self.sortListBox = QtGui.QTreeWidget()
        boxLayout.addWidget(self.sortListBox)
        self.sortListBox.setRootIsDecorated(False)
        self.sortListBox.setColumnCount(3)
        self.sortListBox.setHeaderLabels(['#', _('Field'), _('Direction')])
        self.sortListBox.currentItemChanged.connect(self.setControlsAvail)

        rightButtonLayout = QtGui.QVBoxLayout()
        horizLayout.addLayout(rightButtonLayout)
        self.upButton = QtGui.QPushButton(_('Move &Up'))
        rightButtonLayout.addWidget(self.upButton)
        self.upButton.clicked.connect(self.moveUp)
        self.downButton = QtGui.QPushButton(_('&Move Down'))
        rightButtonLayout.addWidget(self.downButton)
        self.downButton.clicked.connect(self.moveDown)
        self.flipButton = QtGui.QPushButton(_('Flip &Direction'))
        rightButtonLayout.addWidget(self.flipButton)
        self.flipButton.clicked.connect(self.flipDirection)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        self.okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.updateContent()

    def updateContent(self):
        """Update dialog contents from current format settings.
        """
        sortFields = [field for field in self.fieldDict.values() if
                      field.sortKeyNum > 0]
        sortFields.sort(key = operator.attrgetter('sortKeyNum'))
        if not sortFields:
            sortFields = [list(self.fieldDict.values())[0]]
        self.fieldListBox.clear()
        for field in self.fieldDict.values():
            if field not in sortFields:
                QtGui.QTreeWidgetItem(self.fieldListBox,
                                      [field.name, field.typeName])
        if self.fieldListBox.topLevelItemCount() > 0:
            self.fieldListBox.setCurrentItem(self.fieldListBox.topLevelItem(0))
        self.fieldListBox.setColumnWidth(0, self.fieldListBox.sizeHint().
                                         width() // 2)
        self.sortListBox.blockSignals(True)
        self.sortListBox.clear()
        for num, field in enumerate(sortFields, 1):
            sortDir = SortKeyDialog.directionNameDict[field.sortKeyForward]
            QtGui.QTreeWidgetItem(self.sortListBox,
                                  [repr(num), field.name, sortDir])
        self.sortListBox.setCurrentItem(self.sortListBox.topLevelItem(0))
        self.sortListBox.blockSignals(False)
        self.sortListBox.setColumnWidth(0, self.sortListBox.sizeHint().
                                        width() // 8)
        self.setControlsAvail()

    def setControlsAvail(self):
        """Set controls available based on selections.
        """
        self.addFieldButton.setEnabled(self.fieldListBox.topLevelItemCount() >
                                       0)
        hasSortItems = self.sortListBox.topLevelItemCount() > 0
        self.removeFieldButton.setEnabled(hasSortItems)
        if hasSortItems:
            sortPosNum = self.sortListBox.indexOfTopLevelItem(self.sortListBox.
                                                              currentItem())
        self.upButton.setEnabled(hasSortItems and sortPosNum > 0)
        self.downButton.setEnabled(hasSortItems and sortPosNum <
                                   self.sortListBox.topLevelItemCount() - 1)
        self.flipButton.setEnabled(hasSortItems)
        self.okButton.setEnabled(hasSortItems)

    def addField(self):
        """Add a field to the sort criteria list.
        """
        itemNum = self.fieldListBox.indexOfTopLevelItem(self.fieldListBox.
                                                        currentItem())
        fieldName = self.fieldListBox.takeTopLevelItem(itemNum).text(0)
        field = self.fieldDict[fieldName]
        sortNum = self.sortListBox.topLevelItemCount() + 1
        sortDir = SortKeyDialog.directionNameDict[field.sortKeyForward]
        self.sortListBox.blockSignals(True)
        sortItem = QtGui.QTreeWidgetItem(self.sortListBox,
                                         [repr(sortNum), fieldName, sortDir])
        self.sortListBox.setCurrentItem(sortItem)
        self.sortListBox.blockSignals(False)
        self.setControlsAvail()
        self.numChanges += 1

    def removeField(self):
        """Remove a field from the sort criteria list.
        """
        itemNum = self.sortListBox.indexOfTopLevelItem(self.sortListBox.
                                                       currentItem())
        self.sortListBox.blockSignals(True)
        fieldName = self.sortListBox.takeTopLevelItem(itemNum).text(1)
        self.renumberSortFields()
        self.sortListBox.blockSignals(False)
        field = self.fieldDict[fieldName]
        sortFieldNames = set()
        for num in range(self.sortListBox.topLevelItemCount()):
            sortFieldNames.add(self.sortListBox.topLevelItem(num).text(1))
        fieldList = [field for field in self.fieldDict.values() if
                     field.name not in sortFieldNames]
        pos = fieldList.index(field)
        fieldItem = QtGui.QTreeWidgetItem([fieldName, field.typeName])
        self.fieldListBox.insertTopLevelItem(pos, fieldItem)
        self.setControlsAvail()
        self.numChanges += 1

    def moveUp(self):
        """Move a field upward in the sort criteria.
        """
        itemNum = self.sortListBox.indexOfTopLevelItem(self.sortListBox.
                                                       currentItem())
        self.sortListBox.blockSignals(True)
        sortItem = self.sortListBox.takeTopLevelItem(itemNum)
        self.sortListBox.insertTopLevelItem(itemNum - 1, sortItem)
        self.sortListBox.setCurrentItem(sortItem)
        self.renumberSortFields()
        self.sortListBox.blockSignals(False)
        self.setControlsAvail()
        self.numChanges += 1

    def moveDown(self):
        """Move a field downward in the sort criteria.
        """
        itemNum = self.sortListBox.indexOfTopLevelItem(self.sortListBox.
                                                       currentItem())
        self.sortListBox.blockSignals(True)
        sortItem = self.sortListBox.takeTopLevelItem(itemNum)
        self.sortListBox.insertTopLevelItem(itemNum + 1, sortItem)
        self.sortListBox.setCurrentItem(sortItem)
        self.renumberSortFields()
        self.sortListBox.blockSignals(False)
        self.setControlsAvail()
        self.numChanges += 1

    def flipDirection(self):
        """Toggle the direction of the current sort field.
        """
        sortItem = self.sortListBox.currentItem()
        oldDirection = SortKeyDialog.directionVarDict[sortItem.text(2)]
        newDirection = SortKeyDialog.directionNameDict[not oldDirection]
        sortItem.setText(2, newDirection)
        self.numChanges += 1

    def renumberSortFields(self):
        """Update field numbers in the sort list.
        """
        for num in range(self.sortListBox.topLevelItemCount()):
            self.sortListBox.topLevelItem(num).setText(0, repr(num + 1))

    def accept(self):
        """Save changes before closing.
        """
        if not self.numChanges:
            return self.reject()
        for field in self.fieldDict.values():
            field.sortKeyNum = 0
            field.sortKeyForward = True
        for num in range(self.sortListBox.topLevelItemCount()):
            fieldItem = self.sortListBox.topLevelItem(num)
            field = self.fieldDict[fieldItem.text(1)]
            field.sortKeyNum = num + 1
            field.sortKeyForward = SortKeyDialog.directionVarDict[fieldItem.
                                                                  text(2)]
        return super().accept()


_mathRefLevels = [_('Self Reference'), _('Parent Reference'),
                  _('Root Reference'), _('Child Reference'), _('Child Count')]
# _mathRefLevelFlags  correspond to _mathRefLevels
_mathRefLevelFlags = ['', '*', '$', '&', '#']
_mathResultTypes = [N_('Numeric Result'), N_('Date Result'), N_('Time Result'),
                    N_('Boolean Result'), N_('Text Result')]
_operatorTypes = [_('Arithmetic Operators'), _('Comparison Operators'),
                  _('Text Operators')]
_arithmeticOperators = [('+', _('add')),
                        ('-', _('subtract')),
                        ('*', _('multiply')),
                        ('/', _('divide')),
                        ('//', _('floor divide')),
                        ('%', _('modulus')),
                        ('**', _('power')),
                        ('sum()', _('sum of items')),
                        ('max()', _('maximum')),
                        ('min()', _('minimum')),
                        ('mean()', _('average')),
                        ('abs()', _('absolute value')),
                        ('sqrt()', _('square root')),
                        ('log()', _('natural logarithm')),
                        ('log10()', _('base-10 logarithm')),
                        ('factorial()', _('factorial')),
                        ('round()', _('round to num digits')),
                        ('floor()', _('lower integer')),
                        ('ceil()', _('higher integer')),
                        ('int()', _('truncated integer')),
                        ('float()', _('floating point')),
                        ('sin()', _('sine of radians')),
                        ('cos()', _('cosine of radians')),
                        ('tan()', _('tangent of radians')),
                        ('asin()', _('arc sine')),
                        ('acos()', _('arc cosine')),
                        ('atan()', _('arc tangent')),
                        ('degrees()', _('radians to degrees')),
                        ('radians()', _('degrees to radians')),
                        ('pi', _('pi constant')),
                        ('e', _('natural log constant'))]
_comparisonOperators = [('==', _('equal to')),
                        ('<', _('less than')),
                        ('>', _('greater than')),
                        ('<=', _('less than or equal to')),
                        ('>=', _('greater than or equal to')),
                        ('!=', _('not equal to')),
                        ('() if () else ()',
                         _('true value, condition, false value')),
                        ('and', _('logical and')),
                        ('or', _('logical or')),
                        ('startswith()',
                         _('true if 1st text arg starts with 2nd arg')),
                        ('endswith()',
                         _('true if 1st text arg ends with 2nd arg')),
                        ('contains()',
                         _('true if 1st text arg contains 2nd arg'))]
_textOperators = [('+', _('concatenate text')),
                  ("join(' ', )", _('join text using 1st arg as separator')),
                  ('upper()', _('convert text to upper case')),
                  ('lower()', _('convert text to lower case')),
                  ('replace()', _('in 1st arg, replace 2nd arg with 3rd arg'))]
# _operatorLists correspond to _operatorTypes
_operatorLists = [_arithmeticOperators, _comparisonOperators, _textOperators]

class MathEquationDialog(QtGui.QDialog):
    """Dialog for defining equations for Math fields.
    """
    def __init__(self, nodeFormat, field, parent=None):
        """Create the math equation dialog.

        Arguments:
            nodeFormat -- the current node format
            field -- the Math field
        """
        super().__init__(parent)
        self.nodeFormat = nodeFormat
        self.typeFormats = self.nodeFormat.parentFormats
        self.field = field
        self.refLevelFlag = ''
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Define Math Field Equation'))

        topLayout = QtGui.QGridLayout(self)
        fieldBox = QtGui.QGroupBox(_('Field References'))
        topLayout.addWidget(fieldBox, 0, 0, 2, 1)
        fieldLayout = QtGui.QVBoxLayout(fieldBox)
        innerLayout = QtGui.QVBoxLayout()
        innerLayout.setSpacing(0)
        fieldLayout.addLayout(innerLayout)
        levelLabel = QtGui.QLabel(_('Reference &Level'))
        innerLayout.addWidget(levelLabel)
        levelCombo = QtGui.QComboBox()
        innerLayout.addWidget(levelCombo)
        levelLabel.setBuddy(levelCombo)
        levelCombo.addItems(_mathRefLevels)
        levelCombo.currentIndexChanged.connect(self.changeRefLevel)
        innerLayout = QtGui.QVBoxLayout()
        innerLayout.setSpacing(0)
        fieldLayout.addLayout(innerLayout)
        typeLabel = QtGui.QLabel(_('Reference &Type'))
        innerLayout.addWidget(typeLabel)
        self.typeCombo = QtGui.QComboBox()
        innerLayout.addWidget(self.typeCombo)
        typeLabel.setBuddy(self.typeCombo)
        self.typeCombo.addItems(self.typeFormats.typeNames())
        self.typeCombo.currentIndexChanged.connect(self.updateFieldList)
        innerLayout = QtGui.QVBoxLayout()
        innerLayout.setSpacing(0)
        fieldLayout.addLayout(innerLayout)
        fieldLabel = QtGui.QLabel(_('Available &Field List'))
        innerLayout.addWidget(fieldLabel)
        self.fieldListBox = QtGui.QTreeWidget()
        innerLayout.addWidget(self.fieldListBox)
        fieldLabel.setBuddy(self.fieldListBox)
        self.fieldListBox.setRootIsDecorated(False)
        self.fieldListBox.setColumnCount(2)
        self.fieldListBox.setHeaderLabels([_('Name'), _('Type')])

        resultTypeBox = QtGui.QGroupBox(_('&Result Type'))
        topLayout.addWidget(resultTypeBox, 0, 1)
        resultTypeLayout = QtGui.QVBoxLayout(resultTypeBox)
        self.resultTypeCombo = QtGui.QComboBox()
        resultTypeLayout.addWidget(self.resultTypeCombo)
        self.resultTypeCombo.addItems([_(str) for str in _mathResultTypes])
        results = [s.split(' ', 1)[0].lower() for s in _mathResultTypes]
        resultStr = fieldformat.mathResultStr[self.field.resultType]
        self.resultTypeCombo.setCurrentIndex(results.index(resultStr))

        operBox = QtGui.QGroupBox(_('Operations'))
        topLayout.addWidget(operBox, 1, 1)
        operLayout = QtGui.QVBoxLayout(operBox)
        innerLayout = QtGui.QVBoxLayout()
        innerLayout.setSpacing(0)
        operLayout.addLayout(innerLayout)
        operTypeLabel = QtGui.QLabel(_('O&perator Type'))
        innerLayout.addWidget(operTypeLabel)
        operTypeCombo = QtGui.QComboBox()
        innerLayout.addWidget(operTypeCombo)
        operTypeLabel.setBuddy(operTypeCombo)
        operTypeCombo.addItems(_operatorTypes)
        operTypeCombo.currentIndexChanged.connect(self.replaceOperatorList)
        innerLayout = QtGui.QVBoxLayout()
        innerLayout.setSpacing(0)
        operLayout.addLayout(innerLayout)
        operListLabel = QtGui.QLabel(_('Oper&ator List'))
        innerLayout.addWidget(operListLabel)
        self.operListBox = QtGui.QTreeWidget()
        innerLayout.addWidget(self.operListBox)
        operListLabel.setBuddy(self.operListBox)
        self.operListBox.setRootIsDecorated(False)
        self.operListBox.setColumnCount(2)
        self.operListBox.setHeaderLabels([_('Name'), _('Description')])
        self.replaceOperatorList(0)

        buttonLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(buttonLayout, 2, 0)
        buttonLayout.addStretch()
        self.addFieldButton = QtGui.QPushButton('\u25bc')
        buttonLayout.addWidget(self.addFieldButton)
        self.addFieldButton.setMaximumWidth(self.addFieldButton.
                                            sizeHint().height())
        self.addFieldButton.clicked.connect(self.addField)
        self.delFieldButton = QtGui.QPushButton('\u25b2')
        buttonLayout.addWidget(self.delFieldButton)
        self.delFieldButton.setMaximumWidth(self.delFieldButton.
                                            sizeHint().height())
        self.delFieldButton.clicked.connect(self.deleteField)
        buttonLayout.addStretch()

        buttonLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(buttonLayout, 2, 1)
        self.addOperButton = QtGui.QPushButton('\u25bc')
        buttonLayout.addWidget(self.addOperButton)
        self.addOperButton.setMaximumWidth(self.addOperButton.
                                           sizeHint().height())
        self.addOperButton.clicked.connect(self.addOperator)

        equationBox = QtGui.QGroupBox(_('&Equation'))
        topLayout.addWidget(equationBox, 3, 0, 1, 2)
        equationLayout = QtGui.QVBoxLayout(equationBox)
        self.equationEdit = TitleEdit()
        equationLayout.addWidget(self.equationEdit)
        self.equationEdit.setText(self.field.equationText())
        self.equationEdit.cursorPositionChanged.connect(self.
                                                        setControlAvailability)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout, 4, 0, 1, 2)
        ctrlLayout.addStretch()
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.setDefault(True)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.changeRefLevel(0)
        self.equationEdit.setFocus()

    def updateFieldList(self):
        """Update field list based on reference type setting.
        """
        currentFormat = self.typeFormats[self.typeCombo.currentText()]
        self.fieldListBox.clear()
        if self.refLevelFlag != '#':
            for field in currentFormat.fields():
                if (hasattr(field, 'mathValue') and field.showInDialog
                    and (self.refLevelFlag or field != self.field)):
                    QtGui.QTreeWidgetItem(self.fieldListBox,
                                          [field.name, _(field.typeName)])
        else:
            QtGui.QTreeWidgetItem(self.fieldListBox,
                                  ['Count', 'Number of Children'])
        if self.fieldListBox.topLevelItemCount():
            selectItem = self.fieldListBox.topLevelItem(0)
            self.fieldListBox.setCurrentItem(selectItem)
            self.fieldListBox.setItemSelected(selectItem, True)
        self.fieldListBox.resizeColumnToContents(0)
        self.fieldListBox.setColumnWidth(0,
                                         self.fieldListBox.columnWidth(0) * 2)
        self.setControlAvailability()

    def setControlAvailability(self):
        """Set controls available based on text cursor movements.
        """
        cursorInField = self.isCursorInField()
        fieldCount = self.fieldListBox.topLevelItemCount()
        self.addFieldButton.setEnabled(cursorInField == None and fieldCount)
        self.delFieldButton.setEnabled(cursorInField == True)
        self.addOperButton.setEnabled(cursorInField == None)

    def addField(self):
        """Add selected field to cursor pos in the equation editor.
        """
        fieldSepName = '{{*{0}{1}*}}'.format(self.refLevelFlag,
                                             self.fieldListBox.currentItem().
                                             text(0))
        self.equationEdit.insert(fieldSepName)
        self.equationEdit.setFocus()

    def deleteField(self):
        """Remove field from cursor pos in the equation editor.
        """
        if self.isCursorInField(True):
            self.equationEdit.insert('')
        self.equationEdit.setFocus()

    def addOperator(self):
        """Add selected operator to cursor pos in the equation editor.
        """
        oper = self.operListBox.currentItem().text(0)
        origText = self.equationEdit.text()
        cursorPos = self.equationEdit.cursorPosition()
        if cursorPos != 0 and origText[cursorPos - 1] != ' ':
            oper = ' ' + oper
        self.equationEdit.insert(oper + ' ')
        parenPos = oper.find(')')
        if parenPos >= 0:
            cursorPos = self.equationEdit.cursorPosition()
            self.equationEdit.setCursorPosition(cursorPos - len(oper) +
                                                parenPos - 1)
        self.equationEdit.setFocus()

    def isCursorInField(self, selectField=False):
        """Return True if a field pattern encloses the cursor/selection.

        Return False if the selection overlaps a field.
        Return None if there is no field at the cursor.
        Arguments:
            selectField -- select the entire field pattern if True.
        """
        cursorPos = self.equationEdit.cursorPosition()
        selectStart = self.equationEdit.selectionStart()
        if selectStart < 0:
            selectStart = cursorPos
        elif selectStart == cursorPos:   # backward selection
            cursorPos += len(self.equationEdit.selectedText())
        start = end = None
        for match in fieldPattern.finditer(self.equationEdit.text()):
            start = (match.start() if match.start() < selectStart < match.end()
                     else None)
            end = (match.end() if match.start() < cursorPos < match.end()
                   else None)
            if start != None or end != None:
                break
        if start == None and end == None:
            return None
        if start == None or end == None:
            return False
        if selectField:
            self.equationEdit.setSelection(start, end - start)
        return True

    def changeRefLevel(self, num):
        """Change the reference level based on a combobox signal.

        Arguments:
            num -- the combobox index selected
        """
        self.refLevelFlag = _mathRefLevelFlags[num]
        if self.refLevelFlag in ('', '#'):
            self.typeCombo.setEnabled(False)
            self.typeCombo.setCurrentIndex(self.typeFormats.typeNames().
                                           index(self.nodeFormat.name))
        else:
            self.typeCombo.setEnabled(True)
        self.updateFieldList()

    def replaceOperatorList(self, num):
        """Change the operator list based on a signal from the oper type combo.

        Arguments:
            num -- the combobox index selected
        """
        self.operListBox.clear()
        for oper, descr in _operatorLists[num]:
            QtGui.QTreeWidgetItem(self.operListBox, [oper, descr])
        self.operListBox.resizeColumnToContents(0)
        self.operListBox.setColumnWidth(0,
                                        self.operListBox.columnWidth(0) * 1.2)
        self.operListBox.resizeColumnToContents(1)
        selectItem = self.operListBox.topLevelItem(0)
        self.operListBox.setCurrentItem(selectItem)
        self.operListBox.setItemSelected(selectItem, True)

    def accept(self):
        """Verify the equation and close the dialog if acceptable.
        """
        eqnText = self.equationEdit.text().strip()
        if eqnText:
            eqn = matheval.MathEquation(eqnText)
            try:
                eqn.validate()
            except ValueError as err:
                QtGui.QMessageBox.warning(self, 'TreeLine',
                                          _('Equation error: {}').format(err))
                return
            self.typeFormats.emptiedMathDict.setdefault(self.nodeFormat.name,
                                                set()).discard(self.field.name)
            self.field.equation = eqn
        else:
            if self.field.equationText():
                self.typeFormats.emptiedMathDict.setdefault(self.nodeFormat.
                                              name, set()).add(self.field.name)
            self.field.equation = None
        resultStr = (_mathResultTypes[self.resultTypeCombo.currentIndex()].
                     split(' ', 1)[0].lower())
        self.field.changeResultType(fieldformat.mathResultVar[resultStr])
        super().accept()
