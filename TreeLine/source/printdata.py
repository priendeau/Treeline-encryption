#!/usr/bin/env python3

#******************************************************************************
# printdata.py, provides a class for printing
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
from PyQt4 import QtCore, QtGui
import treeoutput
import printdialogs
import globalref

entireTree, selectBranch, selectNode = range(3)


class PrintData:
    """Class to handle printing of tree output data.
    
    Stores print data and main printing functions.
    """
    def __init__(self, localControl):
        """Initialize the print data.

        Arguments:
            localControl -- a reference to the parent local control
        """
        self.localControl = localControl
        self.outputGroup = None
        self.printWhat = entireTree
        self.includeRoot = True
        self.openOnly = False
        self.printer = QtGui.QPrinter(QtGui.QPrinter.HighResolution)
        self.setDefaults()
        self.adjustSpacing()

    def setDefaults(self):
        """Set all paparmeters saved in TreeLine files to default values.
        """
        self.drawLines = True
        self.widowControl = True
        self.indentFactor = 2.0
        self.printer.setPaperSize(QtGui.QPrinter.Letter)
        self.printer.setOrientation(QtGui.QPrinter.Portrait)
        self.printer.setPageMargins(0.5, 0.5, 0.5, 0.5, QtGui.QPrinter.Inch)
        self.headerMargin = 0.2
        self.footerMargin = 0.2
        self.numColumns = 1
        self.columnSpacing = 0.5
        self.headerText = ''
        self.footerText = ''
        self.useDefaultFont = True
        self.setDefaultFont()

    def setDefaultFont(self):
        """Set the default font initially and based on an output font change.
        """
        self.defaultFont = QtGui.QTextDocument().defaultFont()
        fontName = globalref.miscOptions.getValue('OutputFont')
        if fontName:
            self.defaultFont.fromString(fontName)
        if self.useDefaultFont:
            self.mainFont = self.defaultFont

    def adjustSpacing(self):
        """Adjust line spacing & indent size based on font & indent factor.
        """
        self.lineSpacing = QtGui.QFontMetrics(self.mainFont,
                                              self.printer).lineSpacing()
        self.indentSize = self.indentFactor * self.lineSpacing

    def xmlAttr(self):
        """Return a dictionary of non-default settings for storage.
        """
        attrs = {}
        if not self.drawLines:
            attrs['printlines'] = 'n'
        if not self.widowControl:
            attrs['printwidowcontrol'] = 'n'
        if self.indentFactor != 2.0:
            attrs['printindentfactor'] = repr(self.indentFactor)
        if self.printer.paperSize() == QtGui.QPrinter.Custom:
            paperWidth, paperHeight = self.roundedPaperSize()
            attrs['printpaperwidth'] = repr(paperWidth)
            attrs['printpaperheight'] = repr(paperHeight)
        elif self.printer.paperSize() != QtGui.QPrinter.Letter:
            paperSizeDict = dict((num, attrib) for attrib, num in
                                 vars(QtGui.QPrinter).items()
                                 if isinstance(num, QtGui.QPrinter.PageSize))
            attrs['printpapersize'] = paperSizeDict[self.printer.paperSize()]
        if self.printer.orientation() != QtGui.QPrinter.Portrait:
            attrs['printportrait'] = 'n'
        if self.roundedMargins() != [0.5] * 4:
            attrs['printmargins'] = ' '.join([repr(margin) for margin in
                                              self.roundedMargins()])
        if self.headerMargin != 0.2:
            attrs['printheadermargin'] = repr(self.headerMargin)
        if self.footerMargin != 0.2:
            attrs['printfootermargin'] = repr(self.footerMargin)
        if self.numColumns > 1:
            attrs['printnumcolumns'] = repr(self.numColumns)
        if self.columnSpacing != 0.5:
            attrs['printcolumnspace'] = repr(self.columnSpacing)
        if self.headerText:
            attrs['printheadertext'] = self.headerText
        if self.footerText:
            attrs['printfootertext'] = self.footerText
        if not self.useDefaultFont:
            attrs['printfont'] = self.mainFont.toString()
        return attrs

    def restoreXmlAttrs(self, attrs):
        """Restore saved settings from a dictionary.

        Arguments:
            attrs -- a dictionary of stored non-default settings
        """
        self.setDefaults()   # necessary for undo/redo
        if attrs.get('printlines', '').startswith('n'):
            self.drawLines = False
        if attrs.get('printwidowcontrol', '').startswith('n'):
            self.widowControl = False
        if 'printindentfactor' in attrs:
            self.indentFactor = float(attrs['printindentfactor'])
        if 'printpapersize' in attrs:
            self.printer.setPaperSize(getattr(QtGui.QPrinter,
                                              attrs['printpapersize']))
        if 'printpaperwidth' in attrs and 'printpaperheight' in attrs:
            width =  float(attrs['printpaperwidth'])
            height = float(attrs['printpaperheight'])
            self.printer.setPaperSize(QtCore.QSizeF(width, height),
                                      QtGui.QPrinter.Inch)
        if attrs.get('printportrait', '').startswith('n'):
            self.printer.setOrientation(QtGui.QPrinter.Landscape)
        if 'printmargins' in attrs:
            margins = [float(margin) for margin in
                       attrs['printmargins'].split()]
            margins.append(QtGui.QPrinter.Inch)
            self.printer.setPageMargins(*margins)
        if 'printheadermargin' in attrs:
            self.headerMargin = float(attrs['printheadermargin'])
        if 'printfootermargin' in attrs:
            self.footerMargin = float(attrs['printfootermargin'])
        if 'printnumcolumns' in attrs:
            self.numColumns = int(attrs['printnumcolumns'])
        if 'printcolumnspace' in attrs:
            self.columnSpacing = float(attrs['printcolumnspace'])
        self.headerText = attrs.get('printheadertext', '')
        self.footerText = attrs.get('printfootertext', '')
        if 'printfont' in attrs:
            self.useDefaultFont = False
            self.mainFont.fromString(attrs['printfont'])
        self.adjustSpacing()

    def roundedMargins(self):
        """Return a list of rounded page margins in inches.

        Rounds to nearest .01" to avoid Qt unit conversion artifacts.
        """
        return [round(margin, 2) for margin in
                self.printer.getPageMargins(QtGui.QPrinter.Inch)]

    def roundedPaperSize(self):
        """Return a tuple of rounded paper width and height.

        Rounds to nearest .01" to avoid Qt unit conversion artifacts.
        """
        size = self.printer.paperSize(QtGui.QPrinter.Inch)
        return (round(size.width(), 2), round(size.height(), 2))

    def setupData(self):
        """Load data to be printed and set page info.
        """
        if self.printWhat == entireTree:
            selNodes = [self.localControl.model.root]
        else:
            selNodes = (self.localControl.currentSelectionModel().
                        selectedNodes())
        self.outputGroup = treeoutput.OutputGroup(selNodes, self.includeRoot,
                                                  self.printWhat != selectNode,
                                                  self.openOnly)
        self.paginate()

    def paginate(self):
        """Define the pages and locations of output items and set page range.
        """
        pageNum = 1
        columnNum = 0
        pagePos = 0
        heightAvail = self.printer.pageRect().height()
        columnSpacing = int(self.columnSpacing * self.printer.logicalDpiX())
        widthAvail = ((self.printer.pageRect().width() -
                       columnSpacing * (self.numColumns - 1)) //
                      self.numColumns)
        newGroup = treeoutput.OutputGroup([])
        while self.outputGroup:
            item = self.outputGroup.pop(0)
            widthRemain = widthAvail - item.level * self.indentSize
            if pagePos != 0 and (newGroup[-1].addSpace or item.addSpace):
                pagePos += self.lineSpacing
            if item.siblingPrefix:
                siblings = treeoutput.OutputGroup([])
                siblings.append(item)
                while True:
                    item = siblings.combineLines()
                    item.setDocHeight(self.printer, widthRemain, self.mainFont,
                                      True)
                    if pagePos + item.height > heightAvail:
                        self.outputGroup.insert(0, siblings.pop())
                        item = (siblings.combineLines() if siblings else
                                None)
                        break
                    if (self.outputGroup and
                        item.level == self.outputGroup[0].level and
                        item.equalPrefix(self.outputGroup[0])):
                        siblings.append(self.outputGroup.pop(0))
                    else:
                        break
            if item:
                item.setDocHeight(self.printer, widthRemain, self.mainFont,
                                  True)
                if item.height > heightAvail:
                    item, newItem = item.splitDocHeight(heightAvail - pagePos,
                                                        heightAvail,
                                                        self.printer,
                                                        widthRemain,
                                                        self.mainFont)
                    if newItem:
                        self.outputGroup.insert(0, newItem)
            if item and pagePos + item.height <= heightAvail:
                item.pageNum = pageNum
                item.columnNum = columnNum
                item.pagePos = pagePos
                newGroup.append(item)
                pagePos += item.height
            else:
                if columnNum + 1 < self.numColumns:
                    columnNum += 1
                else:
                    pageNum += 1
                    columnNum = 0
                pagePos = 0
                if item:
                    self.outputGroup.insert(0, item)
                    if self.widowControl and not item.siblingPrefix:
                        moveItems = []
                        moveHeight = 0
                        level = item.level
                        while (newGroup and not newGroup[-1].siblingPrefix and
                               newGroup[-1].level == level - 1 and
                               ((newGroup[-1].pageNum == pageNum - 1 and
                                 newGroup[-1].columnNum == columnNum) or
                                (newGroup[-1].pageNum == pageNum and
                                newGroup[-1].columnNum == columnNum - 1))):
                            moveItems.insert(0, newGroup.pop())
                            moveHeight += moveItems[0].height
                            level -= 1
                        if moveItems and moveHeight < (heightAvail // 5):
                            self.outputGroup[0:0] = moveItems
                        else:
                            newGroup.extend(moveItems)
        self.outputGroup = newGroup
        self.outputGroup.loadFamilyRefs()
        self.printer.setFromTo(1, pageNum)

    def paintData(self, printer):
        """Paint data to be printed to the printer.
        """
        pageNum = 1
        maxPageNum = self.outputGroup[-1].pageNum
        if self.printer.printRange() != QtGui.QPrinter.AllPages:
            pageNum = self.printer.fromPage()
            maxPageNum = self.printer.toPage()
        painter = QtGui.QPainter()
        if not painter.begin(self.printer):
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                   'TreeLine', _('Error initializing printer'))
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        while True:
            self.paintPage(pageNum, painter)
            if pageNum == maxPageNum:
                QtGui.QApplication.restoreOverrideCursor()
                return
            pageNum += 1
            self.printer.newPage()

    def paintPage(self, pageNum, painter):
        """Paint data for the given page to the printer.

        Arguments:
            pageNum -- the page number to be printed
            painter -- the painter for this print job
        """
        totalNumPages = self.outputGroup[-1].pageNum
        headerDoc = self.headerFooterDoc(True, pageNum, totalNumPages)
        if headerDoc:
            layout = headerDoc.documentLayout()
            layout.setPaintDevice(self.printer)
            headerDoc.setTextWidth(self.printer.pageRect().width())
            painter.save()
            topMargin = self.printer.getPageMargins(QtGui.QPrinter.Inch)[1]
            headerDelta = ((self.headerMargin - topMargin) *
                           self.printer.logicalDpiX())
            painter.translate(0, int(headerDelta))
            layout.draw(painter,
                        QtGui.QAbstractTextDocumentLayout.PaintContext())
            painter.restore()
        painter.save()
        columnSpacing = int(self.columnSpacing * self.printer.logicalDpiX())
        columnDelta = ((self.printer.pageRect().width() -
                        columnSpacing * (self.numColumns - 1)) /
                       self.numColumns) + columnSpacing
        for columnNum in range(self.numColumns):
            if columnNum > 0:
                painter.translate(columnDelta, 0)
            self.paintColumn(pageNum, columnNum, painter)
        painter.restore()
        footerDoc = self.headerFooterDoc(False, pageNum, totalNumPages)
        if footerDoc:
            layout = footerDoc.documentLayout()
            layout.setPaintDevice(self.printer)
            footerDoc.setTextWidth(self.printer.pageRect().width())
            painter.save()
            bottomMargin = self.printer.getPageMargins(QtGui.QPrinter.Inch)[3]
            footerDelta = ((bottomMargin - self.footerMargin) *
                           self.printer.logicalDpiX())
            painter.translate(0, self.printer.pageRect().height() +
                                 int(footerDelta) - self.lineSpacing)
            layout.draw(painter,
                        QtGui.QAbstractTextDocumentLayout.PaintContext())
            painter.restore()

    def paintColumn(self, pageNum, columnNum, painter):
        """Paint data for the given column to the printer.

        Arguments:
            pageNum -- the page number to be printed
            columnNum -- the column number to be printed
            painter -- the painter for this print job
        """
        columnItems = [item for item in self.outputGroup if
                       item.pageNum == pageNum and item.columnNum == columnNum]
        for item in columnItems:
            layout = item.doc.documentLayout()
            painter.save()
            painter.translate(item.level * self.indentSize, item.pagePos)
            layout.draw(painter,
                        QtGui.QAbstractTextDocumentLayout.PaintContext())
            painter.restore()
        if self.drawLines:
            self.addPrintLines(pageNum, columnNum, columnItems, painter)

    def addPrintLines(self, pageNum, columnNum, columnItems, painter):
        """Paint lines between parent and child items on the page.

        Arguments:
            pageNum -- the page number to be printed
            columnNum -- the column number to be printed
            columnItems -- a list of items in this column
            painter -- the painter for this print job
        """
        parentsDrawn = set()
        horizOffset = self.indentSize // 2
        vertOffset = self.lineSpacing // 2
        heightAvail = self.printer.pageRect().height()
        for item in columnItems:
            if item.level > 0:
                indent = item.level * self.indentSize
                vertPos = item.pagePos + vertOffset
                painter.drawLine(indent - horizOffset, vertPos,
                                 indent - self.lineSpacing // 4, vertPos)
                parent = item.parentItem
                while parent:
                    if parent in parentsDrawn:
                        break
                    lineStart = 0
                    lineEnd = heightAvail
                    if (parent.pageNum == pageNum and
                        parent.columnNum == columnNum):
                        lineStart = parent.pagePos + parent.height
                    if (parent.lastChildItem.pageNum == pageNum and
                        parent.lastChildItem.columnNum == columnNum):
                        lineEnd = parent.lastChildItem.pagePos + vertOffset
                    if (parent.lastChildItem.pageNum > pageNum or
                        (parent.lastChildItem.pageNum == pageNum and
                         parent.lastChildItem.columnNum >= columnNum)):
                        horizPos = ((parent.level + 1) * self.indentSize -
                                    horizOffset)
                        painter.drawLine(horizPos, lineStart,
                                         horizPos, lineEnd)
                    parentsDrawn.add(parent)
                    parent = parent.parentItem

    def formatHeaderFooter(self, header=True, pageNum=1, numPages=1):
        """Return an HTML table formatted header or footer.

        Return an empty string if no header/footer is defined.
        Arguments:
            header -- return header if True, footer if false
        """
        if header:
            textParts = printdialogs.splitHeaderFooter(self.headerText)
        else:
            textParts = printdialogs.splitHeaderFooter(self.footerText)
        if not textParts:
            return ''
        fileInfoFormat = self.localControl.model.formats.fileInfoFormat
        fileInfoNode = self.localControl.model.fileInfoNode
        fileInfoFormat.updateFileInfo(self.localControl.filePath, fileInfoNode)
        fileInfoNode.data[fileInfoFormat.pageNumFieldName] = repr(pageNum)
        fileInfoNode.data[fileInfoFormat.numPagesFieldName] = repr(numPages)
        fileInfoFormat.changeOutputLines(textParts, keepBlanks=True)
        textParts = fileInfoFormat.formatOutput(fileInfoNode, keepBlanks=True)
        alignments = ('left', 'center', 'right')
        result = ['<table width="100%"><tr>']
        for text, align in zip(textParts, alignments):
            if text:
                result.append('<td align="{0}">{1}</td>'.format(align, text))
        if len(result) > 1:
            result.append('</tr></table>')
            return '\n'.join(result)
        return ''

    def headerFooterDoc(self, header=True, pageNum=1, numPages=1):
        """Return a text document for the header or footer.

        Return None if no header/footer is defined.
        Arguments:
            header -- return header if True, footer if false
        """
        text = self.formatHeaderFooter(header, pageNum, numPages)
        if text:
            doc = QtGui.QTextDocument()
            doc.setHtml(text)
            doc.setDefaultFont(self.mainFont)
            frameFormat = doc.rootFrame().frameFormat()
            frameFormat.setBorder(0)
            frameFormat.setMargin(0)
            frameFormat.setPadding(0)
            doc.rootFrame().setFrameFormat(frameFormat)
            return doc
        return None

    def printSetup(self):
        """Show a dialog to set margins, page size and other printing options.
        """
        setupDialog = printdialogs.PrintSetupDialog(self, True,
                                                    QtGui.QApplication.
                                                    activeWindow())
        setupDialog.exec_()

    def printPreview(self):
        """Show a preview of printing results.
        """
        self.setupData()
        previewDialog = printdialogs.PrintPreviewDialog(self,
                                                        QtGui.QApplication.
                                                        activeWindow())
        previewDialog.previewWidget.paintRequested.connect(self.paintData)
        if globalref.genOptions.getValue('SaveWindowGeom'):
            previewDialog.restoreDialogGeom()
        previewDialog.exec_()

    def filePrint(self):
        """Show dialog and print tree output based on current options.
        """
        self.setupData()
        printDialog = QtGui.QPrintDialog(self.printer,
                                         QtGui.QApplication.activeWindow())
        if printDialog.exec_() == QtGui.QDialog.Accepted:
            self.paintData(self.printer)

    def filePrintPdf(self):
        """Export to a PDF file with current options.
        """
        filters = ';;'.join((globalref.fileFilters['pdf'],
                             globalref.fileFilters['all']))
        defaultFilePath = globalref.mainControl.defaultFilePath()
        defaultFilePath = os.path.splitext(defaultFilePath)[0]
        if os.path.basename(defaultFilePath):
            defaultFilePath = '{0}.{1}'.format(defaultFilePath, 'pdf')
        filePath = QtGui.QFileDialog.getSaveFileName(QtGui.QApplication.
                                                    activeWindow(),
                                                    _('TreeLine - Export PDF'),
                                                    defaultFilePath, filters)
        if not filePath:
            return
        if not os.path.splitext(filePath)[1]:
            filePath = '{0}.{1}'.format(filePath, 'pdf')
        self.printer.setOutputFormat(QtGui.QPrinter.PdfFormat)
        self.printer.setOutputFileName(filePath)
        self.adjustSpacing()
        self.setupData()
        self.paintData(self.printer)
        self.printer.setOutputFormat(QtGui.QPrinter.NativeFormat)
        self.printer.setOutputFileName('')
        self.adjustSpacing()
