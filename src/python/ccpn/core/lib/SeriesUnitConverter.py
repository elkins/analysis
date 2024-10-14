"""SpectrumGroup-related series unit converters.

This module provides tools for converting units to SI and was created exclusively for the (NMR) Series. Of course there are external packages for converting units:
Pint,SymPy, Astropy, etc.  but they all require customisation and wrappers to achieve what is needed for the Series,
 this explains why this module was created...

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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$Date: 2024-07-17 14:29:44 +0100 (Wed, July 17, 2024) $"
__dateModified__ = "$dateModified: 2024-10-14 17:20:01 +0100 (Mon, October 14, 2024) $"
__version__ = "$Revision: 3.2.9.alpha $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author:  Luca Mureddu $"
__date__ = "$Date: 2024-07-17 14:28:36 +0100 (Wed, July 17, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.Logging import getLogger
# from scipy.constants import kilo, milli, micro, nano, pico, femto, atto, centi, deci, tera, giga, mega
from ccpn.core.SpectrumGroup import SeriesTypes
from decimal import Decimal

# Constants
CONCENTRATION = 'Concentration'
TIME = 'Time'
TEMPERATURE = 'Temperature'
PRESSURE= 'Pressure'
pH = 'pH'
ARBITRARYUNIT = 'Arbitrary Unit'
NOTAPPLICABLE = 'Not Applicable'
UNDEFINED = 'Undefined'
UNITLESS = 'Unitless'
AU = 'A.U.'
OTHER = 'Other'
EQUIVALENT = 'Equivalent'
VOLUME = 'Volume'
MASS = 'Mass'
DISTANCE = 'Distance'
GENERIC = 'Generic'
FREQUENCY = 'Frequency'

PRIMARY_SERIES_CATEGORY = [CONCENTRATION, TIME, EQUIVALENT, ARBITRARYUNIT]
SECONDARY_SERIES_CATEGORY = [OTHER, TEMPERATURE, pH, PRESSURE,  DISTANCE, VOLUME, MASS, ]

# SI prefix multipliers
quetta = 1e30
ronna = 1e27
yotta = 1e24
zetta = 1e21
exa = 1e18
peta = 1e15
tera = 1e12
giga = 1e9
mega = 1e6
kilo = 1e3
hecto = 1e2
deka = 1e1
deci = 1e-1
centi = 1e-2
milli = 1e-3
micro = 1e-6
nano = 1e-9
pico = 1e-12
femto = 1e-15
atto = 1e-18
zepto = 1e-21
yocto = 1e-24
ronto = 1e-27
quecto = 1e-30

_microUnicode = '\u00B5'


conversionMultipliersTexts = {
    # ----------- Above  Base ---------- #
    'R' : 'Ronna%s (10^27)',
    'Y' : 'Yotta%s (10^24)',
    'Z' : 'Zetta%s (10^21)',
    'E' : 'Exa%s (10^18)',
    'P' : 'Peta%s (10^15)',
    'T' : 'Tera%s (10^12)',
    'G' : 'Giga%s (10^9)',
    'M' : 'Mega%s (10^6)',
    'k' : 'Kilo%s (10^3)',
    'h' : 'Hecto%s (10^2)',
    'da': 'Deka%s (10^1)',
    '': 'Base Unit%s (1)',
    # ----------- Below  Base ---------- #
    'd' : 'Deci%s (10^-1)',
    'c' : 'Centi%s (10^-2)',
    'm' : 'Milli%s (10^-3)',
    _microUnicode : 'Micro%s (10^-6)',
    'n' : 'Nano%s (10^-9)',
    'p' : 'Pico%s (10^-12)',
    'f' : 'Femto%s (10^-15)',
    'a' : 'Atto%s (10^-18)',
    'z' : 'Zepto%s (10^-21)',
    'y' : 'Yocto%s (10^-24)',
    'r' : 'Ronto%s (10^-27)',
    }


class _SI_Unit:

    SI_baseUnit = None #str, to be subclassed . e.g.: s for TimeUnit class
    SI_baseUnitWord = None #str, to be subclassed . e.g.: second for TimeUnit class

    quantity = None   #str, to be subclassed . e.g.: time, temperature etc
    ## ConversionMultipliers: These prefixes are used ONLY to build the various units based on the subclass SI_baseUnit.
    ## Some prefixes are more theoretical and not really of common usage. Defined just for completeness.
    conversionMultipliers = {
                                        'R': ronna,   # Ronna- (10^27)
                                        'Y': yotta,    # Yotta- (10^24)
                                        'Z': zetta,    # Zetta- (10^21)
                                        'E': exa,      # Exa- (10^18)
                                        'P': peta,     # Peta- (10^15)
                                        'T': tera,      # Tera- (10^12)
                                        'G': giga,     # Giga- (10^9)
                                        'M': mega,  # Mega- (10^6)
                                        'k': kilo,       # Kilo- (10^3)
                                        'h': hecto,   # Hecto- (10^2)
                                        'da': deka,  # Deka- (10^1),
                                        # ----------- Above  Base ---------- #
                                        '' : 1,         # Base unit # replaced with the SI BaseUnit, (except for Kg)
                                        # ----------- Below  Base ---------- #
                                        'd': deci,      # Deci- (10^-1)
                                        'c': centi,     # Centi- (10^-2)
                                        'm': milli,     # Milli- (10^-3)
                                        _microUnicode: micro,    # Micro- (10^-6)
                                        'n': nano,     # Nano- (10^-9)
                                        'p': pico,      # Pico- (10^-12)
                                        'f': femto,     # femto- (10^-15)
                                        'a': atto,       # atto- (10^-18)
                                        'z': zepto,    # zepto- (10^-21)
                                        'y': yocto,    # yocto- (10^-24)
                                        'r': ronto,     # ronto- (10^-27)
        }

    uiPrefixSelection = list(conversionMultipliers.keys()) # list of prefix units to display on the GUI.
    _allowedDataTypes = [SeriesTypes.FLOAT]


    def __init__(self, value, unit):
        self.value = value
        self.unit = unit
        self._updateConversionMultipliers()
        self.toSI()

    @staticmethod
    def getAllUnits(cls):
        """A list of all units for the quantity"""
        availableUnits = []
        for x, m in cls.conversionMultipliers.items():
            if cls.SI_baseUnit:
                u = f'{x}{cls.SI_baseUnit}'
                if m == 1:
                    u = cls.SI_baseUnit
                availableUnits.append(u)
        return availableUnits

    @property
    def unitsSelection(self):
        """ A list of units to be displayed in the GUI"""
        return [self.SI_baseUnit] + [f'{x}{self.SI_baseUnit}' for x in self.uiPrefixSelection]

    @property
    def unitsTipTextSelection(self):
        """ A list of tip texts for each prefix units to be displayed in the GUI"""
        prefixes = [prefix.rstrip(self.SI_baseUnit) for prefix in self.unitsSelection]
        tt = [f'''{conversionMultipliersTexts.get(prefix)%self.SI_baseUnitWord}'''
              if prefix != ''
              else f'''{self.SI_baseUnitWord}, SI base unit for {self.quantity}'''
              for prefix in prefixes
              ]
        return tt

    @property
    def SI_value(self):
        return self.toSI()

    def toSI(self):
        """

        :return: Float. Converted value to the SI base unit.
        Note. We use Decimal to ensure a precise result, avoiding the floating-point arithmetic issues inherent in using binary floating-point numbers.
        """
        if self.unit not in self.conversionMultipliers:
            raise ValueError(f"Unknown unit: {self.unit}. Cannot convert to {self.SI_baseUnit}")
        multiplier = self.conversionMultipliers[self.unit]
        result = Decimal(self.value) * Decimal(str(multiplier))
        return float(result)

    def _updateConversionMultipliers(self):
        updatedConversionMultipliers = {}
        if self.SI_baseUnit is not None:
            for prefix, multiplier in self.conversionMultipliers.items():
                updatedConversionMultipliers[f'{prefix}{self.SI_baseUnit}'] = multiplier
        self.conversionMultipliers = updatedConversionMultipliers

    def convertTo(self, targetUnit):
        """
        Convert between units of the same scale
        :param targetUnit: The desired unit
        :return:
        """
        if targetUnit not in self.conversionMultipliers:
            raise ValueError(f"Unknown target unit: {targetUnit}")
        currentMultiplier = self.conversionMultipliers[self.unit]
        targetMultiplier = self.conversionMultipliers[targetUnit]
        valueInSI = self.value * currentMultiplier
        convertedValue = valueInSI / targetMultiplier
        return convertedValue

    def __repr__(self):
        return f'{self.SI_value}{self.SI_baseUnit}'


class TimeUnit(_SI_Unit):
    SI_baseUnit = 's'
    SI_baseUnitWord = 'Second'
    quantity = TIME
    uiPrefixSelection = ['m', _microUnicode, 'n', 'p']

class ConcentrationUnit(_SI_Unit):
    """Molar Concentration. In SI unit is mol/m^3, commonly used as M (mol/L) """
    SI_baseUnit = 'M'
    SI_baseUnitWord = 'Molar'
    quantity = CONCENTRATION
    uiPrefixSelection = ['m', _microUnicode, 'n', 'p']

class MoleUnit(_SI_Unit):
    """ """
    SI_baseUnit = 'mol'
    SI_baseUnitWord = 'Mole'

    quantity = 'Substance Amount'
    uiPrefixSelection = ['m', _microUnicode, 'n', 'p']


class MassUnit(_SI_Unit):
    SI_baseUnit = 'kg'
    SI_baseUnitWord = 'Kilogram'

    quantity = MASS
    uiPrefixSelection = ['m', _microUnicode, 'n', ]

    def _updateConversionMultipliers(self):
        updatedConversionMultipliers = {}
        for prefix, multiplier in self.conversionMultipliers.items():
            updatedConversionMultipliers[f'{prefix}g'] = multiplier*milli
        self.conversionMultipliers = updatedConversionMultipliers

    @property
    def unitsSelection(self):
        """ A list of units to be displayed in the GUI. """
        return ['kg', 'g',]+[f'{x}g' for x in self.uiPrefixSelection]

    @property
    def unitsTipTextSelection(self):
        """ A list of tip texts for each prefix units to be displayed in the GUI"""
        prefixes = [prefix.rstrip('g') for prefix in self.unitsSelection]
        tts = []
        for prefix in prefixes:
            if prefix == 'k':
                txt =  f'''{self.SI_baseUnitWord}, SI base unit for {self.quantity}'''
                tts.append(txt)
            elif prefix == '':
                txt = f'''Gram'''
                tts.append(txt)
            else:
                txt =f'''{conversionMultipliersTexts.get(prefix) % 'gram'}'''
                tts.append(txt)
        return tts

class DistanceUnit(_SI_Unit):
    SI_baseUnit = 'm'
    SI_baseUnitWord = 'Metre'
    quantity = DISTANCE

    uiPrefixSelection = ['k', 'c', 'm', _microUnicode, 'n', ]

class FrequencyUnit(_SI_Unit):
    SI_baseUnit = 'hz'
    SI_baseUnitWord = 'hertz'
    quantity = FREQUENCY

    uiPrefixSelection = ['G', 'M', 'k']

# ---------------- Special cases -------------------- #

class VolumeUnit(_SI_Unit):
    """Technically not SI but accepted as SI. The SI is m^3"""
    SI_baseUnit = 'L'
    SI_baseUnitWord = 'Litre'
    quantity = VOLUME
    uiPrefixSelection = ['d', 'c', 'm', _microUnicode, 'n', 'p']

    @property
    def unitsTipTextSelection(self):
        """ A list of tip texts for each prefix units to be displayed in the GUI"""
        prefixes = [prefix.rstrip(self.SI_baseUnit) for prefix in self.unitsSelection]
        note = 'N.B.	Non-SI unit accepted for use with SI. Litre is a metric unit of volume.'
        tt = [f'''{conversionMultipliersTexts.get(prefix)%self.SI_baseUnitWord}. {note}'''
              if prefix != ''
              else f'''{self.SI_baseUnitWord}, Base unit for {self.quantity}. {note}'''
              for prefix in prefixes
              ]
        return tt

class TemperatureUnit(_SI_Unit):
    SI_baseUnit = 'K'
    quantity = TEMPERATURE
    uiPrefixSelection = [] # not allowed for Kelvin. Unlikely to be ever needed

    @property
    def unitsSelection(self):
        """ A list of units to be displayed in the GUI"""
        return [self.SI_baseUnit] + ['C', 'F'] # not K-related but other common Units easily convertable to Kelvin

    @property
    def unitsTipTextSelection(self):
        return ['Kelvin (SI)', 'Celsius (Non-SI)', 'Fahrenheit (Non-SI)']

    def toSI(self):
        if self.unit == 'C':
            return self.value + 273.15  # Celsius to Kelvin
        elif self.unit == 'F':
            return (self.value - 32) * 5/9 + 273.15  # Fahrenheit to Kelvin
        elif 'K' in self.unit:
            return super().toSI()
        else:
            raise ValueError(f"Unknown unit for Temperature: {self.unit}. Use C, F or K")

    def convertTo(self, targetUnit):
        if targetUnit not in self.conversionMultipliers:
            raise ValueError(f"Unknown target unit: {targetUnit}")

        # First, convert to SI (Kelvin)
        valueInSI = self.toSI()
        if targetUnit == 'C':
            convertedValue = valueInSI - 273.15  # Kelvin to Celsius
        elif targetUnit == 'F':
            convertedValue = (valueInSI - 273.15) * 9 / 5 + 32  # Kelvin to Fahrenheit
        elif 'K' in targetUnit:
            convertedValue = valueInSI
        else:
            raise ValueError(f"Unknown target unit for Temperature: {targetUnit}")

        return convertedValue

class EquivalentUnit(_SI_Unit):
    SI_baseUnit = 'Eq'
    SI_baseUnitWord = EQUIVALENT
    quantity = EQUIVALENT
    uiPrefixSelection = [] #no other prefix needed here

    @property
    def unitsTipTextSelection(self):
        """ A list of tip texts for each prefix units to be displayed in the GUI"""
        prefixes = [prefix.rstrip(self.SI_baseUnit) for prefix in self.unitsSelection]
        note = 'N.B. Non-SI unit. '
        tt = [f'''{conversionMultipliersTexts.get(prefix)%self.SI_baseUnitWord}. {note}'''
              if prefix != ''
              else f'''{self.SI_baseUnitWord}. {note}'''
              for prefix in prefixes
              ]
        return tt


class GenericUnit(_SI_Unit):
    SI_baseUnit = None
    SI_baseUnitWord = None
    quantity = GENERIC
    uiPrefixSelection = [] # there aren't SI prefix for this unit.
    _allowedDataTypes = [SeriesTypes.FLOAT, SeriesTypes.INTEGER, SeriesTypes.STRING] # all allowed, because no conversions are made in this Unit.

    @property
    def unitsSelection(self):
        """ A list of units to be displayed in the GUI"""
        return [ARBITRARYUNIT, UNITLESS]

    @property
    def unitsTipTextSelection(self):
        return [f'{x} (Non-SI)' for x in self.unitsSelection]

    def toSI(self):
        return self.value

    def _updateConversionMultipliers(self):
        self.conversionMultipliers = {}

    def convertTo(self, targetUnit):
        """
        Convert between units is not possible here
        """
        raise ValueError(f'Converting between units is not possible for this Unit')

    def __repr__(self):
        return f'{self.SI_value}{self.unit}'


SERIESUNITS = {
    TimeUnit.quantity: TimeUnit,
    ConcentrationUnit.quantity: ConcentrationUnit,
    EquivalentUnit.quantity: EquivalentUnit,
    GenericUnit.quantity: GenericUnit,
    TemperatureUnit.quantity: TemperatureUnit,
    DistanceUnit.quantity: DistanceUnit,
    VolumeUnit.quantity: VolumeUnit,
    MassUnit.quantity: MassUnit,
    MoleUnit.quantity: MoleUnit,
    FrequencyUnit.quantity:FrequencyUnit
    }

def getAllSeriesUnits():
    """Convenient function to retrieve all Series Units from the various classes as a dictionary quantity:units"""
    units4quantityDict = {}
    for quantity, unitClass in SERIESUNITS.items():
            units4quantityDict[quantity] = unitClass.getAllUnits(unitClass)
    return units4quantityDict

def findQuantitiesByUnit(unit:str):
    """
    Given a unit, find the relative quantities. Ideally should be unique, but not necessarily.
    :param unit: str. eg. ms
    :return: list. List of string. The quantities. e.g. [Time,]
    """
    found = []
    for quantity, units in getAllSeriesUnits().items():
        if unit in units:
            found.append(quantity)
    return found


if __name__ == '__main__':
    # time
    print('100ns is:',TimeUnit(100, 'ns'))
    # concentration
    print('5mM is:', ConcentrationUnit(5, 'mM'))
    # temperature
    print('25C is:', TemperatureUnit(25, 'C'))

    c = TemperatureUnit(256, 'F')
    b = c.convertTo('mK')
    print('25C is:', TemperatureUnit(25, 'C'))

    # Generic
    g = GenericUnit('100', AU)
    print('A generic unit of', g)

    # distance
    print('25cm is:', DistanceUnit(25, 'cm'))
    # Converting between scale units
    unit = DistanceUnit(100, 'm')
    print('Converting...')
    convertTo = 'km'
    converted_value = unit.convertTo(convertTo)
    print(f"{unit.value} {unit.unit} is {converted_value}{convertTo}")
    convertTo = 'mm'
    converted_value = unit.convertTo(convertTo)
    print(f"{unit.value} {unit.unit} is {converted_value}{convertTo}")


    #search a quantity by unit:
    quantities = findQuantitiesByUnit('ms')
    allQ = getAllSeriesUnits()
    print(f" ms is of quantity: {quantities}")
    print(f"allQ: {allQ}")

