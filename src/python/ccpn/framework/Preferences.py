"""
This file contains the Preference object and related methods;
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
__dateModified__ = "$dateModified: 2024-10-16 10:05:19 +0100 (Wed, October 16, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2022-01-18 10:28:48 +0000 (Tue, January 18, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import json
from itertools import chain

from ccpn.ui.gui.guiSettings import FONTLIST
from ccpn.util.AttrDict import AttrDict
from ccpn.util.Logging import getLogger
from ccpn.util.decorators import singleton
from ccpn.util.Path import aPath
from ccpn.util.Common import uniquify, isMacOS, isLinux

from ccpn.framework.PathsAndUrls import (userPreferencesPath,
                                         userPreferencesPathInvalid,
                                         userPreferencesDirectory,
                                         defaultPreferencesPath)
from ccpn.framework.Application import getApplication


ARIA_PATH = 'externalPrograms.aria'
CYANA_PATH = 'externalPrograms.cyana'
XPLOR_NIH_PATH = 'externalPrograms.xplor'
TALOS_PATH = 'externalPrograms.talos'
PYMOL_PATH = 'externalPrograms.pymol'

USER_DATA_PATH = 'general.dataPath'
USER_MACRO_PATH = 'general.userMacroPath'
USER_PLUGIN_PATH = 'general.userPluginPath'
USER_PIPES_PATH = 'general.userPipesPath'
USER_LAYOUTS_PATH = 'general.userLayoutsPath'

PRINT_OPTIONS = 'printSettings.printOptions'
USE_PROJECT_PATH = 'general.useProjectPath'
APPEARANCE = 'appearance'


def getPreferences():
    """Return the Preferences instance"""
    if (app := getApplication()) is None:
        raise RuntimeError('getPreferences: application has not registered itself!')
    return app.preferences


@singleton
class Preferences(AttrDict):
    """A singleton class to hold the preferences,
    implemented as a AttrDict-of-AttrDict-of-AttrDict
    """

    def __init__(self, application, userPreferences=True):
        super().__init__()

        # self._applicationVersion = str(application.applicationVersion) # removed to fix order of operations
        self._lastPath = None

        if not userPreferencesDirectory.exists():
            userPreferencesDirectory.mkdir()

        # read the default preference and populate self so all valid keys
        # are defined
        self.update(self._getDefaultPreferences())
        if userPreferences:
            self._getUserPreferences()

        # needs to be after user prefs are loaded as this is always true
        self._applicationVersion = str(application.applicationVersion)
        self._overrideDefaults(self)
        self._updateOldPrefs(self)

    def _readPreferencesFile(self, path):
        """Read the preference from the json file path,
        :return the json encoded preferences object
        """
        path = aPath(path)
        if not path.exists():
            return None

        with path.open(mode='r') as fp:
            _prefs = json.load(fp, object_hook=AttrDict)

        self._lastPath = str(path)

        # self._overrideDefaults(_prefs)

        return _prefs

    def _getDefaultPreferences(self):
        """Return the default preferences file.
        """
        if _prefs := self._readPreferencesFile(defaultPreferencesPath):
            return _prefs
        raise ValueError(f'Preferences._readPreferences: path {defaultPreferencesPath} does not exist')

    def _getUserPreferences(self):
        """Read the user preferences file, updating the current values
        """
        if _prefs := self._readPreferencesFile(userPreferencesPath):
            _prefs["_lastPath"] = self._lastPath  # forces correct path
            self._recursiveUpdate(theDict=self, updateDict=_prefs)
            self._validatePrefs(_prefs)
        # just some patches to the data
        self.recentMacros = uniquify(self.recentMacros)
        return _prefs

    def _saveUserPreferences(self):
        """Save the current preferences to the user preferences file
        """
        diffDict = {"_applicationVersion" : self._applicationVersion,
                    "_lastPath" : self._lastPath}

        _defPrefs = self._readPreferencesFile(defaultPreferencesPath)

        self.recentMacros = self.recentMacros[-10:]
        self.recentFiles = self.recentFiles[-10:]

        for dd in self:
            if isinstance(tab := self[dd], (AttrDict, dict)):
                for key, value in tab.items():
                    # set to new value if not default
                    try:
                        if value != _defPrefs[dd][key]:
                            diffDict.setdefault(dd, {})
                            diffDict[dd][key] = value
                    except KeyError:
                        # store the key in the output
                        #   these will be discarded on loading preferences until
                        #   keys are defined in defaultv3settings (but not required now)
                        diffDict.setdefault(dd, {})
                        diffDict[dd][key] = value

            if isinstance(ll := self[dd], list) and ll:
                diffDict[dd] = ll

        with userPreferencesPath.open(mode='w') as fp:
            json.dump(diffDict, fp, indent=4)

    def _recursiveUpdate(self, theDict, updateDict):
        """update theDict with key,value from updateDict, if key exists in theDict
        Recursively update, by expanding any dict-like value first
        """
        if not isinstance(theDict, (dict, AttrDict)):
            raise ValueError(f'Preferences._recursiveUpdate: invalid dict  {theDict}')

        if not isinstance(updateDict, (dict, AttrDict)):
            raise ValueError(f'Preferences._recursiveUpdate: invalid updateDict  {updateDict}')

        for key, value in theDict.items():
            # check and update for any keys in theDict that are in updateDict
            if key in updateDict :
                updateValue = updateDict[key]

                if isinstance(value, (dict, AttrDict)):
                    self._recursiveUpdate(value, updateValue)

                else:
                    theDict[key] = updateValue

    dashes = '-' * 5

    def _recursivePrint(self, theDict, keys=None):
        """print (key, value) of theDict, recursively expanding key for dict-like value's
        """
        if keys is None:
            keys = []

        for key, value in theDict.items():
            _keys = keys[:] + [key]

            if isinstance(value, AttrDict) and len(_keys) < 2:
                self._recursivePrint(value, keys=_keys)

            else:
                _keyStr = '.'.join(_keys)
                print(f'{_keyStr:40} : {repr(value)}')

    def get(self, key, default=None):
        """Return the value for key if key is in the dictionary, else default.
        Check for key to be a "dotted" one; e.g. "aap.noot" If so, recusively
        decent.
        """
        if key is None or not isinstance(key, str) or len(key) == 0:
            raise KeyError(f'invalid key {repr(key)}')

        _keys = key.split('.')
        _value = AttrDict.get(self, _keys[0], default)

        if _value is None or \
                len(_keys) == 1 or \
                len(_keys) > 1 and len(_keys[1]) == 0:
            return _value

        elif isinstance(_value, (dict, AttrDict)):
            # Re
            return Preferences.get(_value, '.'.join(_keys[1:]), default=default)

        else:
            raise KeyError(f'invalid key {repr(key)}; unable to decode')

    def print(self):
        """Print items of self
        """
        print(self.dashes, self, self.dashes)
        self._recursivePrint(self)

    def __str__(self):
        return f'<Preferences: {repr(self._lastPath)}>'

    @staticmethod
    def _overrideDefaults(prefs):
        """Override any settings that are currently causing problems
        """
        # NOTE:ED - there is a bug in pyqt5.12.3 that causes a crash when using QWebEngineView
        prefs.general.useNativeWebbrowser = True
        prefs.general.backupSaveEnabled = True
        if (pr := prefs.get(APPEARANCE)) is None:
            # appearance is not in very early settings
            return

        pr.useOnlineDocumentation = False
        # if the fonts have not been defined, copy from the OS-specific settings
        if isMacOS():
            fontPrefix = 'MacOS'
        elif isLinux():
            fontPrefix = 'Linux'
        else:
            fontPrefix = 'MS'
        # iterate through the current fonts
        for fontNum, fontName in enumerate(FONTLIST):
            prefFont = f'font{fontNum}'
            frmFont = f'{fontPrefix}{prefFont}'
            # set from the default for the OS-specific
            if not pr.get(prefFont):
                pr[prefFont] = pr.get(frmFont, '')

    @staticmethod
    def _updateOldPrefs(prefs):
        """update any changed preferences to ensure correct type
        """
        # 3.2.7
        if prefs.general.useProjectPath in [True, 'True']:
            # previously checkbox now Key
            prefs.general.useProjectPath = 'Alongside'
        elif prefs.general.useProjectPath in [False, 'False']:
            # shouldn't reach this, as cur/prev default
            prefs.general.useProjectPath = 'User-defined'

    def _validatePrefs(self, prefs):
        """Validated preferences are of the correct type
         compared to the default

         :param prefs: preferences dict to be checked
         """
        defPref = self._getDefaultPreferences()
        invalidPrefs = False
        try:
            # should probably make this recursive to be more thorough
            for subDictKey in list(chain(prefs)):
                subDict = prefs[subDictKey]
                if isinstance(subDict, (AttrDict, dict)):
                    for key, value in subDict.items():
                        if not isinstance(value, type(defPref[subDictKey][key])):
                            # This is the only default 'null' value
                            if key == "traceColour":
                                continue
                            invalidPrefs = True
                            try:
                                self[subDictKey][key] = type(defPref[subDictKey][key])(value)
                                getLogger().warning(f'Preference {key} type corrected to {type(defPref[subDictKey][key])}')
                            except TypeError:
                                # set value to default if of wrong type.
                                self[subDictKey][key] = defPref[subDictKey][key]
                                getLogger().warning(f'Preference {key} should be type: {type(defPref[subDictKey][key])} \
                                                    setting to default.')
        except KeyError as e:
            # Catch any bigger inconsistencies in the dictionaries
            getLogger().error(f'Preferences validation error: {repr(e)}')

        if invalidPrefs:
            # saves a copy of the bad preferences for the user.
            if not (invDir := userPreferencesPathInvalid).exists():
                invDir.mkdir(parents=True, exist_ok=True)

            invFile = invDir / f'v3settings-{prefs._applicationVersion}.json'
            with invFile.open(mode='w') as fp:
                json.dump(prefs, fp, indent=4)

            getLogger().warning(f'Invalid Settings file backed-up ({invFile.asString()})')
