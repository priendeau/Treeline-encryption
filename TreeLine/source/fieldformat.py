#!/usr/bin/env python3

#******************************************************************************
# fieldformat.py, provides a class to handle field format types
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
import os.path
import xml.sax.saxutils
from PyQt4 import QtCore, QtGui
import globalref
import gennumber
import genboolean
import numbering
import dataeditors
import matheval
import urltools

fieldTypes = [N_('Text'), N_('HtmlText'), N_('OneLineText'), N_('SpacedText'),
              N_('Number'), N_('Math'), N_('Numbering'), N_('Boolean'),
              N_('Date'), N_('Time'), N_('Choice'), N_('AutoChoice'),
              N_('Combination'), N_('AutoCombination'), N_('ExternalLink'),
              N_('InternalLink'), N_('Picture'), N_('RegularExpression')]
_errorStr = '#####'
_dateStampString = _('Now')
_timeStampString = _('Now')
numericResult, dateResult, timeResult, booleanResult, textResult = range(5)
mathResultStr = {numericResult: 'numeric', dateResult: 'date',
                 timeResult: 'time', booleanResult: 'boolean',
                 textResult: 'text'}
mathResultVar = {mathResultStr[key]: key for key in mathResultStr}
_mathResultBlank = {numericResult: 0, dateResult: 0, timeResult: 0,
                    booleanResult: False, textResult: ''}
linkRegExp = re.compile(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
linkSeparateNameRegExp = re.compile(r'(.*?)\[(.*)\]')
imageRegExp = re.compile(r'<img [^>]*src="([^"]+)"[^>]*>', re.I | re.S)


class TextField:
    """Class to handle a rich-text field format type.
    
    Stores options and format strings for a text field type.
    Provides methods to return formatted data.
    """
    typeName = 'Text'
    defaultFormat = ''
    useRichText = True
    defaultNumLines = 1
    editorClass = dataeditors.RichTextEditor
    formatHelpMenuList = []
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        self.name = name
        if not attrs:
            attrs = {}
        self.setFormat(attrs.get('format', type(self).defaultFormat))
        self.prefix = attrs.get('prefix', '')
        self.suffix = attrs.get('suffix', '')
        self.initDefault = attrs.get('init', '')
        self.numLines = int(attrs.get('lines', type(self).defaultNumLines))
        self.sortKeyNum = int(attrs.get('sortkeynum', '0'))
        self.sortKeyForward = not attrs.get('sortkeydir', '').startswith('r')
        self.useFileInfo = False
        self.showInDialog = True
        # following lines used to convert from old TreeLine 1.x versions only:
        self.oldHasHtml = attrs.get('html', '').startswith('y')
        self.oldRef = attrs.get('ref', '').startswith('y')
        self.oldLinkAltField = attrs.get('linkalt', '')
        self.oldTypeName = ''
        attrType = attrs.get('type', '')
        if attrType and attrType != self.typeName:
            self.oldTypeName = attrType

    def setFormat(self, format):
        """Set the format string and initialize as required.

        Derived classes may raise a ValueError if the format is illegal.
        Arguments:
            format -- the new format string
        """
        self.format = format

    def outputText(self, node, titleMode, formatHtml):
        """Return formatted output text for this field in this node.

        Arguments:
            node -- the tree item storing the data
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        if self.useFileInfo:
            node = node.modelRef.fileInfoNode
        storedText = node.data.get(self.name, '')
        if storedText:
            return self.formatOutput(storedText, titleMode, formatHtml)
        return ''

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        prefix = self.prefix
        suffix = self.suffix
        if titleMode:
            storedText = removeMarkup(storedText)
            if formatHtml:
                prefix = removeMarkup(prefix)
                suffix = removeMarkup(suffix)
        elif not formatHtml:
            prefix = xml.sax.saxutils.escape(prefix)
            suffix = xml.sax.saxutils.escape(suffix)
        return '{0}{1}{2}'.format(prefix, storedText, suffix)

    def editorText(self, node):
        """Return text formatted for use in the data editor.

        The function for default text just returns the stored text.
        Overloads may raise a ValueError if the data does not match the format.
        Arguments:
            node -- the tree item storing the data
        """
        storedText = node.data.get(self.name, '')
        return self.formatEditorText(storedText)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        The function for default text just returns the stored text.
        Overloads may raise a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        return storedText

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        The function for default text field just returns the editor text.
        Overloads may raise a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        return editorText

    def getInitDefault(self):
        """Return the initial stored value for newly created nodes.
        """
        return self.initDefault

    def setInitDefault(self, editorText):
        """Set the default initial value from editor text.

        The function for default text field just returns the stored text.
        Arguments:
            editorText -- the new text entered into the editor
        """
        self.initDefault = self.storedText(editorText)

    def getEditorInitDefault(self):
        """Return initial value in editor format.

        The function for default text field just returns the initial value.
        """
        return self.formatEditorText(self.initDefault)

    def initDefaultChoices(self):
        """Return a list of choices for setting the init default.
        """
        return []

    def xmlAttr(self):
        """Return a dictionary of this field's attributes.
        """
        attrs = {'type': self.typeName}
        if self.format:
            attrs['format'] = self.format
        if self.prefix:
            attrs['prefix'] = self.prefix
        if self.suffix:
            attrs['suffix'] = self.suffix
        if self.initDefault:
            attrs['init'] = self.initDefault
        if self.numLines != self.defaultNumLines:
            attrs['lines'] = repr(self.numLines)
        if self.sortKeyNum > 0:
            attrs['sortkeynum'] = repr(self.sortKeyNum)
            if not self.sortKeyForward:
                attrs['sortkeydir'] = 'r'
        return attrs

    def mathValue(self, node, zeroBlanks=True):
        """Return a value to be used in math field equations.

        Return None if blank and not zeroBlanks.
        Arguments:
            node -- the tree item storing the data
            zeroBlanks -- accept blank field values if True
        """
        storedText = node.data.get(self.name, '')
        storedText = removeMarkup(storedText)
        return storedText if storedText or zeroBlanks else None

    def compareValue(self, node):
        """Return a value for comparison to other nodes and for sorting.

        Returns lowercase text for text fields or numbers for non-text fields.
        Arguments:
            node -- the tree item storing the data
        """
        storedText = node.data.get(self.name, '')
        storedText = removeMarkup(storedText)
        return storedText.lower()

    def sortKey(self, node):
        """Return a tuple with field type and comparison value for sorting.

        Allows different types to be sorted.
        Arguments:
            node -- the tree item storing the data
        """
        return ('80_text', self.compareValue(node))

    def adjustedCompareValue(self, value):
        """Return value adjusted like the compareValue for use in conditionals.

        Text version removes any markup and goes to lower case.
        Arguments:
            value -- the comparison value to adjust
        """
        value = removeMarkup(value)
        return value.lower()

    def changeType(self, newType):
        """Change this field's type to newType with a default format.

        Arguments:
            newType -- the new type name, excluding "Field"
        """
        self.__class__ = globals()[newType + 'Field']
        self.setFormat(self.defaultFormat)

    def sepName(self):
        """Return the name enclosed with {* *} separators
        """
        if self.useFileInfo:
            return '{{*!{0}*}}'.format(self.name)
        return '{{*{0}*}}'.format(self.name)

    def getFormatHelpMenuList(self):
        """Return the list of descriptions and keys for the format help menu.
        """
        return self.formatHelpMenuList


class HtmlTextField(TextField):
    """Class to handle an HTML text field format type
    
    Stores options and format strings for an HTML text field type.
    Does not use the rich text editor.
    Provides methods to return formatted data.
    """
    typeName = 'HtmlText'
    useRichText = False
    editorClass = dataeditors.HtmlTextEditor
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)


class OneLineTextField(TextField):
    """Class to handle a single-line rich-text field format type.

    Stores options and format strings for a text field type.
    Provides methods to return formatted data.
    """
    typeName = 'OneLineText'
    editorClass = dataeditors.OneLineTextEditor
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        text = storedText.split('<br />', 1)[0]
        return super().formatOutput(text, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        return storedText.split('<br />', 1)[0]


class SpacedTextField(HtmlTextField):
    """Class to handle a preformatted text field format type.
    
    Stores options and format strings for a spaced text field type.
    Uses <pre> tags to preserve spacing.
    Does not use the rich text editor.
    Provides methods to return formatted data.
    """
    typeName = 'SpacedText'
    editorClass = dataeditors.PlainTextEditor
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        if storedText:
            storedText = '<pre>{0}</pre>'.format(storedText)
        return super().formatOutput(storedText, titleMode, formatHtml)


class NumberField(HtmlTextField):
    """Class to handle a general number field format type.

    Stores options and format strings for a number field type.
    Provides methods to return formatted data.
    """
    typeName = 'Number'
    defaultFormat = '#.##'
    editorClass = dataeditors.LineEditor
    formatHelpMenuList = [(_('Optional Digit\t#'), '#'),
                          (_('Required Digit\t0'), '0'),
                          (_('Digit or Space (external)\t<space>'), ' '),
                          ('', ''),
                          (_('Decimal Point\t.'), '.'),
                          (_('Decimal Comma\t,'), ','),
                          ('', ''),
                          (_('Comma Separator\t\,'), '\,'),
                          (_('Dot Separator\t\.'), '\.'),
                          (_('Space Separator (internal)\t<space>'), ' '),
                          ('', ''),
                          (_('Optional Sign\t-'), '-'),
                          (_('Required Sign\t+'), '+'),
                          ('', ''),
                          (_('Exponent (capital)\tE'), 'E'),
                          (_('Exponent (small)\te'), 'e')]

    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        try:
            text = gennumber.GenNumber(storedText).numStr(self.format)
        except ValueError:
            text = _errorStr
        return super().formatOutput(text, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if not storedText:
            return ''
        return gennumber.GenNumber(storedText).numStr(self.format)

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if not editorText:
            return ''
        return repr(gennumber.GenNumber().setFromStr(editorText, self.format))

    def mathValue(self, node, zeroBlanks=True):
        """Return a numeric value to be used in math field equations.

        Return None if blank and not zeroBlanks,
        raise a ValueError if it isn't a number.
        Arguments:
            node -- the tree item storing the data
            zeroBlanks -- replace blank field values with zeros if True
        """
        storedText = node.data.get(self.name, '')
        if storedText:
            return gennumber.GenNumber(storedText).num
        return 0 if zeroBlanks else None

    def compareValue(self, node):
        """Return a value for comparison to other nodes and for sorting.

        Returns lowercase text for text fields or numbers for non-text fields.
        Arguments:
            node -- the tree item storing the data
        """
        storedText = node.data.get(self.name, '')
        try:
            return gennumber.GenNumber(storedText).num
        except ValueError:
            return 0

    def sortKey(self, node):
        """Return a tuple with field type and comparison values for sorting.

        Allows different types to be sorted.
        Arguments:
            node -- the tree item storing the data
        """
        return ('20_num', self.compareValue(node))

    def adjustedCompareValue(self, value):
        """Return value adjusted like the compareValue for use in conditionals.

        Number version converts to a numeric value.
        Arguments:
            value -- the comparison value to adjust
        """
        try:
            return gennumber.GenNumber(value).num
        except ValueError:
            return 0


class MathField(NumberField):
    """Class to handle a math calculation field type.

    Stores options and format strings for a math field type.
    Provides methods to return formatted data.
    """
    typeName = 'Math'
    editorClass = dataeditors.ReadOnlyEditor
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)
        self.equation = None
        self.resultType = mathResultVar[attrs.get('resulttype', 'numeric')]
        equationText = attrs.get('eqn', '').strip()
        if equationText:
            self.equation = matheval.MathEquation(equationText)
            try:
                self.equation.validate()
            except ValueError:
                self.equation = None

    def setFormat(self, format):
        """Set the format string and initialize as required.

        Arguments:
            format -- the new format string
        """
        if not hasattr(self, 'equation'):
            self.equation = None
            self.resultType = numericResult
        super().setFormat(format)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        text = storedText
        if self.resultType == numericResult:
            return super().formatOutput(text, titleMode, formatHtml)
        if self.resultType == dateResult:
            date = QtCore.QDate.fromString(text, QtCore.Qt.ISODate)
            if date.isValid():
                text = date.toString(self.format)
            else:
                text = _errorStr
        elif self.resultType == timeResult:
            time = QtCore.QTime.fromString(text)
            if time.isValid():
                text = time.toString(self.format)
            else:
                text = _errorStr
        elif self.resultType == booleanResult:
            try:
                text =  genboolean.GenBoolean(text).boolStr(self.format)
            except ValueError:
                text = _errorStr
        return HtmlTextField.formatOutput(self, text, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if not storedText:
            return ''
        if self.resultType == numericResult:
            return super().formatEditorText(storedText)
        if self.resultType == dateResult:
            date = QtCore.QDate.fromString(storedText, QtCore.Qt.ISODate)
            if date.isValid():
                editorFormat = globalref.genOptions.getValue('EditDateFormat')
                return date.toString(editorFormat)
        elif self.resultType == timeResult:
            time = QtCore.QTime.fromString(storedText)
            if time.isValid():
                editorFormat = globalref.genOptions.getValue('EditTimeFormat')
                return time.toString(editorFormat)
        elif self.resultType == booleanResult:
            return genboolean.GenBoolean(storedText).boolStr(self.format)
        else:
            return storedText
        raise ValueError

    def equationText(self):
        """Return the current equation text.
        """
        if self.equation:
            return self.equation.equationText()
        return ''

    def equationValue(self, node):
        """Return a text value from the result of the equation.

        Returns the '#####' error string for illegal math operations.
        Arguments:
            node -- the tree item with this equation
        """
        if self.equation:
            try:
                num = self.equation.equationValue(node,
                                             _mathResultBlank[self.resultType])
            except ValueError:
                return _errorStr
            if num == None:
                return ''
            if self.resultType in (numericResult, booleanResult, textResult):
                return str(num)
            elif self.resultType == dateResult:
                date = DateField.refDate.addDays(num)
                if not date.isValid():
                    return _errorStr
                return date.toString(QtCore.Qt.ISODate)
            else:
                time = TimeField.refTime.addSecs(num)
                if not time.isValid():
                    return _errorStr
                return time.toString()
        return ''

    def xmlAttr(self):
        """Return a dictionary of this field's attributes.

        Add the math equation to the standard XML output.
        """
        attrs = super().xmlAttr()
        if self.equation:
            attrs['eqn'] = self.equation.equationText()
        if self.resultType != numericResult:
            attrs['resulttype'] = mathResultStr[self.resultType]
        return attrs

    def changeResultType(self, resultType):
        """Change the result type and reset the output format.

        Arguments:
            resultType -- the new result type
        """
        if resultType != self.resultType:
            self.resultType = resultType
            if resultType == numericResult:
                self.setFormat(self.defaultFormat)
            elif resultType == dateResult:
                self.setFormat(DateField.defaultFormat)
            elif resultType == timeResult:
                self.setFormat(TimeField.defaultFormat)
            elif resultType == booleanResult:
                self.setFormat(BooleanField.defaultFormat)
            else:
                self.setFormat('')

    def getFormatHelpMenuList(self):
        """Return the list of descriptions and keys for the format help menu.
        """
        if self.resultType == numericResult:
            return self.formatHelpMenuList
        if self.resultType == dateResult:
            return DateField.formatHelpMenuList
        if self.resultType == timeResult:
            return TimeField.formatHelpMenuList
        if self.resultType == booleanResult:
            return BooleanField.formatHelpMenuList
        return []


class NumberingField(HtmlTextField):
    """Class to handle formats for hierarchical node numbering.

    Stores options and format strings for a node numbering field type.
    Provides methods to return formatted node numbers.
    """
    typeName = 'Numbering'
    defaultFormat = '1..'
    editorClass = dataeditors.LineEditor
    formatHelpMenuList = [(_('Number\t1'), '1'),
                          (_('Capital Letter\tA'), 'A'),
                          (_('Small Letter\ta'), 'a'),
                          (_('Capital Roman Numeral\tI'), 'I'),
                          (_('Small Roman Numeral\ti'), 'i'),
                          ('', ''),
                          (_('Level Separator\t/'), '/'),
                          (_('Section Separator\t.'), '.'),
                          ('', ''),
                          (_('"/" Character\t//'), '//'),
                          (_('"." Character\t..'), '..'),
                          ('', ''),
                          (_('Outline Example\tI../A../1../a)/i)'),
                           'I../A../1../a)/i)'),
                          (_('Section Example\t1.1.1.1'), '1.1.1.1')]

    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        self.numFormat = None
        super().__init__(name, attrs)

    def setFormat(self, format):
        """Set the format string and initialize as required.

        Arguments:
            format -- the new format string
        """
        self.numFormat = numbering.NumberingGroup(format)
        super().setFormat(format)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        try:
            text = self.numFormat.numString(storedText)
        except ValueError:
            text = _errorStr
        return super().formatOutput(text, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if storedText:
            checkData = [int(num) for num in storedText.split('.')]
        return storedText

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if editorText:
            checkData = [int(num) for num in editorText.split('.')]
        return editorText

    def compareValue(self, node):
        """Return a value for comparison to other nodes and for sorting.

        Returns lowercase text for text fields or numbers for non-text fields.
        Arguments:
            node -- the tree item storing the data
        """
        storedText = node.data.get(self.name, '')
        if storedText:
            try:
                return [int(num) for num in editorText.split('.')]
            except ValueError:
                pass
        return [0]

    def sortKey(self, node):
        """Return a tuple with field type and comparison values for sorting.

        Allows different types to be sorted.
        Arguments:
            node -- the tree item storing the data
        """
        return ('10_numbering', self.compareValue(node))

    def adjustedCompareValue(self, value):
        """Return value adjusted like the compareValue for use in conditionals.

        Number version converts to a numeric value.
        Arguments:
            value -- the comparison value to adjust
        """
        if value:
            try:
                return [int(num) for num in value.split('.')]
            except ValueError:
                pass
        return [0]


class ChoiceField(HtmlTextField):
    """Class to handle a field with pre-defined, individual text choices.

    Stores options and format strings for a choice field type.
    Provides methods to return formatted data.
    """
    typeName = 'Choice'
    editSep = '/'
    defaultFormat = '1/2/3/4'
    editorClass = dataeditors.ComboEditor
    numChoiceColumns = 1
    autoAddChoices = False
    formatHelpMenuList = [(_('Separator\t/'), '/'), ('', ''),
                          (_('"/" Character\t//'), '//'), ('', ''),
                          (_('Example\t1/2/3/4'), '1/2/3/4')]
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def setFormat(self, format):
        """Set the format string and initialize as required.

        Arguments:
            format -- the new format string
        """
        super().setFormat(format)
        self.choiceList = self.splitText(self.format)
        self.choices = set([xml.sax.saxutils.escape(choice) for choice in
                            self.choiceList])

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        if storedText not in self.choices:
            storedText = _errorStr
        return super().formatOutput(storedText, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if storedText and storedText not in self.choices:
            raise ValueError
        return xml.sax.saxutils.unescape(storedText)

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        editorText = xml.sax.saxutils.escape(editorText)
        if not editorText or editorText in self.choices:
            return editorText
        raise ValueError

    def comboChoices(self):
        """Return a list of choices for the combo box.
        """
        return self.choiceList

    def initDefaultChoices(self):
        """Return a list of choices for setting the init default.
        """
        return self.choiceList

    def splitText(self, textStr):
        """Split textStr using editSep, return a list of strings.

        Double editSep's are not split (become single).
        Removes duplicates and empty strings.
        Arguments:
            textStr -- the text to split
        """
        result = []
        textStr = textStr.replace(self.editSep * 2, '\0')
        for text in textStr.split(self.editSep):
            text = text.strip().replace('\0', self.editSep)
            if text and text not in result:
                result.append(text)
        return result


class AutoChoiceField(HtmlTextField):
    """Class to handle a field with automatically populated text choices.

    Stores options and possible entries for an auto-choice field type.
    Provides methods to return formatted data.
    """
    typeName = 'AutoChoice'
    editorClass = dataeditors.ComboEditor
    numChoiceColumns = 1
    autoAddChoices = True
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)
        self.choices = set()

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Arguments:
            storedText -- the source text to format
        """
        return xml.sax.saxutils.unescape(storedText)

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Arguments:
            editorText -- the new text entered into the editor
        """
        return xml.sax.saxutils.escape(editorText)

    def comboChoices(self):
        """Return a list of choices for the combo box.
        """
        choices = [xml.sax.saxutils.unescape(text) for text in self.choices]
        return sorted(choices, key=str.lower)

    def addChoice(self, text):
        """Add a new choice.

        Arguments:
            text -- the choice to be added
        """
        if text:
            self.choices.add(text)

    def clearChoices(self):
        """Remove all current choices.
        """
        self.choices = set()


class CombinationField(ChoiceField):
    """Class to handle a field with multiple pre-defined text choices.

    Stores options and format strings for a combination field type.
    Provides methods to return formatted data.
    """
    typeName = 'Combination'
    editorClass = dataeditors.CombinationEditor
    numChoiceColumns = 2
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def setFormat(self, format):
        """Set the format string and initialize as required.

        Arguments:
            format -- the new format string
        """
        TextField.setFormat(self, format)
        format = xml.sax.saxutils.escape(format)
        self.choiceList = self.splitText(format)
        self.choices = set(self.choiceList)
        self.outputSep = ''

    def outputText(self, node, titleMode, formatHtml):
        """Return formatted output text for this field in this node.

        Sets output separator prior to calling base class methods.
        Arguments:
            node -- the tree item storing the data
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        self.outputSep = node.nodeFormat().outputSeparator
        return super().outputText(node, titleMode, formatHtml)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        selections, valid = self.sortedSelections(storedText)
        if valid:
            result = self.outputSep.join(selections)
        else:
            result = _errorStr
        return TextField.formatOutput(self, result, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        selections = set(self.splitText(storedText))
        if selections.issubset(self.choices):
            return xml.sax.saxutils.unescape(storedText)
        raise ValueError

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        editorText = xml.sax.saxutils.escape(editorText)
        selections, valid = self.sortedSelections(editorText)
        if not valid:
            raise ValueError
        return self.joinText(selections)

    def comboChoices(self):
        """Return a list of choices for the combo box.
        """
        return [xml.sax.saxutils.unescape(text) for text in self.choiceList]

    def comboActiveChoices(self, editorText):
        """Return a sorted list of choices currently in editorText.

        Arguments:
            editorText -- the text entered into the editor
        """
        selections, valid = self.sortedSelections(xml.sax.saxutils.
                                                  escape(editorText))
        return [xml.sax.saxutils.unescape(text) for text in selections]

    def initDefaultChoices(self):
        """Return a list of choices for setting the init default.
        """
        return []

    def sortedSelections(self, inText):
        """Split inText using editSep and sort like format string.

        Return a tuple of resulting selection list and bool validity.
        Valid if all choices are in the format string.
        Arguments:
            inText -- the text to split and sequence
        """
        selections = set(self.splitText(inText))
        result = [text for text in self.choiceList if text in selections]
        return (result, len(selections) == len(result))

    def joinText(self, textList):
        """Join the text list using editSep, return the string.

        Any editSep in text items become double.
        Arguments:
            textList -- the list of text items to join
        """
        return self.editSep.join([text.replace(self.editSep, self.editSep * 2)
                                  for text in textList])


class AutoCombinationField(CombinationField):
    """Class for a field with multiple automatically populated text choices.

    Stores options and possible entries for an auto-choice field type.
    Provides methods to return formatted data.
    """
    typeName = 'AutoCombination'
    autoAddChoices = True
    defaultFormat = ''
    formatHelpMenuList = []
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)
        self.choices = set()
        self.outputSep = ''

    def outputText(self, node, titleMode, formatHtml):
        """Return formatted output text for this field in this node.

        Sets output separator prior to calling base class methods.
        Arguments:
            node -- the tree item storing the data
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        self.outputSep = node.nodeFormat().outputSeparator
        return super().outputText(node, titleMode, formatHtml)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        result = self.outputSep.join(self.splitText(storedText))
        return TextField.formatOutput(self, result, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Arguments:
            storedText -- the source text to format
        """
        return xml.sax.saxutils.unescape(storedText)

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Also resets outputSep, to be defined at the next output.
        Arguments:
            editorText -- the new text entered into the editor
        """
        self.outputSep = ''
        editorText = xml.sax.saxutils.escape(editorText)
        selections = sorted(self.splitText(editorText), key=str.lower)
        return self.joinText(selections)

    def comboChoices(self):
        """Return a list of choices for the combo box.
        """
        return [xml.sax.saxutils.unescape(text) for text in
                sorted(self.choices, key=str.lower)]

    def comboActiveChoices(self, editorText):
        """Return a sorted list of choices currently in editorText.

        Arguments:
            editorText -- the text entered into the editor
        """
        selections, valid = self.sortedSelections(xml.sax.saxutils.
                                                  escape(editorText))
        return [xml.sax.saxutils.unescape(text) for text in selections]

    def sortedSelections(self, inText):
        """Split inText using editSep and sort like format string.

        Return a tuple of resulting selection list and bool validity.
        This version always returns valid.
        Arguments:
            inText -- the text to split and sequence
        """
        selections = sorted(self.splitText(inText), key=str.lower)
        return (selections, True)

    def addChoice(self, text):
        """Add a new choice.

        Arguments:
            text -- the stored text combinations to be added
        """
        for choice in self.splitText(text):
            self.choices.add(choice)

    def clearChoices(self):
        """Remove all current choices.
        """
        self.choices = set()


class BooleanField(ChoiceField):
    """Class to handle a general boolean field format type.

    Stores options and format strings for a boolean field type.
    Provides methods to return formatted data.
    """
    typeName = 'Boolean'
    defaultFormat = _('yes/no')
    formatHelpMenuList = [(_('true/false'), 'true/false'),
                          (_('T/F'), 'T/F'), ('', ''),
                          (_('yes/no'), 'yes/no'),
                          (_('Y/N'), 'Y/N'), ('', ''),
                          ('1/0', '1/0')]
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        try:
            text =  genboolean.GenBoolean(storedText).boolStr(self.format)
        except ValueError:
            text = _errorStr
        return super().formatOutput(text, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if not storedText:
            return ''
        return genboolean.GenBoolean(storedText).boolStr(self.format)

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if not editorText:
            return ''
        try:
            return repr(genboolean.GenBoolean().setFromStr(editorText,
                                                           self.format))
        except ValueError:
            return repr(genboolean.GenBoolean(editorText))

    def mathValue(self, node, zeroBlanks=True):
        """Return a value to be used in math field equations.

        Return None if blank and not zeroBlanks,
        raise a ValueError if it isn't a valid boolean.
        Arguments:
            node -- the tree item storing the data
            zeroBlanks -- replace blank field values with zeros if True
        """
        storedText = node.data.get(self.name, '')
        if storedText:
            return genboolean.GenBoolean(storedText).value
        return False if zeroBlanks else None

    def compareValue(self, node):
        """Return a value for comparison to other nodes and for sorting.

        Returns lowercase text for text fields or numbers for non-text fields.
        Bool fields return True or False values.
        Arguments:
            node -- the tree item storing the data
        """
        storedText = node.data.get(self.name, '')
        try:
            return genboolean.GenBoolean(storedText).value
        except ValueError:
            return False

    def sortKey(self, node):
        """Return a tuple with field type and comparison values for sorting.

        Allows different types to be sorted.
        Arguments:
            node -- the tree item storing the data
        """
        return ('30_bool', self.compareValue(node))

    def adjustedCompareValue(self, value):
        """Return value adjusted like the compareValue for use in conditionals.

        Bool version converts to a bool value.
        Arguments:
            value -- the comparison value to adjust
        """
        try:
            return genboolean.GenBoolean().setFromStr(value, self.format).value
        except ValueError:
            try:
                return genboolean.GenBoolean(value).value
            except ValueError:
                return False


class DateField(HtmlTextField):
    """Class to handle a general date field format type.

    Stores options and format strings for a date field type.
    Provides methods to return formatted data.
    """
    typeName = 'Date'
    defaultFormat = 'MMMM d, yyyy'
    editorClass = dataeditors.DateEditor
    refDate = QtCore.QDate(1970, 1, 1)
    formatHelpMenuList = [(_('Day (1 or 2 digits)\td'), 'd'),
                          (_('Day (2 digits)\tdd'), 'dd'), ('', ''),
                          (_('Weekday Abbreviation\tddd'), 'ddd'),
                          (_('Weekday Name\tdddd'), 'dddd'), ('', ''),
                          (_('Month (1 or 2 digits)\tM'), 'M'),
                          (_('Month (2 digits)\tMM'), 'MM'),
                          (_('Month Abbreviation\tMMM'), 'MMM'),
                          (_('Month Name\tMMMM'), 'MMMM'), ('', ''),
                          (_('Year (2 digits)\tyy'), 'yy'),
                          (_('Year (4 digits)\tyyyy'), 'yyyy'), ('', '')]

    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        date = QtCore.QDate.fromString(storedText, QtCore.Qt.ISODate)
        if date.isValid():
            text = date.toString(self.format)
        else:
            text = _errorStr
        return super().formatOutput(text, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if not storedText:
            return ''
        date = QtCore.QDate.fromString(storedText, QtCore.Qt.ISODate)
        if date.isValid():
            editorFormat = globalref.genOptions.getValue('EditDateFormat')
            return date.toString(editorFormat)
        raise ValueError

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Two digit years are interpretted as 1950-2049.
        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if not editorText:
            return ''
        editorFormat = globalref.genOptions.getValue('EditDateFormat')
        date = QtCore.QDate.fromString(editorText, editorFormat)
        if not date.isValid():
            # allow use of single digit month and day
            editorFormat = re.sub(r'(?<!M)MM(?!M)', 'M', editorFormat, 1)
            editorFormat = re.sub(r'(?<!d)dd(?!d)', 'd', editorFormat, 1)
            date = QtCore.QDate.fromString(editorText, editorFormat)
        if date.isValid():
            if 1900 <= date.year() < 1950 and 'yyyy' not in editorFormat:
                date = date.addYears(100)
            return date.toString(QtCore.Qt.ISODate)
        # allow use of a 4-digit year to fix invalid dates
        if 'yyyy' not in editorFormat and 'yy' in editorFormat:
            modFormat = editorFormat.replace('yy', 'yyyy', 1)
            date = QtCore.QDate.fromString(editorText, modFormat)
            if date.isValid():
                return date.toString(QtCore.Qt.ISODate)
        raise ValueError

    def mathValue(self, node, zeroBlanks=True):
        """Return a numeric value to be used in math field equations.

        Return None if blank and not zeroBlanks,
        raise a ValueError if it isn't a valid date.
        Arguments:
            node -- the tree item storing the data
            zeroBlanks -- replace blank field values with zeros if True
        """
        storedText = node.data.get(self.name, '')
        if storedText:
            date = QtCore.QDate.fromString(storedText, QtCore.Qt.ISODate)
            if not date.isValid():
                raise ValueError
            return DateField.refDate.daysTo(date)
        return 0 if zeroBlanks else None

    def getInitDefault(self):
        """Return the initial stored value for newly created nodes.
        """
        if self.initDefault == _dateStampString:
            date = QtCore.QDate.currentDate()
            return date.toString(QtCore.Qt.ISODate)
        return super().getInitDefault()

    def setInitDefault(self, editorText):
        """Set the default initial value from editor text.

        The function for default text field just returns the stored text.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if editorText == _dateStampString:
            self.initDefault = _dateStampString
        else:
            super().setInitDefault(editorText)

    def getEditorInitDefault(self):
        """Return initial value in editor format.

        The function for default text field just returns the initial value.
        """
        if self.initDefault == _dateStampString:
            return _dateStampString
        return super().getEditorInitDefault()

    def initDefaultChoices(self):
        """Return a list of choices for setting the init default.
        """
        return [_dateStampString]

    def compareValue(self, node):
        """Return a value for comparison to other nodes and for sorting.

        Returns lowercase text for text fields or numbers for non-text fields.
        Date field uses ISO date format (YYY-MM-DD).
        Arguments:
            node -- the tree item storing the data
        """
        return node.data.get(self.name, '')

    def sortKey(self, node):
        """Return a tuple with field type and comparison values for sorting.

        Allows different types to be sorted.
        Arguments:
            node -- the tree item storing the data
        """
        return ('40_date', self.compareValue(node))

    def adjustedCompareValue(self, value):
        """Return value adjusted like the compareValue for use in conditionals.

        Date version converts to an ISO date format (YYY-MM-DD).
        Arguments:
            value -- the comparison value to adjust
        """
        if not value:
            return ''
        editorFormat = globalref.genOptions.getValue('EditDateFormat')
        if value == _dateStampString:
            return QtCore.QDate.currentDate().toString(QtCore.Qt.ISODate)
        date = QtCore.QDate.fromString(value, editorFormat)
        if not date.isValid():
            # allow use of single digit month and day
            editorFormat = re.sub(r'(?<!M)MM(?!M)', 'M', editorFormat, 1)
            editorFormat = re.sub(r'(?<!d)dd(?!d)', 'd', editorFormat, 1)
            date = QtCore.QDate.fromString(value, editorFormat)
        if date.isValid():
            if 1900 <= date.year() < 1950 and 'yyyy' not in editorFormat:
                date = date.addYears(100)
            return date.toString(QtCore.Qt.ISODate)
        # allow use of a 4-digit year to fix invalid dates
        if 'yyyy' not in editorFormat and 'yy' in editorFormat:
            modFormat = editorFormat.replace('yy', 'yyyy', 1)
            date = QtCore.QDate.fromString(value, modFormat)
            if date.isValid():
                return date.toString(QtCore.Qt.ISODate)
        return value


class TimeField(HtmlTextField):
    """Class to handle a general time field format type

    Stores options and format strings for a time field type.
    Provides methods to return formatted data.
    """
    typeName = 'Time'
    defaultFormat = 'h:mm:ss AP'
    editorClass = dataeditors.ComboEditor
    numChoiceColumns = 2
    autoAddChoices = False
    refTime = QtCore.QTime(0, 0)
    formatHelpMenuList = [(_('Hour (0-23, 1 or 2 digits)\tH'), 'H'),
                          (_('Hour (00-23, 2 digits)\tHH'), 'HH'),
                          (_('Hour (1-12, 1 or 2 digits)\th'), 'h'),
                          (_('Hour (01-12, 2 digits)\thh'), 'hh'), ('', ''),
                          (_('Minute (1 or 2 digits)\tm'), 'm'),
                          (_('Minute (2 digits)\tmm'), 'mm'), ('', ''),
                          (_('Second (1 or 2 digits)\ts'), 's'),
                          (_('Second (2 digits)\tss'), 'ss'), ('', ''),
                          (_('Milliseconds (1 to 3 digits)\tz'), 'z'),
                          (_('Milliseconds (3 digits)\tzzz'), 'zzz'), ('', ''),
                          (_('AM/PM\tAP'), 'AP'),
                          (_('am/pm\tap'), 'ap')]
    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        time = QtCore.QTime.fromString(storedText)
        if time.isValid():
            text = time.toString(self.format)
        else:
            text = _errorStr
        return super().formatOutput(text, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if not storedText:
            return ''
        time = QtCore.QTime.fromString(storedText)
        if time.isValid():
            editorFormat = globalref.genOptions.getValue('EditTimeFormat')
            return time.toString(editorFormat)
        raise ValueError

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if not editorText:
            return ''
        editorFormat = globalref.genOptions.getValue('EditTimeFormat')
        time = QtCore.QTime.fromString(editorText, editorFormat)
        if not time.isValid():
            editorFormat = editorFormat.replace(':ss', '', 1)
            editorFormat = editorFormat.replace(':s', '', 1)
            time = QtCore.QTime.fromString(editorText, editorFormat)
            if not time.isValid():
                editorFormat = editorFormat.replace('AP', '', 1)
                editorFormat = editorFormat.replace('ap', '', 1)
                editorFormat = editorFormat.strip()
                time = QtCore.QTime.fromString(editorText, editorFormat)
        if time.isValid():
            return time.toString()
        raise ValueError

    def annotatedComboChoices(self, editorText):
        """Return a list of (choice, annotation) tuples for the combo box.

        Arguments:
            editorText -- the text entered into the editor
        """
        editorFormat = globalref.genOptions.getValue('EditTimeFormat')
        choices = [(QtCore.QTime.currentTime().toString(editorFormat),
                    '({0})'.format(_timeStampString))]
        for hour in (6, 9, 12, 15, 18, 21, 0):
            choices.append((QtCore.QTime(hour, 0).toString(editorFormat), ''))
        return choices

    def mathValue(self, node, zeroBlanks=True):
        """Return a numeric value to be used in math field equations.

        Return None if blank and not zeroBlanks,
        raise a ValueError if it isn't a valid time.
        Arguments:
            node -- the tree item storing the data
            zeroBlanks -- replace blank field values with zeros if True
        """
        storedText = node.data.get(self.name, '')
        if storedText:
            time = QtCore.QTime.fromString(storedText)
            if not time.isValid():
                raise ValueError
            return TimeField.refTime.secsTo(time)
        return 0 if zeroBlanks else None

    def getInitDefault(self):
        """Return the initial stored value for newly created nodes.
        """
        if self.initDefault == _timeStampString:
            time = QtCore.QTime.currentTime()
            return time.toString()
        return super().getInitDefault()

    def setInitDefault(self, editorText):
        """Set the default initial value from editor text.

        The function for default text field just returns the stored text.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if editorText == _timeStampString:
            self.initDefault = _timeStampString
        else:
            super().setInitDefault(editorText)

    def getEditorInitDefault(self):
        """Return initial value in editor format.

        The function for default text field just returns the initial value.
        """
        if self.initDefault == _timeStampString:
            return _timeStampString
        return super().getEditorInitDefault()

    def initDefaultChoices(self):
        """Return a list of choices for setting the init default.
        """
        return [_timeStampString]

    def compareValue(self, node):
        """Return a value for comparison to other nodes and for sorting.

        Returns lowercase text for text fields or numbers for non-text fields.
        Time field uses HH:MM:SS format.
        Arguments:
            node -- the tree item storing the data
        """
        return node.data.get(self.name, '')

    def sortKey(self, node):
        """Return a tuple with field type and comparison values for sorting.

        Allows different types to be sorted.
        Arguments:
            node -- the tree item storing the data
        """
        return ('50_time', self.compareValue(node))

    def adjustedCompareValue(self, value):
        """Return value adjusted like the compareValue for use in conditionals.

        Time version converts to HH:MM:SS format.
        Arguments:
            value -- the comparison value to adjust
        """
        if not value:
            return ''
        editorFormat = globalref.genOptions.getValue('EditTimeFormat')
        if value == _timeStampString:
            time = QtCore.QTime.currentTime()
        else:
            time = QtCore.QTime.fromString(value, editorFormat)
            if not time.isValid():
                editorFormat = editorFormat.replace(':ss', '', 1)
                editorFormat = editorFormat.replace(':s', '', 1)
                time = QtCore.QTime.fromString(value, editorFormat)
                if not time.isValid():
                    editorFormat = editorFormat.replace('AP', '', 1)
                    editorFormat = editorFormat.replace('ap', '', 1)
                    editorFormat = editorFormat.strip()
                    time = QtCore.QTime.fromString(value, editorFormat)
            if not time.isValid():
                return value
        return time.toString()


class ExternalLinkField(HtmlTextField):
    """Class to handle a field containing various types of external HTML links.

    Protocol choices include http, https, file, mailto.
    Stores data as HTML tags, shows in editors as "protocol:address [name]".
    """
    typeName = 'ExternalLink'
    editorClass = dataeditors.ExtLinkEditor

    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        if titleMode:
            linkMatch = linkRegExp.search(storedText)
            if linkMatch:
                address, name = linkMatch.groups()
                storedText = name.strip()
                if not storedText:
                    storedText = address.lstrip('#')
        return super().formatOutput(storedText, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if not storedText:
            return ''
        linkMatch = linkRegExp.search(storedText)
        if not linkMatch:
            raise ValueError
        address, name = linkMatch.groups()
        name = name.strip()
        if not name:
            name = urltools.shortName(address)
        return '{0} [{1}]'.format(address, name)

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if not editorText:
            return ''
        nameMatch = linkSeparateNameRegExp.match(editorText)
        if nameMatch:
            address, name = nameMatch.groups()
        else:
            address = editorText
            name = urltools.shortName(address)
        return '<a href="{0}">{1}</a>'.format(address.strip(), name.strip())

    def compareValue(self, node):
        """Return a value for comparison to other nodes and for sorting.

        Returns lowercase text for text fields or numbers for non-text fields.
        Link fields use stored link format
        Arguments:
            node -- the tree item storing the data
        """
        storedText = node.data.get(self.name, '')
        if not storedText:
            return ''
        linkMatch = linkRegExp.search(storedText)
        if not linkMatch:
            return storedText
        address, name = linkMatch.groups()
        return address.lstrip('#').lower()

    def sortKey(self, node):
        """Return a tuple with field type and comparison values for sorting.

        Allows different types to be sorted.
        Arguments:
            node -- the tree item storing the data
        """
        return ('50_link', self.compareValue(node))


class InternalLinkField(ExternalLinkField):
    """Class to handle a field containing internal links to nodes.

    Stores data as HTML local link tag, shows in editors as "id [name]".
    """
    typeName = 'InternalLink'
    editorClass = dataeditors.IntLinkEditor

    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def editorText(self, node):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Also raises a ValueError if the link is not a valid destination, with
        the editor text as the second argument to the exception.
        Arguments:
            node -- the tree item storing the data
        """
        storedText = node.data.get(self.name, '')
        return self.formatEditorText(storedText, node.modelRef)

    def formatEditorText(self, storedText, modelRef=None):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Also raises a ValueError if the link is not a valid destination, with
        the editor text as the second argument to the exception.
        Arguments:
            storedText -- the source text to format
            modelRef -- a model ref to check for valid links if given
        """
        if not storedText:
            return ''
        linkMatch = linkRegExp.search(storedText)
        if not linkMatch:
            raise ValueError
        address, name = linkMatch.groups()
        address = address.lstrip('#')
        name = name.strip()
        if not name:
            name = address
        result = '{0} [{1}]'.format(address, name)
        if modelRef and address not in modelRef.nodeIdDict:
            raise ValueError('invalid address', result)
        return result

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        if not editorText:
            return ''
        nameMatch = linkSeparateNameRegExp.match(editorText)
        if nameMatch:
            address, name = nameMatch.groups()
        else:
            address = editorText
            name = address
        return '<a href="#{0}">{1}</a>'.format(address.strip(), name.strip())


class PictureField(HtmlTextField):
    """Class to handle a field containing various types of external HTML links.

    Protocol choices include http, https, file, mailto.
    Stores data as HTML tags, shows in editors as "protocol:address [name]".
    """
    typeName = 'Picture'
    editorClass = dataeditors.PictureLinkEditor

    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        if titleMode:
            linkMatch = imageRegExp.search(storedText)
            if linkMatch:
                address = linkMatch.group(1)
                storedText = address.strip()
        return super().formatOutput(storedText, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        if not storedText:
            return ''
        linkMatch = imageRegExp.search(storedText)
        if not linkMatch:
            raise ValueError
        return linkMatch.group(1)

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        editorText = editorText.strip()
        if not editorText:
            return ''
        nameMatch = linkSeparateNameRegExp.match(editorText)
        if nameMatch:
            address, name = nameMatch.groups()
        else:
            address = editorText
            name = urltools.shortName(address)
        return '<img src="{0}" />'.format(editorText)

    def compareValue(self, node):
        """Return a value for comparison to other nodes and for sorting.

        Returns lowercase text for text fields or numbers for non-text fields.
        Link fields use stored link format
        Arguments:
            node -- the tree item storing the data
        """
        storedText = node.data.get(self.name, '')
        if not storedText:
            return ''
        linkMatch = imageRegExp.search(storedText)
        if not linkMatch:
            return storedText
        return linkMatch.group(1).lower()

    def sortKey(self, node):
        """Return a tuple with field type and comparison values for sorting.

        Allows different types to be sorted.
        Arguments:
            node -- the tree item storing the data
        """
        return ('50_link', self.compareValue(node))


class RegularExpressionField(HtmlTextField):
    """Class to handle a field format type controlled by a regular expression.

    Stores options and format strings for a number field type.
    Provides methods to return formatted data.
    """
    typeName = 'RegularExpression'
    defaultFormat = '.*'
    editorClass = dataeditors.LineEditor
    formatHelpMenuList = [(_('Any Character\t.'), '.'),
                          (_('End of Text\t$'), '$'),
                          ('', ''),
                          (_('0 Or More Repetitions\t*'), '*'),
                          (_('1 Or More Repetitions\t+'), '+'),
                          (_('0 Or 1 Repetitions\t?'), '?'),
                          ('', ''),
                          (_('Set of Numbers\t[0-9]'), '[0-9]'),
                          (_('Lower Case Letters\t[a-z]'), '[a-z]'),
                          (_('Upper Case Letters\t[A-Z]'), '[A-Z]'),
                          (_('Not a Number\t[^0-9]'), '[^0-9]'),
                          ('', ''),
                          (_('Or\t|'), '|'),
                          (_('Escape a Special Character\t\\'), '\\')]

    def __init__(self, name, attrs=None):
        """Initialize a field format type.

        Arguments:
            name -- the field name string
            attrs -- the attributes that define this field's format
        """
        super().__init__(name, attrs)

    def setFormat(self, format):
        """Set the format string and initialize as required.

        Raise a ValueError if the format is illegal.
        Arguments:
            format -- the new format string
        """
        try:
            re.compile(format)
        except re.error:
            raise ValueError
        super().setFormat(format)

    def formatOutput(self, storedText, titleMode, formatHtml):
        """Return formatted output text from stored text for this field.

        Arguments:
            storedText -- the source text to format
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        match = re.match(self.format, xml.sax.saxutils.unescape(storedText))
        if not storedText or match:
            text = storedText
        else:
            text = _errorStr
        return super().formatOutput(text, titleMode, formatHtml)

    def formatEditorText(self, storedText):
        """Return text formatted for use in the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            storedText -- the source text to format
        """
        editorText = xml.sax.saxutils.unescape(storedText)
        match = re.match(self.format, editorText)
        if not editorText or match:
            return editorText
        raise ValueError

    def storedText(self, editorText):
        """Return new text to be stored based on text from the data editor.

        Raises a ValueError if the data does not match the format.
        Arguments:
            editorText -- the new text entered into the editor
        """
        match = re.match(self.format, editorText)
        if not editorText or match:
            return xml.sax.saxutils.escape(editorText)
        raise ValueError


class AncestorLevelField(TextField):
    """Placeholder format for ref. to ancestor fields at specific levels.
    """
    typeName = 'AncestorLevel'
    def __init__(self, name, ancestorLevel=1):
        """Initialize a field format placeholder type.

        Arguments:
            name -- the field name string
            ancestorLevel -- the number of generations to go back
        """
        super().__init__(name, {})
        self.ancestorLevel = ancestorLevel

    def outputText(self, node, titleMode, formatHtml):
        """Return formatted output text for this field in this node.

        Finds the appropriate ancestor node to get the field text.
        Arguments:
            node -- the tree node to start from
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        for num in range(self.ancestorLevel):
            node = node.parent
            if not node:
                return ''
        try:
            field = node.nodeFormat().fieldDict[self.name]
        except KeyError:
            return ''
        return field.outputText(node, titleMode, formatHtml)

    def sepName(self):
        """Return the name enclosed with {* *} separators
        """
        return '{{*{0}{1}*}}'.format(self.ancestorLevel * '*', self.name)


class AnyAncestorField(TextField):
    """Placeholder format for ref. to matching ancestor fields at any level.
    """
    typeName = 'AnyAncestor'
    def __init__(self, name):
        """Initialize a field format placeholder type.

        Arguments:
            name -- the field name string
        """
        super().__init__(name, {})

    def outputText(self, node, titleMode, formatHtml):
        """Return formatted output text for this field in this node.

        Finds the appropriate ancestor node to get the field text.
        Arguments:
            node -- the tree node to start from
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        while node.parent:
            node = node.parent
            try:
                field = node.nodeFormat().fieldDict[self.name]
            except KeyError:
                pass
            else:
                return field.outputText(node, titleMode, formatHtml)
        return ''

    def sepName(self):
        """Return the name enclosed with {* *} separators
        """
        return '{{*?{0}*}}'.format(self.name)


class ChildListField(TextField):
    """Placeholder format for ref. to matching ancestor fields at any level.
    """
    typeName = 'ChildList'
    def __init__(self, name):
        """Initialize a field format placeholder type.

        Arguments:
            name -- the field name string
        """
        super().__init__(name, {})

    def outputText(self, node, titleMode, formatHtml):
        """Return formatted output text for this field in this node.

        Returns a joined list of matching child field data.
        Arguments:
            node -- the tree node to start from
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        result = []
        for child in node.childList:
            try:
                field = child.nodeFormat().fieldDict[self.name]
            except KeyError:
                pass
            else:
                result.append(field.outputText(child, titleMode, formatHtml))
        outputSep = node.nodeFormat().outputSeparator
        return outputSep.join(result)

    def sepName(self):
        """Return the name enclosed with {* *} separators
        """
        return '{{*&{0}*}}'.format(self.name)


class DescendantCountField(TextField):
    """Placeholder format for count of descendants at a given level.
    """
    typeName = 'DescendantCount'
    def __init__(self, name, descendantLevel=1):
        """Initialize a field format placeholder type.

        Arguments:
            name -- the field name string
            descendantLevel -- the level to descend to
        """
        super().__init__(name, {})
        self.descendantLevel = descendantLevel

    def outputText(self, node, titleMode, formatHtml):
        """Return formatted output text for this field in this node.

        Returns a count of descendants at the approriate level.
        Arguments:
            node -- the tree node to start from
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        newNodes = [node]
        for i in range(self.descendantLevel):
            prevNodes = newNodes
            newNodes= []
            for child in prevNodes:
                newNodes.extend(child.childList)
        return repr(len(newNodes))

    def sepName(self):
        """Return the name enclosed with {* *} separators
        """
        return '{{*#{0}*}}'.format(self.name)


class UniqueIdField(TextField):
    """Placeholder format for output of the unique ID for a node.
    """
    typeName = 'UniqueId'
    def __init__(self, name):
        """Initialize a field format placeholder type.

        Arguments:
            name -- the field name string
        """
        super().__init__(name, {})

    def outputText(self, node, titleMode, formatHtml):
        """Return formatted output text for this field in this node.

        Returns the node's unique ID.
        Arguments:
            node -- the tree node to start from
            titleMode -- if True, removes all HTML markup for tree title use
            formatHtml -- if False, escapes HTML from prefix & suffix
        """
        return node.uniqueId

    def sepName(self):
        """Return the name enclosed with {* *} separators
        """
        return '{{*!{0}*}}'.format(self.name)


####  Utility Functions  ####

_stripTagRe = re.compile('<.*?>')

def removeMarkup(text):
    """Return text with all HTML Markup removed and entities unescaped.
    """
    text = _stripTagRe.sub('', text)
    return xml.sax.saxutils.unescape(text)
