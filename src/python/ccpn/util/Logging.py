"""CCPN logger handling

"""
from __future__ import annotations


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
__dateModified__ = "$dateModified: 2025-03-21 15:35:52 +0000 (Fri, March 21, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Wayne Boucher $"
__date__ = "$Date: 2017-03-17 12:22:34 +0000 (Fri, March 17, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import datetime
import functools
import logging
import os
import time
import inspect
import sys
import re
from typing import cast
from ccpn.util.Path import aPath


DEBUG = DEBUG1 = logging.DEBUG  # = 10
DEBUG2 = 9
DEBUG3 = 8
INFO = logging.INFO
WARNING = logging.WARNING

defaultLogLevel = logging.INFO
# defaultLogLevel = logging.DEBUG

# this code assumes we only have one project open at a time
# when a new logger is created the handlers for the old one are closed

# note that cannot do logger = getLogger() at top of a module because it almost certainly
# will not be what one wants. instead one has to do it at runtime, e.g. in a constructor
# inside a class or in a non-class function

# in general the application should call createLogger() before anyone calls getLogger()
# but getLogger() can be called first for "short term", "setup" or "testing" use; it then returns
# the default logger

MAX_LOG_FILE_DAYS = 7
LOG_FIELD_WIDTH = 128


# Define a custom logger subclass with _loggingCommandBlock
# No object is actually created from this, it acts more like a Protocol to expose the
# extra attributes to the type-checker
class CustomLogger(logging.Logger):
    _loggingCommandBlock: int  # Specify the type of _loggingCommandBlock
    _fileHandler: DeferredFileHandler | None
    _streamHandler: logging.StreamHandler | None

    debugGL: _message
    echoInfo: _message
    info: _message
    debug1: _message
    debug: _message
    debug2: _message
    debug3: _message
    debug3_backup_thread: _message
    warning: _message


logger: CustomLogger | None = None
defaultLogger: logging.Logger | None = logging.getLogger('defaultLogger')
defaultLogger.propagate = False
ANSIESCAPEPATTERN = re.compile(r'\033\[[0-9;]*m')  # Matches ANSI escape sequences


def _countAnsi(text: str) -> int:
    """
    Count the number of ANSI escape sequences (color control characters) in the string.

    :param text: The input string containing ANSI escape sequences.
    :type text: str
    :return: The total length of all ANSI escape sequences in the string.
    :rtype: int
    """
    return sum(map(len, ANSIESCAPEPATTERN.findall(text)))


def getLogger() -> CustomLogger:
    global logger, defaultLogger

    if logger:
        # logger._loggingCommandBlock = 0
        return logger

    defaultLogger._loggingCommandBlock = 0

    # Cast to the expected type that includes _loggingCommandBlock
    logger = cast(CustomLogger, defaultLogger)

    if not hasattr(logger, 'echoInfo'):
        # add the new methods
        # required because default logger called before correct instantiated
        # but needed for loading from command line
        logger.debugGL = functools.partial(_debugGLError, DEBUG1, logger)
        logger.echoInfo = functools.partial(_message, INFO, logger, includeInspection=False)
        logger.info = functools.partial(_message, INFO, logger)
        logger.debug1 = functools.partial(_message, DEBUG1, logger)
        logger.debug = logger.debug1
        logger.debug2 = functools.partial(_message, DEBUG2, logger)
        logger.debug3 = functools.partial(_message, DEBUG3, logger)
        logger.debug3_backup_thread = logger.debug3
        logger.warning = functools.partial(_message, WARNING, logger)

        logging.addLevelName(DEBUG2, 'DEBUG2')
        logging.addLevelName(DEBUG3, 'DEBUG3')

    return logger


def _logCaller(logger: CustomLogger, fmsg: list[str], *, stacklevel: int = 1):
    """
    Create the postfix to the error message as (Module:function:lineNo).

    This function replaces the formatting which contains the wrong information for decorated functions.

    :param logger: CustomLogger instance used to find the caller.
    :type logger: CustomLogger
    :param fmsg: List of strings representing the formatted message.
    :type fmsg: list[str]
    :param stacklevel: The stack level to use when finding the caller, defaults to 1.
    :type stacklevel: int, optional
    :return: Formatted log message with the correct caller information.
    :rtype: str
    """
    _file, _line, _func, _ = logger.findCaller(stack_info=False, stacklevel=stacklevel)
    _fileLine = f'({aPath(_file).basename}.{_func}:{_line})'
    _msg = '; '.join(fmsg)
    return f'{_msg:<{LOG_FIELD_WIDTH + _countAnsi(_msg)}}    {_fileLine}'


def _debugGLError(MESSAGE: int, logger: CustomLogger, msg: str, *args, stacklevel: int = 1, **kwargs):
    """
    Logs a formatted message using the specified logger.

    This function constructs a message with the provided `msg`, optional arguments (`args`, `kwargs`),
    and logs it using the given logger. The `stacklevel` can be adjusted to control the stack trace depth.

    :param MESSAGE: The log level/message type (e.g., logging.DEBUG, logging.INFO).
    :type MESSAGE: int
    :param logger: The logger instance used to log the message.
    :type logger: CustomLogger
    :param msg: The main message to be logged.
    :type msg: str
    :param args: Optional positional arguments that are formatted and appended to the message.
    :param stacklevel: The stack level to include in the log entry. Defaults to 1.
    :type stacklevel: Optional int
    :param kwargs: Optional keyword arguments that are formatted as key-value pairs and appended to the message.
    :type kwargs: dict, optional

    :return: None

    :note:
        If `logger._loggingCommandBlock` is True, the message will not be logged to prevent nested logging.
    """
    if logger._loggingCommandBlock:
        # ignore nested logging
        return
    # inspect.stack can be very slow - but needs more stack info than below
    stk = inspect.stack()
    stk = [stk[st][3] for st in range(min(3, len(stk)), 0, -1)]
    fmsg = ['[' + '/'.join(stk) + '] ' + msg]
    if args: fmsg.append(', '.join([str(arg) for arg in args]))
    if kwargs: fmsg.append(', '.join([str(ky) + '=' + str(kwargs[ky]) for ky in kwargs.keys()]))
    _msg = _logCaller(logger, fmsg, stacklevel=stacklevel)
    # increase the stack level to account for the partial wrapper
    logger.log(MESSAGE, _msg, stacklevel=stacklevel)


def _message(MESSAGE: int, logger: CustomLogger, msg: str, *args,
             includeInspection: bool = True, stacklevel: int = 1, **kwargs):
    """
    Logs a formatted message using the specified logger.

    This function constructs a message with the provided `msg`, optional arguments (`args`, `kwargs`),
    and logs it using the given logger. If `includeInspection` is True, the message includes additional
    caller inspection information. The `stacklevel` can be adjusted to control the stack trace depth.

    :param MESSAGE: The log level/message type (e.g., logging.DEBUG, logging.INFO).
    :type MESSAGE: int
    :param logger: The logger instance used to log the message.
    :type logger: CustomLogger
    :param msg: The main message to be logged.
    :type msg: str
    :param args: Optional positional arguments that are formatted and appended to the message.
    :param includeInspection: Whether to include inspection details in the message. Defaults to True.
    :type includeInspection: bool, optional
    :param stacklevel: The stack level to include in the log entry. Defaults to 1.
    :type stacklevel: Optional int
    :param kwargs: Optional keyword arguments that are formatted as key-value pairs and appended to the message.
    :type kwargs: dict, optional

    :return: None

    :note:
        If `logger._loggingCommandBlock` is True, the message will not be logged to prevent nested logging.
        If `includeInspection` is False, no additional caller inspection details are included in the message.
    """
    if logger._loggingCommandBlock:
        # ignore nested logging
        return
    fmsg = [msg]
    if args: fmsg.append(', '.join([str(arg) for arg in args]))
    if kwargs: fmsg.append(', '.join([str(ky) + '=' + str(kwargs[ky]) for ky in kwargs.keys()]))
    _msg = _logCaller(logger, fmsg, stacklevel=stacklevel) if includeInspection else '; '.join(fmsg)
    # increase the stack level to account for the partial wrapper
    logger.log(MESSAGE, _msg, stacklevel=stacklevel)


def createLogger(loggerName,
                 logDirectory,
                 stream=None,
                 level=None,
                 mode='a',
                 readOnly=True,
                 now='',
                 # removeOldLogsDays=MAX_LOG_FILE_DAYS
                 ) -> CustomLogger:
    """Return a (unique) logger for this memopsRoot and with given programName, if any.
       Puts log output into a log file but also optionally can have output go to
       another, specified, stream (e.g. a console)
    """
    from ccpn.util.Path import aPath

    global logger

    assert mode in ('a', 'w'), 'for now mode must be "a" or "w"'

    _logDirectory = aPath(logDirectory)
    if not _logDirectory.exists():
        if not readOnly:
            try:
                _logDirectory.mkdir(parents=False, exist_ok=False)
            except (PermissionError, FileNotFoundError):
                sys.stderr.write('>>> Folder may be read-only\n')

    today = datetime.date.today()
    fileName = f'log_{loggerName}_{today.year:02d}{today.month:02d}{today.day:02d}_{now}.txt'
    logPath = _logDirectory / fileName

    # _removeOldLogFiles(logPath, removeOldLogsDays)

    if logger:
        # there seems no way to close the logger itself
        # and just closing the handler does not work
        # (and certainly do not want to close stdout or stderr)
        for handler in tuple(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
    else:
        logger = logging.getLogger(loggerName)
        logger.propagate = False

    logger.logPath = logPath  # just for convenience
    logger.shutdown = logging.shutdown  # just for convenience but tricky
    if level is None:
        level = defaultLogLevel
    logger.setLevel(level)
    # create attributes to store the file/stream state when enabling/disabling loggers
    logger._streamHandler = None
    logger._fileHandler = None

    # if not readOnly:
    #     try:
    #         handler = logging.FileHandler(logPath, mode=mode)
    #         _setupHandler(handler, level)
    #     except (PermissionError, FileNotFoundError):
    #         sys.stderr.write('>>> Folder may be read-only\n')

    try:
        # store the file-handler for later
        handler = DeferredFileHandler(logPath, mode=mode, delay=True, readOnly=readOnly)
        _setupHandler(handler, level)
        logger._fileHandler = handler

    except (PermissionError, FileNotFoundError):
        sys.stderr.write('>>> Folder may be read-only\n')

    try:
        # store the stream-handler for later
        if stream:
            handler = logging.StreamHandler(stream)
            _setupHandler(handler, level)
            logger._streamHandler = handler

    except (PermissionError, FileNotFoundError):
        sys.stderr.write('>>> Folder may be read-only\n')

    logger.debugGL = functools.partial(_debugGLError, DEBUG1, logger)
    logger.echoInfo = functools.partial(_message, INFO, logger, includeInspection=False)
    logger.info = functools.partial(_message, INFO, logger)
    logger.debug1 = functools.partial(_message, DEBUG1, logger)
    logger.debug = logger.debug1
    logger.debug2 = functools.partial(_message, DEBUG2, logger)
    logger.debug3 = functools.partial(_message, DEBUG3, logger)
    logger.debug3_backup_thread = logger.debug3
    logger.warning = functools.partial(_message, WARNING, logger)

    logging.addLevelName(DEBUG2, 'DEBUG2')
    logging.addLevelName(DEBUG3, 'DEBUG3')

    return logger


def updateLogger(loggerName,
                 logDirectory,
                 level=None,
                 mode='a',
                 readOnly=True,
                 flush=False,
                 now=''):
    global logger

    if not logger:
        raise RuntimeError('There is no logger!')

    _logDirectory = aPath(logDirectory)
    if not _logDirectory.exists() and not readOnly:
        try:
            _logDirectory.mkdir(parents=False, exist_ok=False)

        except (PermissionError, FileNotFoundError):
            sys.stderr.write('>>> Folder may be read-only\n')

    today = datetime.date.today()
    fileName = f'log_{loggerName}_{today.year:02d}{today.month:02d}{today.day:02d}_{now}.txt'
    logPath = _logDirectory / fileName

    # there seems no way to close the logger itself
    # and just closing the handler does not work
    # (and certainly do not want to close stdout or stderr)
    for handler in tuple(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    # if not readOnly:
    #     # re-insert the originals
    #     try:
    #         handler = logging.FileHandler(logPath, mode=mode)
    #         _setupHandler(handler, level)
    #     except (PermissionError, FileNotFoundError):
    #         sys.stderr.write('>>> Folder may be read-only\n')

    if logger._fileHandler:
        try:
            logger._fileHandler._updateFilename(logPath)
            _setupHandler(logger._fileHandler, level)
            logger._fileHandler._readOnly = readOnly
            if flush:
                # flush the stream and write all, file is re-opened as required on next log emit
                logger._fileHandler.close()

        except (PermissionError, FileNotFoundError):
            sys.stderr.write('>>> Folder may be read-only\n')

    if logger._streamHandler:
        try:
            _setupHandler(logger._streamHandler, level)

        except (PermissionError, FileNotFoundError):
            sys.stderr.write('>>> Folder may be read-only\n')


def _setupHandler(handler, level):
    """Add a stream handler for the logger.
    """

    if logger is not None:
        handler.setLevel(level)

        # define a simple logging message, extra information is inserted in _logCaller
        _format = '%(levelname)-7s: %(message)s'

        formatter = logging.Formatter(_format)
        handler.setFormatter(formatter)

        logger.addHandler(handler)


def _clearLogHandlers():
    """clear all log handlers
    """
    if logger is not None:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


def _removeOldLogFiles(logPath, removeOldLogsDays=MAX_LOG_FILE_DAYS):
    """Remove old log files.
    """

    logDirectory = os.path.dirname(logPath)
    logFiles = [os.path.join(logDirectory, x) for x in os.listdir(logDirectory)]
    logFiles = [logFile for logFile in logFiles if logFile != logPath and not os.path.isdir(logFile)]

    currentTime = time.time()
    removeTime = currentTime - removeOldLogsDays * 24 * 3600
    for logFile in logFiles:
        mtime = os.path.getmtime(logFile)
        if mtime < removeTime:
            os.remove(logFile)


def setLevel(logger, level=logging.INFO):
    """Set the logger level (including for the handlers)
    """

    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


class DeferredFileHandler(logging.FileHandler):
    """Deferred file-handler that queues messages until read-only mode is disabled.
    """

    def __init__(self, filename, readOnly=False, **kwds):
        super().__init__(filename, **kwds)

        self._queued = []
        self._readOnly = readOnly

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record to the file-stream.
        If readOnly is set, then records are stored in queue until the next emit or handler is closed
        """
        if self._readOnly:
            # append to the queue of records
            self._queued.append(record)
            return

        try:
            # emit all queued items first, then new item
            for rcd in self._queued:
                super().emit(rcd)
            self._queued = []
            super().emit(record)

        except (PermissionError, FileNotFoundError):
            # any write-error, keep queue and add new item to the end
            self._queued.append(record)

    def close(self) -> None:
        if not self._readOnly:
            # emit all queued items to the stream
            for rcd in self._queued:
                super().emit(rcd)
            self._queued = []

        super().close()

    def _updateFilename(self, filename):
        """Update the filename to the new folder
        """
        filename = os.fspath(filename)
        #keep the absolute path, otherwise derived classes which use this
        #may come a cropper when the current directory changes
        self.baseFilename = os.path.abspath(filename)
