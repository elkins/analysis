"""

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
__dateModified__ = "$dateModified: 2024-09-05 14:00:08 +0100 (Thu, September 05, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2023-02-03 10:04:03 +0000 (Fri, February 03, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================




############################################################
#####################    User Settings      #######################
############################################################


## Some Graphics Settings
titlePdf  = 'Consistency Test'
windowTitle = f'CcpNmr V3 - {titlePdf}'
interactivePlot = True # True if you want the plot to popup as a new windows, to allow the zooming and panning of the figure.
lineColour='black'
theoreticalLineColour = 'blue'
lineErrorColour='red'
lineErrorLW = 0.1
lineErrorCapsize=0
lineErrorCapthick=0.05
fontTitleSize = 6
fontXSize = 4
fontYSize =  4
scatterSize = 5
scatterFontSize = 5
labelMajorSize=4
labelMinorSize=3
titleColor = 'blue'
hspace= 1
figureTitleFontSize = 10
plotLinewidth=0.5

# exporting to pdf: Default save to same location and name.pdf as this macro
#  alternatively, provide a full valid path
outputPath = None

############################################################
##################   End User Settings     ########################
############################################################

import numpy as np
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.macros.relaxation._macrosLib as macrosLib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
from ccpn.AnalysisDynamics.lib.modelFreeAnalysis.modelFree.src.io._inputDataLoader import Rates_Excel_DataLoader
from ccpn.framework.lib.experimentAnalysis.ExperimentConstants import N15gyromagneticRatio, HgyromagneticRatio
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, RobustScaler
import itertools

###################      start inline macro       #####################

## get the data
dataPath = '/Users/luca/Projects/AnalysisV3/src/python/ccpn/AnalysisDynamics/lib/modelFreeAnalysis/examples/gb1/inputs/GB1_rates.xlsx'


loader = Rates_Excel_DataLoader(dataPath)
dataDict = loader.loadAndGroupDataByFrequency()
sfs = list(dataDict.keys())

# for each Field we want calculate the J0
j0dict = {}
scalingFactor = 1e6
arrays = []
for sf, df in dataDict.items():
    R1 = df[sv.R1].values
    R2 = df[sv.R2].values
    NOE = df[sv.HETNOE].values
    R1_err = df[sv.R1_ERR].values
    R2_err = df[sv.R2_ERR].values
    NOE_err = df[sv.HETNOE_ERR].values
    wN = sdl.calculateOmegaN(sf, scalingFactor)
    csaN = -160 / scalingFactor
    C1 = sdl.calculate_c_factor(wN, csaN)
    D1 = sdl.calculate_d_factor()
    j0 = sdl.calculateJ0(NOE, R1, R2, D1, C1, N15gyromagneticRatio, HgyromagneticRatio)
    j0dict[sf] = j0
    arrays.append(j0*scalingFactor)

resCodes = df[sv.NMRRESIDUECODE]
resCodes = resCodes.astype(int)
resCodes = resCodes.values
arrayCount = len(arrays)
items = list(range(arrayCount))


# Stack the 1D arrays into a 2D array
data = np.vstack(arrays).T

# Standardize the data
scaler = StandardScaler()
dataStandardised = scaler.fit_transform(data)

# Perform PCA
pca = PCA(n_components=arrayCount)
principal_components = pca.fit_transform(dataStandardised)
reconstructed_data = pca.inverse_transform(principal_components)

# Calculate Q-scores
reconstruction_error = np.linalg.norm(dataStandardised - reconstructed_data, axis=1)
q_scores = reconstruction_error**2
q_scores_normalized = (q_scores - np.min(q_scores)) / (np.max(q_scores) - np.min(q_scores))

qscore_scaler = StandardScaler()
q_scores_standardized = qscore_scaler.fit_transform(q_scores.reshape(-1, 1))
q_scores_standardized = q_scores_standardized.flatten()

# Create a 2x2 subplot grid
fig, axs = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle('Data Consistency Analysis\n', fontsize=16)

pairs = list(itertools.combinations(items, 2))
xs = []
ys = []
for pair in pairs:
    ix, iy = pair
    x, y = arrays[ix], arrays[iy]
    xSF, ySF = sfs[ix], sfs[iy]
    xs.append(x)
    ys.append(y)
    axs[0, 0].scatter(x, y, label=f'{xSF} MHz vs {ySF} MHz', alpha=0.5, )# s=scatterSize)

    for i, txt in enumerate(resCodes):
            axs[0, 0].annotate(str(txt), (x[i], y[i]))

maxX = np.max(xs)
maxY = np.max(ys)

axs[0, 0].plot([0, maxX*2], [0, maxY*2], color='black', linestyle='--', linewidth=0.5)  # diagonal line. Syntax as for x and y in the range [0,1]
axs[0, 0].set_title('J0 data')
axs[0, 0].set_xlabel('Field 1')
axs[0, 0].set_ylabel('Field 2')
axs[0, 0].legend()

# ratios
for pair in pairs:
    ix, iy = pair
    x, y = arrays[ix], arrays[iy]
    xSF, ySF = sfs[ix], sfs[iy]
    ratios = y/x
    axs[0, 1].hist(ratios, bins='fd',  label=f'{ySF}/{xSF} MHz', alpha=0.5)     #bins = fd is Freedman-Diaconis Rule.
axs[0, 1].set_title('Ratio distribution (Freedman-Diaconis bins)')
axs[0, 1].legend()
axs[0, 1].margins(x=0.35, y=0.35)  # 35% margin on both axes

# Modelling
# PCA Component 1 vs Component 2
axs[1, 0].scatter(principal_components[:, 0], principal_components[:, 1], c='purple', alpha=0.5)
axs[1, 0].set_title('PCA')
axs[1, 0].set_xlabel('Component 1')
axs[1, 0].set_ylabel('Component 2')
axs[1, 0].margins(x=0.35, y=0.35)  # 35% margin on both axes
# labels
for i, txt in enumerate(resCodes):
    # axs[0, 0].annotate(str(txt), (x[i], y[i]))
    axs[1, 0].text(principal_components[i, 0], principal_components[i, 1], txt, )
axs[1, 0].axhline(0, color='black', linestyle='--', linewidth=0.5)
axs[1, 0].axvline(0, color='black', linestyle='--', linewidth=0.5)

# Q-score
axs[1, 1].plot(resCodes, q_scores_standardized, 'o', color='blue')
axs[1, 1].axhline(y=np.percentile(q_scores_standardized, 95), color='red', linestyle='--', linewidth=0.5,  label='95th percentile')
# axs[1, 1].plot(q_scores, 'o', color='blue')
# axs[1, 1].axhline(y=np.percentile(q_scores, 95), color='red', linestyle='--', label='95th percentile')
axs[1, 1].set_xlabel('Residue Code')
axs[1, 1].set_ylabel('Q-score (Standardised)')
axs[1, 1].set_title('Q-scores for PCA')
axs[1, 1].legend()

plt.tight_layout()
plt.show()



xs = []
ys = []
for pair in pairs:
    ix, iy = pair
    x, y = arrays[ix], arrays[iy]
    xSF, ySF = sfs[ix], sfs[iy]
    xs.append(x)
    ys.append(y)
    # Define the quantiles to compute
    quantile_probs = np.linspace(0, 1, len(y))
    # Compute the quantiles for each dataset
    data1_quantiles = np.percentile(x, quantile_probs * 100)
    data2_quantiles = np.percentile(y, quantile_probs * 100)
    plt.figure(figsize=(6, 6))
    plt.scatter(data1_quantiles, data2_quantiles, alpha=0.5)
    plt.plot([data1_quantiles.min(), data1_quantiles.max()], [data1_quantiles.min(), data1_quantiles.max()], 'r--')  # Diagonal reference line
    plt.xlabel(f'Quantiles of {xSF}')
    plt.ylabel(f'Quantiles of {ySF}')

    plt.title(f'Q-Q Plot of {xSF} vs {ySF}')
    for i, txt in enumerate(resCodes):
            plt.annotate(str(txt), (data1_quantiles[i], data2_quantiles[i]))

plt.show()
