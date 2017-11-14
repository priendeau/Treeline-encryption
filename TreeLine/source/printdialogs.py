#!/usr/bin/env python3

#******************************************************************************
# printdialogs.py, provides print preview and print settings dialogs
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
from PyQt4 import QtCore, QtGui
import printdata
import configdialog
import treeformats
import undo
import globalref


class PrintPreviewDialog(QtGui.QDialog):
    """Dialog for print previews.

    Similar to QPrintPreviewDialog but calls a custom page setup dialog.
    """
    def __init__(self, printData, parent=None):
        """Create the print preview dialog.

        Arguments:
            printData -- the PrintData object
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Print Preview'))
        self.printData = printData
        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)

        toolBar = QtGui.QToolBar(self)
        topLayout.addWidget(toolBar)

        self.previewWidget = QtGui.QPrintPreviewWidget(printData.printer, self)
        topLayout.addWidget(self.previewWidget)
        self.previewWidget.previewChanged.connect(self.updateControls)

        self.zoomWidthAct = QtGui.QAction(_('Fit Width'), self, checkable=True)
        icon = globalref.toolIcons.getIcon('printpreviewzoomwidth')
        if icon:
            self.zoomWidthAct.setIcon(icon)
        self.zoomWidthAct.triggered.connect(self.zoomWidth)
        toolBar.addAction(self.zoomWidthAct)

        self.zoomAllAct = QtGui.QAction(_('Fit Page'), self, checkable=True)
        icon = globalref.toolIcons.getIcon('printpreviewzoomall')
        if icon:
            self.zoomAllAct.setIcon(icon)
        self.zoomAllAct.triggered.connect(self.zoomAll)
        toolBar.addAction(self.zoomAllAct)
        toolBar.addSeparator()

        self.zoomCombo = QtGui.QComboBox(self)
        self.zoomCombo.setEditable(True)
        self.zoomCombo.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.zoomCombo.addItems(['  12%', '  25%', '  50%', '  75%', ' 100%',
                                 ' 125%', ' 150%', ' 200%', ' 400%', ' 800%'])
        self.zoomCombo.currentIndexChanged[str].connect(self.zoomToValue)
        self.zoomCombo.lineEdit().returnPressed.connect(self.zoomToValue)
        toolBar.addWidget(self.zoomCombo)

        zoomInAct = QtGui.QAction(_('Zoom In'), self)
        icon = globalref.toolIcons.getIcon('printpreviewzoomin')
        if icon:
            zoomInAct.setIcon(icon)
        zoomInAct.triggered.connect(self.zoomIn)
        toolBar.addAction(zoomInAct)

        zoomOutAct = QtGui.QAction(_('Zoom Out'), self)
        icon = globalref.toolIcons.getIcon('printpreviewzoomout')
        if icon:
            zoomOutAct.setIcon(icon)
        zoomOutAct.triggered.connect(self.zoomOut)
        toolBar.addAction(zoomOutAct)
        toolBar.addSeparator()

        self.previousAct = QtGui.QAction(_('Previous Page'), self)
        icon = globalref.toolIcons.getIcon('printpreviewprevious')
        if icon:
            self.previousAct.setIcon(icon)
        self.previousAct.triggered.connect(self.previousPage)
        toolBar.addAction(self.previousAct)

        self.pageNumEdit = QtGui.QLineEdit(self)
        self.pageNumEdit.setAlignment(QtCore.Qt.AlignRight |
                                      QtCore.Qt.AlignVCenter)
        width = QtGui.QFontMetrics(self.pageNumEdit.font()).width('0000')
        self.pageNumEdit.setMaximumWidth(width)
        self.pageNumEdit.returnPressed.connect(self.setPageNum)
        toolBar.addWidget(self.pageNumEdit)

        self.maxPageLabel = QtGui.QLabel(' / 000 ', self)
        toolBar.addWidget(self.maxPageLabel)

        self.nextAct = QtGui.QAction(_('Next Page'), self)
        icon = globalref.toolIcons.getIcon('printpreviewnext')
        if icon:
            self.nextAct.setIcon(icon)
        self.nextAct.triggered.connect(self.nextPage)
        toolBar.addAction(self.nextAct)
        toolBar.addSeparator()

        self.onePageAct = QtGui.QAction(_('Single Page'), self, checkable=True)
        icon = globalref.toolIcons.getIcon('printpreviewsingle')
        if icon:
            self.onePageAct.setIcon(icon)
        self.onePageAct.triggered.connect(self.previewWidget.
                                          setSinglePageViewMode)
        toolBar.addAction(self.onePageAct)

        self.twoPageAct = QtGui.QAction(_('Facing Pages'), self,
                                        checkable=True)
        icon = globalref.toolIcons.getIcon('printpreviewdouble')
        if icon:
            self.twoPageAct.setIcon(icon)
        self.twoPageAct.triggered.connect(self.previewWidget.
                                          setFacingPagesViewMode)
        toolBar.addAction(self.twoPageAct)
        toolBar.addSeparator()

        pageSetupAct = QtGui.QAction(_('Print Setup'), self)
        icon = globalref.toolIcons.getIcon('fileprintsetup')
        if icon:
            pageSetupAct.setIcon(icon)
        pageSetupAct.triggered.connect(self.printSetup)
        toolBar.addAction(pageSetupAct)

        filePrintAct = QtGui.QAction(_('Print'), self)
        icon = globalref.toolIcons.getIcon('fileprint')
        if icon:
            filePrintAct.setIcon(icon)
        filePrintAct.triggered.connect(self.filePrint)
        toolBar.addAction(filePrintAct)

    def updateControls(self):
        """Update control availability and status based on a change signal.
        """
        self.zoomWidthAct.setChecked(self.previewWidget.zoomMode() ==
                                     QtGui.QPrintPreviewWidget.FitToWidth)
        self.zoomAllAct.setChecked(self.previewWidget.zoomMode() ==
                                   QtGui.QPrintPreviewWidget.FitInView)
        zoom = self.previewWidget.zoomFactor() * 100
        self.zoomCombo.setEditText('{0:4.0f}%'.format(zoom))
        self.previousAct.setEnabled(self.previewWidget.currentPage() > 1)
        self.nextAct.setEnabled(self.previewWidget.currentPage() <
                                self.previewWidget.pageCount())
        self.pageNumEdit.setText(str(self.previewWidget.currentPage()))
        self.maxPageLabel.setText(' / {0} '.format(self.previewWidget.
                                                   pageCount()))
        self.onePageAct.setChecked(self.previewWidget.viewMode() ==
                                   QtGui.QPrintPreviewWidget.SinglePageView)
        self.twoPageAct.setChecked(self.previewWidget.viewMode() ==
                                   QtGui.QPrintPreviewWidget.FacingPagesView)

    def zoomWidth(self, checked=True):
        """Set the fit to width zoom mode if checked.

        Arguments:
            checked -- set this mode if True
        """
        if checked:
            self.previewWidget.setZoomMode(QtGui.QPrintPreviewWidget.
                                           FitToWidth)
        else:
            self.previewWidget.setZoomMode(QtGui.QPrintPreviewWidget.
                                           CustomZoom)
        self.updateControls()

    def zoomAll(self, checked=True):
        """Set the fit in view zoom mode if checked.

        Arguments:
            checked -- set this mode if True
        """
        if checked:
            self.previewWidget.setZoomMode(QtGui.QPrintPreviewWidget.FitInView)
        else:
            self.previewWidget.setZoomMode(QtGui.QPrintPreviewWidget.
                                           CustomZoom)
        self.updateControls()

    def zoomToValue(self, factorStr=''):
        """Zoom to the given combo box string value.

        Arguments:
            factorStr -- the zoom factor as a string, often with a % suffix
        """
        if not factorStr:
            factorStr = self.zoomCombo.lineEdit().text()
        try:
            factor = float(factorStr.strip(' %')) / 100
            self.previewWidget.setZoomFactor(factor)
        except ValueError:
            pass
        self.updateControls()

    def zoomIn(self):
        """Increase the zoom level by an increment.
        """
        self.previewWidget.zoomIn()
        self.updateControls()

    def zoomOut(self):
        """Decrease the zoom level by an increment.
        """
        self.previewWidget.zoomOut()
        self.updateControls()

    def previousPage(self):
        """Go to the previous page of the preview.
        """
        self.previewWidget.setCurrentPage(self.previewWidget.currentPage() - 1)
        self.updateControls()

    def nextPage(self):
        """Go to the next page of the preview.
        """
        self.previewWidget.setCurrentPage(self.previewWidget.currentPage() + 1)
        self.updateControls()

    def setPageNum(self):
        """Go to a page number from the line editor based on a signal.
        """
        try:
            self.previewWidget.setCurrentPage(int(self.pageNumEdit.text()))
        except ValueError:
            pass
        self.updateControls()

    def printSetup(self):
        """Show a dialog to set margins, page size and other printing options.
        """
        setupDialog = PrintSetupDialog(self.printData, False, self)
        if setupDialog.exec_() == QtGui.QDialog.Accepted:
            self.printData.setupData()
            self.previewWidget.updatePreview()

    def filePrint(self):
        """Show dialog and print tree output based on current options.
        """
        self.close()
        self.printData.filePrint()

    def sizeHint(self):
        """Return a larger default height.
        """
        size = super().sizeHint()
        size.setHeight(600)
        return size

    def restoreDialogGeom(self):
        """Restore dialog window geometry from history options.
        """
        rect = QtCore.QRect(globalref.histOptions.getValue('PrintPrevXPos'),
                            globalref.histOptions.getValue('PrintPrevYPos'),
                            globalref.histOptions.getValue('PrintPrevXSize'),
                            globalref.histOptions.getValue('PrintPrevYSize'))
        if rect.height() and rect.width():
            self.setGeometry(rect)

    def saveDialogGeom(self):
        """Savedialog window geometry to history options.
        """
        globalref.histOptions.changeValue('PrintPrevXSize', self.width())
        globalref.histOptions.changeValue('PrintPrevYSize', self.height())
        globalref.histOptions.changeValue('PrintPrevXPos', self.geometry().x())
        globalref.histOptions.changeValue('PrintPrevYPos', self.geometry().y())

    def closeEvent(self, event):
        """Save dialog geometry at close.

        Arguments:
            event -- the close event
        """
        if globalref.genOptions.getValue('SaveWindowGeom'):
            self.saveDialogGeom()


class PrintSetupDialog(QtGui.QDialog):
    """Base dialog for setting the print configuration.
    
    Pushes most options to the PrintData class.
    """
    def __init__(self, printData, showExtraButtons=True, parent=None):
        """Create the printing setup dialog.

        Arguments:
            printData -- a reference to the PrintData class
            showExtraButtons -- add print preview and print shortcut buttons
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Printing Setup'))
        self.printData = printData

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)

        tabs = QtGui.QTabWidget()
        topLayout.addWidget(tabs)
        generalPage = GeneralPage(self.printData)
        tabs.addTab(generalPage, _('&General Options'))
        pageSetupPage = PageSetupPage(self.printData)
        tabs.addTab(pageSetupPage, _('Page &Setup'))
        fontPage = FontPage(self.printData)
        tabs.addTab(fontPage, _('&Font Selection'))
        headerPage = HeaderPage(self.printData)
        tabs.addTab(headerPage, _('&Header/Footer'))
        self.tabPages = [generalPage, pageSetupPage, fontPage, headerPage]

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        if showExtraButtons:
            previewButton =  QtGui.QPushButton(_('Print Pre&view...'))
            ctrlLayout.addWidget(previewButton)
            previewButton.clicked.connect(self.preview)
            printButton = QtGui.QPushButton(_('&Print...'))
            ctrlLayout.addWidget(printButton)
            printButton.clicked.connect(self.quickPrint)
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def quickPrint(self):
        """Accept this dialog and go to print dialog"""
        self.accept()
        self.printData.filePrint()

    def preview(self):
        """Accept this dialog and go to print preview dialog"""
        self.accept()
        self.printData.printPreview()

    def accept(self):
        """Store results before closing dialog"""
        changed = False
        undoObj = undo.StateSettingUndo(self.printData.localControl.model.
                                        undoList, self.printData.xmlAttr,
                                        self.printData.restoreXmlAttrs)
        for page in self.tabPages:
            if page.saveChanges():
                changed = True
        if changed:
            self.printData.adjustSpacing()
            self.printData.localControl.setModified()
        else:
            self.printData.localControl.model.undoList.removeLastUndo(undoObj)
        super().accept()


class GeneralPage(QtGui.QWidget):
    """Dialog page for misc. print options.
    """
    def __init__(self, printData, parent=None):
        """Create the general settings page.

        Arguments:
            printData -- a reference to the PrintData class
            parent -- the parent dialog
        """
        super().__init__(parent)
        self.printData = printData
        topLayout = QtGui.QGridLayout(self)
        self.setLayout(topLayout)

        whatGroupBox = QtGui.QGroupBox(_('What to print'))
        topLayout.addWidget(whatGroupBox, 0, 0)
        whatLayout = QtGui.QVBoxLayout(whatGroupBox)
        self.whatButtons = QtGui.QButtonGroup(self)
        treeButton = QtGui.QRadioButton(_('&Entire tree'))
        self.whatButtons.addButton(treeButton, printdata.entireTree)
        whatLayout.addWidget(treeButton)
        branchButton = QtGui.QRadioButton(_('Selected &branches'))
        self.whatButtons.addButton(branchButton, printdata.selectBranch)
        whatLayout.addWidget(branchButton)
        nodeButton = QtGui.QRadioButton(_('Selected &nodes'))
        self.whatButtons.addButton(nodeButton, printdata.selectNode)
        whatLayout.addWidget(nodeButton)
        self.whatButtons.button(self.printData.printWhat).setChecked(True)
        self.whatButtons.buttonClicked.connect(self.updateCmdAvail)

        includeBox = QtGui.QGroupBox(_('Included Nodes'))
        topLayout.addWidget(includeBox, 1, 0)
        includeLayout = QtGui.QVBoxLayout(includeBox)
        self.rootButton = QtGui.QCheckBox(_('&Include root node'))
        includeLayout.addWidget(self.rootButton)
        self.rootButton.setChecked(self.printData.includeRoot)
        self.openOnlyButton = QtGui.QCheckBox(_('Onl&y open node children'))
        includeLayout.addWidget(self.openOnlyButton)
        self.openOnlyButton.setChecked(self.printData.openOnly)

        featureBox = QtGui.QGroupBox(_('Features'))
        topLayout.addWidget(featureBox, 0, 1)
        featureLayout = QtGui.QVBoxLayout(featureBox)
        self.linesButton = QtGui.QCheckBox(_('&Draw lines to children'))
        featureLayout.addWidget(self.linesButton)
        self.linesButton.setChecked(self.printData.drawLines)
        self.widowButton = QtGui.QCheckBox(_('&Keep first child with parent'))
        featureLayout.addWidget(self.widowButton)
        self.widowButton.setChecked(self.printData.widowControl)

        indentBox = QtGui.QGroupBox(_('Indent'))
        topLayout.addWidget(indentBox, 1, 1)
        indentLayout = QtGui.QHBoxLayout(indentBox)
        indentLabel = QtGui.QLabel(_('Indent Offse&t\n(line height units)'))
        indentLayout.addWidget(indentLabel)
        self.indentSpin =  QtGui.QDoubleSpinBox()
        indentLayout.addWidget(self.indentSpin)
        indentLabel.setBuddy(self.indentSpin)
        self.indentSpin.setMinimum(0.5)
        self.indentSpin.setSingleStep(0.5)
        self.indentSpin.setDecimals(1)
        self.indentSpin.setValue(self.printData.indentFactor)

        topLayout.setRowStretch(2, 1)
        self.updateCmdAvail()

    def updateCmdAvail(self):
        """Update options available based on print what settings.
        """
        if self.whatButtons.checkedId() == printdata.selectNode:
            self.rootButton.setChecked(True)
            self.rootButton.setEnabled(False)
            self.openOnlyButton.setChecked(False)
            self.openOnlyButton.setEnabled(False)
        else:
            self.rootButton.setEnabled(True)
            self.openOnlyButton.setEnabled(True)

    def saveChanges(self):
        """Update print data with current dialog settings.

        Return True if saved settings have changed, False otherwise.
        """
        self.printData.printWhat = self.whatButtons.checkedId()
        self.printData.includeRoot = self.rootButton.isChecked()
        self.printData.openOnly = self.openOnlyButton.isChecked()
        changed = False
        if self.printData.drawLines != self.linesButton.isChecked():
            self.printData.drawLines = self.linesButton.isChecked()
            changed = True
        if self.printData.widowControl != self.widowButton.isChecked():
            self.printData.widowControl = self.widowButton.isChecked()
            changed = True
        if self.printData.indentFactor != self.indentSpin.value():
            self.printData.indentFactor = self.indentSpin.value()
            changed = True
        return changed


_paperSizes = collections.OrderedDict([('Letter', _('Letter (8.5 x 11 in.)')),
                                       ('Legal', _('Legal (8.5 x 14 in.)'),),
                                       ('Tabloid', _('Tabloid (11 x 17 in.)')),
                                       ('A3', _('A3 (279 x 420 mm)')),
                                       ('A4', _('A4 (210 x 297 mm)')),
                                       ('A5', _('A5 (148 x 210 mm)')),
                                       ('Custom', _('Custom Size'))])
_units = collections.OrderedDict([('in', _('Inches (in)')),
                                  ('mm', _('Millimeters (mm)')),
                                  ('cm', _('Centimeters (cm)'))])
_unitValues = {'in': 1.0, 'cm': 2.54, 'mm': 25.4}
_unitDecimals = {'in': 2, 'cm': 1, 'mm': 0}

class PageSetupPage(QtGui.QWidget):
    """Dialog page for page setup options.
    """
    def __init__(self, printData, parent=None):
        """Create the page setup settings page.

        Arguments:
            printData -- a reference to the PrintData class
            parent -- the parent dialog
        """
        super().__init__(parent)
        self.printData = printData
        topLayout = QtGui.QHBoxLayout(self)
        self.setLayout(topLayout)
        leftLayout = QtGui.QVBoxLayout()
        topLayout.addLayout(leftLayout)

        unitsBox = QtGui.QGroupBox(_('&Units'))
        leftLayout.addWidget(unitsBox)
        unitsLayout = QtGui.QVBoxLayout(unitsBox)
        unitsCombo = QtGui.QComboBox()
        unitsLayout.addWidget(unitsCombo)
        unitsCombo.addItems(list(_units.values()))
        self.currentUnit = globalref.miscOptions.getValue('PrintUnits')
        if self.currentUnit not in _units:
            self.currentUnit = 'in'
        unitsCombo.setCurrentIndex(list(_units.keys()).index(self.currentUnit))
        unitsCombo.currentIndexChanged.connect(self.changeUnits)

        paperSizeBox = QtGui.QGroupBox(_('Paper &Size'))
        leftLayout.addWidget(paperSizeBox)
        paperSizeLayout = QtGui.QGridLayout(paperSizeBox)
        spacing = paperSizeLayout.spacing()
        paperSizeLayout.setVerticalSpacing(0)
        paperSizeLayout.setRowMinimumHeight(1, spacing)
        paperSizeCombo = QtGui.QComboBox()
        paperSizeLayout.addWidget(paperSizeCombo, 0, 0, 1, 2)
        paperSizeCombo.addItems(list(_paperSizes.values()))
        paperSizeDict = dict((num, attrib) for attrib, num in
                             vars(QtGui.QPrinter).items()
                             if isinstance(num, QtGui.QPrinter.PageSize))
        self.currentPaperSize = paperSizeDict[self.printData.printer.
                                              paperSize()]
        if self.currentPaperSize not in _paperSizes:
            self.currentPaperSize = 'Custom'
        paperSizeCombo.setCurrentIndex(list(_paperSizes.keys()).
                                       index(self.currentPaperSize))
        paperSizeCombo.currentIndexChanged.connect(self.changePaper)
        widthLabel = QtGui.QLabel(_('&Width:'))
        paperSizeLayout.addWidget(widthLabel, 2, 0)
        self.paperWidthSpin = UnitSpinBox(self.currentUnit)
        paperSizeLayout.addWidget(self.paperWidthSpin, 3, 0)
        widthLabel.setBuddy(self.paperWidthSpin)
        paperWidth, paperHeight = self.printData.roundedPaperSize()
        self.paperWidthSpin.setInchValue(paperWidth)
        heightlabel = QtGui.QLabel(_('Height:'))
        paperSizeLayout.addWidget(heightlabel, 2, 1)
        self.paperHeightSpin = UnitSpinBox(self.currentUnit)
        paperSizeLayout.addWidget(self.paperHeightSpin, 3, 1)
        heightlabel.setBuddy(self.paperHeightSpin)
        self.paperHeightSpin.setInchValue(paperHeight)
        if self.currentPaperSize != 'Custom':
            self.paperWidthSpin.setEnabled(False)
            self.paperHeightSpin.setEnabled(False)

        orientbox = QtGui.QGroupBox(_('Orientation'))
        leftLayout.addWidget(orientbox)
        orientLayout = QtGui.QVBoxLayout(orientbox)
        portraitButton = QtGui.QRadioButton(_('Portra&it'))
        orientLayout.addWidget(portraitButton)
        landscapeButton = QtGui.QRadioButton(_('Lan&dscape'))
        orientLayout.addWidget(landscapeButton)
        self.portraitOrient = (self.printData.printer.orientation() ==
                               QtGui.QPrinter.Portrait)
        if self.portraitOrient:
            portraitButton.setChecked(True)
        else:
            landscapeButton.setChecked(True)
        portraitButton.toggled.connect(self.changeOrient)

        rightLayout = QtGui.QVBoxLayout()
        topLayout.addLayout(rightLayout)

        marginsBox = QtGui.QGroupBox(_('Margins'))
        rightLayout.addWidget(marginsBox)
        marginsLayout = QtGui.QGridLayout(marginsBox)
        spacing = marginsLayout.spacing()
        marginsLayout.setVerticalSpacing(0)
        marginsLayout.setRowMinimumHeight(2, spacing)
        marginsLayout.setRowMinimumHeight(5, spacing)
        leftLabel = QtGui.QLabel(_('&Left:'))
        marginsLayout.addWidget(leftLabel, 3, 0)
        leftMarginSpin = UnitSpinBox(self.currentUnit)
        marginsLayout.addWidget(leftMarginSpin, 4, 0)
        leftLabel.setBuddy(leftMarginSpin)
        topLabel = QtGui.QLabel(_('&Top:'))
        marginsLayout.addWidget(topLabel, 0, 1)
        topMarginSpin = UnitSpinBox(self.currentUnit)
        marginsLayout.addWidget(topMarginSpin, 1, 1)
        topLabel.setBuddy(topMarginSpin)
        rightLabel = QtGui.QLabel(_('&Right:'))
        marginsLayout.addWidget(rightLabel, 3, 2)
        rightMarginSpin = UnitSpinBox(self.currentUnit)
        marginsLayout.addWidget(rightMarginSpin, 4, 2)
        rightLabel.setBuddy(rightMarginSpin)
        bottomLabel = QtGui.QLabel(_('&Bottom:'))
        marginsLayout.addWidget(bottomLabel, 6, 1)
        bottomMarginSpin = UnitSpinBox(self.currentUnit)
        marginsLayout.addWidget(bottomMarginSpin, 7, 1)
        bottomLabel.setBuddy(bottomMarginSpin)
        self.marginControls = (leftMarginSpin, topMarginSpin, rightMarginSpin,
                               bottomMarginSpin)
        for control, value in zip(self.marginControls,
                                  self.printData.roundedMargins()):
            control.setInchValue(value)
        headerLabel = QtGui.QLabel(_('He&ader:'))
        marginsLayout.addWidget(headerLabel, 0, 2)
        self.headerMarginSpin = UnitSpinBox(self.currentUnit)
        marginsLayout.addWidget(self.headerMarginSpin, 1, 2)
        headerLabel.setBuddy(self.headerMarginSpin)
        self.headerMarginSpin.setInchValue(self.printData.headerMargin)
        footerLabel = QtGui.QLabel(_('Foot&er:'))
        marginsLayout.addWidget(footerLabel, 6, 2)
        self.footerMarginSpin = UnitSpinBox(self.currentUnit)
        marginsLayout.addWidget(self.footerMarginSpin, 7, 2)
        footerLabel.setBuddy(self.footerMarginSpin)
        self.footerMarginSpin.setInchValue(self.printData.footerMargin)

        columnsBox = QtGui.QGroupBox(_('Columns'))
        rightLayout.addWidget(columnsBox)
        columnLayout = QtGui.QGridLayout(columnsBox)
        numLabel = QtGui.QLabel(_('&Number of columns'))
        columnLayout.addWidget(numLabel, 0, 0)
        self.columnSpin = QtGui.QSpinBox()
        columnLayout.addWidget(self.columnSpin, 0, 1)
        numLabel.setBuddy(self.columnSpin)
        self.columnSpin.setMinimum(1)
        self.columnSpin.setMaximum(9)
        self.columnSpin.setValue(self.printData.numColumns)
        spaceLabel = QtGui.QLabel(_('Space between colu&mns'))
        columnLayout.addWidget(spaceLabel, 1, 0)
        self.columnSpaceSpin = UnitSpinBox(self.currentUnit)
        columnLayout.addWidget(self.columnSpaceSpin, 1, 1)
        spaceLabel.setBuddy(self.columnSpaceSpin)
        self.columnSpaceSpin.setInchValue(self.printData.columnSpacing)

    def changeUnits(self, unitNum):
        """Change the current unit and update conversions based on a signal.

        Arguments:
            unitNum -- the unit index number from the combobox
        """
        oldUnit = self.currentUnit
        self.currentUnit = list(_units.keys())[unitNum]
        self.paperWidthSpin.changeUnit(self.currentUnit)
        self.paperHeightSpin.changeUnit(self.currentUnit)
        for control in self.marginControls:
            control.changeUnit(self.currentUnit)
        self.headerMarginSpin.changeUnit(self.currentUnit)
        self.footerMarginSpin.changeUnit(self.currentUnit)
        self.columnSpaceSpin.changeUnit(self.currentUnit)

    def changePaper(self, paperNum):
        """Change the current paper size based on a signal.

        Arguments:
            paperNum -- the paper size index number from the combobox
        """
        self.currentPaperSize = list(_paperSizes.keys())[paperNum]
        if self.currentPaperSize != 'Custom':
            tempPrinter = QtGui.QPrinter()
            tempPrinter.setPaperSize(getattr(QtGui.QPrinter,
                                             self.currentPaperSize))
            if not self.portraitOrient:
                tempPrinter.setOrientation(QtGui.QPrinter.Landscape)
            paperSize = tempPrinter.paperSize(QtGui.QPrinter.Inch)
            self.paperWidthSpin.setInchValue(round(paperSize.width(), 2))
            self.paperHeightSpin.setInchValue(round(paperSize.height(), 2))
        self.paperWidthSpin.setEnabled(self.currentPaperSize == 'Custom')
        self.paperHeightSpin.setEnabled(self.currentPaperSize == 'Custom')

    def changeOrient(self, isPortrait):
        """Change the orientation based on a signal.

        Arguments:
            isPortrait -- true if portrait orientation is selected
        """
        self.portraitOrient = isPortrait
        width = self.paperWidthSpin.inchValue
        height = self.paperHeightSpin.inchValue
        if (self.portraitOrient and width > height) or (not self.portraitOrient
                                                        and width < height):
            self.paperWidthSpin.setInchValue(height)
            self.paperHeightSpin.setInchValue(width)

    def saveChanges(self):
        """Update print data with current dialog settings.

        Return True if saved settings have changed, False otherwise.
        """
        if self.currentUnit != globalref.miscOptions.getValue('PrintUnits'):
            globalref.miscOptions.changeValue('PrintUnits', self.currentUnit)
            globalref.miscOptions.writeFile()
        changed = False
        if self.currentPaperSize != 'Custom':
            size = getattr(QtGui.QPrinter, self.currentPaperSize)
            if size != self.printData.printer.paperSize():
                self.printData.printer.setPaperSize(size)
                changed = True
        else:
            size = (self.paperWidthSpin.inchValue,
                    self.paperHeightSpin.inchValue)
            if size != self.printData.roundedPaperSize():
                self.printData.printer.setPaperSize(QtCore.QSizeF(*size),
                                                    QtGui.QPrinter.Inch)
                changed = True
        orient = (QtGui.QPrinter.Portrait if self.portraitOrient else
                  QtGui.QPrinter.Landscape)
        if orient != self.printData.printer.orientation():
            self.printData.printer.setOrientation(orient)
            changed = True
        margins = [control.inchValue for control in self.marginControls]
        if margins != self.printData.roundedMargins():
            margins.append(QtGui.QPrinter.Inch)
            self.printData.printer.setPageMargins(*margins)
            changed = True
        if self.printData.headerMargin != self.headerMarginSpin.inchValue:
            self.printData.headerMargin = self.headerMarginSpin.inchValue
            changed = True
        if self.printData.footerMargin != self.footerMarginSpin.inchValue:
            self.printData.footerMargin = self.footerMarginSpin.inchValue
            changed = True
        if self.printData.numColumns != self.columnSpin.value():
            self.printData.numColumns = self.columnSpin.value()
            changed = True
        if self.printData.columnSpacing != self.columnSpaceSpin.inchValue:
            self.printData.columnSpacing = self.columnSpaceSpin.inchValue
            changed = True
        return changed


class UnitSpinBox(QtGui.QDoubleSpinBox):
    """Spin box with unit suffix that can convert the units of its contents.

    Stores the value at full precision to avoid round-trip rounding errors.
    """
    def __init__(self, unit, parent=None):
        """Create the unit spin box.
        
        Arguments:
            unit -- the original unit (abbreviated string)
            parent -- the parent dialog if given
        """
        super().__init__(parent)
        self.unit = unit
        self.inchValue = 0.0
        self.setupUnit()
        self.valueChanged.connect(self.changeValue)

    def setupUnit(self):
        """Set the suffix, decimal places and maximum based on the unit.
        """
        self.blockSignals(True)
        self.setSuffix(' {0}'.format(self.unit))
        decPlaces = _unitDecimals[self.unit]
        self.setDecimals(decPlaces)
        # set maximum to 5 digits total
        self.setMaximum((10**5 - 1) / 10**decPlaces)
        self.blockSignals(False)

    def changeUnit(self, unit):
        """Change current unit.

        Arguments:
            unit -- the new unit (abbreviated string)
        """
        self.unit = unit
        self.setupUnit()
        self.setInchValue(self.inchValue)

    def setInchValue(self, inchValue):
        """Set box to given value, converted to current unit.

        Arguments:
            inchValue -- the value to set in inches
        """
        self.inchValue = inchValue
        value = self.inchValue * _unitValues[self.unit]
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)
        if value < 4:
            self.setSingleStep(0.1)
        elif value > 50:
            self.setSingleStep(10)
        else:
            self.setSingleStep(1)

    def changeValue(self):
        """Change the stored inch value based on a signal.
        """
        self.inchValue = round(self.value() / _unitValues[self.unit], 2)


class SmallListWidget(QtGui.QListWidget):
    """ListWidget with a smaller size hint"""
    def __init__(self, parent=None):
        QtGui.QListWidget.__init__(self, parent)

    def sizeHint(self):
        """Return smaller width"""
        itemHeight = self.visualItemRect(self.item(0)).height()
        return QtCore.QSize(100, itemHeight * 3)


class FontPage(QtGui.QWidget):
    """Font selection print option dialog page.
    """
    def __init__(self, printData, useSysDfltLabel=False, parent=None):
        """Create the font settings page.

        Arguments:
            printData -- a reference to the PrintData class
            useSysDfltLabel -- default is system if True, o/w TreeLine output
            parent -- the parent dialog
        """
        super().__init__(parent)
        self.printData = printData
        self.currentFont = self.printData.mainFont

        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)
        defaultBox = QtGui.QGroupBox(_('Default Font'))
        topLayout.addWidget(defaultBox)
        defaultLayout = QtGui.QVBoxLayout(defaultBox)
        defaultText = (_('&Use system default font') if useSysDfltLabel else
                       _('&Use TreeLine output view font'))
        self.defaultCheck = QtGui.QCheckBox(defaultText)
        defaultLayout.addWidget(self.defaultCheck)
        self.defaultCheck.setChecked(self.printData.useDefaultFont)
        self.defaultCheck.clicked.connect(self.setFontSelectAvail)

        self.fontBox = QtGui.QGroupBox(_('Select Font'))
        topLayout.addWidget(self.fontBox)
        fontLayout = QtGui.QGridLayout(self.fontBox)
        spacing = fontLayout.spacing()
        fontLayout.setSpacing(0)

        label = QtGui.QLabel(_('&Font'))
        fontLayout.addWidget(label, 0, 0)
        label.setIndent(2)
        self.familyEdit = QtGui.QLineEdit()
        fontLayout.addWidget(self.familyEdit, 1, 0)
        self.familyEdit.setReadOnly(True)
        self.familyList = SmallListWidget()
        fontLayout.addWidget(self.familyList, 2, 0)
        label.setBuddy(self.familyList)
        self.familyEdit.setFocusProxy(self.familyList)
        fontLayout.setColumnMinimumWidth(1, spacing)
        families = [family for family in QtGui.QFontDatabase().families()]
        families.sort(key=str.lower)
        self.familyList.addItems(families)
        self.familyList.currentItemChanged.connect(self.updateFamily)

        label = QtGui.QLabel(_('Font st&yle'))
        fontLayout.addWidget(label, 0, 2)
        label.setIndent(2)
        self.styleEdit = QtGui.QLineEdit()
        fontLayout.addWidget(self.styleEdit, 1, 2)
        self.styleEdit.setReadOnly(True)
        self.styleList = SmallListWidget()
        fontLayout.addWidget(self.styleList, 2, 2)
        label.setBuddy(self.styleList)
        self.styleEdit.setFocusProxy(self.styleList)
        fontLayout.setColumnMinimumWidth(3, spacing)
        self.styleList.currentItemChanged.connect(self.updateStyle)

        label = QtGui.QLabel(_('Si&ze'))
        fontLayout.addWidget(label, 0, 4)
        label.setIndent(2)
        self.sizeEdit = QtGui.QLineEdit()
        fontLayout.addWidget(self.sizeEdit, 1, 4)
        self.sizeEdit.setFocusPolicy(QtCore.Qt.ClickFocus)
        validator = QtGui.QIntValidator(1, 512, self)
        self.sizeEdit.setValidator(validator)
        self.sizeList = SmallListWidget()
        fontLayout.addWidget(self.sizeList, 2, 4)
        label.setBuddy(self.sizeList)
        self.sizeList.currentItemChanged.connect(self.updateSize)

        fontLayout.setColumnStretch(0, 30)
        fontLayout.setColumnStretch(2, 25)
        fontLayout.setColumnStretch(4, 10)

        sampleBox = QtGui.QGroupBox(_('Sample'))
        topLayout.addWidget(sampleBox)
        sampleLayout = QtGui.QVBoxLayout(sampleBox)
        self.sampleEdit = QtGui.QLineEdit()
        sampleLayout.addWidget(self.sampleEdit)
        self.sampleEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.sampleEdit.setText(_('AaBbCcDdEeFfGg...TtUuVvWvXxYyZz'))
        self.sampleEdit.setFixedHeight(self.sampleEdit.sizeHint().height() * 2)

        self.setFontSelectAvail()

    def setFontSelectAvail(self):
        """Disable font selection if default font is checked.

        Also set the controls with the current or default fonts.
        """
        if self.defaultCheck.isChecked():
            font = self.readFont()
            if font:
                self.currentFont = font
            self.setFont(self.printData.defaultFont)
            self.fontBox.setEnabled(False)
        else:
            self.setFont(self.currentFont)
            self.fontBox.setEnabled(True)

    def setFont(self, font):
        """Set the font selector to the given font.
        
        Arguments:
            font -- the QFont to set.
        """
        fontInfo = QtGui.QFontInfo(font)
        family = fontInfo.family()
        matches = self.familyList.findItems(family, QtCore.Qt.MatchExactly)
        if matches:
            self.familyList.setCurrentItem(matches[0])
            self.familyList.scrollToItem(matches[0],
                                         QtGui.QAbstractItemView.PositionAtTop)
        style = QtGui.QFontDatabase().styleString(fontInfo)
        matches = self.styleList.findItems(style, QtCore.Qt.MatchExactly)
        if matches:
            self.styleList.setCurrentItem(matches[0])
            self.styleList.scrollToItem(matches[0])
        size = repr(fontInfo.pointSize())
        matches = self.sizeList.findItems(size, QtCore.Qt.MatchExactly)
        if matches:
            self.sizeList.setCurrentItem(matches[0])
            self.sizeList.scrollToItem(matches[0])

    def updateFamily(self, currentItem, previousItem):
        """Update the family edit box and adjust the style and size options.
        
        Arguments:
            currentItem -- the new list widget family item
            previousItem -- the previous list widget item
        """
        family = currentItem.text()
        self.familyEdit.setText(family)
        if self.familyEdit.hasFocus():
            self.familyEdit.selectAll()
        prevStyle = self.styleEdit.text()
        prevSize = self.sizeEdit.text()
        fontDb = QtGui.QFontDatabase()
        styles = [style for style in fontDb.styles(family)]
        self.styleList.clear()
        self.styleList.addItems(styles)
        if prevStyle:
            try:
                num = styles.index(prevStyle)
            except ValueError:
                num = 0
            self.styleList.setCurrentRow(num)
            self.styleList.scrollToItem(self.styleList.currentItem())
        sizes = [repr(size) for size in fontDb.pointSizes(family)]
        self.sizeList.clear()
        self.sizeList.addItems(sizes)
        if prevSize:
            try:
                num = sizes.index(prevSize)
            except ValueError:
                num = 0
            self.sizeList.setCurrentRow(num)
            self.sizeList.scrollToItem(self.sizeList.currentItem())
            self.updateSample()

    def updateStyle(self, currentItem, previousItem):
        """Update the style edit box.
        
        Arguments:
            currentItem -- the new list widget style item
            previousItem -- the previous list widget item
        """
        if currentItem:
            style = currentItem.text()
            self.styleEdit.setText(style)
            if self.styleEdit.hasFocus():
                self.styleEdit.selectAll()
            self.updateSample()

    def updateSize(self, currentItem, previousItem):
        """Update the size edit box.
        
        Arguments:
            currentItem -- the new list widget size item
            previousItem -- the previous list widget item
        """
        if currentItem:
            size = currentItem.text()
            self.sizeEdit.setText(size)
            if self.sizeEdit.hasFocus():
                self.sizeEdit.selectAll()
            self.updateSample()

    def updateSample(self):
        """Update the font sample edit font.
        """
        font = self.readFont()
        if font:
            self.sampleEdit.setFont(font)

    def readFont(self):
        """Return the selected font or None.
        """
        family = self.familyEdit.text()
        style = self.styleEdit.text()
        size = self.sizeEdit.text()
        if family and style and size:
            return QtGui.QFontDatabase().font(family, style, int(size))
        return None

    def saveChanges(self):
        """Update print data with current dialog settings.

        Return True if saved settings have changed, False otherwise.
        """
        if self.defaultCheck.isChecked():
            if not self.printData.useDefaultFont:
                self.printData.useDefaultFont = True
                self.printData.mainFont = self.printData.defaultFont
                return True
        else:
            font = self.readFont()
            if font and (self.printData.useDefaultFont or
                         font != self.printData.mainFont):
                self.printData.useDefaultFont = False
                self.printData.mainFont = font
                return True
        return False


_headerNames = (_('&Header Left'), _('Header C&enter'), _('Header &Right'))
_footerNames = (_('Footer &Left'), _('Footer Ce&nter'), _('Footer Righ&t'))

class HeaderPage(QtGui.QWidget):
    """Header/footer print option dialog page.
    """
    def __init__(self, printData, parent=None):
        """Create the header/footer settings page.

        Arguments:
            printData -- a reference to the PrintData class
            parent -- the parent dialog
        """
        super().__init__(parent)
        self.printData = printData
        self.focusedEditor = None

        topLayout = QtGui.QGridLayout(self)
        fieldBox = QtGui.QGroupBox(_('Fiel&ds'))
        topLayout.addWidget(fieldBox, 0, 0, 3, 1)
        fieldLayout = QtGui.QVBoxLayout(fieldBox)
        self.fieldListWidget = FieldListWidget()
        fieldLayout.addWidget(self.fieldListWidget)
        fieldFormatButton = QtGui.QPushButton(_('Field For&mat'))
        fieldLayout.addWidget(fieldFormatButton)
        fieldFormatButton.clicked.connect(self.showFieldFormatDialog)

        self.addFieldButton = QtGui.QPushButton('>>')
        topLayout.addWidget(self.addFieldButton, 0, 1)
        self.addFieldButton.setMaximumWidth(self.addFieldButton.sizeHint().
                                            height())
        self.addFieldButton.clicked.connect(self.addField)

        self.delFieldButton = QtGui.QPushButton('<<')
        topLayout.addWidget(self.delFieldButton, 1, 1)
        self.delFieldButton.setMaximumWidth(self.delFieldButton.sizeHint().
                                            height())
        self.delFieldButton.clicked.connect(self.delField)

        headerFooterBox = QtGui.QGroupBox(_('Header and Footer'))
        topLayout.addWidget(headerFooterBox, 0, 2, 2, 1)
        headerFooterLayout = QtGui.QGridLayout(headerFooterBox)
        spacing = headerFooterLayout.spacing()
        headerFooterLayout.setVerticalSpacing(0)
        headerFooterLayout.setRowMinimumHeight(2, spacing)

        self.headerEdits = self.addLineEdits(_headerNames, headerFooterLayout,
                                             0)
        self.footerEdits = self.addLineEdits(_footerNames, headerFooterLayout,
                                             3)
        self.loadContent()

    def addLineEdits(self, names, layout, startRow):
        """Add line edits for header or footer.

        Return a list of line edits added to the top layout.
        Arguments:
            names -- a list of label names
            layout -- the grid layout t use
            startRow -- the initial row number
        """
        lineEdits = []
        for num, name in enumerate(names):
            label = QtGui.QLabel(name)
            layout.addWidget(label, startRow, num)
            lineEdit = configdialog.TitleEdit()
            layout.addWidget(lineEdit, startRow + 1, num)
            label.setBuddy(lineEdit)
            lineEdit.cursorPositionChanged.connect(self.setControlAvailability)
            lineEdit.focusIn.connect(self.setCurrentEditor)
            lineEdits.append(lineEdit)
        return lineEdits

    def loadContent(self):
        """Load field names and header/footer text into the controls.
        """
        self.fieldListWidget.addItems(self.printData.localControl.model.
                                      formats.fileInfoFormat.fieldNames())
        self.fieldListWidget.setCurrentRow(0)
        for text, lineEdit in zip(splitHeaderFooter(self.printData.headerText),
                                  self.headerEdits):
            lineEdit.blockSignals(True)
            lineEdit.setText(text)
            lineEdit.blockSignals(False)
        for text, lineEdit in zip(splitHeaderFooter(self.printData.footerText),
                                  self.footerEdits):
            lineEdit.blockSignals(True)
            lineEdit.setText(text)
            lineEdit.blockSignals(False)
        self.focusedEditor = self.headerEdits[0]
        self.headerEdits[0].setFocus()
        self.setControlAvailability()

    def setControlAvailability(self):
        """Set controls available based on text cursor movements.
        """
        cursorInField = self.isCursorInField()
        self.addFieldButton.setEnabled(cursorInField == None)
        self.delFieldButton.setEnabled(cursorInField == True)

    def setCurrentEditor(self, sender):
        """Set focusedEditor based on editor focus change signal.

        Arguments:
            sender -- the line editor to focus
        """
        self.focusedEditor = sender
        self.setControlAvailability()

    def isCursorInField(self, selectField=False):
        """Return True if a field pattern encloses the cursor/selection.

        Return False if the selection overlaps a field.
        Return None if there is no field at the cursor.
        Arguments:
            selectField -- select the entire field pattern if True.
        """
        cursorPos = self.focusedEditor.cursorPosition()
        selectStart = self.focusedEditor.selectionStart()
        if selectStart < 0:
            selectStart = cursorPos
        elif selectStart == cursorPos:   # backward selection
            cursorPos += len(self.focusedEditor.selectedText())
        textLine = self.focusedEditor.text()
        for match in configdialog.fieldPattern.finditer(textLine):
            start = (match.start() if match.start() < selectStart < match.end()
                     else None)
            end = (match.end() if match.start() < cursorPos < match.end()
                   else None)
            if start != None and end != None:
                if selectField:
                    self.focusedEditor.setSelection(start, end - start)
                return True
            if start != None or end != None:
                return False
        return None

    def addField(self):
        """Add selected field to cursor pos in current line editor.
        """
        fieldName = self.fieldListWidget.currentItem().text()
        self.focusedEditor.insert('{{*!{0}*}}'.format(fieldName))
        self.focusedEditor.setFocus()

    def delField(self):
        """Remove field from cursor pos in current line editor.
        """
        if self.isCursorInField(True):
            self.focusedEditor.insert('')
            self.focusedEditor.setFocus()

    def showFieldFormatDialog(self):
        """Show thw dialog used to set file info field formats.
        """
        fileInfoFormat = (self.printData.localControl.model.formats.
                          fileInfoFormat)
        fieldName = self.fieldListWidget.currentItem().text()
        field = fileInfoFormat.fieldDict[fieldName]
        dialog = HeaderFieldFormatDialog(field, self.printData.localControl,
                                         self)
        dialog.exec_()

    def saveChanges(self):
        """Update print data with current dialog settings.

        Return True if saved settings have changed, False otherwise.
        """
        changed = False
        headerList = [lineEdit.text().replace('/', r'\/') for lineEdit in
                      self.headerEdits]
        while len(headerList) > 1 and not headerList[-1]:
            del headerList[-1]
        text = '/'.join(headerList)
        if self.printData.headerText != text:
            self.printData.headerText = text
            changed = True
        footerList = [lineEdit.text().replace('/', r'\/') for lineEdit in
                      self.footerEdits]
        while len(footerList) > 1 and not footerList[-1]:
            del footerList[-1]
        text = '/'.join(footerList)
        if self.printData.footerText != text:
            self.printData.footerText = text
            changed = True
        return changed


class FieldListWidget(QtGui.QListWidget):
    """List widget for fields with smaller width size hint.
    """
    def __init__(self, parent=None):
        """Create the list widget.

        Arguments:
            parent -- the parent dialog
        """
        super().__init__(parent)

    def sizeHint(self):
        """Return a size with a smaller width.
        """
        return QtCore.QSize(120, 100)


class HeaderFieldFormatDialog(QtGui.QDialog):
    """Dialog to modify file info field formats used in headers and footers.
    """
    def __init__(self, field, localControl, parent=None):
        """Create the field format dialog.

        Arguments:
            field -- the field to be modified
            localControl -- a ref to the control to save changes and undo
        """
        super().__init__(parent)
        self.field = field
        self.localControl = localControl

        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)
        self.setWindowTitle(_('Field Format for "{0}"').format(field.name))
        topLayout = QtGui.QVBoxLayout(self)
        self.setLayout(topLayout)

        self.formatBox = QtGui.QGroupBox(_('Output &Format'))
        topLayout.addWidget(self.formatBox)
        formatLayout = QtGui.QHBoxLayout(self.formatBox)
        self.formatEdit = QtGui.QLineEdit()
        formatLayout.addWidget(self.formatEdit)
        self.helpButton = QtGui.QPushButton(_('Format &Help'))
        formatLayout.addWidget(self.helpButton)
        self.helpButton.clicked.connect(self.formatHelp)

        extraBox = QtGui.QGroupBox(_('Extra Text'))
        topLayout.addWidget(extraBox)
        extraLayout = QtGui.QVBoxLayout(extraBox)
        spacing = extraLayout.spacing()
        extraLayout.setSpacing(0)
        prefixLabel = QtGui.QLabel(_('&Prefix'))
        extraLayout.addWidget(prefixLabel)
        self.prefixEdit = QtGui.QLineEdit()
        extraLayout.addWidget(self.prefixEdit)
        prefixLabel.setBuddy(self.prefixEdit)
        extraLayout.addSpacing(spacing)
        suffixLabel = QtGui.QLabel(_('&Suffix'))
        extraLayout.addWidget(suffixLabel)
        self.suffixEdit = QtGui.QLineEdit()
        extraLayout.addWidget(self.suffixEdit)
        suffixLabel.setBuddy(self.suffixEdit)

        ctrlLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        okButton = QtGui.QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

        self.prefixEdit.setText(self.field.prefix)
        self.suffixEdit.setText(self.field.suffix)
        self.formatEdit.setText(self.field.format)

        self.formatBox.setEnabled(self.field.defaultFormat != '')

    def formatHelp(self):
        """Provide a format help menu based on a button signal.
        """
        menu = QtGui.QMenu(self)
        self.formatHelpDict = {}
        for descript, key in self.field.getFormatHelpMenuList():
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

    def accept(self):
        """Set changes after OK is hit"""
        prefix = self.prefixEdit.text()
        suffix = self.suffixEdit.text()
        format = self.formatEdit.text()
        if (self.field.prefix != prefix or self.field.suffix != suffix or
            self.field.format != format):
            undo.FormatUndo(self.localControl.model.undoList,
                            self.localControl.model.formats,
                            treeformats.TreeFormats())
            self.field.prefix = prefix
            self.field.suffix = suffix
            self.field.format = format
            self.localControl.setModified()
        super().accept()


_headerSplitRe = re.compile(r'(?<!\\)/')

def splitHeaderFooter(combinedText):
    """Return a list of header/footer parts from the text, separated by "/".

    Backslash escapes avoid splits.
    Arguments:
        combinedText -- the text to split
    """
    textList = _headerSplitRe.split(combinedText)
    return [text.replace(r'\/', '/') for text in textList]
