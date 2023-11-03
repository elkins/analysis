"""
This module defines the code for creating  Journal Article References
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license",
               )
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y"
                )
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2023-11-03 11:50:36 +0000 (Fri, November 03, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2023-10-03 11:50:37 +0100 (Tue, October 03, 2023)  $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.traits.TraitBase import TraitBase
from ccpn.util.traits.CcpNmrTraits import Unicode, Int, Float, Bool, List, RecursiveDict, Dict

class JournalReferenceABC(TraitBase):
    """Journal Article Reference base class.
    A class to contain and nicely format bibliography for its usage within the CCPN software.
    This module is not meant to be used for writing the bibliography in journal articles!
    For more complex manipulation of bibliography use dedicated tools, such as "pybtex" for Python or stand-alone programs such as Mendeley, Zotero, EndNote...
    See also https://github.com/citation-style-language
    Journal names are not shortened automatically. There is not an imminent need to include a package for shortening the journal name from the full name. See https://github.com/jxhe/bib-journal-abbreviation
    """

    title = Unicode(allow_none=False, default_value='Title: N/A').tag(info='The Journal Article name to be referenced')
    authors = List(default_value=[{'names':[], 'surnames':[]}]).tag(info='A list of  dict of any names and surnames')
    journalName = Unicode(allow_none=False, default_value='Journal: N/A').tag(info='The Journal Article publisher name')
    journalNameShort = Unicode(allow_none=False, default_value='Journal: N/A').tag(info='The Journal Article publisher short name')
    volume = Unicode(allow_none=False, default_value='?').tag(info='The Journal Article volume')
    issue = Unicode(allow_none=True, default_value='').tag(info='The Journal Article issue')
    pages = Unicode(allow_none=False, default_value='?-?').tag(info='The Journal Article pages ')
    year = Unicode(allow_none=False, default_value='YYYY').tag(info='The Journal Article year')
    refType = Unicode(allow_none=False, default_value='Journal Article').tag(info='The Journal Article type')
    doi = Unicode(allow_none=False, default_value='').tag(info='The Journal Article DOI ')
    url = Unicode(allow_none=True, default_value='').tag(info='The Journal Article URL')

    # --------- Styles ---------- #

    @property
    def genericLong(self):
        """Generic long formatting: as
         All authors. Title. JournalTitle. Year; volume(issue): pages. DOI.
         """
        authors = self.getAuthors(count=None, inititialOnly=True, nameSep='', add_etal=True)
        return f"{authors}. {self.title}. {self.journalName}. {self.year}; {self.volume}{self._getIssue()}, {self.pages}. {self.DOI}"

    @property
    def genericShort(self):
        """ Generic short formatting: as
        First author et al. Title. shortJournalTitle. Year;  DOI.
         """
        authors = self.getAuthors(count=1, inititialOnly=True, nameSep='', add_etal=True)
        return  f"{authors}. {self.title}. {self.journalNameShort}. {self.year}. {self.DOI}"

    @property
    def genericMinimal(self):
        """ Generic minimal formatting
        First author et al. YYYY. Short journal.  DOI.
         """
        authors = self.getAuthors(count=1, inititialOnly=True, nameSep='', add_etal=True)
        return f"{authors}. {self.year}. {self.journalNameShort}. {self.doi}"

    @property
    def vancouver(self):
        """ A representation of the Vancouver style.
         Required elements: Author(s) (after 7 add et al). Article Title. Abbreviated Journal Title. Date of Publication; Volume Number(issue): Page numbers. """
        authors = self.getAuthors(8, inititialOnly=True, nameSep='', add_etal=True)
        cite = f"{authors}. {self.title}. {self.journalNameShort}. {self.year}; {self.volume}{self._getIssue()}:{self.pages}"
        return cite

    @property
    def CSE(self):
        """ A representation of the CSE style.
         Required elements:  Author(s). Article Title. Abbreviated Journal Title. Year; Volume(issue):page numbers..
        """
        authors = self.getAuthors(8, inititialOnly=True, nameSep='', add_etal=True)
        cite = f"{authors}. {self.title}. {self.journalNameShort}. {self.year}; {self.volume}{self._getIssue()}:{self.pages}"
        return cite

    @property
    def harvard(self):
        """ A representation of the generic Harvard style.
         Required elements:  Author(s)[Surname, initial]. (Year) 'Article Title'.  Journal Title, Volume(issue), page numbers. DOI.
        """
        authors = self.getAuthors(8, inititialOnly=True, nameSep='.', surnameNameSep=', ', add_etal=True)
        cite = f"{authors} ({self.year}) '{self.title}'. {self.journalName}, {self.volume}{self._getIssue()}, pp.{self.pages}. {self.DOI}"
        return cite

    # --------- End  Styles ---------- #

    def getAuthors(self, count:int=None, inititialOnly=False, nameSep=', ', surnameSep=' ', authorsSep = ', ', surnameNameSep=' ', nameSurnameSep=' ', surnameFirst=True, add_etal=False):
        """Get the list of authors.
        :param count: int or None. None to list all authors
        """
        authors = []
        authorDefs = self.authors[:count]
        for authorDef in authorDefs:
            names = authorDef.get('names', [])
            surnames = authorDef.get('surnames', [])
            surnames = surnameSep.join(surnames)
            if inititialOnly:
                names  = ''.join([f'{name[0]}{nameSep}' for name in names])
            else:
                names = nameSep.join(names)
            if surnameFirst: # make name-surname per author
                fullname = f'{surnames}{surnameNameSep}{names}'
            else:
                fullname = f'{names}{nameSurnameSep}{surnames}'
            authors.append(fullname)
        if len(authors)==2:
            authors = f'{authors[0]} and {authors[1]}'
        else:
            authors = authorsSep.join(authors)
        if count is not None:
           if add_etal and len(self.authors) > count:
            authors += ' et al'
        return authors

    @property
    def DOI(self):
        return f"DOI: {self.doi} "

    def _getIssue(self):
        return f'({self.issue})' if self.issue else ''


######################################################################################################################################################

class CcpNmrAnalysisScreen(JournalReferenceABC):

    title = 'CcpNmr AnalysisScreen, a new software programme with dedicated automated analysis tools for fragment‐based drug discovery by NMR'
    journalName = "Journal of Biomolecular NMR"
    journalNameShort = 'J. Biomol. NMR'
    volume = '74'
    issue = ''
    doi = 'https://doi.org/10.1007/s10858-020-00321-1'
    pages = '565-577'
    year = '2020'
    authors = [{'names':['Luca', 'G'], 'surnames':['Mureddu']},
               {'names':['Timothy', 'J'], 'surnames':['Ragan']},
               {'names': ['Edward', 'J'], 'surnames': ['Brooksbank']},
               {'names': ['Geerten', 'W'], 'surnames': ['Vuister']},
               ]


if __name__ == '__main__':
    #     run a test
    j = CcpNmrAnalysisScreen()
    print('----'*100)
    print(f'The generic long style: \n{j.genericLong}')
    print('==='*30)
    print(f'The generic short style: \n{j.genericShort}')
    print('==='*30)
    print(f'The generic minimal style: \n{j.genericMinimal}')
    print('==='*30)
    print(f'Harvard style: \n{j.harvard}')
    print('==='*30)
    print(f'Vancouver style: \n{j.vancouver}')
    print('==='*30)
    print(f'CSE style: \n{j.CSE}')
    print('----'*100)
