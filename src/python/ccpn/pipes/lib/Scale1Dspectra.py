import numpy as np


def resetSpectraScale(spectra, value = 1):
    for sp in spectra:
        sp.scale = value


def getAutoScalingFactor1D(controlSpectrum, targetSpectrum, controlSpectrumWeight=1.1):
    """
    #Screening-specific.
    This factor will scale the spectra in a way  to have the Control-Spectrum (e.g. without a protein-target)
    with higher intensities than a Target-Spectrum (recorded with a protein-target).
    :param controlSpectrum: Spectrum object
    :param targetSpectrum: Spectrum object
    :param controlSpectrumWeight: a weighting factor for the control spectrum intensities. Default 1.1 (arbitrary)
    :return: float. a scaling factor from the intensities std-ratio
    The scaling factor is defined as the ratio of the standard deviation of intensities in the Target Spectrum to that of the weighted Control Spectrum.
    Latex:  \text{factor} = \frac{\sigma{I}_{target}}{\sigma{I}_{control} \cdot C_{weight}}

    """
    controlSpectrumWeight = controlSpectrumWeight if controlSpectrumWeight !=0 else 1
    factor = np.std(targetSpectrum.intensities) / (np.std(controlSpectrum.intensities) * controlSpectrumWeight)
    return float(factor)


def scaleSpectraByStandardScaler(spectra):
    """ Scale spectra busing the StandardScaler from sklearn.
    Standardise features by removing the mean and scaling to unit variance.
    See docs https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html
    """

    from sklearn.preprocessing import StandardScaler

    for spectrum in spectra:
        intensities = spectrum.intensities
        ## reshape to a 2D as required
        intensities_nd = intensities.reshape(len(intensities), 1)
        ## init the scaler
        scaler = StandardScaler()
        scaler = scaler.fit(intensities_nd, )
        ## create the new scaled curve
        normalizedRef = scaler.transform(intensities_nd)
        z = normalizedRef.flatten()
        ## scaling value
        if scaler.scale_ and len(scaler.scale_)>0:
            scalingValue = scaler.scale_[0]
            ## apply to the spectrum object
            if scalingValue != 0:
                spectrum.scale = 1 / scalingValue



def scaleSpectraByStd(spectra, pts = 200):
    '''
    Scale 1D spectra intensities by the mean of stds for the first selected pts
    so that all spectra have (roughly the same baseline noise)
    '''
    if len(spectra)<1: return
    stds = []
    resetSpectraScale(spectra,1)
    ys = [sp.intensities for sp in spectra]
    for y in ys:
        y0_m = np.std(y[:pts])
        stds.append(y0_m)

    targetValue = np.mean(stds)
    if targetValue == 0 : return
    scaleValues = targetValue/stds
    for sp, y, v in zip(spectra, ys, scaleValues):
        if v == 0:
            v = 1
            print('Not possible to scale %s' %sp.name)
        sp.scale = float(v)
        # sp.intensities = sp.intensities * v     #in case don't want use the scale property


def scaleSpectraByRegion(spectra, limits, engine = 'mean', resetScale=True):
    '''
    Scale 1D spectra intensities by a region of interest.
    eg a region between a peak, so that the spectra are scaled relative to that peak.
    engine =    'mean':  heights will be the median of the two
                'min' :  heights will be relative to the lower
                'max' :  heights will be relative to the highest

    resetScale: always start with a scale of 1 (original spectrum data)
    limits = list of 1d regions in ppm, eg [1,3]
    '''
    availableEngines = ['mean', 'min', 'max', 'std']
    if engine not in availableEngines:
        engine = availableEngines[0]
    if len(spectra)<1: return
    point1, point2 = np.max(limits), np.min(limits)
    ys = []
    for sp in spectra:
        # if resetScale: sp.scale = 1  # reset first
        xRef, yRef = sp.positions, sp.intensities
        x_filtered = np.where((xRef <= point1) & (xRef >= point2))
        y_filtered = yRef[x_filtered]
        ys.append(y_filtered)

    maxs = []
    for y in ys:
            y0_m = np.max(abs(y)) #so will work also for negative regions
            maxs.append(y0_m)

    targetValue = getattr(np, engine)(maxs)
    if targetValue == 0 : return
    scaleValues = targetValue/maxs
    for sp, y, v in zip(spectra, ys, scaleValues):
        sp.scale = float(v)
        # sp.intensities = sp.intensities * v     #in case don't want use the scale property

