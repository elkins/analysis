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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2025-02-11 15:57:08 +0000 (Tue, February 11, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


from typing import Tuple, Optional, Union, Sequence, Iterable
import re
from ccpn.util.Logging import getLogger
import textwrap
import warnings
import pandas as pd

# definitions as they appear in the dataframe and in the underlining objects
CODE1LETTER =  'code1Letter'
CODE3LETTER = 'code3Letter'
CCPCODE = 'ccpCode'
MOLTYPE = 'molType'
ISSTANDARD = 'isStandard'
OBJ = 'obj'
ERRORS = 'errors'
INPUT = 'input'
PROTEIN = 'protein'
DNA= 'DNA'
RNA = 'RNA'
ISVALID = 'isValid'

class SequenceHandler():
    """ A  tool designed for converting compound codes between 1-letter, 3-letter and ccpCode representations.
    It also includes parser and validator for ensuring the sequence contains valid entries prior creation of the Chain Core object.
    The underlining objects that make these routine possible are ChemComps definitions.
    Note, not every Chemical Compound has a 1Letter or 3Letter code representation, so conversions are not always possible.
    DNA and RNA have 2 and 1 characters for the 3-Letter Code
    errorMode: str. Raise or warn
    """

    def __init__(self, project, moleculeType:str, errorMode:str='raise', supressWarning=False):
        self.project = project
        self._chemCompsData = self.project._chemCompsData.copy() # needs to be a copy to ensure we don't modify the original dataframe
        self.setMoleculeType(moleculeType)
        self._errorMode = errorMode
        self._supressWarning = supressWarning


    @property
    def data(self):
        return  self._getDataForMolType(self.moleculeType)

    def getAvailableCode3Letter(self, standardsOnly=True):
        """
        :return: A list of all available Code3Letter from the loaded ChemComps in the project for the defined MoleculeType
        """
        df = self.data
        if standardsOnly:
            df = self.data[self.data[ISSTANDARD]]
        return list(df[CODE3LETTER].values)

    def getAvailableCode1Letter(self, standardsOnly=True):
        """
        :return: A list of all available Code1Letter from the loaded ChemComps in the project for the defined MoleculeType
        """
        df = self.data
        if standardsOnly:
            df = self.data[self.data[ISSTANDARD]]
        return list(df[CODE1LETTER].values)

    def getAvailableCcpCodes(self, standardsOnly=True):
        """
        :return: A list of all available CcpCode from the loaded ChemComps in the project for the defined MoleculeType
        """
        df = self.data
        if standardsOnly:
            df = self.data[self.data[ISSTANDARD]]
        return list(df[CCPCODE].values)

    def getAvailableCodeByType(self, codeType, standardsOnly=True):
        """
        :return: A list of all available Codes by the given type
        """
        funcs = {
            CODE1LETTER:self.getAvailableCode1Letter,
            CODE3LETTER: self.getAvailableCode3Letter,
           CCPCODE: self.getAvailableCcpCodes}
        func = funcs.get(codeType)
        if func is None:
            getLogger().warning('Code type not recognised')
            return []
        return func(standardsOnly=standardsOnly)

    def oneToThreeCode(self, sequence1Letter, standardsOnly=True) -> list:
        """ Convert one To ThreeCode"""
        result = self._sequenceConversionBase(sequence1Letter,
                                              CODE1LETTER, CODE3LETTER,
                                              standardsOnly=standardsOnly)
        return result

    def oneToCcpCode(self, sequence1Letter, standardsOnly=True) -> list:
        """ Convert one To CcpCode for Standard """
        result = self._sequenceConversionBase(sequence1Letter,
                                              CODE1LETTER, CCPCODE,
                                              standardsOnly=standardsOnly)
        return result

    def ccpCodeToOneCode(self, sequence3Letters, standardsOnly=True) -> list:
        """ Convert CcpCodes To OneCode """
        result = self._sequenceConversionBase(sequence3Letters,
                                              CCPCODE, CODE1LETTER,
                                              standardsOnly=standardsOnly)
        return result

    def threeToCcpCode(self, sequence3Letters, standardsOnly=False) -> list:
        """ Convert  Three to CcpCode """
        result = self._sequenceConversionBase(sequence3Letters,
                                              CODE3LETTER, CCPCODE,
                                              standardsOnly=standardsOnly)
        return result

    def ccpCodeToThreeCode(self, sequence3Letters, standardsOnly=False) -> list:
        """ Convert CcpCodes To Three Code. """
        result = self._sequenceConversionBase(sequence3Letters,
                                              CCPCODE, CODE3LETTER,
                                              standardsOnly=standardsOnly)
        return result

    def threeToOneCode(self, sequence3Letters, standardsOnly=True) -> list:
        """ Convert ThreeCodes To OneCode"""
        result = self._sequenceConversionBase(sequence3Letters,
                                              CODE3LETTER, CODE1LETTER,
                                              standardsOnly=standardsOnly)
        return result

    def setMoleculeType(self, moleculeType):
        availableMolTypes = self._chemCompsData[MOLTYPE].unique()
        if moleculeType not in availableMolTypes:
            raise ValueError(f'Molecule Type {moleculeType} is not recognised. Use one of:  {availableMolTypes}')
        self.moleculeType = moleculeType

    def setErrorMode(self, errorMode):
        """
        set the error mode when parsing a sequence to raise or warn
        :param errorMode: str. one of raise or warn
        :return:
        """
        self.errorMode = errorMode

    def isValidSequence(self, sequence):
        return self._isValidSequence(sequence)

    def splitStringSequenceToList(self, sequence:str, codeLength:int=1) -> list:
        """
        Split a string to a list.
        e.g.:
            sequence =  'AAAAAA'
            splitStringSequenceToList(sequence, codeLength=1)
            ->>>   ['A', 'A', 'A', 'A', 'A']

            sequence =  'ALAALAALA'
            splitStringSequenceToList(sequence, codeLength=3)
            ->>>    ['ALA', 'ALA', 'ALA']
        :param sequence: str
        :param codeLength: int
        :return: list of strings
        """
        if not isinstance(sequence, str):
            raise ValueError('Sequence must be a string')
        if self._strContainsSpacesCommas(sequence):
            raise ValueError('Sequence cannot contain separators')
        return textwrap.wrap(sequence, width=codeLength)

    def updateData(self):
        """ Run this if you uploaded new ChemComps and you have an instance opened of this class"""
        self._chemCompsData = self.project._chemCompsData.copy()

    def parseSequence(self, sequence, standardsOnly=False):
        """
        Parse a generic formatted sequence.
        Note  A CcpCode is case-sensitive and uniquely defines a Compound, also known as ChemComp. Every ChemComp has a CcpCode.
        Not every ChemComp has a 1LetterCode and 3LetterCode. So conversions are  not always possible.
        :param sequence: str or list of str.

            allowed sequence formats:
                - 1-Letter-Code
                    sequence =  'AAAAAA'
                    sequence =  'A A A A A A'
                    sequence =  'A, A, A, A, A, A'
                    sequence =  ['A', 'A', 'A', 'A', 'A']
                - 3-Letter-Code
                    sequence =  'ALA ALA ALA ALA'
                    sequence =  'ALA, ALA, ALA, ALA'
                    sequence =  ['ALA', 'ALA', 'ALA']
                - ccpCodes:
                    - sequence containing Standard residue(s) CcpCodes e.g.::
                        sequence = 'Ala Leu Ala'
                        sequence = 'Ala, Leu, Ala'
                        sequence = ['Ala', 'Leu', 'Ala']
                    - sequence containing Non-Standard residue(s) CcpCodes e.g.:
                        sequence = ['Ala', 'Aba', Orn]
                    - sequence of a small-molecule CcpCodes: (Note you need to import the ChemComp first if not available in the Project. see docs)
                        sequence = ['Atp']
                        sequence = ['MySmallMolecule']

            not supported:
                - mix of CcpCodes and 3-Letter-Code either as string or list of strings
                - sequence of string of CcpCodes without separators. e.g.: sequence = 'AlaAbaOrn'

                Notes:
                Sequence of one single 3LetterCode or CcpCode MUST BE a list.
                Otherwise is ambiguous and is  parsed as  individual 1-Letter-Code. e.g.:
                    sequence =  'ALA' translates to 'ALA LEU ALA'
                not supported:
                    - mix of 1-Letter-Code and 3-Letter-Code either as string or list of strings
                    - sequence of string  of 3-Letter-Code without separators. e.g.: sequence =  'ALAALAALAALA'.
                      you can use the sequenceHandler, see docs:
                      'newSequence = sequenceHandler._strSequenceToList(sequence, splitByLength=3)'
                     - mix of CcpCodes and 3-Letter-Code either as string or list of strings
                     - sequence of string of CcpCodes without separators. e.g.: sequence = 'AlaAbaOrn'

        :param sequence: str or list
        :return: dict
        """
        result = self._getSequenceMapTemplate()
        # ~~~~ error checking ~~~~ #
        if isinstance(sequence, str):
            # Convert to a list of string to allow a unified handling
            sequence = self._strSequenceToList(sequence)

        if not isinstance(sequence, list):
            error = 'Sequence must be a List to be parsed at this point.'
            raise TypeError(error)

        if len(sequence) == 0:
            result[ISVALID] = True ## This will allow to create empty chains
            return result

        # ~~~~ error checking done ~~~~ #
        result[INPUT] = sequence
        if self.moleculeType in [RNA, DNA]: # these are allowed only in ccpCode to be safe and avoid ambiguities
            result = self._parseCCPsequence(result, sequence, standardsOnly=False, conversionErrorMode='skip')
            return result
        ##  deal with 1CodeLetter
        is1Code = self._isCode1LetterSequence(sequence)
        if is1Code:
            isValid, errorIndices = self._isValidSequence(sequence, CODE1LETTER, standardsOnly=True)
            result[ISVALID] = isValid
            result[CODE1LETTER] = sequence
            result[CODE3LETTER] = self.oneToThreeCode(sequence, standardsOnly=True) #can be only standards
            result[CCPCODE] = self.oneToCcpCode(sequence, standardsOnly=True) #can be only standards
            result[ERRORS] = errorIndices
            return result

        ##  deal with 3CodeLetter
        is3Code = self._isCode3LetterSequence(sequence)
        if is3Code:
            isValid, errorIndices = self._isValidSequence(sequence, CODE3LETTER, standardsOnly=standardsOnly)
            result[ISVALID] = isValid
            result[CODE1LETTER] = self.threeToOneCode(sequence, standardsOnly=standardsOnly)
            result[CODE3LETTER] = sequence
            result[CCPCODE] = self.threeToCcpCode(sequence, standardsOnly=standardsOnly)
            result[ERRORS] = errorIndices
            return result
        ##  deal with a CcpCode format.
        else:
            self. _parseCCPsequence(result, sequence, standardsOnly=False, conversionErrorMode = 'warning' )
        return result

    def _parseCCPsequence(self, result, sequence, standardsOnly=False, conversionErrorMode = 'warning' ):
        # result = self._getSequenceMapTemplate()
        isValid, errorIndices = self._isValidSequence(sequence, CCPCODE, standardsOnly=standardsOnly)
        result[CCPCODE] = self._validateCcpCode(sequence)
        result[ISVALID] = isValid
        result[ERRORS] = errorIndices
        ## temporarily switch to warning mode to try the conversion to 1-3 letter code.
        self._errorMode = conversionErrorMode  # only because the conversion to 1-3 letter code is not guaranteed to be available, but still be a valid sequence
        result[CODE1LETTER] = self.ccpCodeToOneCode(sequence, standardsOnly=True)  #1letter is only for standards!
        result[CODE3LETTER] = self.ccpCodeToThreeCode(sequence, standardsOnly=standardsOnly)
        self._errorMode = conversionErrorMode
        return result

    def _getSequenceMapTemplate(self):
        """ The dictionary template used for conversions and parsing"""
        return {
            ISVALID                 : False,
            INPUT                   : None,
            CODE3LETTER    : [],
            CODE1LETTER    : [],
            CCPCODE            : [],
            MOLTYPE             : self.moleculeType,
            ERRORS               : [],
            }

    def _sequenceConversionBase(self, sequence, inputType, outputType, standardsOnly=True) -> list:
        """
         Convert for Standard residues only
        :param sequence: the sequence to convert
        :param inputType: column name, One of CODE1LETTER,  CODE3LETTER, CCPCODE
        :param outputType: column name, One of CODE1LETTER,  CODE3LETTER, CCPCODE
        :return: converted sequence
        """
        if isinstance(sequence, str):
            sequence = self._strSequenceToList(sequence)
        df = self.data
        if standardsOnly:
            df = self.data[self.data[ISSTANDARD]]
        result = self._covertCodes(df, sequence, inputType,  outputType )
        return result

    def _covertCodes(self, df, sequence, columnOrigin,  columnTarget ):

        """
        Convert the code from one CodeType to another based on the df definitions.
        # FYI:This is a one-liner if we were 100% sure the input was valid:
        # result = [df.loc[df[columnOrigin] == item, columnTarget].values[0] for item in sequence]
        """
        result = []
        if not columnOrigin in df or not columnTarget in df:
            raise RuntimeError('Cannot convert. DataFrame does not contain the proper columns.')
        for i, code in enumerate(sequence):
            foundDf = df[df[columnOrigin] == code]
            if foundDf.empty:
                msg = f'Cannot convert {code} from {columnOrigin} to {columnTarget}.'
                if self._errorMode in ['raise', 'strict', 'ValueError']:
                    raise RuntimeError(msg)
                elif self._errorMode in ['warn', 'warning']:
                    convertedCode = None
                    if not self._supressWarning:
                        warnings.warn(msg)
                else:
                    continue
            else:
                convertedCode = foundDf[columnTarget].values[-1]
            result.append(convertedCode)
        return result

    def _get3CodeLengthByMolType(self):
        lengths = {
                        PROTEIN : 3,
                        DNA: 2,
                        RNA: 1,
                        }
        length = lengths.get(self.moleculeType, -1)
        return length

    def _isCode1LetterSequence(self, sequence: list):
        """
        True if at least a Code is present in the list of available Code1Letter. Standards Only.
        :param sequence: a list of strings
        :return: bool
        """
        availableCodes = self.getAvailableCode1Letter(standardsOnly=True)
        for item in sequence:
            if item in availableCodes:
                return True
        return False

    def _isCode3LetterSequence(self, sequence: list):
        """
       True if at least a Code is present in the list of available Code3Letter. Standards and non
        :param sequence: a list of strings
        :return: bool
        """
        availableCodes = self.getAvailableCode3Letter(standardsOnly=False)
        for item in sequence:
            if item in availableCodes:
                return True
        return False

    def _validateCcpCode(self, sequence:list):
        """
       it is a CcpCode sequence  if at least one code is present in the list of available CcpCodes
        :param sequence: a list of strings
        :return: bool
        """
        availableCcpCodes = self.getAvailableCcpCodes(standardsOnly=False)
        curatedSequence = []
        for item in sequence:
            if item in availableCcpCodes:
                curatedSequence.append(item)
            else:
                curatedSequence.append(None)
        return curatedSequence

    def _strContainsSpacesCommas(self, string):
        """
        Regex pattern to match spaces or commas
        :param string:
        :return:
        """
        pattern = re.compile(r'[ ,]')
        return pattern.search(string)

    def _cleanString(self, string):
        """Remove any space, comma etc"""
        string = re.sub(r'\s|[,;:.]', '', string)
        return ''.join(string)

    def _splitStrBySeparators(self, sequence):
        """ split by commas or spaces. Others are not allowed here."""
        tokens = re.split(r'[,\s]+', sequence)  # just splitting by space and/or comma
        sequence = [token.strip() for token in tokens if token.strip()]  # remove any unwanted spaces/commas
        return sequence

    def _strSequenceToList(self, sequence, codeLength=1):
        """
        Convert a string to a list.
        If contains a separator, then we split by the separator, e.g.: commas or spaces,
        :param sequence: str
        :param codeLength: int, Use -1 to don't split and convert directly to list.
        :return:
        """
        if self._strContainsSpacesCommas(sequence):
            sequence= self._splitStrBySeparators(sequence)
        else:
            if codeLength >= 1:
                sequence = self.splitStringSequenceToList(sequence, codeLength=1)  # default 1 and not allowed other automatic splitting. (too ambiguous)
            else:
                sequence = [sequence]
        return sequence

    def _getDataForMolType(self, molType):
        data = self._chemCompsData
        data = data[data['molType'] == molType]
        return data

    def _getAvailableCodes(self):
        """ Get all available Codes needed for validating a sequence"""
        codes = self.data[[CCPCODE, CODE3LETTER, CODE1LETTER]].values.flatten()
        codes = list(set([i for i in codes if i is not None]))
        return codes

    def _isValidSequence(self, sequence, seqType, standardsOnly=True):
        """Check if the single element in a sequence are known.
        :return bool, list of indexes for the invalid elements"""

        invalidIndices = []
        allowedValues = self.getAvailableCodeByType(seqType, standardsOnly=standardsOnly)
        for i, code in enumerate(sequence):
            if code not in allowedValues:
                invalidIndices.append(i)
        return len(invalidIndices)==0, invalidIndices


def _copySequenceToClipboard(sequenceMap, codeType, separatorType):

    if not sequenceMap.get(ISVALID):
        getLogger().warn(f'Cannot copy Sequence as {codeType}. Inspect: {sequenceMap}')
        return

    sequence = sequenceMap.get(codeType, '')
    values = separatorType.join(sequence)
    df = pd.DataFrame([values])
    df.to_clipboard(index=False, header=False)
