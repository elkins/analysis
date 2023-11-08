"""
A basic SS drawer using matplotlib

"""


import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpl_patches
import matplotlib.ticker as ticker


DSSP_definitions = {
           'H': 'H', # 3-turn helix (310 helix). Min length 3 residues.
           'G': 'H', # 4-turn helix (α helix). Minimum length 4 residues.
           'I': 'H',  #  5-turn helix (π helix). Minimum length 5 residues.
           'B': 'E', # extended strand in parallel and/or anti-parallel β-sheet conformation. Min length 2 residues.
           'E': 'E', # residue in isolated β-bridge (single pair β-sheet hydrogen bond formation)
           'T': 'T', # hydrogen bonded turn (3, 4 or 5 turn)
           'S': 'T', #  coil (residues which are not in any of the above conformations).
            'C':'C', # DSSP_definitions, only a blank placeholder to join blocks,
            }

def createBlocksFromSequence(ss_sequence):
    blocks = []  # (type, start, end)
    prev = None
    for idx, elem in enumerate(ss_sequence):
        reducedElement = DSSP_definitions.get(elem, 'C')
        if reducedElement != prev:
            blocks.append([reducedElement, idx, idx])
            prev = reducedElement
        blocks[-1][-1] = idx
    return blocks


def plotSS(ax, x, sequence, ss_sequence, startSequenceCode=1, fontsize=10,
           sheetColour='blue', helixColour='red', baselineColour='black',
            loopColour='yellow', showBottomAxis = False,showLeftAxis = False,
           centerY_SS = 1, arrowWidth = 0.05,   Helix_width = 0.025,
            arrowHeadWidth=0.1, arrowHeadLength=0.5,
           showSequenceNumber = True, sequenceNumberFont=5,
           sequenceNumberOffset=0.01, sequenceSeparatorSymbol='.',
           sequenceNumberColour='gray'):

    blocks = createBlocksFromSequence(ss_sequence=ss_sequence)

    maxSSWidth = np.max([arrowWidth, Helix_width, arrowHeadWidth])
    sequenceLetterYcoord =  centerY_SS - maxSSWidth
    sequenceDashYcoord = sequenceLetterYcoord - sequenceNumberOffset
    sequenceNumberYcoord = sequenceDashYcoord - sequenceNumberOffset
    maxSSWidth = np.max([maxSSWidth, sequenceNumberYcoord])

    yss = [centerY_SS]*len(x)
    ax.plot(x,yss, color=baselineColour)
    for blk_idx, ss_blk in enumerate(blocks, ):
        ss_type, start, last = ss_blk
        start, last = start + startSequenceCode, last + startSequenceCode

        _x = np.arange(start, last)
        y = [centerY_SS]*len(_x)
        if len(_x) == 0:
            continue
        if ss_type == 'H':
            _helix = [centerY_SS+Helix_width, centerY_SS-Helix_width]*int((len(_x)/2))
            hY = [centerY_SS] + _helix[:-1] + [centerY_SS]
            hX = np.arange(start, start+len(hY))
            ax.plot(_x, y, color=ax.get_facecolor(),antialiased=False )
            ax.plot(hX, hY, color=helixColour)

        elif ss_type == 'E': #sheet

            ax.plot(_x, y, color=sheetColour)

            ax.arrow(x=_x[0], y=y[0], dx=_x[-1] - _x[0],
                      dy=0, width=arrowWidth, color=sheetColour,
                      head_width=arrowHeadWidth, head_length=arrowHeadLength)

        elif ss_type == 'T': # loop TO DO
            ax.plot(_x,y, '_', color=loopColour)
        else:
            ax.plot(_x,y, color=baselineColour)


    for i, txt in zip(x, sequence):
        ax.annotate(str(txt), (i, sequenceLetterYcoord), fontsize=fontsize, ha='center')
        if showSequenceNumber:
            ax.annotate(str(sequenceSeparatorSymbol), (i, sequenceDashYcoord), fontsize=sequenceNumberFont, ha='center',  color=sequenceNumberColour,)
            ax.annotate(str(i), (i, sequenceNumberYcoord), fontsize=sequenceNumberFont, ha='center',  color=sequenceNumberColour,)

    minY, maxY = ax.get_ylim()
    ax.set_ylim([maxSSWidth,  maxY])
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.get_yaxis().set_visible(showLeftAxis)
    ax.get_xaxis().set_visible(showBottomAxis)
    ax.spines['bottom'].set_visible(showBottomAxis)


    return ax


if __name__ == '__main__':
    ss_sequence   =  'CCHHHHHHHHHHHHTTSSBTTEEEHHHHHHHHHHHCTTTTTTTSCHHHHHHHHCTTCSSEEEHHHHHHHHHHHC'
    sequence  = 'KSPEELKGIFEKYAAKEGDPNQLSKEELKLLLQTEFPSLLKGGSTLDELFEELDKNGDGEVSFEEFQLVKKISQ'
    startSequenceCode = 17
    x = np.arange(startSequenceCode, startSequenceCode+len(sequence))
    blocks = createBlocksFromSequence(ss_sequence=ss_sequence)

    fig = plt.figure(dpi=400)
    ax = fig.add_subplot(311)
    axss = plotSS(ax=ax, x=x, sequence=sequence, ss_sequence=ss_sequence, startSequenceCode=startSequenceCode)
    plt.show()


