"""
Module Documentation here
"""
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
__dateModified__ = "$dateModified: 2025-03-21 18:56:22 +0000 (Fri, March 21, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 15:44:35 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

# import sys
# from PyQt5 import QtWidgets
from ccpn.util.Path import aPath
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame
from reportlab.platypus.doctemplate import _doNothing
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from contextlib import suppress
# from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import SPECTRUM_STACKEDMATRIX, SPECTRUM_MATRIX
# from collections import OrderedDict
import io


# import numpy as np
# from reportlab.lib import colors
# from reportlab.graphics import renderSVG, renderPS
# from reportlab.graphics.shapes import Drawing, Rect, String, PolyLine, Line, Group, Path
# from reportlab.lib.units import mm


DEFAULTMARGIN = 2.0 * cm


class SimpleDocTemplateNoPadding(SimpleDocTemplate):

    def build(self, flowables, onFirstPage=_doNothing, onLaterPages=_doNothing, canvasmaker=canvas.Canvas):
        """build the document using the flowables.  Annotate the first page using the onFirstPage
               function and later pages using the onLaterPages function.  The onXXX pages should follow
               the signature

                  def myOnFirstPage(canvas, document):
                      # do annotations and modify the document
                      ...

               The functions can do things like draw logos, page numbers,
               footers, etcetera. They can use external variables to vary
               the look (for example providing page numbering or section names).
        """
        self._calc()  # in case we changed margins sizes etc
        frameT = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal',
                       leftPadding=0, bottomPadding=0,
                       rightPadding=0, topPadding=0,
                       showBoundary=0)
        self.addPageTemplates([PageTemplate(id='First', frames=frameT, onPage=onFirstPage, pagesize=self.pagesize),
                               PageTemplate(id='Later', frames=frameT, onPage=onLaterPages, pagesize=self.pagesize)])
        if onFirstPage is _doNothing and hasattr(self, 'onFirstPage'):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self, 'onLaterPages'):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        BaseDocTemplate.build(self, flowables, canvasmaker=canvasmaker)


class Report:
    """
    Class container for generating pdf reports
    """

    def __init__(self, filename, pagesize=A4,
                 leftMargin=DEFAULTMARGIN, rightMargin=DEFAULTMARGIN, topMargin=DEFAULTMARGIN,
                 bottomMargin=DEFAULTMARGIN):
        """
        Initialise a new pdf report

        :param filename: - filename to save pdf as
        :param pagesize: - pagesize; e.g. LETTER, A4
        :param leftMargin:
        :param rightMargin:
        :param topMargin:
        :param bottomMargin:
        """

        # set the class attributes
        self.filename = filename
        self.canv = None
        self.defaultMargin = DEFAULTMARGIN

        # buffer for exporting
        self.buf = io.BytesIO()

        self.doc = SimpleDocTemplateNoPadding(
                self.buf,
                rightMargin=rightMargin,
                leftMargin=leftMargin,
                topMargin=topMargin,
                bottomMargin=bottomMargin,
                pagesize=pagesize,
                )

        # Styling paragraphs
        # styles = getSampleStyleSheet()

        # initialise a new story - the items that are to be added to the document
        self.story = []

    def addItemToStory(self, item):
        """
        Add a new item to the current story
        :param item; e.g., paragraph or drawing
        """
        self.story.append(item)

    def buildDocument(self):
        """
        Build the document from the story
        """
        self.doc.build(self.story)

    def writeDocument(self):
        """
        Write the document to the file
        """
        with open(aPath(self.filename), 'wb') as fn:
            fn.write(self.buf.getvalue())

    def clear(self):
        """Clean up the class for garbage collection"""
        with suppress(Exception):
            self.buf.close()
        self.__dict__.clear()
