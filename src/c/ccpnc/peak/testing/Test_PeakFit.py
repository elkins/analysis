"""Module Documentation here

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
__dateModified__ = "$dateModified: 2024-10-08 20:19:17 +0100 (Tue, October 08, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from operator import itemgetter
import numpy as np
import sys
# from ccpnmodel.ccpncore.testing.CoreTesting import CoreTesting
# from ccpnmodel.ccpncore.lib.ccp.nmr.Nmr import DataSource
from ccpnc.peak import Peak

REGIONOFFSET = 4
SETNOISE = 0.001


class PeakFitTest():
    # Path of project to load (None for new project
    projectPath = 'CcpnCourse1a'

    def Test_PeakFit(self, *args, **kwds):
        spectrum = self.nmrProject.findFirstExperiment(name='HSQC').findFirstDataSource()
        data = spectrum.getPlaneData()
        print('data.shape = %s' % (data.shape,))

        haveLow = 0
        haveHigh = 1
        low = 0  # arbitrary
        high = 1.0e8
        buffer = [1, 1]
        nonadjacent = 0
        dropFactor = 0.0
        minLinewidth = [0.0, 0.0]

        peakPoints = Peak.findPeaks(data, haveLow, haveHigh, low, high, buffer, nonadjacent, dropFactor, minLinewidth, [], [], [])
        print('number of peaks found = %d' % len(peakPoints))

        peakPoints.sort(key=itemgetter(1), reverse=True)

        position, height = peakPoints[0]
        print('position of highest peak = %s, height = %s' % (position, height))

        numDim = len(position)
        peakArray = np.array(position, dtype='float32')
        firstArray = peakArray - 2
        lastArray = peakArray + 3
        peakArray = peakArray.reshape((1, numDim))
        firstArray = firstArray.astype('int32')
        lastArray = lastArray.astype('int32')
        regionArray = np.array((firstArray, lastArray))

        method = 0  # Gaussian
        result = Peak.fitPeaks(data, regionArray, peakArray, method)
        intensity, center, linewidth = result[0]
        print('Gaussian fit: intensity = %s, center = %s, linewidth = %s' % (intensity, center, linewidth))

        method = 1  # Lorentzian
        result = Peak.fitPeaks(data, regionArray, peakArray, method)
        intensity, center, linewidth = result[0]
        print('Lorentzian fit: intensity = %s, center = %s, linewidth = %s' % (intensity, center, linewidth))


if __name__ == '__main__':

    # Ed testing the gauss function

    import matplotlib


    matplotlib.use('Qt5Agg')
    from mpl_toolkits import mplot3d
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm


    res = 99
    span = ((-(res // 2), res // 2), (-(res // 2), res // 2))
    plotMax = 20
    plotRange = ((0, plotMax), (0, plotMax))

    # testPeaks = ((1.0, 2.0, 0.0, 0.0, 1.0),
    #              (1.0, 2.4, 2.0, 10.0, 1.7),
    #              (2.5, 1.7, 10.0, 1.0, 1.7),
    #              (4.2, 1.8, 7.0, 7.0, 1.1)
    #              )

    # testPeaks = ((3.5, 4.0, 0.0, 0.0, 1.0),
    #              (3.0, 2.5, 2.0, 10.0, 2.0),
    #              (2.5, 3.0, 10.0, 1.0, 2.0),
    #              # (4.2, 1.8, 7.0, 7.0, 1.1)
    #              )

    # distinct peaks - discrete
    testPeaks = ((1.0, 1.0, 7.0, 7.0, 1.0),
                 (1.0, 1.0, 13.0, 13.0, 1.25),
                 )

    # # distinct peaks - overlapped
    # testPeaks = ((2.5, 2.5, 7.0, 7.0, 1.0),
    #              (2.5, 2.5, 13.0, 13.0, 1.25),
    #              )
    #
    # # merged peaks - only single maxima
    # testPeaks = ((2.5, 2.5, 8.0, 8.0, 1.0),
    #              (2.5, 2.5, 12.0, 12.0, 1.5),
    #              )

    # h = 1.0
    # x0 = 2.245
    # y0 = -1.2357
    # sigmax = 1.0
    # sigmay = 1.0

    haveLow = 0
    haveHigh = 1
    low = 0  # arbitrary
    high = 0.001
    buffer = [1, 1]
    nonadjacent = 1
    dropFactor = 0.01
    minLinewidth = [0.0, 0.0]

    def sigma2fwhm(sigma):
        return sigma * np.sqrt(8 * np.log(2))


    def fwhm2sigma(fwhm):
        return fwhm / np.sqrt(8 * np.log(2))


    def _gaussFWHM(ii, jj, sigmax=1.0, sigmay=1.0, mx=0.0, my=0.0, h=1.0):
        """Calculate the normal(gaussian) distribution in Full-width-Half-Maximum.

        (https://arthursonzogni.com/Diagon/#math)

                    ⎛              ⎛       2          2⎞⎞
                    ⎜              ⎜⎛  x  ⎞    ⎛  y  ⎞ ⎟⎟
            h ⋅ exp ⎜-4 ⋅ log(2) ⋅ ⎜⎜─────⎟  + ⎜─────⎟ ⎟⎟
                    ⎜              ⎜⎜fwhm ⎟    ⎜fwhm ⎟ ⎟⎟
                    ⎝              ⎝⎝    x⎠    ⎝    y⎠ ⎠⎠

        """
        pos = [ii - mx, jj - my]

        fwhmx = sigma2fwhm(sigmax)
        fwhmy = sigma2fwhm(sigmay)

        return h * np.exp(-4*np.log(2) * ((pos[0] / fwhmx)**2 + (pos[1] / fwhmy)**2))

    def _gaussSigma(ii, jj, sigmax=1.0, sigmay=1.0, mx=0.0, my=0.0, h=1.0):
        """Calculate the normal(gaussian) distribution.

                ⎛     2       2⎞
                ⎜ ⎛ x⎞    ⎛ y⎞ ⎟
            exp ⎜-⎜──⎟  - ⎜──⎟ ⎟
                ⎜ ⎜ς ⎟    ⎜ς ⎟ ⎟
                ⎝ ⎝ x⎠    ⎝ y⎠ ⎠

            ⎛            h           ⎞
            ⎜────────────────────────⎟
            ⎜    ____________________⎟
            ⎜   ╱    ⎛ 2⎞            ⎟
            ⎜  ╱ 4 ⋅ ⎝π ⎠ ⋅ ⎛ς  ⋅ ς ⎞⎟
            ⎝╲╱             ⎝ x    y⎠⎠

        """
        pos = [ii - mx, jj - my]

        # ex = np.exp(-(pos[0] ** 2 / sigmax ** 2) - (pos[1] ** 2 / sigmay ** 2))
        ex = np.exp(-(pos[0] / sigmax) ** 2 - (pos[1] / sigmay) ** 2)
        return (h / np.sqrt(4 * (np.pi ** 2) * (sigmax * sigmay))) * ex


    def make_gauss(N, sigma, mu, height):
        k = height     # / (sigma * np.sqrt(2 * np.pi))
        s = -1.0 / (2 * sigma * sigma)

        return k * np.exp(s * (N - mu) * (N - mu))

    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    # print('SHOULD BE:', res, h, x0, y0, sigma2fwhm(sigmax), sigma2fwhm(sigmay))

    # xx = np.linspace(*span[0], res)
    # yy = np.linspace(*span[1], res)
    xx = np.linspace(*plotRange[0], res)
    yy = np.linspace(*plotRange[1], res)
    xm, ym = np.meshgrid(xx, yy)

    dataArray = np.zeros(shape=(res, res), dtype=np.float32)
    dataArrayCheck = np.zeros(shape=(res, res), dtype=np.float32)
    for thisPeak in testPeaks:

        sigmax, sigmay, mx, my, h = thisPeak

        print('>>>testPeak', sigmax, sigmay, mx, my, h)

        peakArrayFWHM = np.array(_gaussFWHM(xm, ym, sigmax=sigmax, sigmay=sigmay, mx=mx, my=my, h=h), dtype=np.float32)
        dataArray = np.add(dataArray, peakArrayFWHM)

        peakArraySigma = np.array(_gaussSigma(xm, ym, sigmax=sigmax, sigmay=sigmay, mx=mx, my=my, h=h), dtype=np.float32)
        dataArraySigma = np.add(dataArray, peakArraySigma)

    peakPoints = Peak.findPeaks(dataArray, haveLow, haveHigh, low, high, buffer, nonadjacent, dropFactor, minLinewidth, [], [], [])

    # OR use the data given
    originalPeakPoints = [((int(pp[2] * res/plotMax), int(pp[3]*res/plotMax)), pp[4]) for pp in testPeaks]

    print('number of peaks found = %d' % len(peakPoints))
    peakPoints.sort(key=itemgetter(1), reverse=True)
    for peak in peakPoints:
        position, height = peak
        print('position of peak = %s, height = %s' % (position, height))

    # make a plot
    # okay, make  2d plot of xxSig, the gauss curve between +-3 sigma

    # testing the calculation of the area under a gaussian curve
    # convert the sigma into a FWHM and plot between volumeIntegralLimits * FWHM
    sigmax = 1.0
    mx = 0.0
    integralLimit = 4.0 # plot to a distance of 4 sigma
    numPoints=45

    thisFWHM = sigma2fwhm(sigmax)
    # height, (l1, l2) = (-40069.83984375, (18.269018037244678 / thisFWHM, 2.781543880701065 / thisFWHM))
    # height, (l1, l2) = (1.0, (2.0 / thisFWHM, 2.0 / thisFWHM))
    height, (l1, l2) = (1.0, (1.0, 1.0)) # should give area 2pi
    # height, (l1, l2) = (2.0, (2.5, 2.7)) # should give area 2pi * height * l1 * l2
    # height, (l1, l2) = (1317701.0, (21.94079803302884 / thisFWHM, 11.697283014655113 / thisFWHM))
    # estimated 2305274.18593

    limX = l1 * integralLimit * thisFWHM / 2.0
    limY = l2 * integralLimit * thisFWHM / 2.0

    fig = plt.figure(figsize=(10, 8), dpi=100)
    ax0 = fig.add_subplot(111, projection='3d')
    plotSigmaRange = ((0, limX), (0, limY))
    xxS = np.linspace(*plotSigmaRange[0], numPoints)
    yyS = np.linspace(*plotSigmaRange[1], numPoints)
    xmS, ymS = np.meshgrid(xxS, yyS)
    peakArrayFWHM = np.array(_gaussFWHM(xmS, ymS, sigmax=l1*sigmax, sigmay=l2*sigmax, mx=mx, my=mx, h=height), dtype=np.float32)
    ax0.plot_wireframe(xmS, ymS, peakArrayFWHM)

    # only need to use quadrant
    vol = 4.0*np.trapz(np.trapz(peakArrayFWHM, xxS), yyS)        # why does this work?
    print(f'>>> 2d volume (should be 2pi for unit gauss)   actual: {vol}    error: {height*l1*l2*2*np.pi - vol}')

    # make a 2d peak of unit height
    lim = 3 * integralLimit * thisFWHM / 2.0
    xxSig = np.linspace(-lim, lim, res)
    vals = make_gauss(xxSig, sigmax, mx, 1.0)
    vals2 = make_gauss(xxSig, sigmax, mx-0.1, 1.0)
    noise = np.random.normal(0.0, 0.008, len(xxSig))
    noisy = vals2 + noise

    fig = plt.figure(figsize=(10, 8), dpi=100)
    axS = fig.gca()

    axS.plot(xxSig, vals, label = 'Best Fit')
    axS.scatter(xxSig, vals, marker='x', s=200, linewidths=2, c='green')

    axS.plot(xxSig, noisy, label = 'Original Signal')
    axS.scatter(xxSig, noisy, marker='+', s=200, linewidths=2, c='red')

    # ax.plot(a, c, 'k--', label='Model length')
    # ax.plot(a, d, 'k:', label='Data length')
    # ax.plot(a, c + d, 'k', label='Total message length')
    # legend = ax.legend(loc='upper center', shadow=True, fontsize='x-large')

    legend = axS.legend(fontsize='x-large')

    axS.grid()

    # make a 2d plot of the peaks contained in testPeaks
    lim = plotMax
    xxSig = np.linspace(0, lim, res)

    colors = ('orange', 'purple', 'pink', 'green')
    fig = plt.figure(figsize=(10, 8), dpi=100)
    axS1 = fig.gca()
    vals = np.zeros(shape=(res, ), dtype=np.float32)

    if SETNOISE:
        mean_noise = 0
        target_noise_watts = SETNOISE
        vals = np.random.normal(mean_noise, np.sqrt(target_noise_watts), len(xxSig))

    for ii, thisPeak in enumerate(testPeaks):

        sigmax, sigmay, mx, my, h = thisPeak

        print('>>>1d testPeak', sigmax, sigmay, mx, my, h)

        valsArrayFWHM = make_gauss(xxSig, sigmax/(2**0.5), mx, h)
        vals = np.add(vals, valsArrayFWHM)

        axS1.plot(xxSig, valsArrayFWHM, c=colors[ii], linewidth=2.0)
        axS1.axvline(linewidth=2.0, x=mx, c=colors[ii], linestyle='dashed')

    axS1.plot(xxSig, vals, linewidth=2.0)
    axS1.grid(False)

    # test from peakTable
    # height = 1.32e6                           # sign doesn't matter
    # l1 = 21.9 / thisFWHM
    # l2 = 11.7 / thisFWHM

    # only need to use half
    area = 2.0*np.trapz(vals, xxSig)     # THIS WORKS! - uses the correct x points for the trapz area
    print(f'>>>volume new  {area}     {abs(height * np.power(area, 2) * l1 * l2)}')
    # estimated = 382919751.28

    lastArea=None
    for numPoints in range(9, 99):
        xxSig = np.linspace(0, lim, numPoints)
        vals = list(make_gauss(xxSig, sigmax, mx, height))
        area = 2.0*np.trapz(vals, xxSig)/height     # THIS WORKS! - uses the correct x points for the trapz area
        if lastArea:
            diff = area-lastArea
            print('>>>', numPoints, area, diff)
            if diff < 1e-8:
                break
        lastArea = area

    # actually area will be area * FWHM * height / thisFWHM

    # make a plot
    # fig = plt.figure(figsize=(10, 8), dpi=100)
    # ax2 = fig.gca(projection='3d')
    # ax2 = fig.add_subplot(111, projection='3d')
    # ax2.plot_wireframe(xm, ym, dataArraySigma, zorder=-1)


    # # testing new bit
    # # fig = plt.figure(figsize=(8, 6))
    # ax2 = plt.axes(projection='3d')
    #
    # # ax.plot(xx, yy, zz, 'ro', alpha=0.5)
    # # ax2.plot_wireframe(xm, ym, dataArraySigma, rcount=res, ccount=res)        # why?
    # ax2.plot_wireframe(xm, ym, dataArray, rcount=res, ccount=res)
    # plt.axis('off')
    # plt.grid(b=None)
    # plt.subplots_adjust(left=-0.1, right=1.1, top=1.2, bottom=-0.1)

    plt.show()
    sys.exit()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # fit all peaks in single operation 1
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # make a plot
    fig = plt.figure(figsize=(10, 8), dpi=100)
    # ax = fig.gca(projection='3d')
    ax = plt.axes(projection='3d')
    ax.plot_wireframe(xm, ym, dataArray, rcount=res, ccount=res)
    plt.axis('off')
    plt.grid(b=None)
    plt.subplots_adjust(left=-0.1, right=1.1, top=1.2, bottom=-0.1)

    peakPoints = [(np.array(position), height) for position, height in peakPoints]

    allPeaksArray = None
    regionArray = None

    for peakNum, (position, height) in enumerate(peakPoints):

        numDim = len(position)
        numPointInt = np.array([dataArray.shape[1], dataArray.shape[0]])
        firstArray = np.maximum(position - REGIONOFFSET, 0)
        lastArray = np.minimum(position + (REGIONOFFSET+1), numPointInt)

        if regionArray is not None:
            firstArray = np.minimum(firstArray, regionArray[0])
            lastArray = np.maximum(lastArray, regionArray[1])

        peakArrayFWHM = position.reshape((1, numDim))
        peakArrayFWHM = peakArrayFWHM.astype('float32')
        firstArray = firstArray.astype('int32')
        lastArray = lastArray.astype('int32')

        regionArray = np.array((firstArray, lastArray))

        if allPeaksArray is None:
            allPeaksArray = peakArrayFWHM
        else:
            allPeaksArray = np.append(allPeaksArray, peakArrayFWHM, axis=0)

    result = Peak.fitPeaks(dataArray, regionArray, allPeaksArray, 0)

    anno = ''
    for peakNum in range(len(result)):
        height, centerGuess, linewidth = result[peakNum]

        actualPos = []

        for dim in range(len(dataArray.shape)):
            mi, ma = plotRange[dim]
            ww = ma - mi

            actualPos.append(mi + (centerGuess[dim] / (dataArray.shape[dim] - 1)) * ww)

        # ax.scatter(*actualPos, height, c='green', marker='x', s=500, linewidth=5, zorder=-1)
        ax.plot([actualPos[0]], [actualPos[1]], [height], c='mediumseagreen', marker=matplotlib.markers.CARETUPBASE, lw=1, ms=15, zorder=20)

        # x2, y2, _ = mplot3d.proj3d.proj_transform(1, 1, 1, ax.get_proj())

        anno += 'x: %.4f\ny: %.4f\nh: %.4f\n\n' % (actualPos[0], actualPos[1], height)
        # ax.text(*actualPos, height, ' x %.4f\n y %.4f\n h %.4f' % (actualPos[0], actualPos[1], height), fontsize=20, zorder=40)

        if len(result) == 1:
            # only a single peak has been found - incorrect
            axS1.axvline(linewidth=2.0, x=actualPos[0], linestyle='dashed')

    ax.text2D(0.15, 0.8, anno, fontSize=16, transform=ax.transAxes, ha='left', va='top')

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # fit all peaks in single operation 2
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # testing new bit
    # fig = plt.figure(figsize=(8, 6))
    fig = plt.figure(figsize=(10, 8), dpi=100)
    ax = plt.axes(projection='3d')

    # ax.plot(xx, yy, zz, 'ro', alpha=0.5)
    # ax2.plot_wireframe(xm, ym, dataArraySigma, rcount=res, ccount=res)        # why?
    ax.plot_wireframe(xm, ym, dataArray, rcount=res, ccount=res)
    plt.axis('off')
    plt.grid(b=None)
    plt.subplots_adjust(left=-0.1, right=1.1, top=1.2, bottom=-0.1)

    peakPoints = [(np.array(position), height) for position, height in originalPeakPoints]

    allPeaksArray = None
    regionArray = None

    for peakNum, (position, height) in enumerate(peakPoints):

        numDim = len(position)
        numPointInt = np.array([dataArray.shape[1], dataArray.shape[0]])
        firstArray = np.maximum(position - REGIONOFFSET, 0)
        lastArray = np.minimum(position + (REGIONOFFSET+1), numPointInt)

        if regionArray is not None:
            firstArray = np.minimum(firstArray, regionArray[0])
            lastArray = np.maximum(lastArray, regionArray[1])

        peakArrayFWHM = position.reshape((1, numDim))
        peakArrayFWHM = peakArrayFWHM.astype('float32')
        firstArray = firstArray.astype('int32')
        lastArray = lastArray.astype('int32')

        regionArray = np.array((firstArray, lastArray))

        if allPeaksArray is None:
            allPeaksArray = peakArrayFWHM
        else:
            allPeaksArray = np.append(allPeaksArray, peakArrayFWHM, axis=0)

    result = Peak.fitPeaks(dataArray, regionArray, allPeaksArray, 0)

    anno = ''
    for peakNum in range(len(result)):
        height, centerGuess, linewidth = result[peakNum]

        actualPos = []

        for dim in range(len(dataArray.shape)):
            mi, ma = plotRange[dim]
            ww = ma - mi

            actualPos.append(mi + (centerGuess[dim] / (dataArray.shape[dim] - 1)) * ww)

        # ax.scatter(*actualPos, height, c='green', marker='x', s=500, linewidth=5, zorder=-1)
        ax.plot([actualPos[0]], [actualPos[1]], [height], c='mediumseagreen', marker=matplotlib.markers.CARETUPBASE, lw=1, ms=15, zorder=20)

        # x2, y2, _ = mplot3d.proj3d.proj_transform(1, 1, 1, ax.get_proj())

        anno += 'x: %.4f\ny: %.4f\nh: %.4f\n\n' % (actualPos[0], actualPos[1], height)
        # ax.text(*actualPos, height, ' x %.4f\n y %.4f\n h %.4f' % (actualPos[0], actualPos[1], height), fontsize=20, zorder=40)
    ax.text2D(0.15, 0.8, anno, fontSize=16, transform=ax.transAxes, ha='left', va='top')

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # fit all peaks in individual operations (not correct)
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # testing new bit
    # fig = plt.figure(figsize=(8, 6))
    fig = plt.figure(figsize=(10, 8), dpi=100)
    ax2 = plt.axes(projection='3d')

    # ax.plot(xx, yy, zz, 'ro', alpha=0.5)
    # ax2.plot_wireframe(xm, ym, dataArraySigma, rcount=res, ccount=res)        # why?
    ax2.plot_wireframe(xm, ym, dataArray, rcount=res, ccount=res)
    plt.axis('off')
    plt.grid(b=None)
    plt.subplots_adjust(left=-0.1, right=1.1, top=1.2, bottom=-0.1)


    anno = ''
    for peakNum, (position, _) in enumerate(peakPoints):

        numDim = len(position)
        numPointInt = np.array([dataArray.shape[1], dataArray.shape[0]])
        firstArray = np.maximum(position - REGIONOFFSET, 0)
        lastArray = np.minimum(position + (REGIONOFFSET+1), numPointInt)

        peakArrayFWHM = position.reshape((1, numDim))
        peakArrayFWHM = peakArrayFWHM.astype('float32')
        firstArray = firstArray.astype('int32')
        lastArray = lastArray.astype('int32')

        regionArray = np.array((firstArray, lastArray))

        result = Peak.fitPeaks(dataArray, regionArray, peakArrayFWHM, 0)

        height, centerGuess, linewidth = result[0]

        actualPos = []

        for dim in range(len(dataArray.shape)):
            mi, ma = plotRange[dim]
            ww = ma - mi

            actualPos.append(mi + (centerGuess[dim] / (dataArray.shape[dim] - 1)) * ww)

        # x2, y2, _ = mplot3d.proj3d.proj_transform(1, 1, 1, ax2.get_proj())
        anno += 'x: %.4f\ny: %.4f\nh: %.4f\n\n' % (actualPos[0], actualPos[1], height)
        # ax2.text(*actualPos, height, anno, fontsize=20, zorder=40)

        # ax2.scatter(*actualPos, height, c='red', marker='+', s=500, linewidth=3, zorder=40)
        ax2.plot([actualPos[0]], [actualPos[1]], [height], c='mediumseagreen', marker=matplotlib.markers.CARETUPBASE, lw=1, ms=15, zorder=20)

    ax2.text2D(0.15, 0.8, anno, fontSize=16, transform=ax.transAxes, ha='left', va='top')
    # plt.axis('off')
    # plt.grid(b=None)
    # # plt.autoscale(tight=True)
    # # plt.tight_layout()
    # plt.subplots_adjust(left=-0.1, right=1.1, top=1.2, bottom=-0.1)

    plt.show()
