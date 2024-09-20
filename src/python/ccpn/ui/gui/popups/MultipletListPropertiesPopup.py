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
__dateModified__ = "$dateModified: 2024-04-04 15:19:22 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier
from ccpn.core.MultipletList import MULTIPLETAVERAGINGTYPES
from ccpn.ui.gui.popups.PMIListPropertiesPopupABC import PMIListPropertiesPopupABC, queueStateChange, BUTTONOPTIONS
from ccpn.ui.gui.popups.Dialog import _verifyPopupApply
from ccpn.core.MultipletList import MultipletList
from ccpn.ui.gui.popups.AttributeEditorPopupABC import getAttributeTipText
from ccpn.util.Common import camelCaseToString
from ccpn.core.lib.ContextManagers import notificationEchoBlocking, undoStackBlocking


MULTIPLETAVERAGING = 'multipletAveraging'


class MultipletListPropertiesPopup(PMIListPropertiesPopupABC):
    """
    Popup to handle changing parameters in multipletLists
    """

    # class of lists handled by popup
    klass = MultipletList
    attributes = [('Id', getattr, None, {'backgroundText': '> Not defined <'}),
                  ('Comment', getattr, setattr, {'backgroundText': '> Optional <'}),
                  ]
    _symbolColourOption = True
    _textColourOption = True
    _lineColourOption = True
    _meritColourOption = True
    _meritOptions = True
    _arrowColourOption = True

    def __init__(self, parent=None, mainWindow=None, multipletList=None, title=None, **kwds):
        super().__init__(
            parent=parent,
            mainWindow=mainWindow,
            ccpnList=multipletList,
            title=f'{self.klass.className} Properties',
            **kwds,
        )

        self.multipletAveragingLabel = Label(self.mainWidget, text=camelCaseToString(MULTIPLETAVERAGING), grid=(self._rowForNewItems, 0))
        if tipText := getAttributeTipText(self.klass, MULTIPLETAVERAGING):
            self.multipletAveragingLabel.setToolTip(tipText)

        multipletAveraging = self.ccpnList.multipletAveraging
        self.multipletAveraging = RadioButtons(self.mainWidget, texts=MULTIPLETAVERAGINGTYPES,
                                               selectedInd=MULTIPLETAVERAGINGTYPES.index(
                                                       multipletAveraging) if multipletAveraging in MULTIPLETAVERAGINGTYPES else 0,
                                               callback=self._queueSetMeritAveraging,
                                               direction='v',
                                               grid=(self._rowForNewItems, 1), hAlign='l',
                                               tipTexts=None,
                                               )

    def _getSettings(self):
        """Fill the settings dict from the listView object
        """
        super()._getSettings()

        # add the merit averaging
        self.listViewSettings[MULTIPLETAVERAGING] = getattr(self.ccpnList, MULTIPLETAVERAGING, None) or \
                                                    MULTIPLETAVERAGINGTYPES[0]

    def _setWidgetSettings(self):
        """Populate the widgets from the settings dict
        """
        super()._setWidgetSettings()

        multipletAveraging = self.listViewSettings[MULTIPLETAVERAGING]
        self.multipletAveraging.setIndex(MULTIPLETAVERAGINGTYPES.index(multipletAveraging)
                                         if multipletAveraging in MULTIPLETAVERAGINGTYPES else 0)

    def _setListViewFromWidgets(self):
        """Set listView object from the widgets
        """
        with notificationEchoBlocking():
            with undoStackBlocking():
                super()._setListViewFromWidgets()

                multipletAveraging = self.multipletAveraging.getIndex()
                setattr(self.ccpnList, MULTIPLETAVERAGING, MULTIPLETAVERAGINGTYPES[multipletAveraging])

    def _setListViewFromSettings(self):
        """Set listView object from the original settings dict
        """
        with notificationEchoBlocking():
            with undoStackBlocking():
                super()._setListViewFromSettings()

                multipletAveraging = self.listViewSettings[MULTIPLETAVERAGING]
                if multipletAveraging is not None:
                    setattr(self.ccpnList, MULTIPLETAVERAGING, multipletAveraging)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _refreshGLItems(self):
        # emit a signal to rebuild all peaks and multiplets
        self.GLSignals.emitEvent(targets=[self.ccpnList], triggers=[GLNotifier.GLMULTIPLETLISTS,
                                                                    GLNotifier.GLMULTIPLETLISTLABELS])

    def _getListViews(self, ccpnList):
        """Return the listViews containing this list
        """
        return [multipletListView for multipletListView in self.project.multipletListViews
                if multipletListView.multipletList == ccpnList]

    def _applyAllChanges(self, changes):
        """Apply all changes - add new multipletList to the spectrum
        """
        super()._applyAllChanges(changes)
        if not self.EDITMODE:

            if 'id' in self.ccpnList:
                del self.ccpnList['id']

            # create the new multipletList
            self.spectrum.newMultipletList(**self.ccpnList)

    def _populateInitialValues(self):
        """Populate the initial values for an empty object
        """
        super()._populateInitialValues()

        # need to get the next available multipletList name
        _num = len(self.spectrum.multipletLists) + 1
        self.ccpnList.id = f'{self.spectrum.name}.{_num}'
        self.ccpnList.multipletAveraging = 0

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @queueStateChange(_verifyPopupApply)
    def _queueSetMeritAveraging(self):
        value = MULTIPLETAVERAGINGTYPES[self.multipletAveraging.getIndex()]
        # set the state of the other buttons
        if value != getattr(self.COMPARELIST, MULTIPLETAVERAGING, MULTIPLETAVERAGINGTYPES[0]):
            return partial(self._setMeritAveraging, value)

    def _setMeritAveraging(self, value):
        setattr(self.ccpnList, MULTIPLETAVERAGING, value)
