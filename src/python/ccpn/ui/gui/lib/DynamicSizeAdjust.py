"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2024-05-13 13:17:42 +0100 (Mon, May 13, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-09-02 13:02:37 +0100 (Fri, September 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtWidgets
from functools import partial
from typing import Optional
from ccpn.util.Logging import getLogger


_INITIAL_STEP = 256
_MAX_ITERATIONS = 50


def _fixedSize(widget, lastSizes, completedFunction):
    """Fix the width/height as required.
    """
    lastSizes.insert(0, (widget.size().width(), widget.size().height()))
    lastSizes = lastSizes[:3]  # keep the last 3

    if len(set(lastSizes)) > 1:
        # size is not stable yet
        QtCore.QTimer().singleShot(0, partial(_fixedSize, widget, lastSizes, completedFunction))
    else:
        wFixed = getattr(widget, 'FIXEDWIDTH', False)
        hFixed = getattr(widget, 'FIXEDHEIGHT', False)
        # size is stable
        if wFixed:
            widget.setFixedWidth(widget.width())
        if hFixed:
            widget.setFixedHeight(widget.height())

        if completedFunction:
            # resizing has finished, call the completedFunction if needed
            completedFunction()


def dynamicSizeAdjust(widget, sizeFunction: callable = None, completedFunction: callable = None,
                      step: int = _INITIAL_STEP, adjustWidth: bool = True, adjustHeight: bool = False,
                      _steps: QtCore.QSize = None, _lastSteps: QtCore.QSize = None, _lastsizes: QtCore.QSize = None,
                      _maxIterations: int = _MAX_ITERATIONS
                      ):
    """Iterator to adjust the size of the widget to a target-size.

    The size of the widget is altered geometrically every frame until the target-size is reached,
    from an initial step-size set by step, which halves each iteration.

    The target-size is defined by the sizeFunction method;
    sizeFunction must return a tuple(target-size: QtCore.QSize, dynamic-size: QtCore.QSize),
    or None to terminate the iteration at any time.
     - the first value is the size to iterate towards, and the second value is the size of the changing widget.

    step is the initial step-size, and must be of the form 2^n, the default initial step-size is 1024.
    Set adjustWidth/Height to adjust the required dimension, the default is adjustWidth is True, adjustWidth is False.

        To start the size operation, call as follows:

        >>> QtCore.QTimer().singleShot(0, partial(dynamicSizeAdjust, widget, sizeFunction, completedFunction,
        >>>                                       adjustWidth=True, adjustHeight=False))

    :param callable sizeFunction: function to return the target-size, match-size
    :param callable completedFunction: function called when the resize has stopped
    :param int step: step to change widget size
    :param bool adjustWidth: adjust the width
    :param bool adjustHeight: adjust the height
    :param QtCore.QSize _steps: current step-size
    :param QtCore.QSize _lastSteps: previous step-size
    :param QtCore.QSize _lastsizes: previous widget size
    :param int _maxIterations: counter to always stop after maximum iterations
    """
    # check parameters are correct
    if not (sizeFunction and callable(sizeFunction)):
        raise TypeError(f'{widget.__class__.__name__}.dynamicSizeAdjust: sizeFunction is not callable')
    if not (isinstance(step, int) and (step & (step - 1) == 0)):
        # nice trick to check that number is power of 2
        raise TypeError(f'{widget.__class__.__name__}.dynamicSizeAdjust: step is not an int of the form 2^n')
    if not isinstance(adjustWidth, bool):
        raise TypeError(f'{widget.__class__.__name__}.dynamicSizeAdjust: adjustWidth must be True/False')
    if not isinstance(adjustHeight, bool):
        raise TypeError(f'{widget.__class__.__name__}.dynamicSizeAdjust: adjustHeight must be True/False')
    if completedFunction and not callable(completedFunction):
        raise TypeError(f'{widget.__class__.__name__}.dynamicSizeAdjust: completedFunction is not callable')

    try:
        if not (_maxIterations := _maxIterations - 1):
            # exit if max iterations reached
            getLogger().debug('dynamicSizeAdjust failed - maximum iterations reached')
            if completedFunction:
                # call the completedFunction if needed
                QtCore.QTimer().singleShot(0, completedFunction)
            return
        # set the step-sizes for the first iteration
        if _steps is None:
            _steps = QtCore.QSize(step, step)
        # get the sizes of the target-widget and the widget to match against
        if (sizes := sizeFunction()) is not None:
            target, size = sizes

            if (_lastSteps == _steps) and (_lastsizes == size):
                # stop if widget isn't resizing correctly
                if completedFunction:
                    # call the completedFunction if needed
                    QtCore.QTimer().singleShot(0, completedFunction)
                return
            _lastSteps, _lastsizes = _steps, size
            thisStepW, thisStepH = _steps.width(), _steps.height()
            while adjustWidth and thisStepW >= 1 and abs(size.width() - target.width()) < thisStepW:
                # iteratively change step-size until less than distance to target-width
                thisStepW = thisStepW // 2
            while adjustHeight and thisStepH >= 1 and abs(size.height() - target.height()) < thisStepH:
                # iteratively change step-size until less than distance to target-height
                thisStepH = thisStepH // 2

            if (adjustWidth and thisStepW >= 1) or (adjustHeight and thisStepH >= 1):
                # if this still needs to adjust the width/height then perform another iteration
                _steps = QtCore.QSize(thisStepW, thisStepH)
                # adjust the size
                adjustW = ((int(thisStepW) if size.width() < target.width() else -int(thisStepW))
                           if adjustWidth else 0)
                adjustH = ((int(thisStepH) if size.height() < target.height() else -int(thisStepH))
                           if adjustHeight else 0)
                widget.setFixedSize(QtWidgets.QWIDGETSIZE_MAX, QtWidgets.QWIDGETSIZE_MAX)
                widget.resize(widget.width() + adjustW, widget.height() + adjustH)
                # create another single-shot - waits until gui is up-to-date before firing
                QtCore.QTimer().singleShot(0, partial(dynamicSizeAdjust, widget=widget,
                                                      sizeFunction=sizeFunction, completedFunction=completedFunction,
                                                      step=step, adjustWidth=adjustWidth, adjustHeight=adjustHeight,
                                                      _steps=_steps, _lastSteps=_lastSteps, _lastsizes=_lastsizes,
                                                      _maxIterations=_maxIterations,
                                                      ))
                return
            QtCore.QTimer().singleShot(0, partial(_fixedSize, widget, [(0, 0)], completedFunction))
    except Exception as es:
        getLogger().debug2(f'dynamicSizeAdjust failed {es}')


#=========================================================================================
# Example size-functions
#=========================================================================================

def _targetTabSize(self) -> tuple | None:
    """Get the size of the widget to match the popup to.
    Returns the size of the clicked tab and current size, or None if there is an error.
    None will terminate the iteration.
    :return tuple | None: (target-size, current-size), or None.
    """
    try:
        # get the widths of the tabWidget and the current tab to match against
        tab = self.tabWidget.currentWidget()
        targetSize = tab._scrollContents.sizeHint() + QtCore.QSize(self.BORDER_OFFSET, 2 * self.BORDER_OFFSET)
        # match against the tab-container
        sourceSize = self.tabWidget.size()
        return targetSize, sourceSize
    except Exception:
        return None


def _targetPopupSize(self) -> tuple | None:
    """Simple method to match a popup to its contents.
    Returns the size of the widget to iterate towards and the current size, or None if there is an error.
    None will terminate the iteration.
    :return tuple | None: (target-size, current-size), or None.
    """
    try:
        targetSize = self.minimumSizeHint()
        sourceSize = self.size()
        return targetSize, sourceSize
    except Exception:
        return None
