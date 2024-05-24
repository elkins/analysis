"""
This module contains all definitions used in the various SeriesAnalysis modules.

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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-05-24 16:22:29 +0100 (Fri, May 24, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================


############################################################################################
##  SeriesDataTable common definitions. Used in I/O tables columns and throughtout modules
############################################################################################

NMRCHAINNAME     = 'nmrChainName'           # -> str   | nmrChain Name
NMRRESIDUECODE   = 'nmrResidueCode'         # -> str   | nmrResidue Sequence Code (e.g.: '1', '1B')
NMRRESIDUETYPE   = 'nmrResidueType'         # -> str   | nmrResidue Type (e.g.: 'ALA')
NMRATOMNAME      = 'nmrAtomName'            # -> str   | nmrAtom name (e.g.: 'Hn')
NMRATOMNAMES     = f'{NMRATOMNAME}s'        # -> str   | nmrAtom names comma separated (e.g.: 'Hn, Nh'). Used in OutPut datarames instead of ATOMNAME

NMRRESIDUECODETYPE = f'{NMRRESIDUECODE}-{NMRRESIDUETYPE}'  # -> str   | nmrResidue Sequence Code + Type (e.g.: '1-ALA')
EXPERIMENT = 'experiment' # -> str, e.g.: T1, T2, HetNoe, 'Cest', etc
_ROW_UID         = 'ROW_UID'             # -> str   | Internal. Unique Identifier (e.g.: randomly generated 6 letters UUID)
INDEX           = 'Index'                   # -> int   | incremental serial
VALUE            = 'Value'               # -> str   | The column header  prefix in a SeriesTable. Used to store data after the CONSTANT_TABLE_COLUMNS
TIME             = 'Time'                # -> str   | A general prefix in a SeriesTable.

NA = 'Not Applicable'
SEP              =  '_'   # the prefix-name-suffix global separator. E.g., used in Value columns: Value_height_at_0
VALUE_           = f'{VALUE}{SEP}'
TIME_            = f'{TIME}{SEP}'
EXCLUDED         = 'excluded'
EXCLUDED_        = f'{EXCLUDED}{SEP}'
_ERR             = '_err'
ERROR            = 'Error'
VALUE_ERR        = f'{VALUE}{_ERR}'
## CSM Fitting Variables
KD               = 'Kd'
BMAX             = 'BMax'
T                = 'T'
T_ERR            = f'{T}{_ERR}'
KD_ERR           = f'{KD}{_ERR}'
BMAX_ERR         = f'{BMAX}{_ERR}'
HillSlope        = 'Hs'
HillSlope_ERR    = f'{HillSlope}{_ERR}'
DIMENSION        = 'dimension'
ISOTOPECODE      = 'isotopeCode'
CLUSTERID        = 'clusterId'
COLLECTIONID     = 'collectionId'
RELDISPLACEMENT  = 'Relative Displacement'
SERIES_STEP_X    = 'series_Step_X'
SERIES_STEP_X_label    = 'series_Step_X_label'
SERIES_STEP_Y    = 'series_Step_Y'
SERIESUNIT       = 'seriesUnit'
PEAKPID          = 'peakPid'
SPECTRUMPID      = 'spectrumPid'
NMRATOMPID       = 'nmrAtomPid'
NMRRESIDUEPID    = 'nmrResiduePid'
COLLECTIONPID    = 'collectionPid'
PID              = 'pid'
ASSIGNEDNMRATOMS = 'assignedNmrAtoms'


EXCLUDED_PEAKPID        = f'{EXCLUDED_}{PEAKPID}'
EXCLUDED_SPECTRUMPID    = f'{EXCLUDED_}{SPECTRUMPID}'
EXCLUDED_NMRATOMPID     = f'{EXCLUDED_}{NMRATOMPID}'
EXCLUDED_COLLECTIONPID  = f'{EXCLUDED_}{COLLECTIONPID}'
EXCLUDED_NMRRESIDUEPID  = f'{EXCLUDED_}{NMRRESIDUEPID}'

# fitting output Stat variables
MINIMISER        = 'minimiser'
RSQR               = 'Rsqr'
CHISQR           = 'chisqr'
REDCHI           = 'redchi'  # DO NOT CHANGE! Hardcoded in dependencies Model
AIC              = 'aic' # DO NOT CHANGE! Hardcoded in dependencies Model
BIC              = 'bic' # DO NOT CHANGE! Hardcoded in dependencies Model
AICc              = 'aicc'
BICc              = 'bicc'


RESIDUAL = 'residual'
MINIMISER_METHOD = 'Method'
MINIMISER_MODEL  = 'Model'
MINIMISER_OBJ  = '_minimiserObj'

## Peak properties. Used to get nmrAtom assigned-peak by dimension and build tables.
_POSITION = 'position'
_POINTPOSITION = 'pointPosition'
_PPMPOSITION = 'ppmPosition'
_LINEWIDTH = 'lineWidth'
HEIGHT = 'height'
VOLUME = 'volume'
POSITIONS = f'{_POSITION}s'
LINEWIDTHS = f'{_LINEWIDTH}s'
POINTPOSITIONS = f'{_POINTPOSITION}s'
PPMPOSITIONS = f'{_PPMPOSITION}s'
_LINEWIDTHS     = LINEWIDTHS
_HEIGHT         =  HEIGHT
_VOLUME         =  VOLUME
_SNR            = 'signalToNoiseRatio'

## ATOM Names
OTHER = 'Other'
H = 'H'
N = 'N'
C = 'C'
_H = H
_N = N
_C = C
_OTHER = OTHER

## IsotopeCode Names

ISOTOPECODES = 'isotopeCodes'
_1H  = '1H'
_15N = '15N'
_13C = '13C'



## Relaxation  Fitting Variables
AMPLITUDE = 'amplitude'
DECAY = 'decay'
AMPLITUDE_ERR = f'{AMPLITUDE}{_ERR}'
DECAY_ERR = f'{DECAY}{_ERR}'

RATE = 'rate'
RATE_ERR = f'{RATE}{_ERR}'
PLATEAU = 'plateau'
PLATEAU_ERR = f'{PLATEAU}{_ERR}'

HETNOE = 'HetNoe'
SAT = 'sat'
UNSAT = 'unSat'
_0 = 0
_1 = 1
UNSAT_OPTIONS = [  int(_0),      # key options to set from a spectrumGroup
                                    float(_0),
                                    str(_0),
                                    UNSAT,
                                    'unsaturated',
                                    'nosat',
                                    'noNOE',
                                    f'no{HETNOE}'
                                  ]
SAT_OPTIONS = [  int(_1),      # key options to set from a spectrumGroup
                                float(_1),
                                str(_1),
                                SAT,
                                'saturated',
                                 'NOE',
                                 HETNOE,
                                ]
CROSSCORRELRATIO = 'Cross-CorrelationRatio'
INPHASE = 'in-phase'
ANTIPHASE = 'anti-phase'

RX = 'R(x)'
R1 = 'R1'
R2 = 'R2'
R2R1 = 'R2/R1'
R2R1_ERR = f'{R2R1}{_ERR}'
R1R2 = 'R1*R2'
R1R2_ERR = f'{R1R2}{_ERR}'
REXVIATROSY = 'RexViaTrosy'
RSDM = 'Reduced_Spectral_Density_Mapping'
J0 = 'J0'
JwX = 'JwX'
JwH = 'JwH'
J0_ERR = f'{J0}{_ERR}'
JwX_ERR = f'{JwX}{_ERR}'
JwH_ERR = f'{JwH}{_ERR}'
S2 = 'S2'
S2s = 'S2s'
S2f = 'S2f'
Ts = 'Ts'
Tf = 'Tf'
Ti = 'Ti'
Ci = 'Ci'
W = 'w'
TE = 'TE'
REX = 'REX'
TC = 'TC'
S2_ERR = f'{S2}{_ERR}'
TE_ERR = f'{TE}{_ERR}'
REX_ERR = f'{REX}{_ERR}'
TC_ERR = f'{TC}{_ERR}'
ETAXY = 'ETAxy'
ETAZ = 'ETAz'
ETAXY_ERR = f'{ETAXY}{_ERR}'
ETAZ_ERR = f'{ETAZ}{_ERR}'
ISOTROPIC = 'Isotropic'
ANISOTROPIC = 'Anisotropic'
AXIALLY_SYMMETRIC = 'Axially-Symmetric'
DIFFUSION = 'Diffusion'
LIPARISZABO = 'Lipari-Szabo'
LIPARISZABO_Original = 'Lipari-Szabo Original'
LIPARISZABO_Extended = 'Lipari-Szabo Extended'

PROLATE = 'Prolate'
OBLATE = 'Oblate'

FLAG = 'Flag'
SERIAL = 'Serial'
SF = 'SF' # spectrometer frequency in Mhz
CONSTANT_STATS_OUTPUT_TABLE_COLUMNS = [MINIMISER_METHOD, MINIMISER_MODEL, RSQR, CHISQR, REDCHI, AIC, BIC]
SpectrumPropertiesHeaders = [DIMENSION, ISOTOPECODE, SERIES_STEP_X, SERIESUNIT, EXPERIMENT]
PeakPropertiesHeaders = [_PPMPOSITION, _HEIGHT, _LINEWIDTH, _VOLUME]
AssignmentPropertiesHeaders = [NMRCHAINNAME, NMRRESIDUECODE, NMRRESIDUETYPE, NMRATOMNAME]
GROUPBYAssignmentHeaders = [NMRCHAINNAME, NMRRESIDUECODE, NMRRESIDUETYPE]
PidHeaders = [COLLECTIONID, COLLECTIONPID, SPECTRUMPID, PEAKPID, NMRATOMPID, NMRRESIDUEPID]

MERGINGHEADERS = [COLLECTIONID, COLLECTIONPID, NMRCHAINNAME, NMRRESIDUECODE, NMRRESIDUETYPE]
EXCLUDED_OBJECTS = [EXCLUDED_COLLECTIONPID, EXCLUDED_NMRRESIDUEPID, EXCLUDED_NMRATOMPID, EXCLUDED_SPECTRUMPID]

############################################################################################
### Used in SeriesFrame tables ABCs
############################################################################################
DATATABLETYPE               = 'DATATABLETYPE'
SERIESANALYSISDATATABLE     = 'SERIESANALYSISDATATABLE'
SERIESANALYSISOUTPUTDATA    = 'SeriesAnalysisResultsData'
SERIESANALYSISINPUTDATA     = 'SeriesAnalysisInputData'
RELAXATION_OUTPUT_FRAME     = 'RelaxationOutputFrame'
HetNoe_OUTPUT_FRAME         = 'HetNoeOutputFrame'
CROSSCORRELRATIO_OUTPUT_FRAME         = 'Cross-CorrelationRatesOutputFrame'
REXVIATROSY_OUTPUT_FRAME         = 'RexViaTrosyOutputFrame'

R2R1_OUTPUT_FRAME         = 'R2R1OutputFrame'
RSDM_OUTPUT_FRAME         = 'RSDMOutputFrame'
CSM_OUTPUT_FRAME            = 'CSMOutputFrame'
SERIESFRAMETYPE             = 'SERIESFRAMETYPE'
_assignmentHeaders          = '_assignmentHeaders'
_valuesHeaders              = '_valuesHeaders'
_peakPidHeaders             = '_peakPidHeaders'
_isSeriesAscending = '_isSeriesAscending'
_SpectrumPropertiesHeaders = 'spectrumPropertiesHeaders'

OUTPUT_SERIESFRAME_TYPES = [
                    CSM_OUTPUT_FRAME,
                    RELAXATION_OUTPUT_FRAME,
                    ]

############################################################################################
### Used in SeriesAnalyisBC
############################################################################################
ChemicalShiftMappingAnalysis = 'ChemicalShiftMappingAnalysis'  # used in SeriesName for the ChemicalShiftMappingAnalysis
RelaxationAnalysis = 'RelaxationAnalysis'                      # used in SeriesName for the RelaxationAnalysis
JCouplingAnalysis = 'JCouplingAnalysis'
RDCAnalysis = 'RDCAnalysis'
PCSAnalysis = 'PseudoContactShiftAnalysis'
PREAnalysis = 'ParamagneticRelaxationEnhancementAnalysis'

## Series Units

STD = 'Std'
MEAN = 'Mean'
MEDIAN = 'Median'
VARIANCE = 'Variance'
MAD = 'MAD (Median Absolute Deviation)'
AAD = 'AAD (Average Absolute Deviation)'
TRIMMED_MEAN = 'Trimmed Mean'

CALCULATION_MODEL = 'calculationModel'
### CSM Calculation Models
## Alpha Factors Definitions used in ChemicalShiftAnalysis DeltaDeltas
uALPHA = '\u03B1'
uDELTA = '\u0394'
uDelta = '\u03B4'
DELTA = 'Delta'
DELTA_DELTA = f'{DELTA*2}'
DELTA_DELTA_ERR = f'{DELTA_DELTA}{_ERR}'
EUCLIDEAN_DISTANCE = 'Euclidean Distance'
TITRATION = 'Titration'
DEFAULT_H_ALPHAFACTOR = 1
DEFAULT_N_ALPHAFACTOR = 0.142
DEFAULT_C_ALPHAFACTOR = 0.25
DEFAULT_OTHER_ALPHAFACTOR = 1
DEFAULT_ALPHA_FACTORS = dict((
                            (_1H, DEFAULT_H_ALPHAFACTOR),
                            (_15N, DEFAULT_N_ALPHAFACTOR),
                            (_13C, DEFAULT_C_ALPHAFACTOR),
                            (_OTHER, DEFAULT_OTHER_ALPHAFACTOR)
                            ))
DEFAULT_FILTERING_ATOMS = (_H, _N)
DEFAULT_EXCLUDED_RESIDUES = ['PRO']

FILTERINGATOMS  = 'FilteringAtoms'
ALPHAFACTORS    = 'AlphaFactors'

ARGA = 'argA'
ARGB = 'argB'
ARGA_VALUE_ERR = f'{ARGA}{_ERR}'
ARGB_VALUE_ERR = f'{ARGB}{_ERR}'

### Relaxation Calculation Models
HETNOE_VALUE = f'{HETNOE}'
HETNOE_VALUE_ERR = f'{HETNOE_VALUE}{_ERR}'
HETNOE_ERR = HETNOE_VALUE_ERR

CROSSRELAXRATIO_VALUE = f'{CROSSCORRELRATIO}'
CROSSRELAXRATIO_VALUE_ERR = f'{CROSSCORRELRATIO}{_ERR}'

R_VALUE = f'{RX}'
R_VALUE_ERR = f'{RX}{_ERR}'

R1_ERR = f'{R1}{_ERR}'
R2_ERR = f'{R2}{_ERR}'

## Fitting models
FITTING_MODEL = 'fittingModel'
MODEL_NAME = 'modelName'
FITTING_MODELS = f'{FITTING_MODEL}s'
OVERRIDE_OUTPUT_DATATABLE = 'overrideOutputDataTables'
OUTPUT_DATATABLE_NAME = 'outputDataTableName'
BLANKMODELNAME = 'Blank'
ETAS_CALCULATION_MODEL = 'ETAs Ratio'
## Receptor Binding Models
ONE_SITE_BINDING_MODEL = 'One-Site (Specific) Binding'
ONE_SITE_TOTAL_BINDING_MODEL = 'One-Site (Total) Binding'
TWO_BINDING_SITE_MODEL = 'Two Site Binding'
ONE_SITE_BINDING_ALLOSTERIC_MODEL = 'One Site with Allosteric Binding'
FRACTION_BINDING_MODEL = 'Fraction Binding'
FRACTION_BINDING_WITHTARGETMODEL = 'Fraction Binding with [Target]'
COOPERATIVITY_BINDING_MODEL = 'Cooperativity Binding'
FMNOYERROR = 'Fitting Model not implemented yet'
#### residues names
EXCLUDEDRESIDUETYPES = 'ExcludedResidueTypes'

LEASTSQ = 'leastsq'

InversionRecovery = 'InversionRecovery'
ExponentialDecay = 'ExponentialDecay'
OnePhaseDecay = 'OnePhaseDecay'
OnePhaseDecayWithPlateau = 'OnePhaseDecayWithPlateau'
USERDEFINEDEXPERIMENT = 'User-Defined'
NONE = 'None'
T1 = 'T1'
T2 = 'T2'
CEST = 'CEST'
TROSY_XYA = 'TROSY_ETAxyA'
TROSY_XYB = 'TROSY_ETAxyB'
TROSY_Z = 'TROSY_ETAz'

EXPERIMENTS  = [USERDEFINEDEXPERIMENT, T1, T2, HETNOE]

## Warnings
UNDER_DEVELOPMENT_WARNING = f'''This functionality is currently under active development. Use it at your own risk.'''
NIY_WARNING = f'''This functionality has not been implemented yet.'''
# Errors
OMIT_MODE = 'omit'
RAISE_MODE = 'raise'


MINIMISER_METHODS = {
    'leastsq': 'Levenberg-Marquardt (default)',
    'powell': 'Powell',
    'cg': 'Conjugate-Gradient',
    'least_squares': 'Least-Squares minimization, using Trust Region Reflective method',
    'emcee': 'Maximum likelihood via Monte-Carlo Markov Chain',
    'differential_evolution': 'differential evolution',
    'brute': 'brute force method',
    'basinhopping': 'basinhopping',
    'ampgo': 'Adaptive Memory Programming for Global Optimization',
    'nelder': 'Nelder-Mead',
    'lbfgsb': 'L-BFGS-B',
    'newton': 'Newton-CG',
    'cobyla': 'Cobyla',
    'bfgs': 'BFGS',
    'tnc': 'Truncated Newton',
    'trust-ncg': 'Newton-CG trust-region',
    'trust-exact': 'nearly exact trust-region',
    'trust-krylov': 'Newton GLTR trust-region',
    'trust-constr': 'trust-region for constrained optimization',
    'dogleg': 'Dog-leg trust-region',
    'slsqp': 'Sequential Linear Squares Programming',
    'shgo': 'Simplicial Homology Global Optimization',
    'dual_annealing': 'Dual Annealing optimization',
    }
