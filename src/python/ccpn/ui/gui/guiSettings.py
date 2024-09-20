"""
Settings used in gui modules, widgets and popups

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
__dateModified__ = "$dateModified: 2024-09-06 12:35:04 +0100 (Fri, September 06, 2024) $"
__version__ = "$Revision: 3.2.6 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: geertenv $"
__date__ = "$Date: 2016-11-15 21:37:50 +0000 (Tue, 15 Nov 2016) $"
#=========================================================================================
# Start of code
#=========================================================================================

from itertools import product
from PyQt5 import QtGui

from ccpn.ui.gui.widgets.Font import (Font, DEFAULTFONT,
                                      DEFAULTFONTSIZE, DEFAULTFONTNAME, CONSOLEFONT, SIDEBARFONT,
                                      TABLEFONT, SEQUENCEGRAPHFONT, _readFontFromAppearances)
from ccpn.util.decorators import singleton
from ccpn.util.Logging import getLogger
from ccpn.util.Colour import (allColours, hexToRgbRatio, autoCorrectHexColour,
                              spectrumHexDarkColours, spectrumHexLightColours, spectrumHexMediumColours,
                              spectrumHexDefaultLightColours, spectrumHexDefaultDarkColours, rgbRatioToHex)
from ccpn.util.DataEnum import DataEnum
from ccpn.framework.Application import getApplication


FONTLIST = ['Modules', 'IPython console', 'Sidebar', 'Tables', 'Sequence graph']


class FontSizes(DataEnum):
    MINIMUM = 0.25, 'minimum, quarter size'
    TINY = 0.5, 'smallest font, half size'
    SMALL = 0.75, 'smaller font'
    MEDIUM = 1.0, 'default sized font, unit scale of the chosen font'
    LARGE = 1.25, 'larger font'
    VLARGE = 1.5, 'very large font'
    HUGE = 2.0, 'huge font'
    MAXIMUM = 3.0, 'maximum, triple default size'


class FontSettings():

    def __init__(self, preferences):

        self.defaultFonts = {}
        for fontNum, fontName in enumerate((DEFAULTFONT, CONSOLEFONT, SIDEBARFONT, TABLEFONT, SEQUENCEGRAPHFONT)):
            _fontAttr = 'font{}'.format(fontNum)
            fontString = _readFontFromAppearances(_fontAttr, preferences)
            self.generateFonts(fontName, fontString)

    def generateFonts(self, fontName, fontString):
        try:
            fontList = fontString.split(',')
            name, size, _, _, weight = fontList[0:5]

            for ii, fontSize in enumerate(FontSizes):
                thisSize = int(size) * fontSize.value

                fontList[1] = str(thisSize)
                # define a default font but override with string values
                for bold, italic in product((False, True), repeat=2):
                    newFont = Font(name, int(size))
                    newFont.fromString(','.join(fontList))
                    newFont.setBold(bold)
                    newFont.setItalic(italic)
                    self.defaultFonts[(fontName, fontSize.name, bold, italic)] = newFont

        except Exception as es:
            getLogger().warning('Reverting to default font {}'.format(es))

            name, size = DEFAULTFONTNAME, DEFAULTFONTSIZE

            for ii, fontSize in enumerate(FontSizes):
                thisSize = DEFAULTFONTSIZE * fontSize.value

                for bold, italic in product((False, True), repeat=2):
                    newFont = Font(name, int(thisSize))
                    newFont.setBold(bold)
                    newFont.setItalic(italic)
                    self.defaultFonts[(fontName, fontSize.name, bold, italic)] = newFont

    def getFont(self, name=DEFAULTFONT, size='MEDIUM', bold=False, italic=False):
        try:
            if bold and italic and (name, size, bold, italic) in self.defaultFonts:
                return self.defaultFonts[(name, size, bold, italic)]
            elif bold and (name, size, bold, italic) in self.defaultFonts:
                return self.defaultFonts[(name, size, bold, italic)]
            elif italic and (name, size, bold, italic) in self.defaultFonts:
                return self.defaultFonts[(name, size, bold, italic)]

            return self.defaultFonts[(name, size, False, False)]
        except Exception:
            getLogger().warning('Font ({}, {}, {}, {}) not found'.format(name, size, bold, italic))
            return Font(DEFAULTFONTNAME, DEFAULTFONTSIZE)


# Colours
# LIGHT = 'light'
# DARK = 'dark'
# DEFAULT = 'default'
MARKS_COLOURS = 'marksColours'


class Theme(DataEnum):
    # name, value, description, dataValue = number of isotope-codes per order
    LIGHT = 0, 'light', 'light'
    DARK = 1, 'dark', 'dark'
    DEFAULT = 2, 'follow appearance->style', 'default'


COLOUR_SCHEMES = Theme.dataValues()

DEFAULT_COLOR = 'default'
SPECTRUM_HEXCOLOURS = 'spectrumHexColours'
SPECTRUM_HEXDEFAULTCOLOURS = 'spectrumHexDefaultColours'
SPECTRUM_HEXMEDIUMCOLOURS = 'spectrumHexMediumColours'
SPECTRUMCOLOURS = 'spectrumColours'

MARK_LINE_COLOUR_DICT = {
    'CA'         : '#0080FF',
    'CB'         : '#6666FF',
    'CG'         : '#0048FF',
    'CD'         : '#006DFF',
    'CE'         : '#0091FF',
    'CZ'         : '#00B6FF',
    'CH'         : '#00DAFF',
    'C'          : '#00FFFF',
    'Cn'         : '#00FFFF',
    'HA'         : '#FF0000',
    'HB'         : '#FF0024',
    'HG'         : '#FF0048',
    'HD'         : '#FF006D',
    'HE'         : '#FF0091',
    'HZ'         : '#FF00B6',
    'HH'         : '#FF00DA',
    'H'          : '#FF00FF',
    'Hn'         : '#FF00FF',
    'N'          : '#00FF00',
    'Nh'         : '#00FF00',
    'ND'         : '#3FFF00',
    'NE'         : '#7FFF00',
    'NZ'         : '#BFFF00',
    'NH'         : '#FFFF00',
    DEFAULT_COLOR: '#e0e0e0'
    }

# Widget definitions
CCPNMODULELABEL_FOREGROUND = 'CCPNMODULELABEL_FOREGROUND'
CCPNMODULELABEL_BACKGROUND = 'CCPNMODULELABEL_BACKGROUND'
CCPNMODULELABEL_BORDER = 'CCPNMODULELABEL_BORDER'
CCPNMODULELABEL_FOREGROUND_ACTIVE = 'CCPNMODULELABEL_FOREGROUND_ACTIVE'
CCPNMODULELABEL_BACKGROUND_ACTIVE = 'CCPNMODULELABEL_BACKGROUND_ACTIVE'
CCPNMODULELABEL_BORDER_ACTIVE = 'CCPNMODULELABEL_BORDER_ACTIVE'

HEXFOREGROUND = 'HEXFOREGROUND'
HEXBACKGROUND = 'HEXBACKGROUND'

# Spectrum GL base class
CCPNGLWIDGET_HEXFOREGROUND = 'CCPNGLWIDGET_HEXFOREGROUND'
CCPNGLWIDGET_HEXBACKGROUND = 'CCPNGLWIDGET_HEXBACKGROUND'
CCPNGLWIDGET_HEXHIGHLIGHT = 'CCPNGLWIDGET_HEXHIGHLIGHT'
CCPNGLWIDGET_FOREGROUND = 'CCPNGLWIDGET_FOREGROUND'
CCPNGLWIDGET_BACKGROUND = 'CCPNGLWIDGET_BACKGROUND'
CCPNGLWIDGET_BUTTON_FOREGROUND = 'CCPNGLWIDGET_BUTTON_FOREGROUND'

CCPNGLWIDGET_PICKCOLOUR = 'CCPNGLWIDGET_PICKCOLOUR'
CCPNGLWIDGET_GRID = 'CCPNGLWIDGET_GRID'
CCPNGLWIDGET_HIGHLIGHT = 'CCPNGLWIDGET_HIGHLIGHT'
CCPNGLWIDGET_LABELLING = 'CCPNGLWIDGET_LABELLING'
CCPNGLWIDGET_PHASETRACE = 'CCPNGLWIDGET_PHASETRACE'
CCPNGLWIDGET_MULTIPLETLINK = 'CCPNGLWIDGET_MULTIPLETLINK'

CCPNGLWIDGET_ZOOMAREA = 'CCPNGLWIDGET_ZOOMAREA'
CCPNGLWIDGET_PICKAREA = 'CCPNGLWIDGET_PICKAREA'
CCPNGLWIDGET_SELECTAREA = 'CCPNGLWIDGET_SELECTAREA'
CCPNGLWIDGET_BADAREA = 'CCPNGLWIDGET_BADAREA'
CCPNGLWIDGET_ZOOMLINE = 'CCPNGLWIDGET_ZOOMLINE'
CCPNGLWIDGET_MOUSEMOVELINE = 'CCPNGLWIDGET_MOUSEMOVELINE'
CCPNGLWIDGET_HARDSHADE = 0.9

GUICHAINLABEL_TEXT = 'GUICHAINLABEL_TEXT'

GUICHAINRESIDUE_UNASSIGNED = 'GUICHAINRESIDUE_UNASSIGNED'
GUICHAINRESIDUE_ASSIGNED = 'GUICHAINRESIDUE_ASSIGNED'
GUICHAINRESIDUE_POSSIBLE = 'GUICHAINRESIDUE_POSSIBLE'
GUICHAINRESIDUE_WARNING = 'GUICHAINRESIDUE_WARNING'
GUICHAINRESIDUE_DRAGENTER = 'GUICHAINRESIDUE_DRAGENTER'
GUICHAINRESIDUE_DRAGLEAVE = 'GUICHAINRESIDUE_DRAGLEAVE'

GUINMRATOM_SELECTED = 'GUINMRATOM_SELECTED'
GUINMRATOM_NOTSELECTED = 'GUINMRATOM_NOTSELECTED'

GUINMRRESIDUE = 'GUINMRRESIDUE'

GUISTRIP_PIVOT = 'GUISTRIP_PIVOT'

FUSION_BACKGROUND = 'FUSION_BACKGROUND'
FUSION_FOREGROUND = 'FUSION_FOREGROUND'

DRAG_FOREGROUND = 'DRAG_FOREGROUND'
DRAG_BACKGROUND = 'DRAG_BACKGROUND'
LABEL_FOREGROUND = 'LABEL_FOREGROUND'
LABEL_BACKGROUND = 'LABEL_BACKGROUND'
LABEL_SELECTEDBACKGROUND = 'LABEL_SELECTEDBACKGROUND'
LABEL_SELECTEDFOREGROUND = 'LABEL_SELECTEDFOREGROUND'
LABEL_HIGHLIGHT = 'LABEL_HIGHLIGHT'
LABEL_WARNINGFOREGROUND = 'LABEL_WARNINGFOREGROUND'
LABEL_DISABLED = 'LABEL_DISABLED'

TABLE_FOREGROUND = 'TABLE_FOREGROUND'

DIVIDER = 'DIVIDER'
SOFTDIVIDER = 'SOFTDIVIDER'

SEQUENCEGRAPHMODULE_LINE = 'SEQUENCEGRAPHMODULE_LINE'
SEQUENCEGRAPHMODULE_TEXT = 'SEQUENCEGRAPHMODULE_TEXT'

SEQUENCEMODULE_DRAGMOVE = 'SEQUENCEMODULE_DRAGMOVE'
SEQUENCEMODULE_TEXT = 'SEQUENCEMODULE_TEXT'

# used in GuiTable stylesheet (cannot change definition)
GUITABLE_BACKGROUND = 'GUITABLE_BACKGROUND'
GUITABLE_ALT_BACKGROUND = 'GUITABLE_ALT_BACKGROUND'
GUITABLE_ITEM_FOREGROUND = 'GUITABLE_ITEM_FOREGROUND'
GUITABLE_SELECTED_FOREGROUND = 'GUITABLE_SELECTED_FOREGROUND'
GUITABLE_SELECTED_BACKGROUND = 'GUITABLE_SELECTED_BACKGROUND'
GUITABLE_DROP_BORDER = 'GUITABLE_DROP_BORDER'
GUITABLE_GRIDLINES = 'GUITABLE_GRIDLINES'
GUITABLEHEADER_SELECTED_FOREGROUND = 'GUITABLEHEADER_SELECTED_FOREGROUND'
GUITABLEHEADER_SELECTED_BACKGROUND = 'GUITABLEHEADER_SELECTED_BACKGROUND'
GUITABLEHEADER_GROUP_GRIDLINES = 'GUITABLEHEADER_GROUP_GRIDLINES'

# strip header colours
GUITABLEHEADER_FOREGROUND = 'GUITABLEHEADER_FOREGROUND'
GUITABLEHEADER_BACKGROUND = 'GUITABLEHEADER_BACKGROUND'

# border for focus/noFocus - QPlainTextEdit
BORDERNOFOCUS = 'BORDER_NOFOCUS'
BORDERFOCUS = 'BORDER_FOCUS'
TOOLTIP_BACKGROUND = 'TOOLTIP_BACKGROUND'
TOOLTIP_FOREGROUND = 'TOOLTIP_FOREGROUND'
HIGHLIGHT = 'HIGHLIGHT'
HIGHLIGHT_SOLID = 'HIGHLIGHT_SOLID'
HIGHLIGHT_BORDER = 'HIGHLIGHT_BORDER'
HIGHLIGHT_VIVID = 'HIGHLIGHT_VIVID'
HIGHLIGHT_FEINT = 'HIGHLIGHT_FEINT'
PALETTE = 'PALETTE'

#----------------------------------------------------------------------------------------------
# Colours
#----------------------------------------------------------------------------------------------

# A gradient of colours "green" to "red", but adjusted for colour-blind people as well
# from: https://www.visualisingdata.com/2019/08/five-ways-to-design-for-red-green-colour-blindness/
COLOUR_BLIND_DARKGREEN = QtGui.QColor('#009297')
COLOUR_BLIND_LIGHTGREEN = QtGui.QColor('#57C4AD')
COLOUR_BLIND_MEDIUM = QtGui.QColor('#E6E1BC')
COLOUR_BLIND_ORANGE = QtGui.QColor('#EDA247')
COLOUR_BLIND_RED = QtGui.QColor('#DB4325')

TEXT_COLOUR = '#22284E'
TEXT_COLOUR_WARNING = '#E06523'
SOFT_DIVIDER_COLOUR = '#888DA5'
LIGHT_GREY = 'rgb(245,245,245)'
STEEL = 'rgb(102,102,102)'  # from apple
MARISHINO = '#004D81'  # rgb(0,77,129) ; red colour (from apple)
MEDIUM_BLUE = '#7777FF'
GREEN1 = '#009a00'
WARNING_RED = '#e01010'
FIREBRICK = hexToRgbRatio(next((k for k, v in allColours.items() if v == 'firebrick'), '#F03010'))
LIGHTCORAL = hexToRgbRatio(next((k for k, v in allColours.items() if v == 'lightcoral'), '#F03010'))
TOOLTIP_BACKGROUND_COLOUR = next((k for k, v in allColours.items() if v == 'lightgoldenrodyellow'), '#F03010')
TOOLTIP_FOREGROUND_COLOUR = '#222438'

BORDERNOFOCUS_COLOUR = '#A9A9A9'
BORDERFOCUS_COLOUR = '#4E86F6'
HIGHLIGHT_COLOUR = '#0063E1'
GUITABLE_DROP_BORDER_COLOUR = GREEN1

# Shades
CCPNGLWIDGET_REGIONSHADE = 0.30
CCPNGLWIDGET_INTEGRALSHADE = 0.1

# Colour schemes definitions
colourSchemes = {
    # all colours defined here
    Theme.DEFAULT.name: {
        HEXFOREGROUND                     : '#070707',
        HEXBACKGROUND                     : '#ffffff',

        # these will get replaced when the theme changes
        CCPNGLWIDGET_HEXFOREGROUND        : '#070707',
        CCPNGLWIDGET_HEXBACKGROUND        : '#FFFFFF',
        CCPNGLWIDGET_HEXHIGHLIGHT         : rgbRatioToHex(0.23, 0.23, 1.0),
        CCPNGLWIDGET_FOREGROUND           : (0.05, 0.05, 0.05, 1.0),
        CCPNGLWIDGET_BACKGROUND           : (1.0, 1.0, 1.0, 1.0),
        CCPNGLWIDGET_BUTTON_FOREGROUND    : (0.2, 0.21, 0.2, 1.0),  #'#080000'
        CCPNGLWIDGET_PICKCOLOUR           : (0.2, 0.5, 0.9, 1.0),
        CCPNGLWIDGET_GRID                 : (0.5, 0.0, 0.0, 1.0),  #'#080000'
        CCPNGLWIDGET_HIGHLIGHT            : (0.23, 0.23, 1.0, 1.0),  #'#3333ff'
        CCPNGLWIDGET_LABELLING            : (0.05, 0.05, 0.05, 1.0),
        CCPNGLWIDGET_PHASETRACE           : (0.2, 0.2, 0.2, 1.0),
        CCPNGLWIDGET_ZOOMAREA             : (0.8, 0.9, 0.2, 0.3),
        CCPNGLWIDGET_PICKAREA             : (0.2, 0.5, 0.9, 0.3),
        CCPNGLWIDGET_SELECTAREA           : (0.8, 0.2, 0.9, 0.3),
        CCPNGLWIDGET_BADAREA              : (0.9, 0.15, 0.1, 0.3),
        CCPNGLWIDGET_ZOOMLINE             : (0.6, 0.7, 0.2, 1.0),
        CCPNGLWIDGET_MOUSEMOVELINE        : (0.8, 0.2, 0.9, 1.0),
        CCPNGLWIDGET_MULTIPLETLINK        : FIREBRICK,

        CCPNMODULELABEL_BACKGROUND        : '#5858C0',
        CCPNMODULELABEL_FOREGROUND        : '#E0E0E0',
        CCPNMODULELABEL_BORDER            : '#5858C0',
        CCPNMODULELABEL_BACKGROUND_ACTIVE : '#7080EE',
        CCPNMODULELABEL_FOREGROUND_ACTIVE : '#FFFFFF',
        CCPNMODULELABEL_BORDER_ACTIVE     : '#7080EE',

        GUICHAINLABEL_TEXT                : TEXT_COLOUR,

        GUICHAINRESIDUE_UNASSIGNED        : 'black',
        GUICHAINRESIDUE_ASSIGNED          : GREEN1,
        GUICHAINRESIDUE_POSSIBLE          : 'orange',
        GUICHAINRESIDUE_WARNING           : WARNING_RED,
        GUICHAINRESIDUE_DRAGENTER         : MARISHINO,
        GUICHAINRESIDUE_DRAGLEAVE         : 'black',  # '#666e98',

        GUINMRATOM_SELECTED               : TEXT_COLOUR,
        GUINMRATOM_NOTSELECTED            : '#FDFDFC',

        GUINMRRESIDUE                     : TEXT_COLOUR,

        GUISTRIP_PIVOT                    : MARISHINO,

        FUSION_FOREGROUND                 : 'white',
        FUSION_BACKGROUND                 : '#73a3f0',

        DRAG_FOREGROUND                   : 'white',
        DRAG_BACKGROUND                   : HIGHLIGHT_COLOUR,
        LABEL_FOREGROUND                  : '#282828',  #TEXT_COLOUR,
        LABEL_WARNINGFOREGROUND           : TEXT_COLOUR_WARNING,
        DIVIDER                           : '#a9a9a9',  # could be could CCPN_WIDGET_BORDER_COLOUR, was TEXT_COLOUR
        SOFTDIVIDER                       : SOFT_DIVIDER_COLOUR,
        LABEL_SELECTEDBACKGROUND          : 'mediumseagreen',
        LABEL_SELECTEDFOREGROUND          : 'black',
        LABEL_HIGHLIGHT                   : 'palegreen',
        LABEL_DISABLED                    : 'whitesmoke',

        SEQUENCEGRAPHMODULE_LINE          : '#808080',
        SEQUENCEGRAPHMODULE_TEXT          : TEXT_COLOUR,

        SEQUENCEMODULE_DRAGMOVE           : MEDIUM_BLUE,
        SEQUENCEMODULE_TEXT               : TEXT_COLOUR,

        GUITABLE_BACKGROUND               : 'white',
        GUITABLE_ALT_BACKGROUND           : LIGHT_GREY,
        GUITABLE_ITEM_FOREGROUND          : TEXT_COLOUR,
        GUITABLE_SELECTED_FOREGROUND      : '#0F0F0F',
        GUITABLE_SELECTED_BACKGROUND      : '#FFFCBA',
        GUITABLE_DROP_BORDER              : GUITABLE_DROP_BORDER_COLOUR,
        GUITABLE_GRIDLINES                : 'lightgrey',
        GUITABLEHEADER_SELECTED_FOREGROUND: '#0F0F0F',
        GUITABLEHEADER_SELECTED_BACKGROUND: 'gainsboro',
        GUITABLEHEADER_GROUP_GRIDLINES    : 'darkgrey',

        GUITABLEHEADER_FOREGROUND         : TEXT_COLOUR,
        GUITABLEHEADER_BACKGROUND         : '#ebebeb',

        BORDERFOCUS                       : BORDERFOCUS_COLOUR,
        BORDERNOFOCUS                     : BORDERNOFOCUS_COLOUR,
        TOOLTIP_BACKGROUND                : TOOLTIP_BACKGROUND_COLOUR,
        TOOLTIP_FOREGROUND                : TOOLTIP_FOREGROUND_COLOUR,

        MARKS_COLOURS                     : MARK_LINE_COLOUR_DICT,
        SPECTRUM_HEXCOLOURS               : spectrumHexDarkColours,
        SPECTRUM_HEXMEDIUMCOLOURS         : spectrumHexMediumColours,
        SPECTRUM_HEXDEFAULTCOLOURS        : spectrumHexDefaultDarkColours,

        HIGHLIGHT                         : HIGHLIGHT_COLOUR,  # this will be updated as the theme changes
        HIGHLIGHT_BORDER                  : HIGHLIGHT_COLOUR,
        HIGHLIGHT_SOLID                   : HIGHLIGHT_COLOUR,
        HIGHLIGHT_FEINT                   : HIGHLIGHT_COLOUR,
        HIGHLIGHT_VIVID                   : HIGHLIGHT_COLOUR,

        PALETTE                           : {  # active, inactive, disabled
            QtGui.QPalette.WindowText     : ['#060606', '#060606', '#060606'],  # 0
            QtGui.QPalette.Button         : ['#ececec', '#ececec', '#ececec'],  # 1
            QtGui.QPalette.Light          : ['#ffffff', '#ffffff', '#ffffff'],  # 2
            QtGui.QPalette.Midlight       : ['#f5f5f5', '#f5f5f5', '#f5f5f5'],  # 3
            QtGui.QPalette.Dark           : ['#bfbfbf', '#bfbfbf', '#bfbfbf'],  # 4
            QtGui.QPalette.Mid            : ['#a9a9a9', '#a9a9a9', '#a9a9a9'],  # 5
            QtGui.QPalette.Text           : ['#080808', '#080808', '#080808'],  # 6
            # QtGui.QPalette.BrightText     : ['#ffffff', '#ffffff', '#ffffff'],  # 7
            QtGui.QPalette.ButtonText     : ['#060606', '#060606', '#060606'],  # 8
            QtGui.QPalette.Base           : ['#ffffff', '#ffffff', '#ececec'],  # 9
            QtGui.QPalette.Window         : ['#ececec', '#ececec', '#ececec'],  # 10
            QtGui.QPalette.Shadow         : ['#22284E', '#181818', '#181818'],  # 11
            QtGui.QPalette.Highlight      : ['#b3d7ff', '#dcdcdc', '#dcdcdc'],  # 12 - default(-ish)
            # QtGui.QPalette.HighlightedText: ['#000000', '#000000', '#000000'],  # 13 - these are both dynamic
            QtGui.QPalette.Link           : ['#0068da', '#0000ff', '#0000ff'],  # 14
            QtGui.QPalette.LinkVisited    : ['#ff00ff', '#ff00ff', '#ff00ff'],  # 15
            QtGui.QPalette.AlternateBase  : ['#f5f5f5', '#f5f5f5', '#f5f5f5'],  # 16
            # QtGui.QPalette.NoRole         : ['#000000', '#000000', '#000000'],  # 17
            # QtGui.QPalette.ToolTipBase    : ['#fafad2', '#fafad2', '#fafad2'],  # 18
            # QtGui.QPalette.ToolTipText    : ['#222438', '#222438', '#222438'],  # 19
            QtGui.QPalette.PlaceholderText: ['#aaaaaa', '#aaaaaa', '#aaaaaa'],  # 20
            }
        },

    # Overridden for dark colour scheme
    Theme.DARK.name   : {
        HEXFOREGROUND                    : '#F0FFFF',
        HEXBACKGROUND                    : '#0F0F0F',

        # these will get replaced when the theme changes
        # CCPNGLWIDGET_HEXFOREGROUND    : '#F0FFFF',
        # CCPNGLWIDGET_HEXBACKGROUND    : '#0F0F0F',
        # CCPNGLWIDGET_HEXHIGHLIGHT     : rgbRatioToHex(0.2, 1.0, 0.3),
        #
        # CCPNGLWIDGET_FOREGROUND       : (0.9, 1.0, 1.0, 1.0),  #'#f0ffff'
        # CCPNGLWIDGET_BACKGROUND       : (0.1, 0.1, 0.1, 1.0),
        # CCPNGLWIDGET_BUTTON_FOREGROUND: (0.75, 0.79, 0.77, 1.0),  #'#080000'
        #
        # CCPNGLWIDGET_PICKCOLOUR       : (0.2, 0.5, 0.9, 1.0),
        # CCPNGLWIDGET_GRID             : (0.9, 1.0, 1.0, 1.0),  #'#f7ffff'
        # CCPNGLWIDGET_HIGHLIGHT        : (0.2, 1.0, 0.3, 1.0),  #'#00ff00'
        # CCPNGLWIDGET_LABELLING        : (1.0, 1.0, 1.0, 1.0),
        # CCPNGLWIDGET_PHASETRACE       : (0.8, 0.8, 0.8, 1.0),
        # CCPNGLWIDGET_ZOOMLINE         : (1.0, 0.9, 0.2, 1.0),
        # CCPNGLWIDGET_MULTIPLETLINK    : LIGHTCORAL,

        CCPNMODULELABEL_BACKGROUND       : '#303580',
        CCPNMODULELABEL_FOREGROUND       : '#E0E0E0',
        CCPNMODULELABEL_BACKGROUND_ACTIVE: '#4045a0',
        CCPNMODULELABEL_FOREGROUND_ACTIVE: '#d0d0d0',

        SPECTRUM_HEXCOLOURS              : spectrumHexLightColours,
        SPECTRUM_HEXMEDIUMCOLOURS        : spectrumHexMediumColours,
        SPECTRUM_HEXDEFAULTCOLOURS       : spectrumHexDefaultLightColours,

        LABEL_FOREGROUND                 : '#e0e0e0',  #'#d8dddd',
        LABEL_SELECTEDBACKGROUND         : 'mediumseagreen',
        LABEL_SELECTEDFOREGROUND         : 'black',
        LABEL_HIGHLIGHT                  : 'palegreen',
        LABEL_DISABLED                   : '#2e2e2e',

        GUITABLE_ITEM_FOREGROUND         : '#d0d8dd',
        GUITABLE_SELECTED_FOREGROUND     : '#efefef',
        GUITABLE_SELECTED_BACKGROUND     : '#5D5900',

        PALETTE                          : {  # active, inactive, disabled
            QtGui.QPalette.WindowText     : ['#cacaca', '#cacaca', '#cacaca'],  # 0 - #f4f4f4
            QtGui.QPalette.Button         : ['#323232', '#323232', '#323232'],  # 1
            QtGui.QPalette.Light          : ['#373737', '#373737', '#373737'],  # 2
            QtGui.QPalette.Midlight       : ['#343434', '#343434', '#343434'],  # 3
            QtGui.QPalette.Dark           : ['#585858', '#585858', '#585858'],  # 4
            QtGui.QPalette.Mid            : ['#242424', '#242424', '#242424'],  # 5
            QtGui.QPalette.Text           : ['#d2d2d2', '#d2d2d2', '#d2d2d2'],  # 6 - #f7f7f7
            # QtGui.QPalette.BrightText     : ['#373737', '#373737', '#373737'],  # 7
            QtGui.QPalette.ButtonText     : ['#cacaca', '#cacaca', '#cacaca'],  # 8
            QtGui.QPalette.Base           : ['#1e1e1e', '#1e1e1e', '#323232'],  # 9
            QtGui.QPalette.Window         : ['#323232', '#323232', '#323232'],  # 10
            QtGui.QPalette.Shadow         : ['#c0c2ca', '#c5c5c5', '#c5c5c5'],  # 11
            QtGui.QPalette.Highlight      : ['#3f638b', '#464646', '#464646'],  # 12 - default(-ish)
            # QtGui.QPalette.HighlightedText: ['#f4f4f4', '#f4f4f4', '#f4f4f4'],  # 13 - these are both dynamic
            QtGui.QPalette.Link           : ['#419cff', '#0000ff', '#0000ff'],  # 14
            QtGui.QPalette.LinkVisited    : ['#e242e2', '#e242e2', '#e242e2'],  # 15
            QtGui.QPalette.AlternateBase  : ['#2c2c2c', '#2c2c2c', '#2c2c2c'],  # 16
            # QtGui.QPalette.NoRole         : ['#000000', '#000000', '#000000'],  # 17
            # QtGui.QPalette.ToolTipBase    : ['#fafad2', '#fafad2', '#fafad2'],  # 18
            # QtGui.QPalette.ToolTipText    : ['#222438', '#222438', '#222438'],  # 19
            QtGui.QPalette.PlaceholderText: ['#787878', '#787878', '#787878'],  # 20
            },
        },

    # Overridden for light colour scheme
    Theme.LIGHT.name  : {

        }
    }

spectrumColourSchemes = {
    # all colours defined here
    # to be dynamically inserted into the above dict as the themes are selected
    Theme.DEFAULT.name: {
        CCPNGLWIDGET_HEXFOREGROUND    : '#070707',
        CCPNGLWIDGET_HEXBACKGROUND    : '#ffffff',
        CCPNGLWIDGET_HEXHIGHLIGHT     : '#3a3aff',
        CCPNGLWIDGET_FOREGROUND       : (0.05, 0.05, 0.05, 1.0),
        CCPNGLWIDGET_BACKGROUND       : (1.0, 1.0, 1.0, 1.0),
        CCPNGLWIDGET_BUTTON_FOREGROUND: (0.2, 0.21, 0.2, 1.0),
        CCPNGLWIDGET_PICKCOLOUR       : (0.2, 0.5, 0.9, 1.0),
        CCPNGLWIDGET_GRID             : (0.5, 0.0, 0.0, 1.0),
        CCPNGLWIDGET_HIGHLIGHT        : (0.23, 0.23, 1.0, 1.0),
        CCPNGLWIDGET_LABELLING        : (0.05, 0.05, 0.05, 1.0),
        CCPNGLWIDGET_PHASETRACE       : (0.2, 0.2, 0.2, 1.0),
        CCPNGLWIDGET_ZOOMLINE         : (0.6, 0.7, 0.2, 1.0),
        CCPNGLWIDGET_MULTIPLETLINK    : FIREBRICK,
        CCPNGLWIDGET_ZOOMAREA         : (0.8, 0.9, 0.2, 0.3),
        CCPNGLWIDGET_PICKAREA         : (0.2, 0.5, 0.9, 0.3),
        CCPNGLWIDGET_SELECTAREA       : (0.8, 0.2, 0.9, 0.3),
        CCPNGLWIDGET_BADAREA          : (0.9, 0.15, 0.1, 0.3),
        CCPNGLWIDGET_MOUSEMOVELINE    : (0.8, 0.2, 0.9, 1.0),
        },

    # Overridden for dark colour scheme
    Theme.DARK.name   : {
        CCPNGLWIDGET_HEXFOREGROUND    : '#f0ffff',
        CCPNGLWIDGET_HEXBACKGROUND    : '#181818',
        CCPNGLWIDGET_HEXHIGHLIGHT     : '#31ff4c',
        CCPNGLWIDGET_FOREGROUND       : (0.9, 1.0, 1.0, 1.0),
        CCPNGLWIDGET_BACKGROUND       : (0.1, 0.1, 0.1, 1.0),
        CCPNGLWIDGET_BUTTON_FOREGROUND: (0.75, 0.79, 0.77, 1.0),
        CCPNGLWIDGET_PICKCOLOUR       : (0.2, 0.5, 0.9, 1.0),
        CCPNGLWIDGET_GRID             : (0.9, 1.0, 1.0, 1.0),
        CCPNGLWIDGET_HIGHLIGHT        : (0.2, 1.0, 0.3, 1.0),
        CCPNGLWIDGET_LABELLING        : (0.95, 0.95, 0.95, 1.0),
        CCPNGLWIDGET_PHASETRACE       : (0.8, 0.8, 0.8, 1.0),
        CCPNGLWIDGET_ZOOMLINE         : (1.0, 0.9, 0.2, 1.0),
        CCPNGLWIDGET_MULTIPLETLINK    : LIGHTCORAL,
        },

    # Overridden for light colour scheme
    Theme.LIGHT.name  : {

        }
    }

# adjust the default marks for the light/dark colour schemes
MARK_LINE_COLOUR_DICT_LIGHT = dict(
        [(k, autoCorrectHexColour(v, '#ffffff', addNewColour=False))
         for k, v in MARK_LINE_COLOUR_DICT.items()])
MARK_LINE_COLOUR_DICT_DARK = dict([(k, autoCorrectHexColour(v, '#0f0f0f', addNewColour=False))
                                   for k, v in MARK_LINE_COLOUR_DICT.items()])

# insert the marks colours into colourScheme
colourSchemes[Theme.LIGHT.name][MARKS_COLOURS] = MARK_LINE_COLOUR_DICT_LIGHT
colourSchemes[Theme.DARK.name][MARKS_COLOURS] = MARK_LINE_COLOUR_DICT_DARK

# NOTE:ED - needs moving
highlight = QtGui.QColor(HIGHLIGHT_COLOUR)
colourSchemes[Theme.DEFAULT.name][HIGHLIGHT_SOLID] = \
    colourSchemes[Theme.DARK.name][HIGHLIGHT_SOLID] = highlight.fromHslF(highlight.hueF(), 0.95, 0.95)
colourSchemes[Theme.DEFAULT.name][HIGHLIGHT_BORDER] = highlight.fromHslF(highlight.hueF(), 0.95,
                                                                         highlight.lightnessF()**3.0)
colourSchemes[Theme.DARK.name][HIGHLIGHT_BORDER] = highlight.fromHslF(highlight.hueF(), 0.95,
                                                                      highlight.lightnessF()**0.333)
colourSchemes[Theme.DEFAULT.name][HIGHLIGHT_VIVID] = \
    colourSchemes[Theme.DARK.name][HIGHLIGHT_FEINT] = highlight.fromHslF(highlight.hueF(), 0.65, 0.25)
colourSchemes[Theme.DEFAULT.name][HIGHLIGHT_FEINT] = \
    colourSchemes[Theme.DARK.name][HIGHLIGHT_VIVID] = highlight.fromHslF(highlight.hueF(), 0.55, 0.80)

DEFAULT_HIGHLIGHT = QtGui.QColor.fromHsvF(0.59, 0.6, 0.9)


# lightPalette = {
#     QtGui.QPalette.WindowText     : ['#060606', '#060606', '#060606'],  # 0
#     QtGui.QPalette.Button         : ['#ececec', '#ececec', '#ececec'],  # 1
#     QtGui.QPalette.Light          : ['#ffffff', '#ffffff', '#ffffff'],  # 2
#     QtGui.QPalette.Midlight       : ['#f5f5f5', '#f5f5f5', '#f5f5f5'],  # 3
#     QtGui.QPalette.Dark           : ['#bfbfbf', '#bfbfbf', '#bfbfbf'],  # 4
#     QtGui.QPalette.Mid            : ['#a9a9a9', '#a9a9a9', '#a9a9a9'],  # 5
#     QtGui.QPalette.Text           : ['#080808', '#080808', '#080808'],  # 6
#     QtGui.QPalette.BrightText     : ['#ffffff', '#ffffff', '#ffffff'],  # 7
#     QtGui.QPalette.ButtonText     : ['#000000', '#000000', '#939393'],  # 8
#     QtGui.QPalette.Base           : ['#ffffff', '#ffffff', '#ececec'],  # 9
#     QtGui.QPalette.Window         : ['#ececec', '#ececec', '#ececec'],  # 10
#     QtGui.QPalette.Shadow         : ['#000000', '#000000', '#000000'],  # 11
#     QtGui.QPalette.Highlight      : ['#b3d7ff', '#dcdcdc', '#dcdcdc'],  # 12
#     QtGui.QPalette.HighlightedText: ['#000000', '#000000', '#000000'],  # 13
#     QtGui.QPalette.Link           : ['#0068da', '#0000ff', '#0000ff'],  # 14
#     QtGui.QPalette.LinkVisited    : ['#ff00ff', '#ff00ff', '#ff00ff'],  # 15
#     QtGui.QPalette.AlternateBase  : ['#f5f5f5', '#f5f5f5', '#f5f5f5'],  # 16
#     QtGui.QPalette.NoRole         : ['#000000', '#000000', '#000000'],  # 17
#     QtGui.QPalette.ToolTipBase    : ['#fafad2', '#fafad2', '#fafad2'],  # 18
#     QtGui.QPalette.ToolTipText    : ['#222438', '#222438', '#222438'],  # 19
#     QtGui.QPalette.PlaceholderText: ['#aaaaaa', '#aaaaaa', '#aaaaaa'],  # 20
#     }
# darkPalette = {
#     QtGui.QPalette.WindowText     : ['#f4f4f4', '#f4f4f4', '#f4f4f4'],  # 0
#     QtGui.QPalette.Button         : ['#323232', '#323232', '#323232'],  # 1
#     QtGui.QPalette.Light          : ['#373737', '#373737', '#373737'],  # 2
#     QtGui.QPalette.Midlight       : ['#343434', '#343434', '#343434'],  # 3
#     QtGui.QPalette.Dark           : ['#787878', '#787878', '#787878'],  # 4
#     QtGui.QPalette.Mid            : ['#242424', '#242424', '#242424'],  # 5
#     QtGui.QPalette.Text           : ['#f7f7f7', '#f7f7f7', '#f7f7f7'],  # 6
#     QtGui.QPalette.BrightText     : ['#373737', '#373737', '#373737'],  # 7
#     QtGui.QPalette.ButtonText     : ['#000000', '#000000', '#1f1f1f'],  # 8
#     QtGui.QPalette.Base           : ['#1e1e1e', '#1e1e1e', '#323232'],  # 9
#     QtGui.QPalette.Window         : ['#323232', '#323232', '#323232'],  # 10
#     QtGui.QPalette.Shadow         : ['#000000', '#000000', '#000000'],  # 11
#     QtGui.QPalette.Highlight      : ['#3f638b', '#464646', '#464646'],  # 12
#     QtGui.QPalette.HighlightedText: ['#ffffff', '#ffffff', '#ffffff'],  # 13
#     QtGui.QPalette.Link           : ['#419cff', '#0000ff', '#0000ff'],  # 14
#     QtGui.QPalette.LinkVisited    : ['#ff00ff', '#ff00ff', '#ff00ff'],  # 15
#     QtGui.QPalette.AlternateBase  : ['#2c2c2c', '#2c2c2c', '#2c2c2c'],  # 16
#     QtGui.QPalette.NoRole         : ['#000000', '#000000', '#000000'],  # 17
#     QtGui.QPalette.ToolTipBase    : ['#fafad2', '#fafad2', '#fafad2'],  # 18
#     QtGui.QPalette.ToolTipText    : ['#222438', '#222438', '#222438'],  # 19
#     QtGui.QPalette.PlaceholderText: ['#787878', '#787878', '#787878'],  # 20
#     }


#=========================================================================================
# Application colour-scheme functions
#=========================================================================================

def getTheme() -> tuple[Theme, str, Theme]:
    """Get the current application colourScheme, spectrumDisplay theme and theme colour.
    Currently, colourScheme is defined as light, dark, default.
    Deafult should return the colourScheme associated with the current OS-theme.
    This is determined at run-time by the lightness of palette.base()
    :return tuple: theme, colourName, themeSD
    """
    if not (application := getApplication()):
        return Theme.LIGHT, 'dodgerblue', Theme.LIGHT
    themeStyle = application._themeStyle
    themeColour = application._themeColour
    themeSDStyle = application._themeSDStyle
    if themeStyle is None:
        themeStyle = Theme.LIGHT
        getLogger().warning(f'getTheme: undefined theme, setting to {themeStyle.dataValue!r}')
    if themeColour is None:
        themeColour = 'dodgerblue'
        getLogger().warning(f'getTheme: undefined colour, setting to {themeColour!r}')
    if themeSDStyle is None:
        themeSDStyle = Theme.LIGHT
        getLogger().warning(f'getTheme: undefined spectrumDisplay theme, setting to {themeSDStyle.dataValue!r}')
    return themeStyle, themeColour, themeSDStyle


def getColourScheme():
    """Get the current colourScheme
    Currently, colourScheme is defined as light, dark, default.
    Deafult should return the colourScheme associated with the current OS-theme.
    This is determined at run-time by the lightness of palette.base()

    :return str: colourScheme
    """
    th, col, thSD = getTheme()
    return th


def getSDTheme() -> Theme:
    """Get the current themeStyle
    Currently, themeStyle is defined as light, dark, auto.
    auto should return the themeStyle associated with the current OS-theme.
    This is determined at run-time by the lightness of palette.base()

    :return Theme: theme
    """
    th, col, thSD = getTheme()
    return thSD


def getThemeColour() -> str:
    """Get the current themeColour
    :return str: colourName
    """
    th, col, thSD = getTheme()
    return col


def setColourScheme(theme, colourName, themeSD, force=False):
    """Set the current colourScheme
    """
    if application := getApplication():
        if not (isinstance(theme, Theme) and isinstance(themeSD, Theme) and isinstance(colourName, str)):
            raise TypeError(f'setColourScheme: bad {theme.name}-{colourName}-{themeSD.name}')
        try:
            if colourName != DEFAULT_COLOR:
                QtGui.QColor(colourName)
        except Exception:
            raise ValueError(f'setColourScheme: colour is not valid {colourName!r}')
        # singleton may not initialise
        colDict = _ColourDict()
        th, col, thSD = getTheme()
        if force or (theme, colourName, themeSD) != (th, col, thSD):
            application._themeStyle = theme
            application._themeColour = colourName
            application._themeSDStyle = themeSD
            getLogger().debug(f'{consoleStyle.fg.darkblue}Changing theme: '
                              f'{theme.name}-{colourName}-{themeSD.name}{consoleStyle.reset}')
            colDict.setColourScheme(theme, colourName, themeSD)
            # return pal
        pal = application._themePalette = colDict.getPalette(colourName)
        return pal
    else:
        getLogger().warning('Application not defined; colourScheme not set')


@singleton
class _ColourDict(dict):
    """
    Singleton Class to store colours;
    """

    def __init__(self, theme=None, colourName=None, themeSD=None):
        super(dict, self).__init__()
        # assure always default values
        th, col, thSD = getTheme()
        theme = theme or th
        colourName = colourName or col
        themeSD = themeSD or thSD
        if theme == Theme.DEFAULT:
            # 'default' not defined for application theme yet
            theme = Theme.LIGHT
        if themeSD == Theme.DEFAULT:
            themeSD = theme  # copy application theme
        self.setColourScheme(theme, colourName, themeSD)

    def setColourScheme(self, theme=None, colourName=None, themeSD=None):
        if isinstance(theme, Theme) and isinstance(themeSD, Theme) and isinstance(colourName, str):
            if theme == Theme.DEFAULT:
                # 'default' not defined for application theme yet
                theme = Theme.LIGHT
            self.update(colourSchemes[Theme.DEFAULT.name])
            self.update(colourSchemes[theme.name])
            # update the spectrumDisplay colours
            self.update(spectrumColourSchemes[Theme.DEFAULT.name])
            if themeSD == Theme.DEFAULT:
                # if 'default' then update from the application theme
                themeSD = theme
            self.update(spectrumColourSchemes[themeSD.name])
        else:
            getLogger().warning(f'setColourScheme: undefined '
                                f'{theme.name}-{colourName}-{themeSD.name}')

    def getPalette(self, colourName):
        groups = [QtGui.QPalette.Active, QtGui.QPalette.Inactive, QtGui.QPalette.Disabled]
        pal = QtGui.QPalette()
        if palSettings := self.get(PALETTE):
            for role, cols in palSettings.items():
                for group, col in zip(groups, cols):
                    pal.setColor(group, role, QtGui.QColor(col))

            base = pal.base().color().lightness()  # use as a guide for light/dark theme
            if colourName == DEFAULT_COLOR:
                highlight = DEFAULT_HIGHLIGHT
            else:
                highlight = QtGui.QColor(colourName)
            if base < 127:
                # a dark theme, modify the colour slightly
                newCol = highlight.darker(120)
            else:
                newCol = highlight.lighter(110)
            r, g, b, _ = newCol.getRgbF()
            # highlight-background perceived luminance
            lumBack = 0.2126 * r + 0.7152 * g + 0.0722 * b
            lumFore = pal.text().color().lightnessF()  # text brightness, easy check for theme
            if (lumBack - 0.6) * (lumFore - 0.5) > 0:
                lumFore = 1 - lumFore  # invert the brightness (to keep correct dark foreground)
            # invert(-ish) to give text colour
            _ht = 2.0 * lumFore - 1.0
            lumFore = (1 + (-1.0 if _ht < 0 else 1.0) * pow(abs(_ht), 0.5)) / 2
            newColHT = highlight.fromHslF(highlight.hslHueF(), 0.05, lumFore)
            for group in [QtGui.QPalette.Active, QtGui.QPalette.Inactive]:
                pal.setColor(group, QtGui.QPalette.Highlight, newCol)
                pal.setColor(group, QtGui.QPalette.HighlightedText, newColHT)
            # grey-out the remaining groups
            greyCol = highlight.fromHsvF(highlight.hueF(), 0.0, 0.5 if base > 127 else 0.45)
            greyColHT = highlight.fromHsvF(highlight.hueF(), 0.0, 0.1 if base < 127 else 0.8)
            for group in [QtGui.QPalette.Disabled]:
                pal.setColor(group, QtGui.QPalette.Highlight, greyCol)
                pal.setColor(group, QtGui.QPalette.HighlightedText, greyColHT)
        return pal


class _ColourDictDark(_ColourDict):
    ...


class _ColourDictLight(_ColourDict):
    ...


#end class


def getColours():
    """
    Return colour for the different schemes
    :return: colourDict
    """
    return _ColourDict()


# def setSDTheme(theme):
#     """Set the current theme for the spectrum-displays."""
#     if application := getApplication():
#         if not isinstance(theme, Theme):
#             raise RuntimeError('Undefined theme')
#         application._themeSDStyle = theme
#         _SDColourDict(theme).setColourScheme(theme)
#     else:
#         getLogger().warning('Application not defined; colourScheme not set')


# @singleton
# class _SDColourDict(dict):
#     """Singleton Class to store spectrumDisplay colours.
#     These don't have to follow the current theme.
#     """
#
#     def __init__(self):
#         super(dict, self).__init__()
#         # assure always default values
#         if (theme := getSDTheme()) is not None:
#             if theme == Theme.DEFAULT:
#                 # replace with the application theme
#                 if (theme := getColourScheme()) is None:
#                     theme = Theme.LIGHT
#             self.setTheme(theme)
#         else:
#             # default to light theme
#             self.setTheme(Theme.LIGHT)
#
#     def setTheme(self, theme):
#         if isinstance(theme, Theme):
#             self.clear()
#             self.update(spectrumColourSchemes[Theme.DEFAULT.name])
#             self.update(spectrumColourSchemes[theme.name])
#             self.theme = theme
#         else:
#             getLogger().warning(f'undefined theme "{theme}", retained "{self.theme}"')
#
#
# def getSDColours() -> _SDColourDict:
#     """Return colour for the spectrum-display.
#     :return: colourDict
#     """
#     return _SDColourDict()


class ZPlaneNavigationModes(DataEnum):
    PERSPECTRUMDISPLAY = 0, 'Per spectrum display', 'spectrumdisplay'
    PERSTRIP = 1, 'Per strip', 'strip'
    INSTRIP = 2, 'In strip', 'instrip'


#=========================================================================================
# console colours
#=========================================================================================

class consoleStyle():
    """Colors class:reset all colors with colors.reset; two
    subclasses fg for foreground
    and bg for background; use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.greenalso, the generic bold, disable,
    underline, reverse, strike through,
    and invisible work with the main class i.e. colors.bold
    """
    reset = '\033[0m'
    bold = '\033[01m'
    disable = '\033[02m'
    underline = '\033[04m'
    reverse = '\033[07m'
    strikethrough = '\033[09m'
    invisible = '\033[08m'


    class fg:
        black = '\033[30m'
        darkred = '\033[31m'
        darkgreen = '\033[32m'
        darkyellow = '\033[33m'
        darkblue = '\033[34m'
        darkmagenta = '\033[35m'
        darkcyan = '\033[36m'
        lightgrey = '\033[37m'
        default = '\033[39m'
        darkgrey = '\033[90m'
        red = '\033[91m'
        green = '\033[92m'
        yellow = '\033[93m'
        blue = '\033[94m'
        magenta = '\033[95m'
        cyan = '\033[96m'
        white = '\033[97m'


    class bg:
        black = '\033[40m'
        darkred = '\033[41m'
        darkgreen = '\033[42m'
        darkyellow = '\033[43m'
        darkblue = '\033[44m'
        darkmagenta = '\033[45m'
        darkcyan = '\033[46m'
        lightgrey = '\033[47m'
        default = '\033[49m'
        darkgrey = '\033[100m'
        red = '\033[101m'
        green = '\033[102m'
        yellow = '\033[103m'
        blue = '\033[104m'
        magenta = '\033[105m'
        cyan = '\033[106m'
        white = '\033[107m'
