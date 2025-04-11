"""
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
__dateModified__ = "$dateModified: 2025-04-11 12:23:32 +0100 (Fri, April 11, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import typing

from ccpn.core.Project import Project
from ccpn.core.Sample import Sample
from ccpn.core.SpectrumHit import SpectrumHit
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.lib import Pid
from ccpn.util import Constants
from ccpn.util.Constants import DEFAULT_LABELLING
from ccpn.util import Common as commonUtil
from ccpnmodel.ccpncore.api.ccp.lims.Sample import Sample as ApiSample
from ccpnmodel.ccpncore.api.ccp.lims.Sample import SampleComponent as ApiSampleComponent
from ccpnmodel.ccpncore.api.ccp.nmr import Nmr
from ccpn.core.lib.ContextManagers import newObject, newObjectList
from ccpn.util.Logging import getLogger


class SampleComponent(AbstractWrapperObject):
    """ A Samplecomponent indicates a Substance contained in a specific Sample,
    (e.g. protein, buffer, salt), and its  concentrations.

    The Substance referred to is defined by the 'name' and 'labelling' attributes.
    For this reason the SampleComponent cannot be renamed. See Substance."""

    #: Short class name, for PID.
    shortClassName = 'SC'
    # Attribute it necessary as subclasses must use superclass className
    className = 'SampleComponent'

    _parentClass = Sample

    #: Name of plural link to instances of class
    _pluralLinkName = 'sampleComponents'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiSampleComponent._metaclass.qualifiedName()

    # Internal namespace
    _ISOTOPECODE2FRACTION = 'isotopeCode2Fraction'
    _SPECTRALOVERLAPSCORE = 'spectralOverlapScore'
    _SPECTRALOVERLAPCOUNT = 'spectralOverlapCount'

    # CCPN properties
    @property
    def _apiSampleComponent(self) -> ApiSampleComponent:
        """ API sampleComponent matching SampleComponent"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """id string - name.labelling"""
        obj = self._wrappedData

        name = obj.name
        labelling = obj.labeling
        if labelling == DEFAULT_LABELLING:
            labelling = ''
        return Pid.createId(name, labelling)

    @property
    def _localCcpnSortKey(self) -> typing.Tuple:
        """Local sorting key, in context of parent."""
        obj = self._wrappedData
        labelling = obj.labeling
        return (obj.name, '' if labelling == DEFAULT_LABELLING else labelling)

    @property
    def name(self) -> str:
        """name of SampleComponent and corresponding substance"""
        return self._wrappedData.name

    @property
    def labelling(self) -> str:
        """labelling descriptor of SampleComponent and corresponding substance """
        result = self._wrappedData.labeling
        if result == DEFAULT_LABELLING:
            result = None
        #
        return result

    @property
    def _parent(self) -> Sample:
        """Sample containing SampleComponent."""
        return self._project._data2Obj[self._wrappedData.parent]

    sample = _parent

    @property
    def role(self) -> str:
        """Role of SampleComponent in solvent, e.g. 'solvent', 'buffer', 'target', ..."""
        return self._wrappedData.role

    @role.setter
    def role(self, value: str):
        self._wrappedData.role = value

    @property
    def concentration(self) -> float:
        """SampleComponent.concentration"""
        return self._wrappedData.concentration

    @concentration.setter
    def concentration(self, value: float):
        self._wrappedData.concentration = value

    @property
    def concentrationError(self) -> float:
        """Estimated Standard error of SampleComponent.concentration"""
        return self._wrappedData.concentrationError

    @concentrationError.setter
    def concentrationError(self, value: float):
        self._wrappedData.concentrationError = value

    @property
    def concentrationUnit(self) -> str:
        """Unit of SampleComponent.concentration, one of:
        'M', 'mM', 'µM', 'nM', 'pM', 'g/L', 'L/L', 'mol/mol', 'g/g' , 'eq'
        """

        result = self._wrappedData.concentrationUnit
        # if result is not None and result not in Constants.concentrationUnits:
        #   self._project._logger.warning(
        #     "Unsupported stored value %s for SampleComponent.concentrationUnit"
        #     % result)
        #
        return result

    @concentrationUnit.setter
    def concentrationUnit(self, value: str):
        # if value not in Constants.concentrationUnits:
        #   self._project._logger.warning(
        #     "Setting unsupported value %s for SampleComponent.concentrationUnit."
        #     % value)
        self._wrappedData.concentrationUnit = value

    @property
    def purity(self) -> float:
        """SampleComponent.purity on a scale between 0 and 1"""
        return self._wrappedData.purity

    @purity.setter
    def purity(self, value: float):
        self._wrappedData.purity = value

    @property
    def spectrumHits(self) -> typing.Tuple[SpectrumHit, ...]:
        """ccpn.SpectrumHits found for SampleComponent"""
        ff = self._project._data2Obj.get
        return tuple(sorted(ff(x) for x in self._apiSampleComponent.spectrumHits))

    @property
    def isotopeCode2Fraction(self) -> typing.Dict[str, float]:
        """{isotopeCode:fraction} dictionary giving uniform isotope percentages

        isotopeCodes are of the form '12C', '13C', and all relevant isotopes for a given
        nucleus must be entered. Fractions must add up to 1.0 for each element.

        Example value:
        {'12C':0.289, '13C':0.711, '1H':0.99985, '2H':0.00015}

        NBNB the internal dictionary is returned directly without checks or encapsulation"""

        result = self._getInternalParameter(self._ISOTOPECODE2FRACTION)
        #
        return result

    @isotopeCode2Fraction.setter
    def isotopeCode2Fraction(self, value):
        if not isinstance(value, dict):
            raise ValueError("SampleComponent.isotopeCode2Fraction must be a dictionary")
        self._setInternalParameter(self._ISOTOPECODE2FRACTION, value)

    #=========================================================================================
    # Implementation functions
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: Sample) -> list:
        """get wrappedData (SampleComponent) for all SampleComponent children of parent Sample"""
        return parent._wrappedData.sortedSampleComponents()

    #=========================================================================================
    # Mixtures Implementation
    #=========================================================================================

    @property
    def spectralOverlapScore(self):
        return self._getInternalParameter(self._SPECTRALOVERLAPSCORE)

    @spectralOverlapScore.setter
    def spectralOverlapScore(self, value):
        self._setInternalParameter(self._SPECTRALOVERLAPSCORE, value)

    @property
    def spectralOverlapCount(self):
        return self._getInternalParameter(self._SPECTRALOVERLAPCOUNT)

    @spectralOverlapCount.setter
    def spectralOverlapCount(self, value):
        self._setInternalParameter(self._SPECTRALOVERLAPCOUNT, value)

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    def copyTo(self, targetSample:Sample):

        kwds = {
            'concentration': self.concentration,
            'concentrationError': self.concentrationError,
            'comment': self.comment,
            'purity': self.purity,
            'role': self.role,
            }
        newSC = _newSampleComponent(targetSample, name=self.name, labelling=self.labelling, **kwds)
        return newSC

    #===========================================================================================
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================


#=========================================================================================
# Connections to parents:
#=========================================================================================


def getter(self: SpectrumHit) -> SampleComponent:
    return self._project._data2Obj.get(self._apiSpectrumHit.sampleComponent)


SpectrumHit.sampleComponent = property(getter, None, None,
                                       "ccpn.SampleComponent in which ccpn.SpectrumHit is found")
del getter


def _newComponent(self: Sample, name: str = None, labelling=DEFAULT_LABELLING, **kwargs) -> SampleComponent:
    """internal. Used to avoid the overhead of decorators.
    """
    apiSubstance = self._project._apiNmrProject.sampleStore.refSampleComponentStore.findFirstComponent(name=name, labeling=labelling)

    if apiSubstance:
        substance = self._project._data2Obj[apiSubstance]
    else:
        from ccpn.core.Substance import _newSubstance

        substance = _newSubstance(self._project, name=name, labelling=labelling)
    obj = self._wrappedData.newSampleComponent(name=name, labeling=substance._wrappedData.labeling, **kwargs)
    return self._project._data2Obj.get(obj)


@newObjectList(('SampleComponent', 'Substance'))
def _newSampleComponent(self: Sample, name: str = None, labelling: str = None, role: str = None,  # ejb
                        concentration: float = None, concentrationError: float = None,
                        concentrationUnit: str = None, purity: float = None, comment: str = None,
                        ) -> typing.Union['SampleComponent', typing.Tuple]:
    """Create new SampleComponent within Sample.

    Automatically creates the corresponding Substance if the name is not already taken.

    See the SampleComponent class for details.

    :param name:
    :param labelling:
    :param role:
    :param concentration:
    :param concentrationError:
    :param concentrationUnit:
    :param purity:
    :param comment:
    :return: a new SampleComponent instance.
    """

    labelling = labelling if labelling is not None else DEFAULT_LABELLING
    if name is None:
        # ensure that always has a name
        name = SampleComponent._uniqueName(self.project, name=name)
    SampleComponent._validateStringValue(attribName='name', value = name)
    SampleComponent._validateStringValue(attribName='labelling', value = labelling, allowNone=True, allowEmpty=True)

    _apiNmrProject = self._project._apiNmrProject
    apiRefComponentStore = _apiNmrProject.sampleStore.refSampleComponentStore
    if self._apiSample.findAllSampleComponents(name=name, labeling=labelling):
        # ensure that always has a name
        name = SampleComponent._uniqueName(self.project, name=name)
    if concentrationUnit is not None and concentrationUnit not in Constants.concentrationUnits:
        self._project._logger.warning(f"Unsupported value {concentrationUnit} for SampleComponent.concentrationUnit")
        raise ValueError(f"SampleComponent.concentrationUnit must be in the list: {Constants.concentrationUnits} "
                         f"- {concentrationUnit}")

    apiSample = self._wrappedData
    apiExistingSubstances = apiRefComponentStore.findAllComponents(name=name, labeling=labelling)
    if len(apiExistingSubstances) > 1:
        # should only return one element
        raise RuntimeError('Too many identical substances')
    if apiSubstance := apiRefComponentStore.findFirstComponent(name=name, labeling=labelling):
        substance = self._project._data2Obj.get(apiSubstance)
    else:
        from ccpn.core.Substance import _newSubstance
        from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking
        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                substance = _newSubstance(self.project, name=name, labelling=labelling)

    # NB - using substance._wrappedData.labelling because we need the API labelling value,
    # which is different for the default case
    obj = apiSample.newSampleComponent(name=name, labeling=substance._wrappedData.labeling,
                                       role=role,
                                       concentration=concentration,
                                       concentrationError=concentrationError,
                                       concentrationUnit=concentrationUnit, details=comment,
                                       purity=purity)

    result = self._project._data2Obj.get(obj)
    if result is None:
        raise RuntimeError('Unable to generate new SampleComponent item')

    # if substance already exists then don't flag for delete through the newObject decorator
    if apiExistingSubstances:
        return (result,)
    else:
        # need to notify that a substance has also been created
        return (result, substance)


#EJB 20181204: moved to Sample
# Sample.newSampleComponent = _newSampleComponent
# del _newSampleComponent

# Notifiers - to notify SampleComponent - SpectrumHit link:
className = Nmr.Experiment._metaclass.qualifiedName()
Project._apiNotifiers.append(
        ('_modifiedLink', {'classNames': ('SampleComponent', 'SpectrumHit')}, className, 'setSample'),
        )
className = ApiSample._metaclass.qualifiedName()
Project._apiNotifiers.extend(
        (('_modifiedLink', {'classNames': ('SampleComponent', 'SpectrumHit')}, className,
          'addNmrExperiment'),
         ('_modifiedLink', {'classNames': ('SampleComponent', 'SpectrumHit')}, className,
          'removeNmrExperiment'),
         ('_modifiedLink', {'classNames': ('SampleComponent', 'SpectrumHit')}, className,
          'setNmrExperiments'),
         )
        )
