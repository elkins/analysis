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
__dateModified__ = "$dateModified: 2024-08-23 19:21:21 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-05-28 10:28:42 +0000 (Sun, May 28, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import time
import matplotlib
import matplotlib.backends.qt_editor.figureoptions as figureoptions
import matplotlib.backend_bases as backends
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backend_tools import ToolBase, ToolToggleBase, ZoomPanBase, cursors, _views_positions
from matplotlib.backend_managers import ToolManager
import matplotlib.pyplot as plt
from PyQt5 import QtWidgets, QtCore
from collections import OrderedDict as od
import ccpn.ui.gui.guiSettings as GS
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Action import Action
from ccpn.ui.gui.widgets.ToolBar import ToolBar
from ccpn.ui.gui.widgets import MessageDialog as md
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.util.Logging import getLogger


CLASSIC = 'classic'
ColourMap = {
    GS.Theme.DEFAULT : CLASSIC,
    GS.Theme.DARK : 'dark_background',
    GS.Theme.LIGHT : 'seaborn-bright',
    }


def _setDefaultGlobalPlotPreferences(plt):
    """
    Set the global preferences in the plt.rcParams dictionary.
    # TODO: make a better mechanism to set these from general preferences.
    # add missing bits:
    # fonts
    # font size
    # font colour
    # curve thickness
    # axis thickness
    # axis colours
    # axis thick orientation
    # zoomPercent
    """
    ccpnColourScheme = GS.getColourScheme()
    ## set background
    plt.style.use(ColourMap.get(ccpnColourScheme, CLASSIC))
    setPlotPreference(plt, 'ytick.right', False)  # don't show Y ticks on right
    setPlotPreference(plt, 'xtick.top', False)  # don't show Top X ticks
    # setPlotPreference(plt, 'ytick.labelright', False)   # don't show label ticks
    # setPlotPreference(plt, 'xtick.labelleft', False)    # don't show label ticks
    ## setup backend
    setPlotPreference(plt, 'interactive', False)  # Set to True here could cause to open twice a plot.
    setPlotPreference(plt, 'backend', 'Qt5Agg')


def setPlotPreference(plt, key, value):
    """
    Set a preference for matplotlib. Require restarting the plot.
    """
    plt.rcParams[key] = value


def getPlotPreferences(plt):
    return plt.rcParams


class PyPlotToolbar(ToolBar, backends.NavigationToolbar2):
    """
    Re-implementation of Matplotlib ToolBar with CcpNmr widgets ands syntax.
    Matplotlib  backends for toolbars gave UserWarning as it was an experimental feature at the time of
    this implementation.
    Navigation Toolbar controls panning and zooming. Therefore re-implementations of those actions are done here.
    """
    message = QtCore.pyqtSignal(str)

    def __init__(self, parent, canvas, coordinates=True, *args, **kwargs):
        super().__init__(canvas)
        backends.NavigationToolbar2.__init__(self, canvas)

        self.canvas = canvas
        self.parent = parent
        self.coordinates = coordinates

        #  set panning the only active mode
        self._active = 'PAN'
        self._initConnections()
        # scrolling
        self.base_scale = 2.
        self.scrollthresh = .5  # .5 second scroll threshold
        self.lastscroll = time.time() - self.scrollthresh
        self._initToolbarActions()

    def _getToolBarDefs(self):
        """
        The menu action definitions
        """
        toolBarDefs = (
            ('MaximiseZoom', od((
                ('text', 'MaximiseZoom'),
                ('toolTip', 'Full zoom'),
                ('icon', Icon('icons/zoom-full.png')),
                ('callback', self.home),
                ('enabled', True)
                ))),
            ('UndoZoom', od((
                ('text', 'UndoZoom'),
                ('toolTip', 'Previous zoom'),
                ('icon', Icon('icons/zoom-undo.png')),
                ('callback', self.back),
                ('enabled', True)
                ))),
            ('RedoZoom', od((
                ('text', 'RedoZoom'),
                ('toolTip', 'Next zoom'),
                ('icon', Icon('icons/zoom-redo.png')),
                ('callback', self.forward),
                ('enabled', True)
                ))),
            (),

            ('settings', od((
                ('text', 'settings'),
                ('toolTip', 'settings'),
                ('icon', Icon('icons/settings_cog.png')),
                ('callback', self.showSettings),
                ('enabled', True)
                ))),
            ('SaveAs', od((
                ('text', 'SaveAs'),
                ('toolTip', 'Save image to disk'),
                ('icon', Icon('icons/saveAs.png')),
                ('callback', self.save_figure),
                ('enabled', True)
                ))),
            (),
            )
        return toolBarDefs

    def _initToolbarActions(self):
        for v in self._getToolBarDefs():
            if len(v) == 2:
                if isinstance(v[1], od):
                    action = Action(self, **v[1])
                    action.setObjectName(v[0])
                    self.addAction(action)
            else:
                self.addSeparator()

    def save_figure(self, *args):
        filetypes = self.canvas.get_supported_filetypes_grouped()
        sorted_filetypes = sorted(filetypes.items())
        default_filetype = self.canvas.get_default_filetype()

        startpath = os.path.expanduser(
                matplotlib.rcParams['savefig.directory'])
        start = os.path.join(startpath, self.canvas.get_default_filename())
        filters = []
        selectedFilter = None
        for name, exts in sorted_filetypes:
            exts_list = " ".join(['*.%s' % ext for ext in exts])
            _filter = '%s (%s)' % (name, exts_list)
            if default_filetype in exts:
                selectedFilter = _filter
            filters.append(_filter)
        filters = ';;'.join(filters)
        # TODO replace with CCPN dialog
        _getSaveFileName = QtWidgets.QFileDialog.getSaveFileName
        fname, _filter = _getSaveFileName(self.canvas.parent(),
                                         "Choose a filename to save to",
                                         start, filters, selectedFilter)
        if fname:
            # Save dir for next time, unless empty str (i.e., use cwd).
            if startpath != "":
                matplotlib.rcParams['savefig.directory'] = (
                    os.path.dirname(fname))
            try:
                self.canvas.figure.savefig(fname)
            except Exception as e:
                md.showError('Error saving', e)

    def showSettings(self):
        self._editParameters()

    def _editParameters(self):
        """
        Copied from NavigationToolbar2QT
        """
        axes = self.canvas.figure.get_axes()
        if not axes:
            QtWidgets.QMessageBox.warning(
                    self.parent, "Error", "There are no axes to edit.")
            return
        elif len(axes) == 1:
            ax, = axes
        else:
            titles = [
                ax.get_label() or
                ax.get_title() or
                " - ".join(filter(None, [ax.get_xlabel(), ax.get_ylabel()])) or
                f"<anonymous {type(ax).__name__}>"
                for ax in axes]
            duplicate_titles = [
                title for title in titles if titles.count(title) > 1]
            for i, ax in enumerate(axes):
                if titles[i] in duplicate_titles:
                    titles[i] += f" (id: {id(ax):#x})"  # Deduplicate titles.
            item, ok = QtWidgets.QInputDialog.getItem(
                    self.parent, 'Customise', 'Select axes:', titles, 0, False)
            if not ok:
                return
            ax = axes[titles.index(item)]
        figureoptions.figure_edit(ax, self)

    def _initConnections(self, *args):
        """
        Re-implemetation of panning/zooming to have a consistent behaviour with other Ccpn widgets.
        Disable the native "pan or zoom' mouse mode
        """

        if self._active:
            self._idPress = self.canvas.mpl_connect(
                    'button_press_event', self.press_pan)
            self._idRelease = self.canvas.mpl_connect(
                    'button_release_event', self.release_pan)
            self._idScroll = self.canvas.mpl_connect(
                    'scroll_event', self.scroll_event)
            # self.mode = 'pan/zoom'
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)

        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

    def scroll_event(self, event):
        if event.inaxes is None:
            return
        if event.button == 'up':
            # deal with zoom in
            scl = self.base_scale
        elif event.button == 'down':
            # deal with zoom out
            scl = 1 / self.base_scale
        else:
            # deal with something that should never happen
            scl = 1

        ax = event.inaxes
        ax._set_view_from_bbox([event.x, event.y, scl])
        self.canvas.draw_idle()  # force re-draw
