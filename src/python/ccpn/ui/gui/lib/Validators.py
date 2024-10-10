"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-10-09 14:37:07 +0100 (Wed, October 09, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-02-10 13:34:53 +0100 (Thu, February 10, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import re

from PyQt5 import QtGui
from ccpn.ui.gui.modules.CcpnModule import INVALIDROWCOLOUR, WARNINGROWCOLOUR
from ccpn.ui.gui.widgets.Entry import VALIDATEASICON


#=========================================================================================
# LineEditValidator
#=========================================================================================

class LineEditValidator(QtGui.QValidator):
    """Validator to restrict input to non-alpha-numeric characters
    """

    def __init__(self, parent=None, allowSpace=True, allowEmpty=True):
        super().__init__(parent=parent)

        self.baseColour = self.parent().palette().color(QtGui.QPalette.Base)
        self._parent = parent
        self._allowSpace = allowSpace
        self._allowEmpty = allowEmpty

    def _isValidInput(self, value):
        notAllowedSequences = {'Illegal_Characters': '[^A-Za-z0-9_ ]+',
                               'Empty_Spaces'      : '\s',
                               }

        if not value and not self._allowEmpty:
            return False
        if self._allowSpace:
            notAllowedSequences.pop('Empty_Spaces')
        return not any(re.findall(seq, value) for seq in notAllowedSequences.values())

    def validate(self, p_str, p_int):
        palette = self.parent().palette()

        if self._isValidInput(p_str):
            palette.setColor(QtGui.QPalette.Base, self.baseColour)
            state = QtGui.QValidator.Acceptable  # entry is valid
        else:
            palette.setColor(QtGui.QPalette.Base, INVALIDROWCOLOUR)
            state = QtGui.QValidator.Intermediate  # entry is NOT valid, but can continue editing
        self.parent().setPalette(palette)

        return state, p_str, p_int

    def clearValidCheck(self):
        palette = self.parent().palette()
        palette.setColor(QtGui.QPalette.Base, self.baseColour)
        self.parent().setPalette(palette)

    def resetCheck(self):
        self.validate(self.parent().text(), 0)

    @property
    def checkState(self):
        state, _, _ = self.validate(self.parent().text(), 0)
        return state


#=========================================================================================
# LineEditValidatorWhiteSpace
#=========================================================================================

class LineEditValidatorWhiteSpace(LineEditValidator):
    """Validator to restrict input to non-whitespace characters
    """

    def __init__(self, parent=None, allowSpace=True, allowEmpty=True, allowPeriod=False):
        super().__init__(parent=parent, allowSpace=allowSpace, allowEmpty=allowEmpty)

        self._allowPeriod = allowPeriod

    def _isValidInput(self, value):
        """Return True if the name does not contain any bad characters
        """
        notAllowedSequences = {'Illegal_Characters': '[^A-Za-z0-9_ \#\!\@\£\$\%\&\*\(\)\-\=\_\+\[\]\{\}\;\.]+',
                               'Empty_Spaces'      : '\s',
                               'Period'            : '\.',
                               }

        if not value and not self._allowEmpty:
            return False
        if self._allowSpace:
            notAllowedSequences.pop('Empty_Spaces')
        if self._allowPeriod:
            notAllowedSequences.pop('Period')
        return not any(re.findall(seq, value) for seq in notAllowedSequences.values())


#=========================================================================================
# LineEditValidatorCoreObject
#=========================================================================================

class LineEditValidatorCoreObject(QtGui.QValidator):
    """Validator to restrict input to non-whitespace characters
    and restrict input to the names not already in the core object klass
    """

    def __init__(self, parent=None, target=None, klass=None, allowSpace=True, allowEmpty=True, warnRename=False):
        super().__init__(parent=parent)

        # self.baseColour = self.parent().palette().color(QtGui.QPalette.Base)
        self.baseColour = QtGui.QColor('#ffffff')  # why the wrong colour?
        self._parent = parent
        self._allowSpace = allowSpace
        self._allowEmpty = allowEmpty
        self._warnRename = warnRename
        self._pluralLinkName = klass._pluralLinkName
        self._target = target

    def _isValidInput(self, value):
        """Return True if the name does not contain any bad characters
        """
        notAllowedSequences = {'Illegal_Characters': '[^A-Za-z0-9_ \#\!\@\£\$\%\&\*\(\)\-\=\_\+\[\]\{\}\;]+',
                               'Empty_Spaces'      : '\s',
                               }

        if not value and not self._allowEmpty:
            return False
        if self._allowSpace:
            notAllowedSequences.pop('Empty_Spaces')
        return not any(re.findall(seq, value) for seq in notAllowedSequences.values())

    def nameFromLineEdit(self, value):
        """Build the name from the lineEdit to compare against the target objects
        """
        # Subclass as required, or replace with a lambda function
        return f'{value}'

    def _isValidObject(self, value):
        """Return True if the name does not exist in the target objects
        """
        # check klass objects
        if self._pluralLinkName and self._target:
            _found = [obj.name for obj in getattr(self._target, self._pluralLinkName, ())]
            if self.nameFromLineEdit(value) in _found:
                return False

        return True

    def validate(self, p_str, p_int):
        """Set the colour/valid state depending on the name and objects in the target list
        """
        palette = self.parent().palette()
        if not p_str:
            palette.setColor(QtGui.QPalette.Base, self.baseColour)
            state = QtGui.QValidator.Acceptable  # treat empty entry is valid
        elif self._isValidInput(p_str):
            if self._warnRename and not self._isValidObject(p_str):
                palette.setColor(QtGui.QPalette.Base, WARNINGROWCOLOUR)
                state = QtGui.QValidator.Intermediate  # entry is valid, but warn for bad object (only if renaming later)
            else:
                palette.setColor(QtGui.QPalette.Base, self.baseColour)
                state = QtGui.QValidator.Acceptable  # entry is valid
        else:
            palette.setColor(QtGui.QPalette.Base, INVALIDROWCOLOUR)
            state = QtGui.QValidator.Intermediate  # entry is NOT valid, but can continue editing
        if not getattr(self.parent(), VALIDATEASICON, False):
            self.parent().setPalette(palette)

        return state, p_str, p_int

    def clearValidCheck(self):
        palette = self.parent().palette()
        palette.setColor(QtGui.QPalette.Base, self.baseColour)
        self.parent().setPalette(palette)

    def resetCheck(self):
        self.validate(self.parent().text(), 0)

    @property
    def checkState(self):
        state, _, _ = self.validate(self.parent().text(), 0)
        return state

    @property
    def isValid(self):
        state, _, _ = self.validate(self.parent().text(), 0)
        return state == QtGui.QValidator.Acceptable


#=========================================================================================
# Subclassed validators
#=========================================================================================

class LineEditValidatorCoreObjectMergeName(LineEditValidatorCoreObject):
    """Validator to restrict input to non-whitespace characters
    and restrict input to the names not already in the core object klass
    Comparison name is constructed from <target-name>_<lineEdit>
    """

    def nameFromLineEdit(self, value):
        """Build the name from the lineEdit to compare against the target objects
        """
        return f'{self._target.name}_{value}' if self._target else f'{value}'

    @property
    def isValid(self):
        """Reurn True if valid and renames are allowed
        """
        p_str = self.parent().text()
        if self._isValidInput(p_str):
            if self._warnRename and not self._isValidObject(p_str):
                return QtGui.QValidator.Intermediate  # entry is valid, but warn for bad object (only if renaming later)
            else:
                return QtGui.QValidator.Acceptable  # entry is valid
        else:
            return QtGui.QValidator.Invalid  # entry is NOT valid, but can continue editing
