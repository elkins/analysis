"""
This file contains the NmrPipe data access class
it serves as an interface between the V3 Spectrum class and the actual spectral data

See SpectrumDataSourceABC for a description of the methods

The NmrPipe data access completely relies on the Hdf5buffer option: the NmrPipe file
is fully read into the temporary buffer at the moment of first data access
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
__dateModified__ = "$dateModified: 2024-11-18 11:44:06 +0000 (Mon, November 18, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2020-11-20 10:28:48 +0000 (Fri, November 20, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys, re
from typing import Sequence
import numpy

from ccpn.util.Path import aPath, Path
from ccpn.util.Logging import getLogger

from ccpn.util.traits.CcpNmrTraits import CList, CInt, Int, CString, Bool

from ccpn.core.lib.SpectrumDataSources.SpectrumDataSourceABC import SpectrumDataSourceABC
from ccpn.core.lib.SpectrumDataSources.lib.NmrPipeHeader import NmrPipeHeader

import ccpn.core.lib.SpectrumLib as specLib

#============================================================================================================

#define FD_QUAD       0
#define FD_COMPLEX    0
#define FD_SINGLATURE 1
#define FD_REAL       1
#define FD_PSEUDOQUAD 2
#define FD_SE         3
#define FD_GRAD       4
from ccpn.core.lib.SpectrumLib import DATA_TYPE_REAL, DATA_TYPE_COMPLEX_PN, DATA_TYPE_COMPLEX_nRnI, DATA_TYPE_COMPLEX_nRI
dataTypeMap = {0:DATA_TYPE_COMPLEX_nRnI, 1:DATA_TYPE_REAL, 2:DATA_TYPE_REAL, 3:DATA_TYPE_COMPLEX_PN, 4:DATA_TYPE_REAL}

from ccpn.core.lib.SpectrumLib import DIMENSION_FREQUENCY, DIMENSION_TIME
PIPE_TIME_DOMAIN  = 0
PIPE_FREQUENCY_DOMAIN  = 1
# map NmrPipe defs on V3 defs
domainMap = {PIPE_TIME_DOMAIN:DIMENSION_TIME, PIPE_FREQUENCY_DOMAIN:DIMENSION_FREQUENCY}

# ordering definitions for the NUS types, to be stored in FDUSER6
NUS_TYPE_NONUS    = 0
NUS_TYPE_NUS      = 1
NUS_TYPE_ISTNUS   = 2
nusMap = {NUS_TYPE_NONUS:"regular", NUS_TYPE_NUS:"nus", NUS_TYPE_ISTNUS:"ist-nus"}


#============================================================================================================
# Silly nmrPipe data size definitions!
#
# in all cases: (nAq, n1) total points along acquisition (X) and indirect-1 (Y),
# time domain (T) or frequency domain (F):
#
#     Acq       Ind1             FDSIZE   FDSPECNUM
#  (T) Complex  (T) Complex  ->   nAq/2     n1
#  (T) Complex  (T) Real     ->   nAq/2     n1
#  (T) Real     (T) Complex  ->   nAq       n1
#  (T) Real     (T) Real     ->   nAq       n1
#
#  (F) Complex  (T) Complex  ->   nAq/2     n1
#  (F) Complex  (T) Real     ->   nAq/2     n1
#  (F) Real     (T) Complex  ->   nAq       n1/2
#  (F) Real     (T) Real     ->   nAq       n1
#
#  (F) Complex  (F) Complex  ->   nAq/2     n1
#  (F) Complex  (F) Real     ->   nAq/2     n1
#  (F) Real     (F) Complex  ->   nAq       n1/2
#  (F) Real     (F) Real     ->   nAq       n1
#
#============================================================================================================

class NmrPipeSpectrumDataSource(SpectrumDataSourceABC):
    """
    NmrPipe nD (n=1-4) binary spectral data reading:
    The NmrPipe files are stored as either:
    - a single file
    - or for 3D/4D as a series of 2D planes defined by a template name; e.g. 'myFile%003d.ft3'

    NmrPipe spectra can be loaded by either:
    - A nD plane file; if required, the template will be reconstructed
    - A folder with a valid NmrPipe suffix and containing a series of numbered 2D planes with a valid
      NmrPipe suffix; e.g. matching *001.dat or *001.pipe or *001.ft3, etc
    """

    #=========================================================================================
    dataFormat = 'NMRPipe'

    isBlocked = False
    wordSize = 4
    headerSize = 512
    blockHeaderSize = 0
    isFloatData = True
    MAXDIM = 4          # Explicitly overide as NmrPipe can only handle upto 4 dimensions

    suffixes = ['.pipe', '.fid', '.ft', '.ft1', '.ft2', '.ft3', '.ft4', '.dat']
    allowDirectory = True
    openMethod = open
    defaultOpenReadMode = 'rb'

    #=========================================================================================

    template = CString(allow_none=True, default_value=None).tag(
                                        info='The template to generate the path of the individual files comprising the nD',
                                       )
    nFiles = CInt(default_value=0).tag(
                                        info='The number of files comprising the nD',
                                       )
    baseDimensionality = CInt(default_value=2).tag(
                                        info='Dimensionality of the NmrPipe files comprising the nD',
                                       )
    isTransposed = Bool(default_value=False).tag(
                                        info='Data of underpinning NmrPipe files are transposed',
                                        )
    isDirectory = Bool(default_value=False).tag(
                                        info='Initiating path was a directory',
                                        )

    #=========================================================================================

    def __init__(self, path=None, spectrum=None, temporaryBuffer=True, bufferPath=None):
        """Initialise; optionally set path or extract from spectrum

        :param path: optional input path
        :param spectrum: associate instance with spectrum and import spectrum's parameters
        :param temporaryBuffer: used temporary file to buffer the data
        :param bufferPath: (optionally) use path to generate buffer file (implies temporaryBuffer=False)
        """
        super().__init__(path=path, spectrum=spectrum)

        self.header = None  # NmrPipeHeader instance
        self.pipeDimension = None
        self.nusDimension = None

        # NmrPipe files are always buffered
        self.setBuffering(True, temporaryBuffer, bufferPath)

    def readParameters(self):
        """Read the parameters from the NmrPipe file header
        Returns self
        """
        logger = getLogger()

        self.setDefaultParameters()

        try:
            # Create NmrPipeHeader instance and read the data"
            if not self.hasOpenFile():
                self.openFile(mode=self.defaultOpenReadMode)
            self.header = NmrPipeHeader(self.headerSize, self.wordSize).read(self.fp, doSeek=True)
            self.isBigEndian = self.header.isBigEndian

            # First map the easy parameters from the NmrPipeHeader definitions to the DataSource definitions
            for parName, pipeName in [
                ('isTransposed', 'transposed'),
                ('nFiles', 'nFiles'),
                ('dimensionCount', 'dimensionCount'),
                ('dimensionOrder', 'dimensionOrder'),
                ('axisLabels', 'axisLabels'),
                ('spectrometerFrequencies', 'spectrometerFrequencies'),
                ('spectralWidthsHz', 'spectralWidthsHz'),
                ('referencePoints', 'referencePoints'),
                ('referenceValues', 'referenceValues'),
                ('phases0', 'phases0'),
                ('phases1', 'phases1'),
            ]:
                value = self.header.getParameterValue(pipeName)
                setattr(self, parName, value)

            # Now do the more complicated ones

            # map the domain types
            _domain = self.header.getParameterValue('domain')
            self.dimensionTypes = [domainMap.get(k, DIMENSION_FREQUENCY) for k in _domain ]

            # map the quad types
            _quadTypes = self.header.getParameterValue('quadType')
            self.dataTypes = [dataTypeMap.get(v, DATA_TYPE_REAL) for v in _quadTypes]
            self.isComplex = [v != DATA_TYPE_REAL for v in self.dataTypes]

            _pointCounts = self.header.getParameterValue('pointCounts')
            # correction for complex types required here
            if (self.dataTypes[specLib.X_AXIS] != DATA_TYPE_REAL):
                _pointCounts[specLib.X_AXIS] *= 2

            if not self.isComplex[specLib.X_AXIS] and \
               self.dimensionTypes[specLib.X_AXIS] == DIMENSION_FREQUENCY and \
               self.isComplex[specLib.Y_AXIS]:
                    _pointCounts[specLib.Y_AXIS] *= 2

            self.pointCounts = _pointCounts

            # temperature
            if (_temp := self.header.getParameterValue('temperature')) == 0.0:
                self.temperature = None
            else:
                self.temperature = _temp

            # Pipe and NUS dimensions
            map1 = {1:specLib.X_DIM, 2:specLib.Y_DIM, 3:specLib.Z_DIM, 4:specLib.A_DIM, 0:None}
            self.pipeDimension = map1[self.header.getParameterValue('pipeDimension')]
            self.nusDimension = map1[self.header.getParameterValue('nusDimension')]

            # Fix isAcquisition for transposed data
            if self.dimensionCount >= 2 and self.isTransposed:
                _isAcquisition = [False] * self.MAXDIM
                _isAcquisition[1] = True
                self.isAcquisition = _isAcquisition

            if self.template is None and self.dimensionCount > 2:
                self.template = self._guessTemplate()

            self._setBaseDimensionality()
            self.blockSizes = [1]*specLib.MAXDIM
            self.blockSizes[0:self.baseDimensionality] = self.pointCounts[0:self.baseDimensionality]

        except Exception as es:
            logger.error('Reading parameters; %s' % es)
            raise es

        # this will set isotopes, axiscodes, assures dimensionality
        super().readParameters()

        # fix possible acquisition axis code
        if self.isTransposed:
            self.acquisitionAxisCode = self.axisCodes[specLib.Y_DIM_INDEX]

        return self

    def _setBaseDimensionality(self):
        """Set the baseDimensionality depending on dimensionCount, nFiles and template
        """
        self.baseDimensionality = 2  # The default
        # nD's stored as a single file
        if self.nFiles == 1:
            self.baseDimensionality = self.dimensionCount
        # 4D's stored as series of 3D's
        if self.dimensionCount == 4 and self.nFiles > 1 and \
           self.template is not None and self.template.count('%') == 1:
            self.baseDimensionality = 3

    def _guessTemplate(self):
        """Guess and return the template based on self.path and dimensionality
        Return None if unsuccessful or not applicable
        """
        logger = getLogger()

        directory, fileName, suffix = self.path.split3()

        if self.dimensionCount == 2:
            pass

        elif self.dimensionCount in [3,4] and self.nFiles == 1:
            pass

        elif self.dimensionCount == 3 and self.nFiles > 1:
            # 3D's stored as series of 2D's
            templates = (re.sub(r'\d\d\d\d', '%04d', fileName),
                         re.sub(r'\d\d\d',   '%03d', fileName),
                         re.sub(r'\d\d',     '%02d', fileName),
            )
            for template in templates:
                # check if we made a subsititution
                if template != fileName:
                    # check if we can find the last 3D file of the series
                    path = Path(directory) / (template % self.pointCounts[specLib.Z_DIM_INDEX]) + suffix
                    if path.exists():
                        return str(Path(directory) / (template) + suffix)

        elif self.dimensionCount == 4 and self.nFiles > 1:
            # 4D's stored as series of 2D's
            templates = (re.sub(r'\d\d\d\d\d\d\d', '%03d%04d', fileName),
                         re.sub(r'\d\d\d\d\d\d',   '%03d%03d', fileName),
                         re.sub(r'\d\d\d\d\d\d',   '%02d%04d', fileName),
                         re.sub(r'\d\d\d\d\d',     '%02d%03d', fileName),
            )
            for template in templates:
                # check if we made a subsititution
                if template != fileName:
                    # check if we can find the last 4D file of the series
                    path = Path(directory) / (template % (self.pointCounts[specLib.Z_DIM_INDEX], self.pointCounts[specLib.A_DIM_INDEX])) + suffix
                    if path.exists():
                        return str(Path(directory) / (template) + suffix)

            # 4D's stored as series of 3D's
            templates = (re.sub(r'\d\d\d\d', '%04d', fileName),
                         re.sub(r'\d\d\d',   '%03d', fileName),
                         re.sub(r'\d\d',     '%02d', fileName),
            )
            for template in templates:
                # check if we made a subsititution
                if template != fileName:
                    # check if we can find the last 4D file of the series
                    path = Path(directory) / (template % self.pointCounts[specLib.A_DIM_INDEX]) + suffix
                    if path.exists():
                        return str(Path(directory) / (template) + suffix)

        logger.debug('NmrPipeSpectrumDataSource._guessTemplate: Unable to guess from "%s"' % self.path)
        return None

    def _getPathAndOffset(self, position):
        """Construct path of NmrPipe file corresponding to position (1-based) from template
        Check presence of result path
        Return aPath instance of path and offset (in bytes) as a tuple
        """
        if self.dimensionCount <= 2:
            path = self.path
            offset = self.headerSize * self.wordSize

        elif self.dimensionCount == 3 and self.nFiles == 1:
            path = self.path
            offset = ( self.headerSize + \
                      (position[specLib.Z_DIM_INDEX]-1) *self.pointCounts[specLib.X_DIM_INDEX] * self.pointCounts[specLib.Y_DIM_INDEX]
                     ) * self.wordSize

        elif self.dimensionCount == 3 and self.baseDimensionality == 2:
            if self.template is None:
                raise RuntimeError('%s: Undefined template' % self)
            path = self.template % (position[specLib.Z_DIM_INDEX],)
            offset = self.headerSize * self.wordSize

        elif self.dimensionCount == 4 and self.baseDimensionality == 2:
            if self.template is None:
                raise RuntimeError('%s: Undefined template' % self)
            path =  self.template % (position[specLib.Z_DIM_INDEX], position[specLib.A_DIM_INDEX])
            offset = self.headerSize * self.wordSize

        elif self.dimensionCount == 4 and self.baseDimensionality == 3:
            if self.template is None:
                raise RuntimeError('%s: Undefined template' % self)
            path =  self.template % (position[specLib.A_DIM_INDEX],)
            offset = ( self.headerSize + \
                      (position[specLib.X_DIM_INDEX]-1) * self.pointCounts[specLib.X_DIM_INDEX] * self.pointCounts[specLib.Y_DIM_INDEX]
                     ) * self.wordSize

        elif self.dimensionCount == 4 and self.nFiles == 1:
            path = self.path
            offset = ( self.headerSize + \
                      (position[specLib.A_DIM_INDEX]-1) *self.pointCounts[specLib.X_DIM_INDEX] * self.pointCounts[specLib.Y_DIM_INDEX] \
                       *self.pointCounts[specLib.Z_DIM_INDEX] + \
                      (position[specLib.Z_DIM_INDEX]-1) *self.pointCounts[specLib.X_DIM_INDEX] * self.pointCounts[specLib.Y_DIM_INDEX]
                     ) * self.wordSize

        else:
            raise RuntimeError('%s: Unable to construct path for position %s' % (self, position))

        path = aPath(path)
        if not path.exists():
            raise FileNotFoundError('NmrPipe file "%s" not found' % path)

        return path, offset

    def setPath(self, path, checkSuffix=False):
        """define valid path to a (binary) data file, if needed appends or substitutes
        the suffix (if defined).

        :return self or None on error
        """
        if path is None:
            self.dataFile = None  # A reset essentially
            return super().setPath(None)

        _path = aPath(path)

        # check for directories
        if _path.is_dir() and _path.suffix in self.suffixes:
            self.isDirectory = False
            # try to establish if this is a directory with a NmrPipe series of files
            for _suffix in self.suffixes:
                pattern = f'*001{_suffix}'
                files = _path.globList(pattern)
                if len(files) > 0:
                    self._path = _path  # retain the initiating path
                    _path = files[0]  # define the first binary
                    self.isDirectory = True
                    break

            if not self.isDirectory:
                # did not find a "001" file
                return None

        return super().setPath(path=_path, checkSuffix=checkSuffix)

    def getAllFilePaths(self) -> list:
        """
        Get all the files handled by this dataSource: the binary and a parameter file.

        :return: list of Path instances
        """

        if self.nFiles == 0:
            raise RuntimeError(f'DataSource {self.dataFormat}: nFiles = 0')
        elif self.nFiles == 1:
            result = [self.path]
        else:
            # nD's: get all the nmrPipe files
            sliceTuples = [(1, p) for p in self.pointCounts]

            result = []
            # loop over all the xy-planes
            for position, aliased in self._selectedPointsIterator(sliceTuples, excludeDimensions=(specLib.X_DIM, specLib.Y_DIM)):
                path, offset = self._getPathAndOffset(position)
                result.append(path)

            # remove any duplicates
            result = list(set(result))

        return result

    def copyFiles(self, destinationDirectory, overwrite=False) -> list:
        """Copy all data files to a new destination directory
        :param destinationDirectory: a string or Path instance defining the destination directory
        :param overwrite: Overwrite any existing files
        :return A list of files copied
        """
        _destination = aPath(destinationDirectory)
        if not _destination.is_dir():
            raise ValueError(f'"{_destination}" is not a valid directory')

        if self.isDirectory:
            # A directory; create the same in the destination
            # self._path contains the originating path
            _dir, _base, _suffix = self._path.split3()
            _destination = _destination / _base + _suffix
            result = [self._path.copyDir(_destination, overwrite=overwrite)]

        elif self.nFiles > 1:
            # More than one file; i.e. a multi-file 3D or 4D.
            # Put in a single new directory within destinationDirectory with name from path and 'pipe' suffix
            _destination = _destination.fetchDir(self.nameFromPath() + self.suffixes[0])
            super().copyFiles(destinationDirectory=_destination, overwrite=overwrite)
            result = [_destination]

        else:
            # effectively the one-file situation; call super class to handle.
            result = super().copyFiles(destinationDirectory=destinationDirectory, overwrite=overwrite)

        return result

    def nameFromPath(self) -> str:
        """Return a name derived from path (to be subclassed for specific cases; e.g. Bruker)
        """
        name = self.path.parent.stem if self.isDirectory else self.path.stem
        return name

    def checkValid(self) -> bool:
        """check if valid format corresponding to dataFormat by:
        - checking template and binary files are defined

        call super class for:
        - checking suffix and existence of path
        - reading (and checking dimensionCount) parameters

        :return: True if ok, False otherwise
        """

        if not super().checkValid():
            return False

        self.isValid = False
        self.shouldBeValid = True

        self.errorString = 'Checking validity'

        if self.nFiles > 1 and self.template is None:
            errorMsg = f'No NmrPipe template defined, in spite of {self.nFiles} files comprising the {self.dimensionCount}D'
            return self._returnFalse(errorMsg)

        self.isValid = True
        self.errorString = ''
        return True


    def fillHdf5Buffer(self):
        """Fill hdf5buffer with data from self
        """
        if not self.isBuffered:
            raise RuntimeError('fillHdf5Buffer: no hdf5Buffer defined')

        getLogger().debug('fillHdf5Buffer: filling buffer %s' % self.hdf5buffer)

        # just some definitions
        xAxis = specLib.X_DIM_INDEX
        xDim = specLib.X_DIM
        yAxis = specLib.Y_DIM_INDEX
        yDim = specLib.Y_DIM

        if self.dimensionCount == 1:
            # 1D
            position = [1]
            path, offset = self._getPathAndOffset(position)
            with open(path, 'r') as fp:
                fp.seek(offset, 0)
                data = numpy.fromfile(file=fp, dtype=self.dtype, count=self.pointCounts[xAxis])
            self.hdf5buffer.setSliceData(data, position=position, sliceDim=xDim)

        else:
            # nD's: fill the buffer, reading x,y planes from the nmrPipe files into the hdf5 buffer
            planeSize = self.pointCounts[xAxis] * self.pointCounts[yAxis]
            sliceTuples = [(1, p) for p in self.pointCounts]
            realPointCounts = self.realPointCounts

            # loop over all the xy-planes
            for position, aliased in self._selectedPointsIterator(sliceTuples, excludeDimensions=(xDim, yDim)):
                path, offset = self._getPathAndOffset(position)
                with open(path, 'r') as fp:
                    fp.seek(offset, 0)
                    data = numpy.fromfile(file=fp, dtype=self.dtype, count=planeSize)
                    data.resize( (self.pointCounts[yAxis], self.pointCounts[xAxis]))

                writePosition = [p for p in position]
                writeData = data

                # For the Z,A dimensions:
                # - the complex time Z,A-axes have n alternating real, imag points (nRI)
                if self.dimensionCount >= 3 and self.isComplex[specLib.Z_AXIS] and \
                   self.dimensionTypes[specLib.Z_AXIS] == DIMENSION_TIME:
                    # adjust the Z-position to nRnI ordering
                    zP = writePosition[specLib.Z_AXIS] - 1  # convert to zero-based
                    if zP % 2:
                        # imaginary point
                        zP = zP // 2 + realPointCounts[specLib.Z_AXIS]
                    else:
                        # real point
                        zP = zP // 2
                    writePosition[specLib.Z_AXIS] = zP + 1 # convert to one-based

                if self.dimensionCount >= 4 and self.isComplex[specLib.A_AXIS] and \
                   self.dimensionTypes[specLib.A_AXIS] == DIMENSION_TIME:
                    # adjust the A-position to nRnI ordering
                    aP = writePosition[specLib.A_AXIS] - 1  # convert to zero-based
                    if aP % 2:
                        # imaginary point
                        aP = aP // 2 + realPointCounts[specLib.A_AXIS]
                    else:
                        # real point
                        aP = aP // 2
                    writePosition[specLib.A_AXIS] = aP + 1 # convert to one-based

                # In a NmrPipe 2D xy plane:
                # - A complex X-axis has n real points followed by n imaginary points (nRnI)
                # - A complex Y-axis has n alternating real, imag points (nRI)
                if self.isComplex[specLib.Y_AXIS] and \
                   self.dimensionTypes[specLib.Y_AXIS] == DIMENSION_TIME:
                    # sort the n-RI data point into nRnI data points
                    totalSize = self.pointCounts[specLib.Y_AXIS]
                    realSize = realPointCounts[specLib.Y_AXIS]
                    writeData = numpy.empty(shape=data.shape)
                    _realData = data[0::2,:]  # The real points
                    _imagData = data[1::2,:]  # The imag points
                    writeData[0:realSize, :] = _realData
                    writeData[realSize:totalSize, :] = _imagData

                self.hdf5buffer.setPlaneData(writeData, position=writePosition, xDim=xDim, yDim=yDim)

        self._bufferFilled = True

# Register this format
NmrPipeSpectrumDataSource._registerFormat()


class NmrPipeInputStreamDataSource(NmrPipeSpectrumDataSource):
    """
    NmrPipe spectral storage, reading from an stdinp stream
    """
    def __init__(self, spectrum=None, temporaryBuffer=True, bufferPath=None):
        """Initialise; optionally set path or extract from spectrum

        :param path: optional input path
        :param spectrum: associate instance with spectrum and import spectrum's parameters
        :param temporaryBuffer: used temporary file to buffer the data
        :param bufferPath: (optionally) use path to generate buffer file (implies temporaryBuffer=False)
        """
        super().__init__(spectrum=spectrum, temporaryBuffer=temporaryBuffer, bufferPath=bufferPath)
        # sys.stdin.reconfigure(encoding='ISO-8859-1')
        self.fp = sys.stdin.buffer
        self.readParameters()
        self.setBuffering(True, bufferIsTemporary=temporaryBuffer, bufferPath=bufferPath)
        self.initialiseHdf5Buffer()
        self.fillHdf5Buffer()

    def _readHeader(self):
        "Create NmrPipeHeader instance and read the data"
        self.header = NmrPipeHeader(self.headerSize, self.wordSize).read(self.fp, doSeek=False)

    def _guessTemplate(self):
        "Guess template not active/required for input stream"
        return None

    def fillHdf5Buffer(self, hdf5buffer):
        """Fill hdf5 buffer reading all slices from input stream
        """
        sliceDim = self.pipeDimension
        if sliceDim is None:
            raise RuntimeError('%s.fillHdf5Buffer: undefined dimension of the input stream')
        getLogger().debug('Fill hdf5 buffer from sys.stdin reading %d slices along dimension %s' %
                          (self.sliceCount, sliceDim))

        sliceTuples = [(1, p) for p in self.pointCounts]
        for position, aliased in self._selectedPointsIterator(sliceTuples, excludeDimensions=(sliceDim,)):
            data = numpy.fromfile(file=self.fp, dtype=self.dtype, count=self.pointCounts[sliceDim-1])
            hdf5buffer.setSliceData(data, position=position, sliceDim=sliceDim)
        self._bufferFilled = True

    def closeFile(self):
        """close the file
        """
        self.fp = None  # Do not close sys.stdin --> set self.fp to None here!
        self.mode = None
        super().closeFile()

# NmrPipeInputStreamDataSource._registerFormat()
