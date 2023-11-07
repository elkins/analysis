"""
Export the project files to the CCPN Analysis V3 .ndf5 format
"""

exportingPath = '/Users/luca/Documents/NMR-Data/Relaxation/Fred_Musket/GB1/20230213_GB1_trosyETA/Trosy_ndf5/'
fileFormat = '.ndf5'
for sp in project.spectra:
    sp.toHdf5(f'{exportingPath}{sp.name}{fileFormat}')
