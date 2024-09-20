"""
Notifier extensions, wrapping it into a class that also acts as the called function,
dispatching the 'user' callback if required.

The Notifier can be defined relative to any valid V3 core object, as well as the current
object as it first checks if the triggered signature is valid.

The triggers CREATE, DELETE, RENAME and CHANGE can be combined in the call signature,
preventing unnecessary code duplication. They are translated into multiple notifiers
of the 'Project V3-machinery' (i.e., the Rasmus callbacks)

The callback function is passed a callback dictionary with relevant info (see
docstring of Notifier class). This idea was copied from the Traitlets package.

April 2017: First design by Geerten Vuister

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
__dateModified__ = "$dateModified: 2024-05-10 16:28:56 +0100 (Fri, May 10, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-18 15:19:30 +0100 (Tue, April 18, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys

from functools import partial
from collections import OrderedDict
from typing import Callable, Any, Optional
from itertools import permutations
from ccpn.util.Logging import getLogger
import weakref


DEBUG = False
_debugIds = ()


# _debugIds = (75, 84, 92, 94,95,96)  # for these _id's, debug will be True. This allows for selective debugging


def skip(*args, **kwargs):
    """Do nothing"""
    pass


class NotifierABC(object):
    """
    Abstract base class for Notifier and GuiNotifier classes
    """
    _currentIndex = 0

    # needs subclassing
    _triggerKeywords = ()

    def __init__(self, theObject, triggers, targetName, callback, setterObject=None, debug=False, **kwargs):

        # Sanity checks
        if len(self._triggerKeywords) == 0:
            raise RuntimeError('Not trigger keywords defined; assure proper subclassing definitions')

        # initialisations
        self._id = NotifierABC._currentIndex
        NotifierABC._currentIndex += 1

        if theObject is None:
            raise RuntimeError('NotifierABC: theObject is None')

        self._theObject = theObject  # The object we are monitoring

        if triggers is not None and (not isinstance(triggers, (list, tuple)) or len(triggers) == 0):
            raise RuntimeError('Invalid triggers (%r); should be a list or tuple' % triggers)

        for trigger in triggers:
            if trigger not in self._triggerKeywords:
                raise ValueError('Invalid trigger "%s" for <%s>' % (trigger, self.__class__.__name__))
        self._triggers = tuple(triggers)

        self._targetName = targetName
        self._callback = callback
        self._kwargs = kwargs

        self._setterObject = weakref.ref(setterObject) if setterObject is not None else None

        self._debug = debug or DEBUG  # ability to report on individual instances
        self._isBlanked = False  # ability to blank notifier
        self._isRegistered = False  # flag indicating if any Notifier was registered

    @property
    def id(self):
        return self._id

    @property
    def project(self):
        """Return the project
        """
        # implemented as a weak reference
        return self._project()

    def setDebug(self, flag: bool):
        """Set debug output on/off"""
        self._debug = flag

    def setBlanking(self, flag: bool):
        """Set blanking on/off"""
        self._isBlanked = flag

    def triggersOn(self, trigger) -> bool:
        """Return True if notifier triggers on trigger"""
        return trigger in self._triggers

    def unRegister(self):
        """Reset the attributes"""
        if self._debug:
            sys.stderr.write('>>> unRegister %s\n' % self)

        self._theObject = None
        self._callback = None
        self._unregister = ()
        self._triggers = ()
        self._isRegistered = False
        self._setterObject = None

    def isRegistered(self) -> bool:
        """:return True if notifier is still registered; i.e. active"""
        return self._isRegistered

    def __str__(self) -> str:
        if self.isRegistered():
            trigs = f'{[(t, self._targetName) for t in self._triggers]}'
            return '<%s (%d): theObject:%s triggers:%s>' % \
                   (self.__class__.__name__,
                    self.id,
                    self._theObject,
                    trigs[1:-1])

        return '<%s (%d): not registered>' % \
               (self.__class__.__name__,
                self.id
                )

    __repr__ = __str__


class Notifier(NotifierABC):
    """
    Notifier class:

    triggers callback function with signature:  callback(callbackDict [, *args] [, **kwargs])

    ____________________________________________________________________________________________________________________

    trigger             targetName           callbackDict keys          Notes
    ____________________________________________________________________________________________________________________

     Notifier.CREATE    className             theObject, object,        targetName: valid child className of theObject
                                              targetName, trigger       (any for project instances)
                                              notifier

     Notifier.DELETE    className             theObject, object,        targetName: valid child className of theObject
                                              targetName, trigger       (any for project instances)
                                              notifier

     Notifier.RENAME    className             theObject, object         targetName: valid child className of theObject
                                              targetName, oldPid,       (any for project instances)
                                              trigger

     Notifier.CHANGE    className             theObject, object         targetName: valid child className of theObject
                                              targetName,               (any for project instances)
                                              trigger, notifier

     Notifier.OBSERVE   attributeName         theObject,targetName      targetName: valid attribute name of theObject
                        or ANY                value, previousValue,     NB: should only be used in isolation; i.e. not
                                              trigger, notifier         combined with other triggers

     Notifier.CURRENT   attributeName         theObject,targetName      theObject should be current object
                                              value, previousValue,     targetName: valid attribute name of current
                                              trigger, notifier         NB: should only be used in isolation; i.e. not
                                                                        combined with other triggers

    Implemention:

      Uses current notifier system from Project and Current;filters for child objects of type targetName in theObject.
      TargetName does need to denote a valid child-class or attribute of theObject, except for Project instances
      which can be triggered by all classes (see Table).

      The callback provides a dict with several key, value pairs and optional arguments and/or keyword arguments if
      defined in the instantiation of the Notifier object. (idea following the Traitlets concept).
      Note that this dict also contains a reference to the Notifier object itself; this way it can be used
      to pass-on additional implementation specific information to the callback function.

    """

    # Trigger keywords
    CREATE = 'create'
    DELETE = 'delete'
    RENAME = 'rename'
    CHANGE = 'change'
    OBSERVE = 'observe'
    CURRENT = 'current'
    _triggerKeywords = (CREATE, DELETE, RENAME, CHANGE, OBSERVE, CURRENT)

    ANY = '<Any>'

    # callback dict keywords
    NOTIFIER = 'notifier'
    THEOBJECT = 'theObject'
    TRIGGER = 'trigger'
    OBJECT = 'object'
    GETPID = 'pid'
    OLDPID = 'oldPid'
    VALUE = 'value'
    PREVIOUSVALUE = 'previousValue'
    TARGETNAME = 'targetName'
    SPECIFIERS = 'specifiers'

    def __init__(self,
                 theObject: Any,
                 triggers: list,
                 targetName: str,
                 callback: Callable[..., Optional[str]],
                 setterObject=None,
                 onceOnly=False,
                 debug=False,
                 **kwargs):
        """
        Create Notifier object;
        The triggers CREATE, DELETE, RENAME and CHANGE can be combined in the call signature

        :param theObject: valid V3 core object or current object to watch
        :param triggers: list of trigger keywords callback
        :param targetName: valid className, attributeName or ANY
        :param callback: callback function with signature: callback(callbackDict, **kwargs])
        :param setterObject: Object that was setting the Notifier
        :param debug: set debug
        :param **kwargs: optional keyword,value arguments to callback
        """
        from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject  # local import to avoid cycles
        from ccpn.core._implementation.V3CoreObjectABC import V3CoreObjectABC  # local import to avoid cycles
        from ccpn.framework.Current import Current  # local import to avoid cycles

        if theObject is None or not isinstance(theObject, (Current, AbstractWrapperObject, V3CoreObjectABC)):
            raise RuntimeError('Notifier: invalid object %r' % theObject)

        super().__init__(theObject=theObject,
                         triggers=triggers,
                         targetName=targetName,
                         setterObject=setterObject,
                         debug=debug,
                         callback=callback, **kwargs
                         )

        # >>>>>>
        if self.id in _debugIds:
            self._debug = True

        # bit of a clutch for now
        _project = None
        if isinstance(theObject, Current):
            # assume we have current
            _project = None
            _current = theObject
            self._project = None
            self._isProject = False
            self._isCurrent = True
        elif isinstance(theObject, AbstractWrapperObject):
            _project = theObject.project
            _current = None
            self._project = weakref.ref(_project)  # toplevel Project instance for theObject
            self._isProject = (theObject == _project)  # theObject is the toplevel Project instance
            self._isCurrent = False
        else:
            raise RuntimeError('Invalid object (%s)', theObject)

        self._previousValue = None  # used to store the value of attribute to observe for change

        self._unregister = []  # list of tuples needed for unregistering

        # some sanity checks
        if len(triggers) > 1 and Notifier.OBSERVE in triggers:
            raise RuntimeError('Notifier: trigger "%s" only to be used in isolation' % Notifier.OBSERVE)
        if len(triggers) > 1 and Notifier.CURRENT in triggers:
            raise RuntimeError('Notifier.__init__: trigger "%s" only to be used in isolation' % Notifier.CURRENT)
        if triggers[0] == Notifier.CURRENT and not self._isCurrent:
            raise RuntimeError('Notifier.__init__: invalid object "%s" for trigger "%s"' % (theObject, triggers[0]))

        if targetName is None:
            raise ValueError('Invalid None targetName')

        # register the callbacks
        for trigger in self._triggers:

            # CURRENT special case; has its own callback mechanism
            if trigger == Notifier.CURRENT:

                if not hasattr(theObject, targetName):
                    raise RuntimeWarning(
                            'Notifier.__init__: invalid targetName "%s" for class "%s"' % (targetName, theObject))

                self._previousValue = getattr(theObject, targetName)
                notifier = (trigger, targetName)
                # current has its own notifier system

                #TODO:change this and remove this hack
                # to register strip, the keywords is strips!
                tName = targetName + 's' if targetName == 'strip' else targetName
                func = _current.registerNotify(partial(self, notifier=notifier), tName)
                self._unregister.append((tName, Notifier.CURRENT, func))
                self._isRegistered = True

            # OBSERVE special case, as the current underpinning implementation does not allow this directly
            # Hence, we track all changes to the object class, filtering those that apply
            elif trigger == Notifier.OBSERVE:
                if targetName != self.ANY and not hasattr(theObject, targetName):
                    raise RuntimeWarning(
                            'Notifier.__init__: invalid targetName "%s" for class "%s"' % (targetName, theObject.className))

                if targetName != self.ANY:
                    self._previousValue = getattr(theObject, targetName)

                notifier = (trigger, targetName)
                func = self.project.registerNotifier(className=theObject.className,
                                                     target=Notifier.CHANGE,
                                                     func=partial(self, notifier=notifier),
                                                     onceOnly=onceOnly)
                self._unregister.append((theObject.className, Notifier.CHANGE, func))
                self._isRegistered = True

            # All other triggers;
            else:
                # Projects allow all registering of all classes
                # allowedClassNames = [c.className for c in theObject._getChildClasses(recursion=self._isProject)]
                # if targetName not in allowedClassNames:
                #     raise RuntimeWarning('Notifier.__init__: invalid targetName "%s" for class "%s"' % (targetName, theObject.className))

                notifier = (trigger, targetName)
                if _project is None:
                    # This should not happen
                    raise RuntimeError(f'Undefined project: cannot register notifier for {theObject}')
                func = _project.registerNotifier(className=targetName,
                                                 target=trigger,
                                                 func=partial(self, notifier=notifier),
                                                 onceOnly=onceOnly)
                self._unregister.append((targetName, trigger, func))
                self._isRegistered = True

        if not self.isRegistered():
            raise RuntimeWarning('Notifier.__init__: no notifiers initialised for theObject=%s, targetName=%r, triggers=%s ' % \
                                 (theObject, targetName, triggers))

        if self._debug:
            sys.stderr.write('>>> registered %s\n' % self)

    def unRegister(self):
        """
        unregister the notifiers
        """

        # >>>>>>
        if self.id in _debugIds:
            sys.stderr.write('>>> un-registering %s\n' % self)

        if not self.isRegistered():
            return

        for targetName, trigger, func in self._unregister:
            if trigger == Notifier.CURRENT:
                self._theObject.unRegisterNotify(func, targetName)
            else:
                self.project.unRegisterNotifier(targetName, trigger, func)

        super().unRegister()  # the end as it clears all attributes

    def __call__(self, obj: Any, parameter2: Any = None, notifier: tuple = None, **actionKwds):
        """
        wrapper, accommodating the different triggers before firing the callback
        """

        if not self.isRegistered():
            getLogger().warning(f'Triggering unregistered notifier {self}')
            return

        if self._isBlanked:
            return

        if obj is None:
            #
            raise RuntimeError('Notifier.__call__: obj is None')

        # if not self._isCurrent and obj.isDeleted:
        #     # It is a V3 core object notifier; check if obj is still around
        #     # hack for now (20181127) until a better implementation
        #     return

        trigger, targetName = notifier

        if self._debug:
            p2 = 'parameter2=%r ' % parameter2 if parameter2 else ''
            sys.stderr.write('--> <%s (%d)> %-25s obj=%-25s %s' % \
                             (self.__class__.__name__, self.id,
                              notifier, obj, p2)
                             )

        notifierFired = False
        callbackDict = {self.NOTIFIER     : self,
                        self.TRIGGER      : trigger,
                        self.THEOBJECT    : self._theObject,
                        self.OBJECT       : obj,
                        self.TARGETNAME   : targetName,
                        self.PREVIOUSVALUE: None,
                        self.VALUE        : None,
                        self.OLDPID       : None,
                        self.GETPID       : None,
                        self.SPECIFIERS   : actionKwds,
                        }

        # CURRENT special case
        if trigger == Notifier.CURRENT:
            value = getattr(self._theObject, targetName)
            if not self._isEqual(value, self._previousValue):
                callbackDict[self.OBJECT] = self._theObject
                callbackDict[self.PREVIOUSVALUE] = self._previousValue
                callbackDict[self.VALUE] = value
                self._callback(callbackDict, **self._kwargs)
                notifierFired = True
                self._previousValue = value

        # OBSERVE ANY special case
        elif trigger == Notifier.OBSERVE and targetName == self.ANY:
            if obj.pid == self._theObject.pid:
                callbackDict[self.OBJECT] = self._theObject
                self._callback(callbackDict, **self._kwargs)
                notifierFired = True

        # OBSERVE targetName special case
        elif trigger == Notifier.OBSERVE and targetName != self.ANY:
            # The check below catches all changes to obj that do not involve targetName, as only
            # when it has changed its value will we trigger the callback
            value = getattr(self._theObject, targetName)
            if obj.pid == self._theObject.pid and not self._isEqual(value, self._previousValue):
                callbackDict[self.OBJECT] = self._theObject
                callbackDict[self.PREVIOUSVALUE] = self._previousValue
                callbackDict[self.VALUE] = value
                self._callback(callbackDict, **self._kwargs)
                notifierFired = True
                self._previousValue = value

        # check if the trigger applies for all other cases
        elif self._isProject or obj._parent.pid == self._theObject.pid:
            if trigger == self.RENAME and parameter2 is not None:
                callbackDict[self.OLDPID] = parameter2
            self._callback(callbackDict, **self._kwargs)
            notifierFired = True

        if self._debug:
            _tmp = 'FIRED' if notifierFired else 'not-FIRED'
            sys.stderr.write('%-9s func:%s\n' % (_tmp, self._callback))

        return

    @staticmethod
    def _isEqual(value1, value2):
        """Return true if values are equal, accounting for tuple/list conversion"""
        if isinstance(value1, tuple):
            value1 = list(value1)
        if isinstance(value2, tuple):
            value1 = list(value2)
        return value1 == value2


# def currentNotifier(attributeName, callback, onlyOnce=False, debug=False, **kwargs):
#     """Convenience method: Return a Notifier instance for current.attributeName
#     """
#     app = getApplication()
#     notifier = Notifier(app.current, [Notifier.CURRENT], targetName=attributeName,
#                         callback=callback, onlyOnce=onlyOnce, debug=debug, **kwargs)
#     return notifier


class _NotifiersDict(OrderedDict):
    """A class to retain all notifiers of an object
    """

    # GWV: not yet used
    # REGISTERED_WITH_OBJECT = 'registeredWithObject'
    # INITIATED_FROM_OBJECT = 'initiatedFromObject'

    def __init__(self):
        super().__init__()


class NotifierBase(object):
    """
    A class confering notifier management routines
    """
    _NOTIFIERSDICT = '_ccpNmrV3notifiersDict'  # attribute name for storing notifiers in Ccpn objects

    def _getObjectNotifiersDict(self):
        """Internal routine to get the object notifiers dict"""
        if not hasattr(self, self._NOTIFIERSDICT):
            setattr(self, self._NOTIFIERSDICT, _NotifiersDict())
        objNotifiers = getattr(self, self._NOTIFIERSDICT)
        # check type
        if not isinstance(objNotifiers, _NotifiersDict):
            raise RuntimeError(f'Invalid NotifiersDict, got {type(objNotifiers)}, expected {type(_NotifiersDict)}')

        return objNotifiers

    def setNotifier(self, theObject: 'AbstractWrapperObject', triggers: list, targetName: str, callback: Callable[..., Optional[str]], **kwargs) -> Notifier:
        """
        Set Notifier for Ccpn V3 object theObject

        :param theObject: V3 object to register a notifier with
        :param triggers: list of triggers to trigger callback
        :param targetName: valid className, attributeName or None (See Notifier doc string for details)
        :param callback: callback function with signature: callback(obj, parameter2 [, *args] [, **kwargs])
        :param **kwargs: optional keyword,value arguments to call back
        :return: a Notifier instance
        """
        objNotifiers = self._getObjectNotifiersDict()
        notifier = Notifier(theObject=theObject,
                            triggers=triggers,
                            targetName=targetName,
                            callback=callback,
                            setterObject=self,
                            **kwargs)
        _id = notifier.id
        # this should never happen; hence just a check
        if _id in objNotifiers:
            raise RuntimeError('%s: a notifier with id "%s" already exists (%s)' % (self, _id, objNotifiers[_id]))
        # add the notifier
        objNotifiers[_id] = notifier
        return notifier

    def setGuiNotifier(self, theObject: 'AbstractWrapperObject', triggers: list, targetName: list,
                       callback: Callable[..., Optional[str]], **kwargs) -> 'GuiNotifier':
        """
        Set Notifier for Ccpn V3 object theObject

        :param theObject: V3 object to register a notifier with
        :param triggers: list of triggers to trigger callback
        :param targetName: valid className, attributeName or None (See Notifier doc string for details)
        :param callback: callback function with signature: callback(obj, parameter2 [, *args] [, **kwargs])
        :param kwargs: optional keyword,value arguments to callback

        :return: a GuiNotifier instance
        """
        from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier  # To avoid circular imports

        objNotifiers = self._getObjectNotifiersDict()
        notifier = GuiNotifier(theObject=theObject,
                               triggers=triggers,
                               targetName=targetName,
                               callback=callback,
                               **kwargs)
        _id = notifier.id
        # this should never happen; hence just a check
        if _id in objNotifiers:
            raise RuntimeError('%s: a notifier with id "%s" already exists (%s)' % (self, _id, objNotifiers[_id]))
        # add the notifier
        objNotifiers[_id] = notifier
        return notifier

    def deleteNotifier(self, notifier: Notifier):
        """
        unregister notifier; remove it from the list and delete it
        :param notifier: Notifier instance
        """
        if not self.hasNotifier(notifier):
            raise RuntimeWarning('"%s" is not a (valid) notifier of "%s"' % (notifier, self))

        objNotifiers = self._getObjectNotifiersDict()
        notifier.unRegister()
        del (objNotifiers[notifier.id])
        del (notifier)

    def hasNotifier(self, notifier: Notifier = None) -> bool:
        """
        return True if theObject has set notifier or
        has any notifier (when notifier==None)

        :param notifier: Notifier instance or None
        :return: True or False
        """
        if not hasattr(self, self._NOTIFIERSDICT):
            return False

        objNotifiers = self._getObjectNotifiersDict()
        if len(objNotifiers) == 0:
            return False

        if notifier is None and len(objNotifiers) > 0:
            return True

        if not isinstance(notifier, NotifierABC):
            raise ValueError('"%s" is not a valid notifier instance' % notifier)

        return notifier.id in objNotifiers

    def searchNotifiers(self, objects=[], triggers=None, targetName=None):
        """Search whether a notifier with the given parameters is already in the list.
        The triggers CREATE, DELETE, RENAME and CHANGE can be combined in the call signature

        :param objects: valid V3 core object or current object to watch
        :param triggers: list of trigger keywords
        :param targetName: valid className, attributeName or ANY
        :return: None or list of existing notifiers
        """
        if not hasattr(self, self._NOTIFIERSDICT):
            return ()

        objNotifiers = self._getObjectNotifiersDict()
        if len(objNotifiers) == 0:
            return ()

        foundNotifiers = ()
        for notifier in objNotifiers.values():
            if notifier._theObject in objects and targetName == notifier._targetName:

                # check if the notifier permutations match
                if tuple(triggers) in permutations(notifier._triggers):
                    foundNotifiers += (notifier,)

        return foundNotifiers

    def deleteAllNotifiers(self):
        """Unregister all the notifiers"""
        if not self.hasNotifier(None):
            # there are no notifiers
            return
        objNotifiers = self._getObjectNotifiersDict()
        for notifier in list(objNotifiers.values()):
            self.deleteNotifier(notifier)

    def setBlankingAllNotifiers(self, flag):
        """Set blanking of all the notifiers of theObject to flag
        """
        if not self.hasNotifier(None):
            return
        objNotifiers = self._getObjectNotifiersDict()
        for notifier in list(objNotifiers.values()):
            notifier.setBlanking(flag)


def _removeDuplicatedNotifiers(notifierQueue):
    """Remove any duplicated notifiers from the queue

    Notifiers are filtered on (obj, trigger)
    Notifier priority from high-low is: DELETE, CREATE, CHANGE
    When one is encountered, the lower-priority are ignored

    Return the condensed list of notifiers
    """
    # based on previous suspendNotification
    executeQueue = []
    scheduledQueue = set()

    # iterate through the queue in reverse order
    for func, data in notifierQueue.items(reverse=True):
        # assume that data is a non-empty dict
        obj = data.get(Notifier.OBJECT) if data else None
        trigger = data.get(Notifier.TRIGGER) if data else None

        match = (obj, trigger)
        if match not in scheduledQueue:
            scheduledQueue.add(match)

            # if True:
            #     # NOTE:ED - still not sure about this, disabled for the minute
            #     #   doesn't work correctly with SequenceGraph
            #     if trigger == Notifier.DELETE:
            #         # # can skip these two notifiers if DELETE found
            #         # scheduledQueue |= {(obj, Notifier.CHANGE), (obj, Notifier.RENAME), (obj, Notifier.CREATE)}
            #         #
            #         # # discard ALL other notifiers, not needed with DELETE
            #         # executeQueue = list(filter(lambda val: val[1][Notifier.OBJECT] != obj, executeQueue))
            #
            #         # can skip this notifier if CREATE found
            #         scheduledQueue |= {(obj, Notifier.CHANGE), (obj, Notifier.RENAME)}
            #
            #         # discard CHANGE, RENAME notifiers
            #         executeQueue = list(filter(lambda val: val[1][Notifier.OBJECT] != obj or
            #                                                val[1][Notifier.TRIGGER] not in [Notifier.CHANGE, Notifier.RENAME],
            #                                    executeQueue))
            #
            #     if trigger == Notifier.CREATE:
            #         # can skip this notifier if CREATE found
            #         scheduledQueue |= {(obj, Notifier.CHANGE), (obj, Notifier.RENAME)}
            #
            #         # discard CHANGE, RENAME notifiers
            #         executeQueue = list(filter(lambda val: val[1][Notifier.OBJECT] != obj or
            #                                                val[1][Notifier.TRIGGER] not in [Notifier.CHANGE, Notifier.RENAME],
            #                                    executeQueue))
            #
            #     elif trigger == Notifier.CHANGE:
            #         # can skip this notifier if RENAME found
            #         scheduledQueue |= {(obj, Notifier.RENAME),}
            #
            #         # discard CHANGE notifiers
            #         executeQueue = list(filter(lambda val: val[1][Notifier.OBJECT] != obj or
            #                                                val[1][Notifier.TRIGGER] not in [Notifier.RENAME],
            #                                    executeQueue))

            # this is in reverse order
            executeQueue.append((func, data))

    return list(reversed(executeQueue))
