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
__dateModified__ = "$dateModified: 2024-10-15 17:45:58 +0100 (Tue, October 15, 2024) $"
__version__ = "$Revision: 3.2.6 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-07-04 15:21:16 +0000 (Tue, July 04, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import difflib
import hashlib
import os
import shutil
import sys
import json
from datetime import datetime
from contextlib import suppress
from ccpn.util import Path
from ccpn.framework.Version import applicationVersion
from ccpn.ui.gui.guiSettings import consoleStyle


ccpn2Url = 'https://www.ccpn.ac.uk'

SERVER = ccpn2Url + '/'
SERVER_DB_ROOT = 'ccpNmrUpdate'
SERVER_DB_FILE = '__UpdateData.db'
# the reason to use a CGI script just to download a file is because of exception handling
# when you just fetch a URL you always get a response but how do you know it is valid
# (and not a 404 or whatever)
SERVER_DOWNLOAD_SCRIPT = 'cgi-bin/update/downloadFile'
SERVER_UPLOAD_SCRIPT = 'cgi-bin/updateadmin/uploadVerifyBeta1'
SERVER_DOWNLOADCHECK_SCRIPT = 'cgi-bin/register/downloadFileCheckV3'

FIELD_SEP = '\t'
PATH_SEP = '__sep_'
WHITESPACE_AND_NULL = {'\x00', '\t', '\n', '\r', '\x0b', '\x0c'}

# require only . and numbers and at least one of these
# 23 Nov 2015: remove below RE because version can have letter in it, so just do exact match
###VERSION_RE = re.compile('^[.\d]+$')

BAD_DOWNLOAD = 'Exception: '
ERROR_DOWNLOAD = 'Error: '
DELETEHASHCODE = '<DELETE>'
TERMSANDCONDITIONS = 'termsConditions'

VERSION_UPDATE_FILE = 'src/python/ccpn/framework/Version.py'
ZIPFILE = 'zip'

SUCCESS = 0
SUCCESS_VERSION = 1
SUCCESS_RELEASE = 2
SUCCESS_MICROUPDATE = 4  # bit alternates between 0|1 when updating micro-version
SUCCESS_MINORUPDATE = 8  # --ditto-- minor-version
SUCCESS_MAJORUPDATE = 16
FAIL_UNEXPECTED = 32
FAIL_NOTUPDATED = 33
FAIL_WRITEERROR = 34
MAX_COUNT = 16


def lastModifiedTime(filePath):
    if not os.path.isfile(filePath):
        return 0

    if not os.access(filePath, os.R_OK):
        return 0

    return os.stat(filePath).st_mtime


def isBinaryFile(fileName):
    """Check whether the fileName is a binary file (not always guaranteed)
    Doesn't check for a fullPath
    Returns False if the file does not exist
    """
    if os.path.isfile(fileName):
        with open(fileName, 'rb') as fileObj:
            # read the first 1024 bytes of the file
            firstData = fileObj.read(1024)

            # remove all characters that are considered as text
            textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
            isBinary = bool(firstData.translate(None, textchars))

            return isBinary


def isBinaryData(data):
    """Check whether the byte-string is binary
    """
    if data:
        # check the first 1024 bytes of the file
        firstData = data[0:max(1024, len(data))]
        try:
            firstData = bytearray(firstData)
        except:
            firstData = bytearray(firstData, encoding='utf-8')

        # remove all characters that are considered as text
        textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
        isBinary = bool(firstData.translate(None, textchars))

        return isBinary


def calcHashCode(filePath):
    if not os.path.isfile(filePath):
        return 0

    if not os.access(filePath, os.R_OK):
        return 0

    try:
        if isBinaryFile(filePath):
            with open(filePath, 'rb') as fp:
                data = fp.read()
        else:
            with open(filePath, 'r', encoding='utf-8') as fp:
                data = fp.read()
            data = bytes(data, 'utf-8')
    except Exception:
        data = ''

    h = hashlib.md5()
    h.update(data)

    return h.hexdigest()


def fetchUrl(url, data=None, headers=None, timeout=2.0, decodeResponse=True):
    """Fetch url request from the server
    """
    from ccpn.util.Url import fetchHttpResponse
    from ccpn.util.UserPreferences import UserPreferences

    try:
        _userPreferences = UserPreferences(readPreferences=True)
        proxySettings = None
        if _userPreferences.proxyDefined:
            proxyNames = ['useProxy', 'proxyAddress', 'proxyPort', 'useProxyPassword',
                          'proxyUsername', 'proxyPassword', 'verifySSL']
            proxySettings = {}
            for name in proxyNames:
                proxySettings[name] = _userPreferences._getPreferencesParameter(name)

        response = fetchHttpResponse('POST', url, data, headers=headers, proxySettings=proxySettings)

        # if response:
        #     ll = len(response.data)
        #     print('>>>>>>responseUpdate', proxySettings, response.data[0:min(ll, 20)])

        return response.data.decode('utf-8') if decodeResponse else response
    except:
        print('Error fetching Url.')


def downloadFile(serverScript, serverDbRoot, fileName, quiet=False):
    """Download a file from the server
    """
    # fileName = os.path.join(serverDbRoot, fileName)
    fileName = '/'.join(list(filter(lambda val: bool(val), [serverDbRoot, fileName])))

    try:
        values = {'fileName': fileName}
        response = fetchUrl(serverScript, values, decodeResponse=False)
        if response is not None:
            data = response.data

            if isBinaryData(data):
                result = data
            else:
                result = data.decode('utf-8')

                if result.startswith(BAD_DOWNLOAD):
                    if not quiet:
                        ll = len(result)
                        bd = len(BAD_DOWNLOAD)
                        print(str(result[min(ll, bd):min(ll, bd + 50)]))
                    return

            return result

        else:
            raise ValueError('No file found')

    except Exception as es:
        print(f'Error downloading file from server. {es}')


def installUpdates(version, dryRun=True):
    updateAgent = UpdateAgent(version, dryRun=dryRun)
    updateAgent.resetFromServer()
    updateAgent.installUpdates()
    if updateAgent._check():
        updateAgent._resetMd5()

    return updateAgent.exitCode


def getUpdateCount(version):
    """Return the number of updates for the specified version.
    """
    updateAgent = UpdateAgent(version)
    return updateAgent.checkNumberUpdates()


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# UpdateFile
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UpdateFile:

    def __init__(self, installLocation, serverDbRoot, filePath, fileServerTime=None,
                 fileStoredAs=None, fileHashCode=None, shouldInstall=True, shouldCommit=False,
                 isNew=False, serverDownloadScript=None, serverUploadScript=None):

        # self.fullFilePath = os.path.join(installLocation, filePath)
        self.fullFilePath = os.path.abspath(os.path.join(installLocation, filePath))

        if fileServerTime:
            fileServerTime = float(fileServerTime)  # from server it comes as a string

        if not fileStoredAs:
            fileStoredAs = PATH_SEP.join(filePath.split('/'))

        if not fileHashCode:
            fileHashCode = calcHashCode(self.fullFilePath)

        self.installLocation = installLocation
        self.serverDbRoot = serverDbRoot
        self.filePath = filePath
        self.fileServerTime = fileServerTime
        self.fileStoredAs = fileStoredAs
        self.fileHashCode = fileHashCode
        self.shouldInstall = shouldInstall
        self.shouldCommit = shouldCommit
        self.isNew = isNew
        self.serverDownloadScript = serverDownloadScript
        self.serverUploadScript = serverUploadScript

        self.fileLocalTime = lastModifiedTime(self.fullFilePath)

        self.fileServerDateTime = str(datetime.fromtimestamp(fileServerTime)) if fileServerTime else ''
        self.fileLocalDateTime = str(datetime.fromtimestamp(self.fileLocalTime))
        self.fileName = os.path.basename(filePath)
        self.fileDir = os.path.dirname(filePath)

    def installUpdate(self):
        """Install updated file
        """
        data = downloadFile(self.serverDownloadScript, self.serverDbRoot, self.fileStoredAs)

        if data is None:
            return

        fullFilePath = self.fullFilePath
        if os.path.isfile(fullFilePath):
            # backup what is there just in case
            shutil.copyfile(fullFilePath, fullFilePath + '__old')
        else:
            directory = os.path.dirname(fullFilePath)
            if not os.path.exists(directory):
                os.makedirs(directory)

        try:
            if isBinaryData(data):
                # always write binary files
                with open(fullFilePath, 'wb') as fp:
                    fp.write(data)

            else:
                # backwards compatible check for half-updated - file contains DELETEHASHCODE as text
                if data and data.startswith(DELETEHASHCODE):
                    os.remove(fullFilePath)

                else:
                    lastHashCode = calcHashCode(fullFilePath) if os.path.isfile(fullFilePath) else '<None>'
                    with open(fullFilePath, 'w', encoding='utf-8') as fp:
                        fp.write(data)

                    if Path.aPath(fullFilePath).suffix == '.py':
                        _file = Path.aPath(fullFilePath)
                        _name = _file.basename

                        # is a python file - remove the pycache to make sure that it loads correctly next time
                        pyDir = _file.filepath / '__pycache__'
                        if pyDir.exists() and pyDir.is_dir():
                            for fp in [Path.aPath(fp) for fp in pyDir.listdir()]:
                                if fp.basename == _name and fp.suffix == '.pyc':
                                    # print(f'cleaning pycache: {fp.name}')
                                    fp.removeFile()

                    # generate the hashcode for the new file here
                    currentHashCode = calcHashCode(fullFilePath)
                    serverHashCode = self.fileHashCode
                    _hashCodeCacheFolder = os.path.abspath(os.path.join(self.installLocation, '.cache'))
                    _hashCodeCache = os.path.join(_hashCodeCacheFolder, '_hashCodeCache.json')
                    if not os.path.exists(_hashCodeCache):
                        if not os.path.exists(_hashCodeCacheFolder):
                            os.makedirs(_hashCodeCacheFolder)
                        data = {}
                    else:
                        with open(_hashCodeCache) as fp:
                            data = json.load(fp)

                    if currentHashCode != serverHashCode:
                        # should only store for windows
                        if lastHashCode in data and lastHashCode != currentHashCode:
                            del data[lastHashCode]
                        data[currentHashCode] = serverHashCode

                    with open(_hashCodeCache, 'w') as fp:
                        json.dump(data, fp, indent=4)

            return True

        except Exception as es:
            pass

    def installDeleteUpdate(self):
        """Remove file as update action
        """
        fullFilePath = self.fullFilePath
        with suppress(OSError):
            os.remove(fullFilePath)
            return True

    # def commitUpdate(self, serverUser, serverPassword):
    #
    #     uploadFile(serverUser, serverPassword, self.serverUploadScript, self.fullFilePath, self.serverDbRoot,
    #                self.fileStoredAs)
    #     self.fileHashCode = calcHashCode(self.fullFilePath)


#=========================================================================================
# UpdateAgent
#=========================================================================================

class UpdateAgent:
    updateFileClass = UpdateFile

    def __init__(self, version, showError=None, showInfo=None, askPassword=None,
                 serverUser=None, server=SERVER, serverDbRoot=SERVER_DB_ROOT, serverDbFile=SERVER_DB_FILE,
                 serverDownloadScript=SERVER_DOWNLOAD_SCRIPT, serverUploadScript=SERVER_UPLOAD_SCRIPT,
                 _updateProgressHandler=None,
                 dryRun=True):

        self.version = version
        self.showError = showError or (lambda title, msg: print(f'{consoleStyle.fg.red}{msg}{consoleStyle.reset}'))
        self.showInfo = showInfo or (lambda title, msg: print(msg))
        self.askPassword = askPassword
        self.serverUser = serverUser  # None for downloads, not None for uploads
        self.server = server
        self.serverDbRoot = '%s%s' % (serverDbRoot, version)
        self.serverDbFile = serverDbFile
        self.serverDownloadScript = serverDownloadScript
        self._serverDownloadCheckScript = SERVER_DOWNLOADCHECK_SCRIPT
        self.serverUploadScript = serverUploadScript
        # self.serverDownloadScript = '%s%s' % (server, serverDownloadScript)
        # self.serverUploadScript = '%s%s' % (server, serverUploadScript)

        self.installLocation = Path.getTopDirectory()
        self.updateFiles = []
        self.updateFileDict = {}
        self._found = None

        self._updateProgressHandler = _updateProgressHandler
        self._dryRun = dryRun

        self.exitCode = 0

    def checkNumberUpdates(self):
        self.fetchUpdateDb()
        return len(self.updateFiles)

    def fetchUpdateDb(self):
        """Fetch list of updates from server."""

        self.updateFiles = updateFiles = []
        self.updateFileDict = updateFileDict = {}
        serverDownloadScript = '%s%s' % (self.server, self.serverDownloadScript)
        serverUploadScript = '%s%s' % (self.server, self.serverUploadScript)
        data = downloadFile(serverDownloadScript, self.serverDbRoot, self.serverDbFile, quiet=True)

        if not data:
            return

        if data.startswith(BAD_DOWNLOAD):
            self.showError('fetching updates', f'Error: Could not download database file from server - {data}')
            return

        if data.startswith(ERROR_DOWNLOAD):
            self.showError('fetching updates', data)
            return

        lines = data.split('\n')
        if lines:
            version = lines[0].strip()

            if version != self.version:
                self.showError('fetching updates', 'Error: Server database version => %s != %s' % (version, self.version))
                return

            for line in lines[1:]:
                line = line.rstrip()
                if line:
                    (filePath, fileTime, fileStoredAs, fileHashCode) = line.split(FIELD_SEP)

                    if fileHashCode == DELETEHASHCODE:
                        # delete file
                        if os.path.exists(os.path.join(self.installLocation, filePath)):
                            # if still exists then need to add to update list
                            updateFile = self.updateFileClass(self.installLocation, self.serverDbRoot, filePath, fileTime,
                                                              fileStoredAs, fileHashCode, serverDownloadScript=serverDownloadScript,
                                                              serverUploadScript=serverUploadScript)
                            updateFiles.append(updateFile)
                            updateFileDict[filePath] = updateFile

                    elif self.serverUser or self.isUpdateDifferent(filePath, fileHashCode):

                        # file exists, is modified and needs updating
                        updateFile = self.updateFileClass(self.installLocation, self.serverDbRoot, filePath, fileTime,
                                                          fileStoredAs, fileHashCode, serverDownloadScript=serverDownloadScript,
                                                          serverUploadScript=serverUploadScript)
                        updateFiles.append(updateFile)
                        updateFileDict[filePath] = updateFile

                    elif fileTime in [0, '0', '0.0']:

                        # file exists, is modified and needs updating
                        updateFile = self.updateFileClass(self.installLocation, self.serverDbRoot, filePath, fileTime,
                                                          fileStoredAs, fileHashCode, serverDownloadScript=serverDownloadScript,
                                                          serverUploadScript=serverUploadScript)
                        updateFiles.append(updateFile)
                        updateFileDict[filePath] = updateFile

    def isUpdateDifferent(self, filePath, fileHashCode):
        """See if local file is different from server file."""

        currentFilePath = os.path.join(self.installLocation, filePath)
        if os.path.exists(currentFilePath):
            currentHashCode = calcHashCode(currentFilePath)

            # get the translated hashcode from the json file in the .cache folder
            try:
                _hashCodeCacheFolder = os.path.abspath(os.path.join(self.installLocation, '.cache'))
                _hashCodeCache = os.path.join(_hashCodeCacheFolder, '_hashCodeCache.json')
                if os.path.exists(_hashCodeCache):
                    with open(_hashCodeCache) as fp:
                        data = json.load(fp)
                else:
                    data = {}
            except Exception as es:
                data = {}
            if currentHashCode in data:
                currentHashCode = data[currentHashCode]

            isDifferent = (currentHashCode != fileHashCode)
        # below means that updates in new directories will be missed
        elif os.path.exists(os.path.dirname(currentFilePath)):
            isDifferent = True
        else:
            # NOTE:ED - was originally False to stop new directories being created, but needed now
            isDifferent = True

        return isDifferent

    def _check(self):
        """Check the checkSum from the gui
        """
        try:
            self._checkMd5()
        except:
            pass
        finally:
            return self._found is not None and 'valid' not in self._found

    def _checkMd5(self):
        """Check the checkSum status on the server
        """
        serverDownloadScript = '%s%s' % (self.server, self._serverDownloadCheckScript)

        try:
            self._numAdditionalUpdates = 0
            self._found = 'invalid'
            from ccpn.util.Register import userAttributes, loadDict, _otherAttributes, _insertRegistration

            registrationDict = loadDict()
            if not registrationDict:
                self.showError('Update error', 'Could not read registration details')
                return

            val2 = _insertRegistration(registrationDict)
            values = {}
            for attr in userAttributes + _otherAttributes:
                if attr in registrationDict:
                    values[attr] = ''.join([c if 32 <= ord(c) < 128 else '_' for c in registrationDict[attr]])
            values.update(val2)
            values['version'] = self.version

            self._found = fetchUrl(serverDownloadScript, values, timeout=2.0, decodeResponse=True)
            if isinstance(self._found, str):
                # file returns with EOF chars on the end
                self._found = self._found.rstrip('\r\n')

        except:
            self.showError('Update error', 'Could not check details on server.')

    def _resetMd5(self):
        # only write the file if it is non-empty
        if self._found:
            # from ccpn.util.UserPreferences import userPreferencesDirectory, ccpnConfigPath
            from ccpn.framework.PathsAndUrls import userPreferencesDirectory, ccpnConfigPath

            fname = ''.join([c for c in map(chr, (108, 105, 99, 101, 110, 99, 101, 75, 101, 121, 46, 116, 120, 116))])
            lfile = os.path.join(userPreferencesDirectory, fname)
            if not os.path.exists(lfile):
                lfile = os.path.join(ccpnConfigPath, fname)
            msg = ''.join([c for c in map(chr, (117, 112, 100, 97, 116, 105, 110, 103, 32, 108, 105, 99, 101, 110, 99, 101))])
            self.showInfo('installing', msg)
            with open(lfile, 'w', encoding='UTF-8') as fp:
                fp.write(self._found)

    def resetFromServer(self):
        try:
            self.fetchUpdateDb()

        except Exception as e:
            self.showError('Update error', 'Could not fetch updates: %s' % e)

    def fetchChangeLog(self):
        serverDownloadScript = '%s%s' % (self.server, self.serverDownloadScript)
        data = downloadFile(serverDownloadScript, '', 'changeLog.json', quiet=True)

        if not data:
            return

        if data.startswith(BAD_DOWNLOAD):
            self.showError('fetching change-log', f'Error: Could not download change-log from server - {data}')
            return

        if data.startswith(ERROR_DOWNLOAD):
            self.showError('fetching change-log', data)
            return

        try:
            return json.loads(data)
        except Exception as es:
            self.showError('fetching change-log', f'Error: Could not download change-log from server - {es}')

    def addFiles(self, filePaths):

        serverDownloadScript = '%s%s' % (self.server, self.serverDownloadScript)
        serverUploadScript = '%s%s' % (self.server, self.serverUploadScript)
        installLocation = self.installLocation
        installErrorCount = 0
        existsErrorCount = 0
        for filePath in filePaths:
            if filePath.startswith(installLocation):
                filePath = filePath[len(installLocation) + 1:]
                if filePath in self.updateFileDict:
                    updateFile = self.updateFileDict[filePath]
                    updateFile.shouldCommit = True

                    self.showInfo('Add Files', 'File %s already in updates' % filePath)
                    existsErrorCount += 1
                else:
                    updateFile = self.updateFileClass(self.installLocation, self.serverDbRoot, filePath, shouldCommit=True,
                                                      isNew=True, serverDownloadScript=serverDownloadScript,
                                                      serverUploadScript=serverUploadScript)
                    self.updateFiles.append(updateFile)
                    self.updateFileDict[filePath] = updateFile
            else:
                self.showInfo('Ignoring Files', 'Ignoring "%s", not on installation path "%s"' % (filePath, installLocation))
                installErrorCount += 1

        if installErrorCount > 0:
            self.showError('Add file error', '%d file%s not added because not on installation path %s' % (
                installErrorCount, installErrorCount > 1 and 's' or '', installLocation))

        if existsErrorCount > 0:
            self.showError('Add file error',
                           '%d file%s not added because already in update list (but now selected for committal)' % (
                               existsErrorCount, existsErrorCount > 1 and 's' or ''))

    def haveWriteAccess(self):
        """See if write-access to local installation."""

        testFile = os.path.join(self.installLocation, '__write_test__')
        try:
            with open(testFile, 'w'):
                pass
            os.remove(testFile)
            return True

        except:
            return False

    def installChosen(self):
        """Download chosen server files to local installation.
        """
        from ccpn.framework.Version import applicationVersion

        updateFiles = [updateFile for updateFile in self.updateFiles if updateFile.shouldInstall]
        if not updateFiles:
            self.showError('No updates', 'No updates for installation')

            # success and version has NOT been updated
            self.exitCode = SUCCESS
            return

        self.exitCode = FAIL_UNEXPECTED  # catch anything unexpected

        n = 0
        updateFilesInstalled = []
        if self.haveWriteAccess():

            # # check that the last file to be updated is the Version.py
            # _allowVersionUpdate = True if (len(updateFiles) == 1 and updateFiles[0].filePath == VERSION_UPDATE_FILE) else False

            self.exitCode = FAIL_NOTUPDATED  # files not updated correctly

            # go through the list is updates and apply each, ignoring Version.py
            for updateFile in updateFiles:

                if self._updateProgressHandler:
                    self._updateProgressHandler()

                # skip the version update file until the next pass
                if updateFile.filePath == VERSION_UPDATE_FILE:
                    continue

                # apply the update
                n = self._updateSingleFile(n, updateFile, updateFilesInstalled)

            # check how many have been updated correctly
            #   if n == all updates, okay with no version update
            #   any lower => version.py still needs updating OR update errors
            ss = n != 1 and 's' or ''
            if n != len(updateFiles):

                notInstalled = list(set(updateFilesInstalled) ^ set(updateFiles))
                # check if only the version update file remains
                if notInstalled and len(notInstalled) == 1 and notInstalled[0].filePath == VERSION_UPDATE_FILE:

                    n = self._updateSingleFile(n, notInstalled[0], updateFilesInstalled)

                    # check whether the version update file installed correctly
                    ss = n != 1 and 's' or ''
                    if n == len(updateFiles):
                        self.showInfo('Update%s installed' % ss, '%d update%s installed successfully' % (n, ss))

                        # success and version has been updated
                        # keep the last bits which would alternate 0|1 as the version-number increases
                        self.exitCode = applicationVersion._bitHash()

                    else:
                        self.showError('Update problem', '%d update%s installed, %d not installed, see console for error messages' % (n, ss, len(updateFiles) - n))
                else:
                    self.showError('Update problem', '%d update%s installed, %d not installed, see console for error messages' % (n, ss, len(updateFiles) - n))

            else:
                self.showInfo('Update%s installed' % ss, '%d update%s installed successfully' % (n, ss))

                # success and version has NOT been updated
                self.exitCode = SUCCESS

        else:
            self.showError('No write permission', 'You do not have write permission in the CCPN installation directory')

            self.exitCode = FAIL_WRITEERROR  # no write permission

        self.resetFromServer()

        return updateFilesInstalled

    def _updateSingleFile(self, n, updateFile, updateFilesInstalled):
        ATTEMPTS = 2

        for attempt in range(ATTEMPTS):
            try:
                if self._dryRun:
                    if updateFile.fileHashCode == DELETEHASHCODE:
                        self.showInfo('Install Updates', f'dry-run Removing {updateFile.fullFilePath}')
                    else:
                        self.showInfo('Install Updates', f'dry-run Installing {updateFile.fullFilePath}')

                elif updateFile.fileHashCode == DELETEHASHCODE:
                    self.showInfo('Install Updates', f'Removing {updateFile.fullFilePath}')
                    if not updateFile.installDeleteUpdate():
                        raise RuntimeError("error deleting original file")

                else:
                    self.showInfo('Install Updates', f'Installing {updateFile.fullFilePath}')
                    if updateFile.installUpdate() is None:
                        raise RuntimeError("error installing update")

                n += 1
                updateFilesInstalled.append(updateFile)

            except Exception as e:
                retry = ' - retrying...' if attempt < (ATTEMPTS - 1) else ''
                self.showError('Install Error', f'Could not install {updateFile.fullFilePath}: {e} {retry}')

            else:
                break

        else:  # no_break
            self.showError('Install Error', f'Could not install {updateFile.fullFilePath} after {ATTEMPTS} attempts')

        return n

    def installUpdates(self):

        for updateFile in self.updateFiles:
            updateFile.shouldInstall = True

        if done := self.installChosen():
            for file in done:
                fp = Path.aPath(file.fullFilePath)
                if file.shouldInstall and \
                        fp.suffix == '.' + ZIPFILE and file.fileDir == '.updates':
                    # unzip as required
                    if self._dryRun:
                        self.showInfo('Unzipping', f'dry-run {file.fullFilePath} --> {file.installLocation}')
                    else:
                        try:
                            # unpack relative to the root of the installation - leading '/' and '..' are checked by shutil
                            self.showInfo('Unzipping', f'Unzipping {file.fullFilePath} --> {file.installLocation}')
                            shutil.unpack_archive(file.fullFilePath, extract_dir=file.installLocation, format=ZIPFILE)
                        except Exception as es:
                            self.showError('Install Error', f'Could not unzip file {file.fullFilePath}: {es}')
                            # need to discard the file?
                            with suppress(OSError):
                                fp.replace(fp.parent / '_' + fp.name)

        return done

    def diffUpdates(self, updateFiles=None, write=sys.stdout.write):

        if updateFiles is None:
            updateFiles = []

        serverDownloadScript = '%s%s' % (self.server, self.serverDownloadScript)
        for updateFile in updateFiles:
            fullFilePath = updateFile.fullFilePath
            write(60 * '*' + '\n')
            write('Diff for %s\n' % fullFilePath)
            if os.path.exists(fullFilePath):
                if updateFile.isNew:
                    write('No server copy of file\n')
                else:
                    haveDiff = False
                    with open(fullFilePath, 'rU', encoding='utf-8') as fp:
                        localLines = fp.readlines()
                    serverData = downloadFile(serverDownloadScript, self.serverDbRoot, updateFile.fileStoredAs)
                    if serverData:
                        serverLines = serverData.splitlines(True)
                        for line in difflib.context_diff(localLines, serverLines, fromfile='local', tofile='server'):
                            haveDiff = True
                            write(line)
                        if haveDiff:
                            write('\n')
                        else:
                            write('No diff\n')
                    else:
                        write('No file on server')
            else:
                write('No local copy of file\n')


def main(doCount=False, doVersion=False, dryRun=False):
    """Main code.
    Either:
        return the number of updates for the current version,
        return the version string,
        or both,
        or install the updates for the current version.
    """

    exitCode = 0  # success
    if doCount and doVersion:
        try:
            count = int(getUpdateCount(applicationVersion))
            print(f'{count}, {applicationVersion}')
        except Exception:
            print(f'-1, {applicationVersion}')

    elif doCount:
        try:
            count = int(getUpdateCount(applicationVersion))
            print(f'{count}')
        except Exception:
            print('-1')

    elif doVersion:
        print(str(applicationVersion))

    else:
        exitCode = installUpdates(applicationVersion, dryRun=dryRun)

    # test to assume that the micro version increments by one each time
    # exitCode = applicationVersion._bitHash()

    # code must be [0, 255] - 0 represents success
    if sys.platform[:3].lower() == 'win':
        os._exit(exitCode)
    else:
        sys.exit(exitCode)


if __name__ == '__main__':
    main(doCount=('--count' in sys.argv),
         doVersion=('--version' in sys.argv),
         dryRun=('--dry-run' in sys.argv))
