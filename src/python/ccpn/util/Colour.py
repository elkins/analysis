"""Module Documentation here

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
__dateModified__ = "$dateModified: 2024-09-03 13:20:31 +0100 (Tue, September 03, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

"""Color specification"""

import numpy as np
from collections import OrderedDict
from PyQt5 import QtGui, QtCore


_AUTO = '<auto>'
_DEFAULT = 'default'
_EMPTY = ''
_HASH = '#'


def _ccpnHex(val):
    """Generate hex value with padded leading zeroes
    """
    val = '{0:#0{1}x}'.format(int(val), 4)
    return f'0x{val[2:].upper()}'


def rgbaToHex(r, g, b, a=255):
    return _HASH + ''.join([_ccpnHex(x)[2:] for x in (r, g, b, a)])


def rgbToHex(r, g, b):
    return _HASH + ''.join([_ccpnHex(x)[2:] for x in (r, g, b)])


def rgbaRatioToHex(r, g, b, a=1.0):
    return _HASH + ''.join([_ccpnHex(x)[2:] for x in (int(255.0 * r),
                                                      int(255.0 * g),
                                                      int(255.0 * b),
                                                      int(255.0 * a))])


def rgbRatioToHex(r, g, b):
    return _HASH + ''.join([_ccpnHex(x)[2:] for x in (int(255.0 * r),
                                                      int(255.0 * g),
                                                      int(255.0 * b))])


def hexToRgb(hx):
    if not hx:
        return

    hx = hx.lstrip(_HASH)
    lv = len(hx)
    return tuple(int(hx[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))


def hexToRgbRatio(hx):
    if not hx:
        return

    hx = hx.lstrip(_HASH)
    lv = len(hx)
    return tuple(float(int(hx[i:i + lv // 3], 16)) / 255 for i in range(0, lv, lv // 3))


def hexToRgba(hx, alpha: int | str = None) -> tuple | None:
    """Convert hex string to rgb(a) tuple.
    hx can be 6|8 hex characters, e.g., #ffffff or #ffffffff.
    If 8 digits, alpha channel is included as last two hex characters;
    otherwise, alpha can be seperately specified, as an int or 2-character string.
    A hash (#) can optionally be placed as prefix to both parameters.

    Returns None if hx not supplied.
    """
    if hx is None:
        return

    hx = hx.lstrip(_HASH)
    if (lv := len(hx)) not in {6, 8}:
        raise ValueError(f'hexToRgba: hx is not the correct length')
    if lv == 8 and alpha is not None:
        raise ValueError(f'hexToRgba: alpha is defined twice.')
    # could use a regex here
    if isinstance(alpha, str):
        alpha = alpha.lstrip(_HASH)
        hx += alpha
        alpha = None
        lv += 2
    cols = [int(hx[i:i + lv // 3], 16) for i in range(0, lv, lv // 3)]
    if alpha is not None:
        cols.append(alpha)
    return tuple(cols)


def hexToRgbaArray(array, alpha: int = None):
    cc = [hexToRgba(hx, alpha) for hx in array]
    return np.array(cc)


# sRGB luminance(Y) values
rY = 0.212655
gY = 0.715158
bY = 0.072187
COLOUR_LIGHT_THRESHOLD = 80
COLOUR_DARK_THRESHOLD = 190  #(256 - COLOUR_LIGHT_THRESHOLD)
COLOUR_THRESHOLD = 40


# Inverse of sRGB "gamma" function. (approx 2.2)
def inv_gam_sRGB(ic):
    c = ic / 255.0
    if (c <= 0.04045):
        return c / 12.92
    else:
        return pow(((c + 0.055) / (1.055)), 1.6)


# sRGB "gamma" function (approx 2.2)
def gam_sRGB(v):
    if (v <= 0.0031308):
        v *= 12.92
    else:
        v = 1.055 * pow(v, 0.625) - 0.055
    return int(v * 255)


# GRAY VALUE ("brightness")
def gray(r, g, b):
    return gam_sRGB(
            rY * inv_gam_sRGB(r) +
            gY * inv_gam_sRGB(g) +
            bY * inv_gam_sRGB(b)
            )


COLORMATRIX256CONST = [16.0, 128.0, 128.0]
COLORMATRIX256 = [[65.738, 129.057, 25.064],
                  [-37.945, -74.494, 112.439],
                  [112.439, -94.154, -18.285]]

COLORMATRIX256INVCONST = [-222.921, 135.576, -276.836]
COLORMATRIX256INV = [[298.082, 0.0, 408.583],
                     [298.082, -100.291, -208.120],
                     [298.082, 516.412, 0.0]]

# Y  = 0.299 R    + 0.587 G  + 0.114 B
# Cb = - 0.1687 R - 0.3313 G + 0.5 B     + 128
# Cr = 0.5 R      - 0.4187 G - 0.0813 B  + 128

COLORMATRIXJPEGCONST = [0, 128, 128]
COLORMATRIXJPEG = [[0.299, 0.587, 0.114],
                   [-0.168736, -0.331264, 0.5],
                   [0.5, -0.418688, -0.081312]]

# R = Y                    + 1.402 (Cr-128)
# G = Y - 0.34414 (Cb-128) - 0.71414 (Cr-128)
# B = Y + 1.772 (Cb-128)

COLORMATRIXJPEGINVCONST = [0, 0, 0]
COLORMATRIXJPEGINVOFFSET = [0, -128, -128]
COLORMATRIXJPEGINV = [[1.0, 0.0, 1.402],
                      [1.0, -0.344136, -0.714136],
                      [1.0, 1.772, 0.0]]


def colourNameNoSpace(name):
    """remove spaces from the colourname
    """
    return name  # currently no effect until sorted

    # return ''.join(name.split())


def colourNameWithSpace(name):
    """insert spaces into the colourname
    """

    # list of all possible words that are in the colourname names
    nounList = ['dark', 'dim', 'medium', 'light', 'pale', 'white', 'rosy', 'indian', 'misty',
                'red', 'orange', 'burly', 'antique', 'navajo', 'blanched', 'papaya', 'floral',
                'lemon', 'olive', 'yellow', 'green', 'lawn', 'sea', 'forest', 'lime', 'spring',
                'slate', 'cadet', 'powder', 'sky', 'steel', 'royal', 'ghost', 'midnight', 'navy', 'rebecca', 'blue',
                'violet', 'deep', 'hot', 'lavender', 'cornflower', 'dodger', 'alice',
                'sandy', 'saddle'
                ]
    subsetNouns = ['goldenrod', 'golden', 'old']

    # insert spaces after found nouns
    colName = name
    for noun in nounList:
        if noun in colName:
            colName = colName.replace(noun, f'{noun} ')

    # check for nouns that also contain shorter nouns
    for noun in subsetNouns:
        if noun in colName:
            colName = colName.replace(noun, f'{noun} ')
            break

    # return the new name without trailing spaces, too many spaces
    return " ".join(colName.split())


def invertRGBLuma(r, g, b):
    """Invert the rgb colour using the ycbcr method by inverting the luma
    rgb input r, g, b in range 0-255
    """
    # rgbprimeIn = [gam_sRGB(r/255.0),gam_sRGB(g/255.0),gam_sRGB(b/255.0)]
    rgbprimeIn = [r, g, b]

    # rgbprimeIn r, g, b in range 0-255
    cie = np.dot(COLORMATRIXJPEG, rgbprimeIn)
    ycbcr = np.add(cie, COLORMATRIXJPEGCONST)
    ycbcr = np.clip(ycbcr, [0, 0, 0], [255, 255, 255])

    # invert the luma - reverse y
    ycbcr[0] = 255 - ycbcr[0]
    ycbcr = np.add(ycbcr, COLORMATRIXJPEGINVOFFSET)

    rgbPrimeOut = np.dot(COLORMATRIXJPEGINV, ycbcr)
    # rgbPrimeOut = np.add(rgbPrimeOut, COLORMATRIXJPEGINVCONST) / 256

    # return tuple([255*inv_gam_sRGB(col) for col in rgbPrimeOut])

    # clip the colours
    rgbPrimeOut = np.clip(rgbPrimeOut, [0, 0, 0], [255, 255, 255])
    return tuple(float(col) for col in rgbPrimeOut)


def invertRGBHue(r, g, b):
    """Invert the rgb colour using the ycbcr method by finding the opposite hue
    rgb input r, g, b in range 0-255
    """
    # rgbprimeIn = [gam_sRGB(r/255.0),gam_sRGB(g/255.0),gam_sRGB(b/255.0)]
    rgbprimeIn = [r, g, b]

    # rgbprimeIn r, g, b in range 0-255
    cie = np.dot(COLORMATRIXJPEG, rgbprimeIn)
    ycbcr = np.add(cie, COLORMATRIXJPEGCONST)
    ycbcr = np.clip(ycbcr, [0, 0, 0], [255, 255, 255])

    # get opposite hue - reverse cb and cr
    ycbcr[1] = 255 - ycbcr[1]
    ycbcr[2] = 255 - ycbcr[2]
    ycbcr = np.add(ycbcr, COLORMATRIXJPEGINVOFFSET)

    rgbPrimeOut = np.dot(COLORMATRIXJPEGINV, ycbcr)
    # rgbPrimeOut = np.add(rgbPrimeOut, COLORMATRIXJPEGINVCONST) / 256

    # return tuple([255*inv_gam_sRGB(col) for col in rgbPrimeOut])

    # clip the colours
    rgbPrimeOut = np.clip(rgbPrimeOut, [0, 0, 0], [255, 255, 255])
    return tuple(float(col) for col in rgbPrimeOut)


def _getRandomColours(numberOfColors):
    import random

    return ["#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)]) for _ in range(numberOfColors)]


def hexRange(hexColor1, hexColor2, count=10, offset=0) -> tuple:
    if hexColor1 is None or hexColor2 is None:
        return None
    r1 = int(f'0x{hexColor1[1:3]}', 16)
    g1 = int(f'0x{hexColor1[3:5]}', 16)
    b1 = int(f'0x{hexColor1[5:7]}', 16)
    r2 = int(f'0x{hexColor2[1:3]}', 16)
    g2 = int(f'0x{hexColor2[3:5]}', 16)
    b2 = int(f'0x{hexColor2[5:7]}', 16)
    colour1 = (r1, g1, b1)
    colour2 = (r2, g2, b2)
    return tuple(f'#{int(res[0]):02x}{int(res[1]):02x}{int(res[2]):02x}'
                 for res in [[(col1 + (col2 - col1) * val) for col1, col2 in zip(colour1, colour2)]
                             for val in np.linspace(0, 1, count)
                             ])[offset:]


def hexRangeAlpha(hexColor1, hexColor2, count=10, offset=0) -> tuple:
    if hexColor1 is None or hexColor2 is None:
        return None
    r1 = int(f'0x{hexColor1[1:3]}', 16)
    g1 = int(f'0x{hexColor1[3:5]}', 16)
    b1 = int(f'0x{hexColor1[5:7]}', 16)
    a1 = int(f'0x{hexColor1[7:9]}', 16)
    r2 = int(f'0x{hexColor2[1:3]}', 16)
    g2 = int(f'0x{hexColor2[3:5]}', 16)
    b2 = int(f'0x{hexColor2[5:7]}', 16)
    a2 = int(f'0x{hexColor2[7:9]}', 16)
    colour1 = (r1, g1, b1, a1)
    colour2 = (r2, g2, b2, a2)
    return tuple(f'#{int(res[0]):02x}{int(res[1]):02x}{int(res[2]):02x}{int(res[3]):02x}'
                 for res in [[(col1 + (col2 - col1) * val) for col1, col2 in zip(colour1, colour2)]
                             for val in np.linspace(0, 1, count)
                             ])[offset:]


ERRORCOLOUR = '#FF0000'

# small set of colours
shortSpectrumColours = OrderedDict([('#cb1400', 'red'),
                                    ('#860700', 'dark red'),
                                    ('#933355', 'burgundy'),
                                    ('#947676', 'bazaar'),

                                    ('#d231cb', 'pink'),
                                    ('#df2950', 'pastel pink'),
                                    ('#ff8eff', 'light pink'),
                                    ('#f9609c', 'mid pink'),

                                    ('#d24c23', 'dark orange'),
                                    ('#fe6c11', 'orange'),
                                    ('#ff932e', 'light pastel orange'),
                                    ('#ecfc00', 'yellow'),
                                    ('#ffff5a', 'light yellow'),

                                    ('#50ae56', 'mid green'),
                                    ('#3fe945', 'light green'),
                                    ('#097a27', 'pastel green'),
                                    ('#064a1a', 'dark green'),
                                    ('#80ff00', 'chartreuse'),

                                    ('#1530ff', 'blue'),
                                    ('#1020aa', 'dark blue'),
                                    ('#4080ff', 'light blue'),
                                    ('#318290', 'pastel blue'),
                                    ('#2d5175', 'mid blue'),
                                    ('#4f9caa', 'light pastel blue'),
                                    ('#957eff', 'heliotrope'),

                                    ('#2f2373', 'dark purple'),
                                    ('#5846d6', 'purple'),
                                    ('#7866f8', 'light purple'),
                                    ('#d8e1cf', 'light seashell'),

                                    ('#3a4e5c', 'dark grey'),
                                    ('#808080', 'mid grey'),
                                    ('#b0b0b0', 'light grey'),

                                    ('#ffffff', 'white'),
                                    ('#000000', 'black')])

# set of colours for spectra on light background
darkDefaultSpectrumColours = OrderedDict([('#008080', 'teal'),
                                          ('#DA70D6', 'orchid'),
                                          ('#800080', 'purple'),
                                          ('#808000', 'olive'),
                                          ('#1E90FF', 'dodgerblue'),
                                          ('#FFA500', 'orange'),
                                          ('#FF0000', 'red'),
                                          ('#4682B4', 'steelblue'),
                                          ('#008000', 'green'),
                                          ('#8A2BE2', 'blueviolet'),
                                          ('#800000', 'maroon'),
                                          ('#00CED1', 'darkturquoise'),
                                          ('#000080', 'navy'),
                                          ('#FF4500', 'orangered'),
                                          ('#FF1493', 'deeppink'),
                                          ('#32CD32', 'limegreen'),
                                          ])

# set of colours for spectra on dark background
lightDefaultSpectrumColours = OrderedDict([('#6B8E23', 'olivedrab'),
                                           ('#DA70D6', 'orchid'),
                                           ('#8A2BE2', 'blueviolet'),
                                           ('#808000', 'olive'),
                                           ('#1E90FF', 'dodgerblue'),
                                           ('#FFA500', 'orange'),
                                           ('#FF0000', 'red'),
                                           ('#4682B4', 'steelblue'),
                                           ('#7FFF00', 'chartreuse'),
                                           ('#9932CC', 'darkorchid'),
                                           ('#A0522D', 'sienna'),
                                           ('#00CED1', 'darkturquoise'),
                                           ('#00FFFF', 'cyan'),
                                           ('#FFFF00', 'yellow'),
                                           ('#FF1493', 'deeppink'),
                                           ('#32CD32', 'limegreen'),
                                           ])


def _stepSort(rgbCol: QtGui.QColor, repetitions=6):
    """Group and sort colours, so they are just a little smoother in the pulldown.
    """
    r, g, b, _ = rgbCol.getRgbF()
    h, s, v, _ = rgbCol.getHsvF()
    lum = pow(.241 * r + .691 * g + .068 * b, 0.5)
    h2 = int(h * repetitions)
    v2 = int(v * repetitions)
    if h2 % 2 == 1:
        # reverse every other section
        v2 = repetitions - v2
        lum = repetitions - lum
    return (h2, lum, v2)  # not sure v2 is required


# grab and order the grey-scale; transparent must be removed, overwrites black
_greys = OrderedDict(sorted([(QtGui.QColor(col).name(), col) for col in QtGui.QColor.colorNames()
                             if (qtc := QtGui.QColor(col)) and
                             ((-3 < qtc.red() - qtc.green() < 3) and
                              (-3 < qtc.red() - qtc.blue() < 3) and
                              (-3 < qtc.blue() - qtc.green() < 3)) and
                             col != 'transparent'],
                            key=lambda cc: QtGui.QColor(cc[0]).value()
                            ))
# grab all the other colours
_colours = OrderedDict(sorted([(QtGui.QColor(col).name(), col) for col in QtGui.QColor.colorNames()
                               if (qtc := QtGui.QColor(col)) and
                               not ((-3 < qtc.red() - qtc.green() < 3) and
                                    (-3 < qtc.red() - qtc.blue() < 3) and
                                    (-3 < qtc.blue() - qtc.green() < 3)) and
                               col != 'transparent'],
                              key=lambda cc: _stepSort(QtGui.QColor(cc[0]))
                              ))
# grab the brighter colours
_brightColours = OrderedDict(sorted([(QtGui.QColor(col).name(), col) for col in QtGui.QColor.colorNames()
                                     if (qtc := QtGui.QColor(col)) and
                                     not ((-3 < qtc.red() - qtc.green() < 3) and
                                          (-3 < qtc.red() - qtc.blue() < 3) and
                                          (-3 < qtc.blue() - qtc.green() < 3)) and
                                     col != 'transparent' and
                                     qtc.hsvSaturation() > COLOUR_LIGHT_THRESHOLD],
                                    key=lambda cc: _stepSort(QtGui.QColor(cc[0]))
                                    ))
# add CCPN selective colours
_CCPNColours = OrderedDict([('#6A3B71', 'CCPNpurple'),
                            ('#2F705C', 'CCPNgreen'),
                            ('#BD9D46', 'CCPNyellow'),
                            ('#0C4F83', 'CCPNblue'),
                            ])

# all colours defined in the Qt colourspace + new CCPN colours
allColours = _greys | _colours | _CCPNColours
# set of colours that have higher saturation + new CCPN colours
brightColours = _greys | _brightColours | _CCPNColours

# default color-ranges
colorSchemeTable = OrderedDict([
    ('redshade', hexRange('#FFC0C0', '#FF0000', 6) + hexRange('#FF0000', '#660000', 6, 1)),
    ('orangeshade', hexRange('#FFC0C0', '#FF8000', 6) + hexRange('#FF8000', '#663300', 6, 1)),
    ('yellowshade', hexRange('#FFFF99', '#FFFF00', 6) + hexRange('#FFFF00', '#555500', 6, 1)),
    ('greenshade', hexRange('#99FF99', '#00C000', 6) + hexRange('#00C000', '#006600', 6, 1)),
    ('blueshade', hexRange('#C0C0FF', '#0000FF', 6) + hexRange('#0000FF', '#000066', 6, 1)),
    ('cyanshade', hexRange('#00FFFF', '#004C4C')),
    ('purpleshade', hexRange('#E6CCFF', '#330059')),
    ('greyshade', hexRange('#CCCCCC', '#333333')),

    ('redshade2', hexRange('#660000', '#FF0000', 6) + hexRange('#FF0000', '#FFC0C0', 6, 1)),
    ('orangeshade2', hexRange('#663300', '#FF8000', 6) + hexRange('#FF8000', '#FFC0C0', 6, 1)),
    ('yellowshade2', hexRange('#555500', '#FFFF00', 6) + hexRange('#FFFF00', '#FFFF99', 6, 1)),
    ('greenshade2', hexRange('#006600', '#00C000', 6) + hexRange('#00C000', '#99FF99', 6, 1)),
    ('blueshade2', hexRange('#000066', '#0000FF', 6) + hexRange('#0000FF', '#C0C0FF', 6, 1)),
    ('cyanshade2', hexRange('#004C4C', '#00FFFF')),
    ('purpleshade2', hexRange('#330059', '#E6CCFF')),
    ('greyshade2', hexRange('#333333', '#CCCCCC')),

    ('rainbow', (hexRange('#ff00ff', '#ff0000', 4) +
                 hexRange('#ff0000', '#ffff00', 4, 1) +
                 hexRange('#ffff00', '#00ff00', 4, 1) +
                 hexRange('#00ff00', '#00ffff', 4, 1) +
                 hexRange('#00ffff', '#0000ff', 4, 1)
                 )),
    ('rainbow2', (hexRange('#0000ff', '#00ffff', 4) +
                  hexRange('#00ffff', '#00ff00', 4, 1) +
                  hexRange('#00ff00', '#ffff00', 4, 1) +
                  hexRange('#ffff00', '#ff0000', 4, 1) +
                  hexRange('#ff0000', '#ff00ff', 4, 1)
                  )),

    ('wimbledon', hexRange('#008000', '#FFFF00')),
    ('wimbledon2', hexRange('#FFFF00', '#008000')),

    ('toothpaste', hexRange('#C0C0FF', '#0000FF', 6) + hexRange('#0000FF', '#00FFFF', 6, 1)),
    ('toothpaste2', hexRange('#00FFFF', '#0000FF', 6) + hexRange('#0000FF', '#C0C0FF', 6, 1)),

    ('cmy', (hexRange('#00FFFF', '#FF00FF', 6) + hexRange('#FF00FF', '#FFFF00', 6, 1))),
    ('cmy2', (hexRange('#FFFF00', '#FF00FF', 6) + hexRange('#FF00FF', '#00FFFF', 6, 1))),

    ('steel', hexRange('#C0C0C0', '#000080')),
    ('steel2', hexRange('#000080', '#C0C0C0')),

    ('rgb', (hexRange('#e00000', '#00a000', 6) + hexRange('#00a000', '#0000ff', 6, 1))),
    ('rgb2', (hexRange('#0000ff', '#00a000', 6) + hexRange('#00a000', '#e00000', 6, 1))),

    ('tropicana', hexRange('#FFFF00', '#FF0080')),
    ('tropicana2', hexRange('#FF0080', '#FFFF00')),

    ('sunset', (hexRange('#FFC0C0', '#FF0000', 6) + hexRange('#FF0000', '#FFFF00', 6, 1))),
    ('sunset2', (hexRange('#FFFF00', '#FF0000', 6) + hexRange('#FF0000', '#FFC0C0', 6, 1))),

    ('magma', (hexRange('#000000', '#FF0000', 6) + hexRange('#FF0000', '#FFFF00', 6, 1))),
    ('magma2', (hexRange('#FFFF00', '#FF0000', 6) + hexRange('#FF0000', '#000000', 6, 1))),

    ('holly', (hexRange('#80FF80', '#008000', 6) + hexRange('#FF0000', '#800000', 4))),
    ('holly2', (hexRange('#800000', '#FF0000', 4) + hexRange('#008000', '#80FF80', 6))),

    ('glacier', (hexRange('#000000', '#0000FF', 6) + hexRange('#0000FF', '#C0C0FF', 6, 1))),
    ('glacier2', (hexRange('#C0C0FF', '#0000FF', 6) + hexRange('#0000FF', '#000000', 6, 1))),

    ('monarchy', (hexRange('#C0C0FF', '#0000FF', 3) +
                  hexRange('#0000FF', '#FF0000', 6, 1) +
                  hexRange('#FF0000', '#800000', 3, 1)
                  )),
    ('monarchy2', (hexRange('#800000', '#FF0000', 3) +
                   hexRange('#FF0000', '#0000FF', 6, 1) +
                   hexRange('#0000FF', '#C0C0FF', 3, 1)
                   )),
    ('contrast', ('#FF0000', '#008000', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF')),
    ('contrast2', ('#00FFFF', '#FF00FF', '#FFFF00', '#0000FF', '#008000', '#FF0000')),
    ('lightspectrum', (
        '#6B8E23', '#DA70D6', '#8A2BE2', '#808000', '#1E90FF', '#FFA500', '#FF0000',
        '#4682B4', '#7FFF00', '#9932CC',
        '#A0522D', '#00CED1', '#00FFFF', '#FFFF00', '#FF1493', '#32CD32')),
    ('lightspectrum2', (
        '#32CD32', '#FF1493', '#FFFF00', '#00FFFF', '#00CED1', '#A0522D', '#9932CC',
        '#7FFF00', '#4682B4', '#FF0000', '#FFA500',
        '#1E90FF', '#808000', '#8A2BE2', '#DA70D6', '#6B8E23')),

    ('red-orange', hexRange('#ff2010', '#ffc030')),
    ('orange-yellow', hexRange('#ffc030', '#eeff10')),
    ('yellow-green', hexRange('#eeff10', '#10cc20')),
    ('green-blue', hexRange('#10cc20', '#2010ff')),
    ('blue-cyan', hexRange('#2010ff', '#20eeff')),
    ('blue-purple', hexRange('#2010ff', '#ee20ff')),
    ('orange-red', hexRange('#ffc030', '#ff2010')),
    ('yellow-orange', hexRange('#eeff10', '#ffc030')),
    ('green-yellow', hexRange('#10cc20', '#eeff10')),
    ('blue-green', hexRange('#2010ff', '#10cc20')),
    ('cyan-blue', hexRange('#20eeff', '#2010ff')),
    ('purple-blue', hexRange('#ee20ff', '#2010ff')),

    ('black-white', hexRange('#000000', '#ffffff')),
    ('white-black', hexRange('#ffffff', '#000000')),
    ('black-gray', hexRange('#000000', '#7f7f7f')),
    ('gray-black', hexRange('#7f7f7f', '#000000')),
    ])

allColoursWithSpaces = OrderedDict([(k, colourNameWithSpace(v)) for k, v in allColours.items()])
colourNameToHexDict = {v: k for k, v in allColours.items()}
# set the spectrum colours to all, override minimum set above
spectrumColours = brightColours

# split the colour palettes into light and dark for different colour schemes
spectrumDarkColours = OrderedDict()
spectrumLightColours = OrderedDict()
spectrumMediumColours = OrderedDict()

for k, v in spectrumColours.items():
    h = hexToRgb(k)

    # colour can belong to both sets
    if gray(*h) > COLOUR_LIGHT_THRESHOLD:
        spectrumLightColours[k] = v
    if gray(*h) < COLOUR_DARK_THRESHOLD:
        spectrumDarkColours[k] = v
    if COLOUR_LIGHT_THRESHOLD < gray(*h) < COLOUR_DARK_THRESHOLD:
        spectrumMediumColours[k] = v

allDarkColours = OrderedDict()
allLightColours = OrderedDict()
allMediumColours = OrderedDict()

for k, v in allColours.items():
    h = hexToRgb(k)

    # colour can belong to both sets
    if gray(*h) > COLOUR_LIGHT_THRESHOLD:
        allLightColours[k] = v
    if gray(*h) < COLOUR_DARK_THRESHOLD:
        allDarkColours[k] = v
    if COLOUR_LIGHT_THRESHOLD < gray(*h) < COLOUR_DARK_THRESHOLD:
        allMediumColours[k] = v

spectrumHexLightColours = tuple(ky for ky in spectrumLightColours.keys() if ky != _HASH)
spectrumHexDarkColours = tuple(ky for ky in spectrumDarkColours.keys() if ky != _HASH)
spectrumHexMediumColours = tuple(ky for ky in spectrumMediumColours.keys() if ky != _HASH)

spectrumHexDefaultLightColours = tuple(ky for ky in lightDefaultSpectrumColours.keys() if ky != _HASH)
spectrumHexDefaultDarkColours = tuple(ky for ky in darkDefaultSpectrumColours.keys() if ky != _HASH)

# override this with spectrumLight/DarkColours when colourScheme is changed
spectrumHexColours = tuple(ky for ky in spectrumColours.keys() if ky != _HASH)

# Note that Colour strings are not re-used
paletteNames = [
    'windowText',  # 0
    'button',  # 1
    'light',  # 2
    'midlight',  # 3
    'dark',  # 4
    'mid',  # 5
    'text',  # 6
    'brightText',  # 7
    'buttonText',  # 8
    'base',  # 9
    'window',  # 10
    'shadow',  # 11
    'highlight',  # 12
    'highlightedText',  # 13
    'link',  # 14
    'linkVisited',  # 15
    'alternateBase',  # 16
    'noRole',  # 17
    'toolTipBase',  # 18
    'toolTipText',  # 19
    'placeholderText',  # 20
    ]


# for colnum, colname in enumerate(colNames):
#     print(f"  QtGui.QPalette.{colname[0].upper()+colname[1:]:20}:  ["
#           f"{pal.color(QtGui.QPalette.Active, QtGui.QPalette.ColorRole(colnum)).name()!r},   "
#           f"{pal.color(QtGui.QPalette.Inactive, QtGui.QPalette.ColorRole(colnum)).name()!r},   "
#           f"{pal.color(QtGui.QPalette.Disabled, QtGui.QPalette.ColorRole(colnum)).name()!r}"
#           f"],  # {colnum}")
#


class Colour(str):
    """ A class to make colour manipulation easier and more transparent.
        Assumes that r, g, b values are 8-bit so between 0 and 255 and have optional a.

        c = Colour('magenta')
        c = Colour('#FF00FF')
        c = Colour((255, 0, 255))
    """

    def __init__(self, value):
        """ value can be name or #rrggbb or #rrggbbaa or (r, g, b) or (r, g, b, a) tuple/list """
        # print(value, 'color init')
        if not value:
            raise ValueError('not allowed blank colour')

        if isinstance(value, str):
            value = value.lower()
            name = value
            if value[0] != _HASH:
                value = colourNameToHexDict[name]

            assert len(value) in {7, 9}, 'len(value) = %d, should be 7 or 9' % len(value)

            r = int(value[1:3], 16)
            g = int(value[3:5], 16)
            b = int(value[5:7], 16)
            a = int(value[7:9], 16) if len(value) == 9 else 255
        else:
            assert isinstance(value, (list, tuple)), f'value must be list or tuple if it is not a string, was {value}'
            assert len(value) in {3, 4}, 'value=%s, len(value) = %d, should be 3 or 4' % (value, len(value))

            r, g, b = value[:3]
            if len(value) == 4:
                a = value[3]
                name = rgbaToHex(r, g, b, a)
            else:
                a = 255
                name = rgbToHex(r, g, b)

        ###str.__init__(self)
        self.r = r
        self.g = g
        self.b = b
        self.a = a
        self.name = name

    def rgba(self):
        """Returns 4-tuple of (r, g, b, a) where each one is in range 0 to 255"""

        return (self.r, self.g, self.b, self.a)

    def scaledRgba(self):
        """Returns 4-tuple of (r, g, b, a) where each one is in range 0.0 to 1.0"""

        return (self.r / 255.0, self.g / 255.0, self.b / 255.0, self.a / 255.0)

    def hex(self):

        return _HASH + ''.join([_ccpnHex(x)[2:] for x in (self.r, self.g, self.b)])

    def __repr__(self):

        return self.name

    def __str__(self):

        return self.__repr__()


def rgba(value):
    return Colour(value).rgba()


def scaledRgba(value):
    # print(value, 'scaledRgba')
    return Colour(value).scaledRgba()


def addNewColour(newColour):
    newIndex = str(len(spectrumColours.items()) + 1)
    spectrumColours[newColour.name()] = f'Colour {newIndex}'


def isSpectrumColour(colourString):
    """Return true if the colourString is in the list
    """
    return colourString in list(spectrumColours.keys())


def addNewColourString(colourString):
    """Add a new Hex colour to the colourlist
    New colour has the name 'Colour <n>' where n is the next free number
    """
    # '#' is reserved for auto colour so shouldn't ever be added
    if colourString != _HASH and colourString not in spectrumColours:
        newIndex = str(len(spectrumColours.items()) + 1)
        spectrumColours[colourString] = f'Colour {newIndex}'


def autoCorrectHexColour(colour, referenceHexColour='#ffffff', addNewColour=True):
    """Autocorrect colours if too close to the reference value
    """
    if colour == _HASH:
        return colour

    g = gray(*hexToRgb(colour))

    rgb = hexToRgb(referenceHexColour)
    gRef = gray(*rgb)

    if abs(g - gRef) < COLOUR_THRESHOLD:
        newCol = invertRGBLuma(*hexToRgb(colour))
        hx = rgbToHex(*newCol)

        if addNewColour:
            addNewColourString(hx)
        return hx

    return colour


def name2Hex(name):
    return colourNameToHexDict.get(name, None)


def splitDataByColours(data, colours):
    gradientColours = []
    count = len(colours)
    groups = np.array_split(np.sort(data), count)
    for h in data:
        for group, c in zip(groups, colours):
            if h in group:
                gradientColours.append(c)
    return gradientColours


def getGradientBrushByArray(gradientName, yArray):
    """ USed to create a gradient in BarGraph"""
    if gradientName not in colorSchemeTable:
        raise ValueError(f'Gradient not available. Use one of {colorSchemeTable.keys()}')
    colourList = colorSchemeTable[gradientName]
    array = np.arange(0, len(colourList))
    z = (array - np.min(array)) / (np.max(array) - np.min(array))
    grad = QtGui.QLinearGradient(0, 0, 0, np.std(yArray))
    for colour, colourAt in zip(colourList, z):
        grad.setColorAt(colourAt, QtGui.QColor(colour))
    return QtGui.QBrush(grad)


# def _setNewColour(colList, newCol:str):
#
#   # check if the colour is in the spectrumColours list
#
#   # check if colour is in you colList
#
#
#   pix = QtGui.QPixmap(QtCore.QSize(20, 20))
#   pix.fill(QtGui.QColor(newCol))
#
#   # add the new colour to the spectrumColours dict
#   newIndex = str(len(spectrumColours.items()) + 1)
#   # spectrumColours[newColour.name()] = 'Colour %s' % newIndex
#   addNewColourString(newCol)
#   if newCol not in colList.texts:
#     colList.addItem(icon=QtGui.QIcon(pix), text='Colour %s' % newIndex)
#     colList.setCurrentIndex(int(newIndex) - 1)

def selectPullDownColour(pulldown, colourString, allowAuto=False):
    # try:
    #     pulldown.setCurrentText(spectrumColours[colourString])
    # except:
    #     if allowAuto and _HASH in pulldown.texts:
    #         pulldown.setCurrentText(_HASH)

    if colourString in spectrumColours:
        pulldown.setCurrentText(spectrumColours[colourString])
    elif colourString in colorSchemeTable:
        pulldown.setCurrentText(colourString)
    elif allowAuto and _AUTO in pulldown.texts:
        pulldown.setCurrentText(_AUTO)


# ICON_SIZE = 20


def fillColourPulldown(pulldown, allowAuto=False, allowNone=False, includeGradients=True):
    # fill the pulldown with the list of colours
    # this has no signals blocked otherwise it doesn't paint, and should be signalBlocked elsewhere
    currText = pulldown.currentText()

    ICON_SIZE = max(pulldown.font().pointSize(), 18)  # seems to be constrained to the pulldown height

    pulldown.clear()
    if allowAuto:
        pulldown.addItem(text=_AUTO)
    if allowNone:
        pulldown.addItem(text=_EMPTY)

    for item in spectrumColours.items():
        # if item[1] not in pulldown.texts:

        colName = item[1]  # colourNameWithSpace(item[1])

        if item[0] != _HASH:
            pix = QtGui.QPixmap(QtCore.QSize(ICON_SIZE, ICON_SIZE))
            pix.fill(QtGui.QColor(item[0]))
            pulldown.addItem(icon=QtGui.QIcon(pix), text=colName)
        elif allowAuto:
            pulldown.addItem(text=colName)

    if includeGradients:
        pix = QtGui.QPixmap(QtCore.QSize(ICON_SIZE, ICON_SIZE))
        for colName, colourList in colorSchemeTable.items():
            stepY = len(colourList) - 1
            painter = QtGui.QPainter(pix)
            grad = QtGui.QLinearGradient(0, 0, ICON_SIZE, 0)
            for ii, col in enumerate(colourList):
                grad.setColorAt(ii / stepY, QtGui.QColor(col))
            painter.fillRect(pix.rect(), grad)
            painter.end()
            pulldown.addItem(icon=QtGui.QIcon(pix), text=colName)

    pulldown.setCurrentText(currText)


def closest_pyqt_color_name(hex_color):
    """Find the closest PyQt color name to the given hex color.
    """
    rgb_color = np.array(hexToRgb(hex_color))

    min_distance = float('inf')
    closest_name = None

    for name in QtGui.QColor.colorNames():
        # Get the RGB values of the named color
        test_color = QtGui.QColor(name)
        test_rgb = np.array([test_color.red(), test_color.green(), test_color.blue()])
        # Calculate the Euclidean distance
        distance = np.sqrt(np.sum((rgb_color - test_rgb)**2))
        if distance < min_distance:
            min_distance = distance
            closest_name = name

    return closest_name


def coloursFromHue(count=12):
    return ['crimson',
            'tomato',
            'darkorange',
            'gold',
            'yellowgreen',
            'limegreen',
            'mediumseagreen',
            'mediumturquoise',
            'deepskyblue',
            'dodgerblue',
            'royalblue',
            'mediumorchid',
            'fuchsia',
            'deeppink',
            ]

    # names = []
    # for cc in range(count):
    #     # 0.8, 0.45 gives slightly nice colours
    #     col = QtGui.QColor.fromHslF(cc/count, 1.0, 0.45)  # only the hue is actually used for the minute
    #     if not (name := closest_pyqt_color_name(col.name())):
    #         raise ValueError('Colour not found')
    #     names.append(name)
    # return names


def fillPulldownFromNames(pulldown, colourList, allowAuto=False, allowNone=False, default=None):
    # fill the pulldown with the list of colours
    # this has no signals blocked otherwise it doesn't paint, and should be signalBlocked elsewhere
    currText = pulldown.currentText()

    ICON_SIZE = max(pulldown.font().pointSize(), 18)  # seems to be constrained to the pulldown height

    pulldown.clear()
    if allowAuto:
        pulldown.addItem(text=_AUTO)
    if allowNone:
        pulldown.addItem(text=_EMPTY)

    for name in colourList:
        if name == _DEFAULT:
            if default is not None:
                pix = QtGui.QPixmap(QtCore.QSize(ICON_SIZE, ICON_SIZE))
                pix.fill(QtGui.QColor(default))
                pulldown.addItem(icon=QtGui.QIcon(pix), text=name)
            else:
                pulldown.addItem(text=name)
        elif name != _HASH:
            pix = QtGui.QPixmap(QtCore.QSize(ICON_SIZE, ICON_SIZE))
            pix.fill(QtGui.QColor(name))
            pulldown.addItem(icon=QtGui.QIcon(pix), text=name)
        elif allowAuto:
            pulldown.addItem(text=name)

    pulldown.setCurrentText(currText)


def _setColourPulldown(pulldown, attrib, allowAuto=False, includeGradients=True, allowNone=False):
    """Populate colour pulldown and set to the current colour
    """
    spectrumColourKeys = list(spectrumColours.keys())
    fillColourPulldown(pulldown, allowAuto=allowAuto, includeGradients=includeGradients, allowNone=allowNone)
    c = attrib.upper() if attrib and attrib.startswith(_HASH) else attrib
    if c in spectrumColourKeys:
        col = spectrumColours[c]
        pulldown.setCurrentText(col)
    elif attrib in colorSchemeTable:
        pulldown.setCurrentText(attrib)
    elif c is None:
        if allowNone:
            pulldown.setCurrentText('')
    else:
        addNewColourString(c)
        fillColourPulldown(pulldown, allowAuto=allowAuto, includeGradients=includeGradients, allowNone=allowNone)
        if c != _HASH or allowAuto is True:
            col = spectrumColours[c]
            pulldown.setCurrentText(col)


def getSpectrumColour(colourName, defaultReturn=None):
    """
    return the hex colour of the named colour
    """
    try:
        colName = colourName  # colourNameNoSpace(colourName)

        if colName in spectrumColours.values():
            col = list(spectrumColours.keys())[list(spectrumColours.values()).index(colName)]
            return col.upper() if col.startswith(_HASH) else col
        elif colName in colorSchemeTable:
            return colName
        else:
            return defaultReturn

    except Exception:
        # colour not found in the list
        return defaultReturn


def getAutoColourRgbRatio(inColour=None, sourceObject=None, colourAttribute=None, defaultColour=None):
    try:
        listColour = inColour
        if listColour == _HASH:
            listColour = getattr(sourceObject, colourAttribute, defaultColour)
            if listColour in colorSchemeTable:
                # get the first item from the colour gradient
                listColour = colorSchemeTable[listColour][0]

        return (hexToRgbRatio(listColour) or defaultColour)[:3]

    except Exception:
        # return red for any error
        return [1.0, 0.2, 0.1]


def findNearestHex(hexCol, colourHexList):
    weights = (0.3, 0.59, 0.11)  # assuming rgb
    rgbIn = hexToRgb(hexCol)

    lastCol = None
    lastDiff = 0.0
    for col in colourHexList:

        rgbTest = hexToRgb(col)

        # use euclidean to find closest colour
        num = 0.0
        for a, b, w in zip(rgbIn, rgbTest, weights):
            num += pow((a - b) * w, 4)

        if lastCol is None or num < lastDiff:
            lastDiff = num
            lastCol = (col, num)

    return lastCol[0]


def interpolateColourRgba(colour1, colour2, value, alpha=1.0):
    result = [(col1 + (col2 - col1) * value) for col1, col2 in zip(colour1, colour2)]
    while len(result) < 4:
        result.append(alpha)
    return tuple(result[:4])


def interpolateColourHex(hexColor1, hexColor2, value, alpha=1.0):
    if hexColor1 is None or hexColor2 is None:
        return None
    value = np.clip(value, 0.0, 1.0)

    r1 = int(f'0x{hexColor1[1:3]}', 16)
    g1 = int(f'0x{hexColor1[3:5]}', 16)
    b1 = int(f'0x{hexColor1[5:7]}', 16)
    r2 = int(f'0x{hexColor2[1:3]}', 16)
    g2 = int(f'0x{hexColor2[3:5]}', 16)
    b2 = int(f'0x{hexColor2[5:7]}', 16)
    colour1 = (r1, g1, b1)
    colour2 = (r2, g2, b2)

    result = [(col1 + (col2 - col1) * value) for col1, col2 in zip(colour1, colour2)]
    return '#%02x%02x%02x' % (int(result[0]), int(result[1]), int(result[2]))


# ('darkredshade', ('#7f6060', '#7f4d4d', '#7f3939', '#7f2626', '#7f1313', '#7f0000', '#6c0000', '#590000', '#460000', '#330000')),
# ('darkorangeshade', ('#7f7060', '#7f6448', '#7f5830', '#7f4c18', '#7f4000', '#703800', '#613000', '#512900', '#422100', '#331900')),
# ('darkyellowshade', ('#7f7f4c', '#7f7f26', '#7f7f00', '#737300', '#676700', '#5b5b00', '#4f4f00', '#434300', '#363600', '#2a2a00')),
# ('darkgreenshade', ('#4c7f4c', '#397839', '#267026', '#136813', '#006000', '#005700', '#004e00', '#004500', '#003c00', '#003300')),
# ('darkblueshade', ('#60607f', '#4d4d7f', '#39397f', '#26267f', '#13137f', '#00007f', '#00006c', '#000059', '#000046', '#000033')),
# ('darkcyanshade', ('#007f7f', '#007676', '#006c6c', '#006262', '#005858', '#004e4e', '#004444', '#003a3a', '#003030', '#002626')),
# ('darkpurpleshade', ('#73667f', '#694c78', '#603370', '#561968', '#4c0060', '#420056', '#38004b', '#2e0041', '#230037', '#19002c')),
# ('darkgreyshade', ('#666666', '#5d5d5d', '#555555', '#4c4c4c', '#444444', '#3b3b3b', '#333333', '#2a2a2a', '#222222', '#191919')),
# ('darkredshade2', ('#330000', '#460000', '#590000', '#6c0000', '#7f0000', '#7f1313', '#7f2626', '#7f3939', '#7f4d4d', '#7f6060')),
# ('darkorangeshade2', ('#331900', '#422100', '#512900', '#613000', '#703800', '#7f4000', '#7f4c18', '#7f5830', '#7f6448', '#7f7060')),
# ('darkyellowshade2', ('#2a2a00', '#363600', '#434300', '#4f4f00', '#5b5b00', '#676700', '#737300', '#7f7f00', '#7f7f26', '#7f7f4c')),
# ('darkgreenshade2', ('#003300', '#003c00', '#004500', '#004e00', '#005700', '#006000', '#136813', '#267026', '#397839', '#4c7f4c')),
# ('darkblueshade2', ('#000033', '#000046', '#000059', '#00006c', '#00007f', '#13137f', '#26267f', '#39397f', '#4d4d7f', '#60607f')),
# ('darkcyanshade2', ('#002626', '#003030', '#003a3a', '#004444', '#004e4e', '#005858', '#006262', '#006c6c', '#007676', '#007f7f')),
# ('darkpurpleshade2', ('#19002c', '#230037', '#2e0041', '#38004b', '#420056', '#4c0060', '#561968', '#603370', '#694c78', '#73667f')),
# ('darkgreyshade2', ('#191919', '#222222', '#2a2a2a', '#333333', '#3b3b3b', '#444444', '#4c4c4c', '#555555', '#5d5d5d', '#666666')),
#
# ('darkrainbow',
#  ('#7f007f', '#7f0040', '#7f0000', '#7f4000', '#7f7f00', '#407f00', '#007f00', '#007f40', '#007f7f', '#00407f', '#00007f', '#40007f')),
# ('darkrainbow2',
#  ('#40007f', '#00007f', '#00407f', '#007f7f', '#007f40', '#007f00', '#407f00', '#7f7f00', '#7f4000', '#7f0000', '#7f0040', '#7f007f')),
# ('darkwimbledon', ('#004000', '#0e4700', '#1c4e00', '#2a5500', '#385c00', '#476300', '#556a00', '#637100', '#717800', '#7f7f00')),
# ('darkwimbledon2', ('#7f7f00', '#717800', '#637100', '#556a00', '#476300', '#385c00', '#2a5500', '#1c4e00', '#0e4700', '#004000')),
# ('darktoothpaste', ('#60607f', '#4d4d7f', '#39397f', '#26267f', '#13137f', '#00007f', '#00207f', '#00407f', '#00607f', '#007f7f')),
# ('darktoothpaste2', ('#007f7f', '#00607f', '#00407f', '#00207f', '#00007f', '#13137f', '#26267f', '#39397f', '#4d4d7f', '#60607f')),
# ('darkcmy', ('#007f7f', '#19667f', '#334c7f', '#4c337f', '#66197f', '#7f007f', '#7f1966', '#7f334c', '#7f4c33', '#7f6619', '#7f7f00')),
# ('darkcmy2', ('#7f7f00', '#7f6619', '#7f4c33', '#7f334c', '#7f1966', '#7f007f', '#66197f', '#4c337f', '#334c7f', '#19667f', '#007f7f')),
# ('darksteel', ('#606060', '#55555c', '#4a4a59', '#404055', '#353552', '#2a2a4e', '#20204a', '#151547', '#0a0a43', '#000040')),
# ('darksteel2', ('#000040', '#0a0a43', '#151547', '#20204a', '#2a2a4e', '#353552', '#404055', '#4a4a59', '#55555c', '#606060')),
# ('darkrgb', ('#7f0000', '#660c00', '#4c1900', '#332600', '#193300', '#004000', '#003319', '#002633', '#00194c', '#000c66', '#00007f')),
# ('darkrgb2', ('#00007f', '#000c66', '#00194c', '#002633', '#003319', '#004000', '#193300', '#332600', '#4c1900', '#660c00', '#7f0000')),
# ('darktropicana', ('#7f7f00', '#7f7107', '#7f630e', '#7f5515', '#7f471c', '#7f3823', '#7f2a2a', '#7f1c31', '#7f0e39', '#7f0040')),
# ('darktropicana2', ('#7f0040', '#7f0e39', '#7f1c31', '#7f2a2a', '#7f3823', '#7f471c', '#7f5515', '#7f630e', '#7f7107', '#7f7f00')),
# ('darksunset', ('#7f6060', '#7f4d4d', '#7f3939', '#7f2626', '#7f1313', '#7f0000', '#7f2000', '#7f4000', '#7f6000', '#7f7f00')),
# ('darksunset2', ('#7f7f00', '#7f6000', '#7f4000', '#7f2000', '#7f0000', '#7f1313', '#7f2626', '#7f3939', '#7f4d4d', '#7f6060')),
# ('darkmagma', ('#000000', '#200000', '#400000', '#600000', '#7f0000', '#7f1900', '#7f3300', '#7f4c00', '#7f6600', '#7f7f00')),
# ('darkmagma2', ('#7f7f00', '#7f6600', '#7f4c00', '#7f3300', '#7f1900', '#7f0000', '#600000', '#400000', '#200000', '#000000')),
# ('darkholly', ('#407f40', '#337333', '#266626', '#195919', '#0c4d0c', '#004000', '#7f0000', '#6a0000', '#550000', '#400000')),
# ('darkholly2', ('#400000', '#550000', '#6a0000', '#7f0000', '#004000', '#0c4d0c', '#195919', '#266626', '#337333', '#407f40')),
# ('darkglacier', ('#000000', '#000020', '#000040', '#000060', '#00007f', '#13137f', '#26267f', '#39397f', '#4d4d7f', '#60607f')),
# ('darkglacier2', ('#60607f', '#4d4d7f', '#39397f', '#26267f', '#13137f', '#00007f', '#000060', '#000040', '#000020', '#000000')),
# ('darkmonarchy', ('#60607f', '#30307f', '#00007f', '#190066', '#33004c', '#4c0033', '#660019', '#7f0000', '#600000', '#400000')),
# ('darkmonarchy2', ('#400000', '#600000', '#7f0000', '#660019', '#4c0033', '#33004c', '#190066', '#00007f', '#30307f', '#60607f')),
# ('darkcontrast', ('#7f0000', '#004000', '#00007f', '#7f7f00', '#7f007f', '#007f7f')),
# ('darkcontrast2', ('#007f7f', '#7f007f', '#7f7f00', '#00007f', '#004000', '#7f0000')),
# ('darkspectrum', (
#     '#004040', '#6d386b', '#400040', '#404000', '#0f487f', '#7f5200', '#7f0000', '#23415a', '#004000', '#451571', '#400000', '#006768', '#000040',
#     '#7f2200', '#7f0a49', '#196619')),
# ('darkspectrum2', (
#     '#196619', '#7f0a49', '#7f2200', '#000040', '#006768', '#400000', '#451571', '#004000', '#23415a', '#7f0000', '#7f5200', '#0f487f', '#404000',
#     '#400040', '#6d386b', '#004040')),
# ('darkred-orange', ('#7f1008', '#7f1a0a', '#7f240c', '#7f2e0e', '#7f3810', '#7f4212', '#7f4c14', '#7f5616', '#7f6018')),
# ('darkorange-yellow', ('#7f6018', '#7e6316', '#7d6714', '#7c6b12', '#7b6f10', '#7a730e', '#79770c', '#787b0a', '#777f08')),
# ('darkyellow-green', ('#777f08', '#697c09', '#5b790a', '#4d750b', '#3f720c', '#316f0d', '#236c0e', '#15690f', '#086610')),
# ('darkgreen-blue', ('#086610', '#095a1d', '#0a4e2b', '#0b4239', '#0c3747', '#0d2b55', '#0e1f63', '#0f1371', '#10087f')),
# ('darkblue-cyan', ('#10087f', '#10157f', '#10237f', '#10317f', '#103f7f', '#104d7f', '#105b7f', '#10697f', '#10777f')),
# ('darkblue-purple', ('#10087f', '#1c097f', '#290a7f', '#360b7f', '#430c7f', '#500d7f', '#5d0e7f', '#6a0f7f', '#77107f')),
# ('darkorange-red', ('#7f6018', '#7f5616', '#7f4c14', '#7f4212', '#7f3810', '#7f2e0e', '#7f240c', '#7f1a0a', '#7f1008')),
# ('darkyellow-orange', ('#777f08', '#787b0a', '#79770c', '#7a730e', '#7b6f10', '#7c6b12', '#7d6714', '#7e6316', '#7f6018')),
# ('darkgreen-yellow', ('#086610', '#15690f', '#236c0e', '#316f0d', '#3f720c', '#4d750b', '#5b790a', '#697c09', '#777f08')),
# ('darkblue-green', ('#10087f', '#0f1371', '#0e1f63', '#0d2b55', '#0c3747', '#0b4239', '#0a4e2b', '#095a1d', '#086610')),
# ('darkcyan-blue', ('#10777f', '#10697f', '#105b7f', '#104d7f', '#103f7f', '#10317f', '#10237f', '#10157f', '#10087f')),
# ('darkpurple-blue', ('#77107f', '#6a0f7f', '#5d0e7f', '#500d7f', '#430c7f', '#360b7f', '#290a7f', '#1c097f', '#10087f')),
#
# ('darkspectrum', (
#     '#008080', '#DA70D6', '#800080', '#808000', '#1E90FF', '#FFA500', '#FF0000', '#4682B4', '#008000', '#8A2BE2', '#800000',
#     '#00CED1', '#000080', '#FF4500', '#FF1493', '#32CD32')),
# ('darkspectrum2', (
#     '#32CD32', '#FF1493', '#FF4500', '#000080', '#00CED1', '#800000', '#8A2BE2', '#008000', '#4682B4', '#FF0000', '#FFA500',
#     '#1E90FF', '#808000', '#800080', '#DA70D6', '#008080')),


#=========================================================================================
# main - generate colours and colour-plots
#=========================================================================================

def main():
    """Simple routine to plot all the named colors in the matplotlib colorspace
    """
    import matplotlib.pyplot as plt
    from matplotlib import colors as mcolors

    colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)

    def colourPlot(names, title='ColourPlot'):
        """make a colour plot of the names
        """
        n = len(names)
        ncols = 4
        nrows = n // ncols + 1

        fig, ax = plt.subplots(figsize=(16, 9))

        # Get height and width
        X, Y = fig.get_dpi() * fig.get_size_inches()

        Y0 = Y - fig.get_dpi() * 1.0  # remove an inch from the size
        h = Y0 // max((nrows + 1), 15)
        w = X // ncols

        for i, name in enumerate(names):
            row = i % nrows
            col = i // nrows

            y = Y0 - (row * h) - h

            xi_line = w * (col + 0.05)
            xf_line = w * (col + 0.25)
            xi_text = w * (col + 0.3)

            ax.text(xi_text, y, name, fontsize=(h * 0.5),
                    horizontalalignment='left',
                    verticalalignment='center')

            if name in colors:
                ax.hlines(y + h * 0.1, xi_line, xf_line,
                          color=colors[name] if name in colors else name,
                          linewidth=(h * 0.6))

        ax.set_xlim(0, X)
        ax.set_ylim(0, Y)
        ax.set_axis_off()

        ax.text(fig.get_dpi() * 0.25, Y - fig.get_dpi() * 0.5,
                title, fontsize=fig.get_dpi() * 0.25,
                horizontalalignment='left',
                verticalalignment='center')

        fig.subplots_adjust(left=0, right=1,
                            top=1, bottom=0,
                            hspace=0, wspace=0)
        plt.show()

    def rowPlot(names, title='ColourPlot'):
        """make a colour plot of the names
        """
        n = len(names)
        fig, ax = plt.subplots(figsize=(16, 9))
        # Get height and width
        X, Y = fig.get_dpi() * fig.get_size_inches()
        inch = fig.get_dpi()
        X0 = X - inch * 2.0
        Y0 = Y - inch * 2.0  # remove an inch from the size
        h = Y0 // 5
        for col, name in enumerate(names):
            y = Y0 - h
            xi_line = inch + (col * X0) / n
            xf_line = inch + ((col + 1) * X0) / n
            if name in colors:
                ax.hlines(y + h * 0.1, xi_line, xf_line,
                          color=colors[name] if name in colors else name,
                          linewidth=(h * 0.6))

        ax.set_xlim(0, X)
        ax.set_ylim(0, Y)
        ax.set_axis_off()
        ax.text(fig.get_dpi() * 0.25, Y - fig.get_dpi() * 0.5,
                title, fontsize=fig.get_dpi() * 0.25,
                horizontalalignment='left',
                verticalalignment='center')
        fig.subplots_adjust(left=0, right=1,
                            top=1, bottom=0,
                            hspace=0, wspace=0)
        plt.show()

    # Sort colors by hue, saturation, value and name.
    by_hsv = sorted((tuple(mcolors.rgb_to_hsv(mcolors.to_rgba(color)[:3])), name)
                    for name, color in colors.items())
    sorted_names = [name for hsv, name in by_hsv
                    if (hsv[0] == 0.0 and hsv[1] == 0.0) or hsv[1] > 0.3]

    # # print the colors to generate full colorList
    # for col in sorted_names:
    #     if isinstance(colors[col], str):
    #         # col = colourNameWithSpace(col)
    #         print('(' + repr(colors[col]) + ', ' + repr(col) + '),')

    colourPlot(spectrumDarkColours.values(), title='Dark Spectrum Colours')
    colourPlot(spectrumMediumColours.values(), title='Medium Spectrum Colours')
    colourPlot(spectrumLightColours.values(), title='Light Spectrum Colours')

    thisPalette = spectrumLightColours
    colourPlot(thisPalette.values(), title='Light Default Spectrum Colours')
    opposites = []
    for col in thisPalette.keys():
        rgbIn = hexToRgb(col)
        negRGB = invertRGBHue(*rgbIn)
        oppCol = rgbToHex(*negRGB)

        oppCol = findNearestHex(oppCol, thisPalette.keys())
        opposites.append(thisPalette[oppCol])

    colourPlot(opposites, title='Light Inverted Colours')

    thisPalette = spectrumDarkColours
    colourPlot(thisPalette.values(), title='Dark Default Spectrum Colours')
    opposites = []
    for col in thisPalette.keys():
        rgbIn = hexToRgb(col)
        negRGB = invertRGBHue(*rgbIn)
        oppCol = rgbToHex(*negRGB)

        oppCol = findNearestHex(oppCol, thisPalette.keys())
        opposites.append(thisPalette[oppCol])

    colourPlot(opposites, title='Dark Inverted Colours')
    rowPlot(brightColours.values(), title='Sorted Bright Colours')


if __name__ == '__main__':
    main()
