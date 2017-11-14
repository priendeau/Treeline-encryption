#!/usr/bin/env python3

#******************************************************************************
# treeline.py, the main program file
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

__progname__ = 'TreeLine'
__version__ = '2.0.2'
__author__ = 'Doug Bell'

docPath = None         # modified by install script if required
iconPath = None        # modified by install script if required
templatePath = None    # modified by install script if required
samplePath = None      # modified by install script if required
translationPath = 'translations'


import sys
import os.path
import argparse
import locale
import builtins
from PyQt4 import QtCore, QtGui


def loadTranslator(fileName, app):
    """Load and install qt translator, return True if sucessful.

    Arguments:
        fileName -- the translator file to load
        app -- the main QApplication
    """
    translator = QtCore.QTranslator(app)
    modPath = os.path.abspath(sys.path[0])
    if modPath.endswith('.zip'):  # for py2exe
        modPath = os.path.dirname(modPath)
    path = os.path.join(modPath, translationPath)
    result = translator.load(fileName, path)
    if not result:
        path = os.path.join(modPath, '..', translationPath)
        result = translator.load(fileName, path)
    if not result:
        path = os.path.join(modPath, '..', 'i18n', translationPath)
        result = translator.load(fileName, path)
    if result:
        QtCore.QCoreApplication.installTranslator(translator)
        return True
    else:
        print('Warning: translation file "{0}" could not be loaded'.
              format(fileName))
        return False

def setupTranslator(app, lang=''):
    """Set language, load translators and setup translator functions.

    Return the language setting
    Arguments:
        app -- the main QApplication
        lang -- language setting from the command line
    """
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass
    if not lang:
        lang = os.environ.get('LC_MESSAGES', '')
        if not lang:
            lang = os.environ.get('LANG', '')
            if not lang:
                try:
                    lang = locale.getdefaultlocale()[0]
                except ValueError:
                    pass
                if not lang:
                    lang = ''
    numTranslators = 0
    if lang and lang[:2] not in ['C', 'en']:
        numTranslators += loadTranslator('qt_{0}'.format(lang), app)
        numTranslators += loadTranslator('treeline_{0}'.format(lang),
                                         app)

    def translate(text, comment=''):
        """Translation function, sets context to calling module's filename.

        Arguments:
            text -- the text to be translated
            comment -- a comment used only as a guide for translators
        """
        try:
            frame = sys._getframe(1)
            fileName = frame.f_code.co_filename
        finally:
            del frame
        context = os.path.basename(os.path.splitext(fileName)[0])
        return QtCore.QCoreApplication.translate(context, text, comment)

    def markNoTranslate(text, comment=''):
        """Dummy translation function, only used to mark text.

        Arguments:
            text -- the text to be translated
            comment -- a comment used only as a guide for translators
        """
        return text

    if numTranslators:
        builtins._ = translate
    else:
        builtins._ = markNoTranslate
    builtins.N_ = markNoTranslate
    return lang


def main():
    """Main event loop function for TreeLine
    """
    app = QtGui.QApplication(sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang', help='language code for GUI translation')
    parser.add_argument('fileList', nargs='*', metavar='filename',
                        help='input filename(s) to load')
    args = parser.parse_args()
    # must setup translator before any treeline module imports
    lang = setupTranslator(app, args.lang)
    import globalref
    globalref.lang = lang
    globalref.localTextEncoding = locale.getpreferredencoding()

    import treemaincontrol
    treeMainControl = treemaincontrol.TreeMainControl(args.fileList)
    app.exec_()


if __name__ == '__main__':
    main()
