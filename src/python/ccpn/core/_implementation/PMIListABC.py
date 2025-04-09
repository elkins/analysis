"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-04-09 18:01:04 +0100 (Wed, April 09, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-05-26 14:50:42 +0000 (Tue, May 26, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================


import re
from typing import Optional, Union
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.Spectrum import Spectrum
from ccpn.util.decorators import logCommand


COLOURCHECK = '#[a-fA-F0-9]{6}$'
INHERITCOLOUR = '#'


class PMIListABC(AbstractWrapperObject):
    """An ABC object containing Peaks/Multiplets/Integrals.
    Note: the object is not a (subtype of a) Python list.
    To access all List objects, use List.items."""

    # The following attributes must be subclassed - change to traits?

    #: Short class name, for PID.
    shortClassName = 'Undefined'
    # Attribute it necessary as subclasses must use superclass className
    className = 'Undefined'

    _parentClass = Spectrum
    _primaryChildClass = None

    #: Name of plural link to instances of class
    _pluralLinkName = 'Undefined'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = None

    # internal namespace
    _MERITCOLOUR = 'meritColour'
    _MERITENABLED = 'meritEnabled'
    _MERITTHRESHOLD = 'meritThreshold'
    _LINECOLOUR = 'lineColour'
    _SYMBOLCOLOUR = 'symbolColour'
    _TEXTCOLOUR = 'textColour'
    _ARROWCOLOUR = 'arrowColour'

    # Special error-raising functions as this is a container for a list
    def __iter__(self):
        raise TypeError(f"'{self.className} object is not iterable - "
                        f"for a list of {self._primaryChildClass._pluralLinkName} "
                        f"use {self.className}.{self._primaryChildClass._pluralLinkName}")

    def __getitem__(self, index):
        raise TypeError(f"'{self.className} object does not support indexing - "
                        f"for a list of {self._primaryChildClass._pluralLinkName} "
                        f"use {self.className}.{self._primaryChildClass._pluralLinkName}")

    def __len__(self):
        raise TypeError(f"'{self.className} object has no length - "
                        f"for a list of {self._primaryChildClass._pluralLinkName} "
                        f"use {self.className}.{self._primaryChildClass._pluralLinkName}")

    def _setPrimaryChildClass(self):
        """Set the primary classType for the child list attached to this container
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self._setPrimaryChildClass()

    #=========================================================================================
    # CCPN properties
    #=========================================================================================

    @property
    def _key(self) -> str:
        """id string - serial number converted to string."""
        return str(self._wrappedData.serial)

    @property
    def serial(self) -> int:
        """serial number of List, used in Pid and to identify the List."""
        return self._wrappedData.serial

    @property
    def spectrum(self) -> Spectrum:
        """Spectrum containing list."""
        return self._project._data2Obj[self._wrappedData.dataSource]

    _parent: Spectrum = spectrum

    @property
    def title(self) -> str:
        """title of List (not used in PID)."""
        return self._wrappedData.name

    @title.setter
    def title(self, value: str):
        self._wrappedData.name = value

    @property
    def symbolStyle(self) -> str:
        """Symbol style for annotation display in all displays."""
        return self._wrappedData.symbolStyle

    @symbolStyle.setter
    @logCommand(get='self', isProperty=True)
    def symbolStyle(self, value: str):
        self._wrappedData.symbolStyle = value

    @property
    def symbolColour(self) -> str:
        """Symbol colour for annotation display in all displays.
        symbolColour must be a valid hex colour string '#ABCDEF' or '#' to denote an auto-colour (take colour from spectrum).
        Lowercase will be changed to uppercase.
        """
        return self._wrappedData.symbolColour

    @symbolColour.setter
    @logCommand(get='self', isProperty=True)
    def symbolColour(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"symbolColour must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")
        if not (re.findall(COLOURCHECK, value) or value == INHERITCOLOUR):
            raise ValueError(f"symbolColour {value} not defined correctly, must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")

        value = value.upper()
        self._wrappedData.symbolColour = value

    @property
    def textColour(self) -> str:
        """Text colour for annotation display in all displays.
        textColour must be a valid hex colour string '#ABCDEF' or '#' to denote an auto-colour (take colour from spectrum).
        Lowercase will be changed to uppercase.
        """
        return self._wrappedData.textColour

    @textColour.setter
    @logCommand(get='self', isProperty=True)
    def textColour(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"textColour must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")
        if not (re.findall(COLOURCHECK, value) or value == INHERITCOLOUR):
            raise ValueError(f"textColour {value} not defined correctly, must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")

        value = value.upper()
        self._wrappedData.textColour = value

    @property
    def isSynthetic(self) -> bool:
        """True if this List is simulated."""
        return self._wrappedData.isSimulated

    @isSynthetic.setter
    @logCommand(get='self', isProperty=True)
    def isSynthetic(self, value: bool):
        self._wrappedData.isSimulated = value

    @property
    def isSimulated(self) -> bool:
        """True if this List is simulated.
        .. note:: This is a depreciated version of isSynthetic
                  and only exists to allow old project saves to work"""
        return self.isSynthetic

    @isSimulated.setter
    @logCommand(get='self', isProperty=True)
    def isSimulated(self, value: bool):
        self._wrappedData.isSynthetic = value

    # @property
    # def isSimulated(self) -> bool:
    #     return self._wrappedData.isSimulated
    #
    # @isSimulated.setter
    # @logCommand(get='self', isProperty=True)
    # def isSimulated(self, value: bool):
    #     self._wrappedData.isSimulated = value

    @property
    def meritColour(self) -> Optional[str]:
        """merit colour for annotation display in all displays.
        meritColour must be a valid hex colour string '#ABCDEF' or '#' to denote an auto-colour (take colour from spectrum).
        Lowercase will be changed to uppercase.
        """
        return self._getInternalParameter(self._MERITCOLOUR)

    @meritColour.setter
    @logCommand(get='self', isProperty=True)
    def meritColour(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"meritColour must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")
        if not (re.findall(COLOURCHECK, value) or value == INHERITCOLOUR):
            raise ValueError(f"meritColour {value} not defined correctly, must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")

        value = value.upper()
        self._setInternalParameter(self._MERITCOLOUR, value)

    @property
    def meritEnabled(self) -> Optional[bool]:
        """Flag to enable merit threshold for annotation display in all displays.
        Must be True/False.
        """
        return self._getInternalParameter(self._MERITENABLED)

    @meritEnabled.setter
    @logCommand(get='self', isProperty=True)
    def meritEnabled(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError("meritEnabled must be True/False.")

        self._setInternalParameter(self._MERITENABLED, value)

    @property
    def meritThreshold(self) -> float:
        """Threshold to determine merit colouring for annotation display in all displays.
        Must be a float in the range [0.0, 1.0]
        """
        return self._getInternalParameter(self._MERITTHRESHOLD)

    @meritThreshold.setter
    @logCommand(get='self', isProperty=True)
    def meritThreshold(self, value: Union[float, int]):
        if not isinstance(value, (float, int)):
            raise TypeError("meritThreshold must be a float or integer")
        if not (0.0 <= value <= 1.0):
            raise ValueError("meritThreshold must be in the range [0.0, 1.0]")
        value = float(value)

        self._setInternalParameter(self._MERITTHRESHOLD, value)

    @property
    def lineColour(self) -> str:
        """line colour for annotation display in all displays.
        lineColour must be a valid hex colour string '#ABCDEF' or '#' to denote an auto-colour (take colour from spectrum).
        Lowercase will be changed to uppercase.
        """
        return self._getInternalParameter(self._LINECOLOUR)

    @lineColour.setter
    @logCommand(get='self', isProperty=True)
    def lineColour(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"lineColour must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")
        if not (re.findall(COLOURCHECK, value) or value == INHERITCOLOUR):
            raise ValueError(f"lineColour {value} not defined correctly, must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")

        value = value.upper()
        self._setInternalParameter(self._LINECOLOUR, value)

    @property
    def arrowColour(self) -> Optional[str]:
        """arrow colour for annotation display in all displays.
        arrowColour must be a valid hex colour string '#ABCDEF' or '#' to denote an auto-colour (take colour from spectrum).
        Lowercase will be changed to uppercase.
        """
        return self._getInternalParameter(self._ARROWCOLOUR)

    @arrowColour.setter
    @logCommand(get='self', isProperty=True)
    def arrowColour(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"arrowColour must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")
        if not (re.findall(COLOURCHECK, value) or value == INHERITCOLOUR):
            raise ValueError(f"arrowColour {value} not defined correctly, must be a hex colour string (e.g. '#ABCDEF' or '{INHERITCOLOUR}')")

        value = value.upper()
        self._setInternalParameter(self._ARROWCOLOUR, value)

    #=========================================================================================
    # Implementation functions
    #=========================================================================================

    @classmethod
    def _restoreObject(cls, project, apiObj):
        """Restore the object and update ccpnInternalData
        """
        MERITSETTINGS = 'meritSettings'
        MERITCOLOUR = 'meritColour'
        MERITENABLED = 'meritEnabled'
        MERITTHRESHOLD = 'meritThreshold'
        LINESETTINGS = 'lineSettings'
        LINECOLOUR = 'lineColour'
        SYMBOLCOLOUR = 'symbolColour'
        TEXTCOLOUR = 'textColour'
        ARROWCOLOUR = 'arrowColour'

        result = super()._restoreObject(project, apiObj)

        for namespace, param, newVar in [(MERITSETTINGS, MERITCOLOUR, cls._MERITCOLOUR),
                                         (MERITSETTINGS, MERITENABLED, cls._MERITENABLED),
                                         (MERITSETTINGS, MERITTHRESHOLD, cls._MERITTHRESHOLD),
                                         (LINESETTINGS, LINECOLOUR, cls._LINECOLOUR),
                                         (LINESETTINGS, SYMBOLCOLOUR, cls._SYMBOLCOLOUR),
                                         (LINESETTINGS, TEXTCOLOUR, cls._TEXTCOLOUR),
                                         (LINESETTINGS, ARROWCOLOUR, cls._ARROWCOLOUR),
                                         ]:
            if result.hasParameter(namespace, param):
                # move the internal parameter to the correct namespace
                value = result.getParameter(namespace, param)
                result.deleteParameter(namespace, param)
                result._setInternalParameter(newVar, value)

        return result

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    # None
