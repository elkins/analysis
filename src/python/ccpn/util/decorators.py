"""Module Documentation here

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-04-17 12:03:20 +0100 (Wed, April 17, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


#===========================================================================================================
# Decorators
#===========================================================================================================

import sys
import os
import linecache
import functools
import cProfile
import decorator
import inspect
import time
from functools import partial
from ccpn.util.SafeFilename import getSafeFilename
from ccpn.util.Path import aPath, Path
import ccpn.util.Logging as Logging
import pandas as pd
from functools import wraps
from ccpn.util.Logging import getLogger

def trace(f):
    def globaltrace(frame, why, arg):
        if why == "call":
            return localtrace
        return None

    def localtrace(frame, why, arg):
        if why == "line":
            # record the file name and line number of every trace
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno

            bname = os.path.basename(filename)
            sys.stderr.write("{}({}): {}".format(bname,
                                                 lineno,
                                                 linecache.getline(filename, lineno)),
                             )
        return localtrace

    def _f(*args, **kwds):
        sys.settrace(globaltrace)
        result = f(*args, **kwds)
        sys.settrace(None)
        return result

    return _f


def singleton(cls, *single_args):
    """ Use class as singleton.
    From: https://wiki.python.org/moin/PythonDecoratorLibrary#Singleton
    Annotated by GWV
    Modified by EJB to keep record of all singletons
     - these can later be destroyed, was causing leakage between running testcases
    """

    @functools.wraps(cls.__new__)
    def singleton_new(cls, *args, **kwds):
        # keep a list of already created singletons
        if not hasattr(singleton, '_instances'):
            singleton._instances = {}
        # check if it already exists
        it = singleton._instances.get(cls)
        if it is not None:
            return it
        # it did not yet exist; generate an instance, store in list
        singleton._instances[cls] = it = cls.__new_original__(cls, *args, **kwds)
        it.__init_original__(*args, **kwds)
        return it

    # keep the new method and replace by singleton_new
    cls.__new_original__ = cls.__new__
    cls.__new__ = singleton_new
    # keep the init method and replace by the object init
    cls.__init_original__ = cls.__init__
    cls.__init__ = object.__init__
    return cls


def pstatToText(pstatPath, outPath=None):
    """
    Converts a profile file of type .pstat into a plain text file.
    :param pstatPath: path of the pstat file. (The output of the decorator "profile")
    :param outPath: output pat. Including the file name and extension ".txt".
                    If None, saves in the same location of pstat with same original name
    :return: the stats object for the file
    """
    import pstats
    import io

    s = io.StringIO()
    ps = pstats.Stats(pstatPath, stream=s).sort_stats('tottime')
    ps.print_stats()
    if not outPath:
        outPath = pstatPath.replace('pstat', 'txt')
    with open(outPath, 'w+') as f:
        f.write(s.getvalue())
    return ps


def profile(dirPath='~', asText=False):
    """
    Get the stats of all related calls firing from inside a specific function/method.
    Add on top of a function/method to profile it. E.g.:

        @profile(dirPath='/myDesktopPath/')
        def my function(*args): ...

    :param dirPath: str, dir where to dump the pstat file.
    :param asText: bool. Make a pstat copy as a human readable text file.
    """

    def _profile(func):
        @functools.wraps(func)
        def profileWrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            try:
                profiler.enable()
                result = func(*args, **kwargs)
                profiler.disable()
                return result
            finally:
                filename = aPath(dirPath).joinpath(func.__name__ + '.pstat')
                filename = getSafeFilename(filename, 'w')
                profiler.dump_stats(filename)
                if asText:
                    pstatToText(str(filename))

        return profileWrapper

    return _profile


def notify(trigger, preExecution=False):
    """A decorator wrap a method around a notification blanking with explicit notification pre- or post-execution
    """

    trigger = 'change' if trigger == 'observe' else trigger

    @decorator.decorator
    def theDecorator(*args, **kwds):

        func = args[0]
        args = args[1:]  # Optional 'self' is now args[0]
        self = args[0]
        project = self.project  # we need a reference now, as the func could be deleting the obj

        if preExecution:
            # call the notification
            self._finaliseAction(trigger)

        # Execute the function with blanked notification
        project.blankNotification()
        result = func(*args, **kwds)
        project.unblankNotification()

        if not preExecution:
            # call the notification
            self._finaliseAction(trigger)

        return result

    return theDecorator


def propertyUndo():
    """A decorator to wrap a method in an undo block
    Requires that the 'self' has 'project' as an attribute
    """
    from ccpn.core.lib.ContextManagers import undoBlock

    @decorator.decorator
    def theDecorator(*args, **kwds):
        func = args[0]
        args = args[1:]  # Optional 'self' is now args[0]
        self = args[0]

        _undo = self.project._undo
        with undoBlock():
            # Execute the function while blocking all additions to the call undo stack
            _undo.increaseBlocking()

            # remember the old value, requires a property getter
            oldValue = getattr(self, func.__name__)

            # call the wrapped function
            result = func(*args, **kwds)

            _undo.decreaseBlocking()

            # add the wrapped function to the undo stack
            _undo._newItem(undoPartial=partial(func, self, oldValue),
                           redoPartial=partial(func, *args, **kwds))

        return result

    return theDecorator


def callList(func):
    """
    Decorator to give the realtime call stack for the decorated function.
    Adds _callList=None, _callStr=None to the parameter list for the function call
    so function can access full list.

    _callList is tuple of tuples of the form:

        ((caller info, simple print string), string)

        caller info is: (index, name of calling method, stack info)

        simple print string is repr if caller info.

    The function will need either _callList=None, or **kwds adding to the parameter list.

    # Not fully tested
    """

    def inner(*args, **kwargs):
        stack = inspect.stack()
        minStack = len(stack)  # min(stack_size, len(stack))
        modules = [(index, inspect.getmodule(stack[index][0]))
                   for index in range(1, minStack)]
        callers = [(0, func.__module__, func.__name__)]
        for index, module in modules:
            try:
                name = module.__name__
            except:
                name = '<NOT_FOUND>'
            callers.append((index, name, stack[index][3]))

        s = '{index:>5} : {module:^%i} : {name}' % 20
        printStr = []
        for i in range(0, len(callers)):
            printStr.append(s.format(index=callers[i][0], module=callers[i][1], name=callers[i][2]))

        kwargs['_callList'] = tuple((cc, pp) for cc, pp in zip(callers, printStr))

        return func(*args, **kwargs)

    return inner


#----------------------------------------------------------------------------------------------
# Adapted from from sandbox.Geerten.Refactored.decorators to fit current setup
#----------------------------------------------------------------------------------------------

def _obj2pid(obj):
    """
    Convert any core objects and CcpnModules to pids;
            expand list, tuples, dicts but don't use recursion
    Convert Path to str
    CCPNINTERNAL: also used in logCommandManager contextmanager
    """

    # local import to prevent circular import
    from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
    from ccpn.ui.gui.modules.CcpnModule import CcpnModule

    if isinstance(obj, (AbstractWrapperObject, CcpnModule)):
        obj = obj.pid

    elif isinstance(obj, list):
        _tmp = []
        for itm in obj:
            if isinstance(itm, (AbstractWrapperObject, CcpnModule)):
                _tmp.append(itm.pid)
            else:
                _tmp.append(itm)
        obj = _tmp

    elif isinstance(obj, tuple):
        _tmp = []
        for itm in obj:
            if isinstance(itm, (AbstractWrapperObject, CcpnModule)):
                _tmp.append(itm.pid)
            else:
                _tmp.append(itm)
        obj = tuple(_tmp)

    elif isinstance(obj, dict):
        _tmp = {}
        for key, value in obj.items():
            if isinstance(value, (AbstractWrapperObject, CcpnModule)):
                _tmp[key] = value.pid
            else:
                _tmp[key] = value
        obj = _tmp

    elif isinstance(obj, Path):
        obj = str(obj)

    return obj


def _makeLogString(prefix, addSelf, func, *args, **kwds):
    """Helper function to create the log string from func, args and kwds

    returns string:

    if addSelf == False:
      prefix+func.__name__(EXPANDED-ARGUMENTS)

    if addSelf == True
      prefix+CLASSNAME-of-SELF+'.'+func.__name__(EXPANDED-ARGUMENTS)

    """

    # get the signature
    sig = inspect.signature(func)
    # fill in the missing parameters
    ba = sig.bind(*args, **kwds)
    ba.apply_defaults()
    # get the parameters kinds that determine how to print them
    kinds = dict([(pName, p.kind) for pName, p in sig.parameters.items()])

    if 'self' in ba.arguments or 'cls' in ba.arguments:
        # we skip the first 'self' or 'cls' in the argument list
        pNames = list(ba.arguments.keys())[1:]
    else:
        pNames = list(ba.arguments.keys())

    # make a string for each parameter
    pStrings = []
    for pName in pNames:
        pValue = ba.arguments[pName]

        if kinds[pName] == inspect.Parameter.VAR_POSITIONAL:  # variable arguments
            pStrings.extend([repr(_obj2pid(p)) for p in pValue])

        elif kinds[pName] == inspect.Parameter.VAR_KEYWORD:  # variable keywords
            pStrings.extend(['{0!s}={1!r}'.format(k, _obj2pid(v)) for (k, v) in pValue.items()])

        elif kinds[pName] == inspect.Parameter.POSITIONAL_ONLY:
            pStrings.append(repr(_obj2pid(pValue)))

        elif kinds[pName] == inspect.Parameter.KEYWORD_ONLY or \
                kinds[pName] == inspect.Parameter.POSITIONAL_OR_KEYWORD:  # #  keywords or positional keywords
            pStrings.append('{0!s}={1!r}'.format(pName, _obj2pid(pValue)))

    if ('self' in ba.arguments or 'cls' in ba.arguments) and addSelf:
        logString = prefix + '%s.%s' % (args[0].__class__.__name__, func.__name__)
    else:
        logString = prefix + '%s' % (func.__name__,)

    logString += '(%s)' % ', '.join(pStrings)
    return logString


def quickCache(func):
    """Class to implement a quick caching decorator

    For speed, only the first argument of the wrapped function is taken as the key
    """

    cache = {}

    def _cacheFunc(*args, **kwds):
        try:
            return cache[args[0]]
        except:
            cache[args[0]] = result = func(*args, **kwds)

        return result

    def cacheClearItem(item):
        if item in cache:
            del cache[item]

    # attach external methods to _cacheFunc
    # must be done like this, as internal functions are only created at runtime
    _cacheFunc.cacheClear = lambda: cache.clear()
    _cacheFunc.cachePrint = lambda: print(f'>>> {cache}')
    _cacheFunc.cacheClearItem = cacheClearItem

    return _cacheFunc


@quickCache
def _inspectFunc(func):
    """Function to return the module.function:lineNo of the wrapped function
    """
    # this is cached to speed up the get_ methods (cache may have to be cleared if modules are reloaded)
    # but can be cleared with _inspectFunc.cacheClear()
    _, _line = inspect.getsourcelines(func)
    _file = aPath(inspect.getsourcefile(func)).basename
    return f'({_file}.{func.__name__}:{_line + 1})'


def logCommand(prefix='', get=None, isProperty=False):
    """A decorator to log the invocation of the call to a Framework, Project, ... method.
    Use prefix to set the proper command context, e.g. 'application.' or 'project.'
    Use isProperty to get ' = 'args[1]
    """
    from ccpn.core.lib.ContextManagers import notificationEchoBlocking  # local to prevent circular imports

    @decorator.decorator
    def theDecorator(*args, **kwds):
        # to avoid potential conflicts with potential 'func' named keywords
        func = args[0]
        args = args[1:]  # Optional 'self' is now args[0]
        self = args[0]

        # application = self.project.application
        # GWV: tried this for application.newProject decoration, but unsuccessful (for now)
        from ccpn.framework.Application import getApplication

        application = getApplication()
        if application is None:
            raise RuntimeError('Error getting application')

        blocking = application._echoBlocking

        if blocking == 0 and application.ui is not None:
            _pref = prefix
            if get == 'self':
                _pref += f"get('{args[0].pid}')."

            if isProperty:
                from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
                from ccpn.core._implementation.V3CoreObjectABC import V3CoreObjectABC
                ##could replace these imports with hasattr(args[1], 'pid')
                if isinstance(args[1], (AbstractWrapperObject, V3CoreObjectABC)):
                    logS = f"{_pref}{func.__name__} = get({args[1].pid})"
                elif isinstance(args[1], pd.DataFrame):
                    logS = f"{_pref}{func.__name__} = $TableFrame"
                else:
                    logS = f"{_pref}{func.__name__} = {repr(args[1])}"
            else:
                logS = _makeLogString(_pref, False, func, *args, **kwds)

            # get the trace for the func method and append to log string (cached function; may need to be cleared?)
            # this has been removed from the logger.formatting and moved to the logging methods
            _trace = _inspectFunc(func)
            msg = f'{logS:90}    {_trace}'
            application.ui.echoCommands([msg])

        # increase blocking
        with notificationEchoBlocking(application=application):
            result = func(*args, **kwds)

        return result

    return theDecorator

def deprecated(arg):
    """Define a deprecation decorator.
    An optional string should refer to the new API to be used instead.
    Example:
      @deprecated
      def old_func(): ...

      @deprecated('new_func')
      def old_func(): ..."""

    subst = arg if isinstance(arg, str) else None

    def decorator(func):
        def wrapper(*args, **kwargs):
            msg = "Call to deprecated function \"{}\"."
            if subst:
                msg += "\n Use \"{}\" instead."
            getLogger().warn(msg.format(func.__name__, subst),
                          category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wraps(func)(wrapper)

    if not subst:
        return decorator(arg)
    else:
        return decorator

def timeDecorator(method):
    """calculate execution time of a function/method
    """

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result

    return timed


def timeitDecorator(method):
    """calculate execution time of a function/method
    """

    def timed(*args, **kwds):
        ts = time.time()
        result = method(*args, **kwds)
        te = time.time()
        final = te - ts
        m = 'Execution time for %r: %.3f ms'
        print(m % (method.__name__, final))
        return result

    return timed

######### Memory leak inspection ###########


def _startInspectMemory():
    """  Call this before a suspected leaking bit.
    Starts a tracemalloc and  take an initial snapshot
    return tracemalloc, snapshot
    """
    import tracemalloc
    tracemalloc.start()
    snapshot = tracemalloc.take_snapshot()
    return tracemalloc, snapshot

def _closeInspectMemory(tracemalloc, snapshot, savingPath=None, topCount=20):
    """  Call this after  a suspected leaking bit  and pass
    :param tracemalloc, snapshot from the _startInspectMemory func.
    :param SavingPath: a global path for a csv if you want save the result to file.
    :return a dataFrame containing the top results,
      including file name, line number  and memory usage in KiB per call

      Usage:
     tracemalloc, snapshot =  _startInspectMemory()
      ... run the slow/leaky func
      df = _closeInspectMemory(tracemalloc, snapshot, '~/resultFile.csv')
      """

    import pandas as pd
    snapshotCurrent = tracemalloc.take_snapshot()
    stats = snapshotCurrent.compare_to(snapshot, 'lineno')
    df = pd.DataFrame()
    for index, stat in enumerate(stats[:topCount]):
        frame = stat.traceback[0]
        ix = index
        df.loc[ix, 'index'] = index
        df.loc[ix, 'filename'] = frame.filename
        df.loc[ix, 'line'] = frame.lineno
        df.loc[ix, 'size (KiB)'] = stat.size / 1024
    if savingPath is not None:
        if not savingPath.endswith('.csv'):
            raise UserWarning('FilePath must be a valid *.csv path.')
        df.to_csv(savingPath)
    tracemalloc.stop()
    return df

def _getObjectCountInMemory(savingPath=None, topCount=100):

    """ Create a DataFrame with a count of the most seen
    Object types held in memory.
    :param SavingPath: str, a global path for a csv if you want save the result to file.
    :param  topCount: int. Number of obj to consider in the most common
    :return pd.DataFrame.
    """

    import pandas as pd
    from collections import Counter
    import gc
    df = pd.DataFrame()
    obs = gc.get_objects()
    obs = [type(i) for i in obs]
    c = Counter(obs)
    for ix, mostCommon in enumerate(c.most_common(topCount)):
        _type, count = mostCommon
        df.loc[ix, 'Index'] = ix
        df.loc[ix, 'Object'] = str(_type)
        df.loc[ix, 'Count'] = count
    if savingPath is not None:
        if not savingPath.endswith('.csv'):
            raise UserWarning('FilePath must be a valid *.csv path.')
        df.to_csv(savingPath)
    return df

def debugEnter(verbosityLevel=Logging.DEBUG1):
    """A decorator to log the invocation of the call
    """

    @decorator.decorator
    def decoratedFunc(*args, **kwds):
        # def debugEnter(func, *args, **kwds):
        # to avoid potential conflicts with potential 'func' named keywords
        func = args[0]
        args = args[1:]

        logs = _makeLogString('ENTERING: ', True, func, *args, **kwds)

        # get a logger and call the correct routine depending on verbosityLevel
        logger = Logging.getLogger()
        if verbosityLevel == Logging.DEBUG1:
            logger.debug(logs)
        elif verbosityLevel == Logging.DEBUG2:
            logger.debug2(logs)
        elif verbosityLevel == Logging.DEBUG3:
            logger.debug3(logs)
        else:
            raise ValueError('invalid verbosityLevel "%s"' % verbosityLevel)

        # execute the function and return the result
        return func(*args, **kwds)

    return decoratedFunc


def debug1Enter():
    """Convenience"""
    return debugEnter(verbosityLevel=Logging.DEBUG1)


def debug2Enter():
    """Convenience"""
    return debugEnter(verbosityLevel=Logging.DEBUG2)


def debug3Enter():
    """Convenience"""
    return debugEnter(verbosityLevel=Logging.DEBUG3)


def debugLeave(verbosityLevel=Logging.DEBUG1):
    """A decorator to log the invocation of the call
    """

    @decorator.decorator
    def decoratedFunc(*args, **kwds):
        # def debugLeave(func, *args, **kwds):
        # to avoid potential conflicts with potential 'func' named keywords
        func = args[0]
        args = args[1:]

        ba = inspect.signature(func).bind(*args, **kwds)
        ba.apply_defaults()
        allArgs = ba.arguments

        #execute the function
        result = func(*args, **kwds)

        if 'self' in allArgs or 'cls' in allArgs:
            logs = 'LEAVING: %s.%s(); result=%r' % \
                   (args[0].__class__.__name__, func.__name__, result)
        else:
            logs = 'LEAVING: %s(); result=%r' % (func.__name__, result)

        # get a logger and call the correct routine depending on verbosityLevel
        logger = Logging.getLogger()
        if verbosityLevel == Logging.DEBUG1:
            logger.debug(logs)
        elif verbosityLevel == Logging.DEBUG2:
            logger.debug2(logs)
        elif verbosityLevel == Logging.DEBUG3:
            logger.debug3(logs)
        else:
            raise ValueError('invalid verbosityLevel "%s"' % verbosityLevel)

        #return the function result
        return result

    return decoratedFunc


def debug1Leave():
    """Convenience"""
    return debugLeave(verbosityLevel=Logging.DEBUG1)


def debug2Leave():
    """Convenience"""
    return debugLeave(verbosityLevel=Logging.DEBUG2)


def debug3Leave():
    """Convenience"""
    return debugLeave(verbosityLevel=Logging.DEBUG3)


#==========================================================================================================================
# testing
#==========================================================================================================================


if __name__ == '__main__':

    def func(par, *args, flag=False, **kwds):

        sig = inspect.signature(func)  # get the signature
        ba = sig.bind(par, *args, flag=flag, **kwds)
        ba.apply_defaults()  # fill in the missing parameters
        kinds = dict([(pName, p.kind) for pName, p in sig.parameters.items()])  # get the parameters kinds that determine
        # how to print them

        pStrings = []
        for pName, pValue in ba.arguments.items():

            if kinds[pName] == inspect.Parameter.VAR_POSITIONAL:  # variable argument
                pStrings.extend([repr(p) for p in pValue])

            elif kinds[pName] == inspect.Parameter.VAR_KEYWORD:  # variable keywords
                pStrings.extend(['{0!s}={1!r}'.format(k, v) for (k, v) in pValue.items()])

            elif kinds[pName] == inspect.Parameter.POSITIONAL_ONLY or \
                    kinds[pName] == inspect.Parameter.POSITIONAL_OR_KEYWORD:  # positional keywords
                pStrings.append(repr(pValue))

            elif kinds[pName] == inspect.Parameter.KEYWORD_ONLY:  #  keywords
                pStrings.append('{0!s}={1!r}'.format(pName, pValue))

        print(', '.join(pStrings))


    func('test', 1, 2, myPar='myValue')
