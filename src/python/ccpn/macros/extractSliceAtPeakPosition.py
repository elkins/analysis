"""
Get the slice Data at a peak position and save it as a new spectrum per each dimension.

Select a peak, Run the macro.
"""

import numpy as np
from ccpn.core.lib.ContextManagers import undoBlockWithSideBar


peak = current.peak
spectrum = peak.spectrum

for dim in spectrum.dimensions:
    pointPositions = np.array(peak.pointPositions, dtype=int)
    data = spectrum.getSliceData(position=list(pointPositions), sliceDim=dim)
    isotopeCodes = spectrum.getByDimensions('isotopeCodes',dimensions=[dim])
    pointCounts = spectrum.getByDimensions('pointCounts', dimensions=[dim])
    dd = {}
    properties = ['spectralWidths', 'spectralWidthsHz', 'spectrometerFrequencies', 'referencePoints', 'referenceValues']
    for p in properties:
        dd[p] = spectrum.getByDimensions(p, [dim])
    with undoBlockWithSideBar():
        # set everything as a single undo-operation
        sp = project.newEmptySpectrum(name=f'{spectrum.name}-slice-{dim}',isotopeCodes=isotopeCodes, pointCounts=pointCounts, **dd)
        sp.noiseLevel = spectrum.noiseLevel
        sp.setBuffering(True)
        sp.setSliceData(data, )
