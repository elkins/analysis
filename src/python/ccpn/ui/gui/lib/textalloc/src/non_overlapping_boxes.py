"""
Routines to align text-boxes.
Moves positions to give non-overlapping boxes/rectangles/ellipses and connecting arrows.

Expanded from the original.
Original by Christoffer Kjellson.
Available from github; https://github.com/ckjellson/textalloc
"""

# MIT License

# Copyright (c) 2022 Christoffer Kjellson

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
__dateModified__ = "$dateModified: 2025-03-14 17:56:48 +0000 (Fri, March 14, 2025) $"
__version__ = "$Revision: 3.2.12 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Original by Christoffer Kjellson $"
__date__ = "$Date: 2022 $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from typing import Tuple, List, Optional
from .candidates import generate_candidates, generate_candidate_lines
from .overlap_functions import (non_overlapping_boxes_to_boxes, inside_plot, non_overlapping_lines_to_boxes,
                                non_overlapping_lines_to_lines, non_overlapping_boxes_to_ellipses,
                                non_overlapping_points_to_boxes)


def get_non_overlapping_boxes(
        original_boxes: list,
        x_lims: Optional[Tuple[float, float]],
        y_lims: Optional[Tuple[float, float]],
        x_margin: float,
        y_margin: float,
        minx_distance: float,
        maxx_distance: float,
        miny_distance: float,
        maxy_distance: float,
        verbose: bool,
        draw_all: bool,
        include_new_lines: bool,
        include_new_boxes: bool,
        scatter_xy: np.ndarray = None,
        lines_xyxy: np.ndarray = None,
        boxes_xyxy: np.ndarray = None,
        ellipses_xyab: np.ndarray = None,
        ) -> Tuple[List[Tuple[float, float, float, float, str, int]], List[int]]:
    """Finds boxes that do not have an overlap with any other objects.

    Args:
        original_boxes (np.ndarray): original boxes containing texts.
        x_lims (Tuple[float, float]): x-limits of plot in pixels.
        y_lims (Tuple[float, float]): y-limits of plot in pixels.
        x_margin (float): x-axis margin between objects in pixels. Increase for larger margins to points and lines.
        y_margin (float): y-axis margin between objects in pixels.
        minx_distance (float): parameter for max distance between text and origin in pixels.
        maxx_distance (float): parameter for max distance between text and origin in pixels.
        miny_distance (float): parameter for max distance between text and origin in pixels.
        maxy_distance (float): parameter for max distance between text and origin in pixels.
        verbose (bool): prints progress.
        draw_all (bool): Draws all texts after allocating as many as possible despite overlap.
        include_new_lines (bool): Avoid the newly added line-segments between points and labels as new labels are found.
        include_new_boxes (bool): Avoid the newly added boxes between points and labels as new labels are found.
        scatter_xy (np.ndarray, optional): 2d array of scattered points in plot.
        lines_xyxy (np.ndarray, optional): 2d array of line segments in plot.
        boxes_xyxy (np.ndarray, optional): 2d array of boxes in plot.
        ellipses_xyab (np.ndarray, optional): 2d array of ellipses in plot.

    Returns:
        Tuple[List[Tuple[float, float, float, float, str, int]], List[int]]: data of non-overlapping boxes and indices of overlapping boxes.
    """
    from ccpn.core.lib.ContextManagers import progressHandler

    xmin_bound, xmax_bound, ymin_bound, ymax_bound = 0, 0, 0, 0
    if x_lims is not None:
        xmin_bound, xmax_bound = x_lims
    if y_lims is not None:
        ymin_bound, ymax_bound = y_lims

    box_arr = np.zeros((0, 4))
    # adaptive-lines, lines that are added between the centre and the found candidate-box
    box_lines_xyxy = np.zeros((0, 4))

    # Iterate original boxes and find ones that do not overlap by creating multiple candidates
    non_overlapping_boxes = []
    overlapping_boxes_inds = []

    with progressHandler(text='Auto-arranging...', maximum=len(original_boxes),
                         raiseErrors=False) as progress:

        for ii, box in enumerate(original_boxes):
            progress.checkCancel()
            progress.setValue(ii)

            x_original, y_original, w, h, s = box

            # create a set of candidate-boxes centred on the x_original/y_original point
            candidates = generate_candidates(w,
                                             h,
                                             x_original,
                                             y_original,
                                             minx_distance,
                                             miny_distance,
                                             maxx_distance,
                                             maxy_distance,
                                             )
            # create a set of candidate lines from the candidate-boxes to the x_original/y_original point
            candidates_lines = generate_candidate_lines(w,
                                                        h,
                                                        x_original,
                                                        y_original,
                                                        minx_distance,
                                                        miny_distance,
                                                        maxx_distance,
                                                        maxy_distance,
                                                        )

            # Check for overlapping with - scatter-points
            if scatter_xy is None:
                non_op = np.zeros((candidates.shape[0],)) == 0
            else:
                non_op = non_overlapping_points_to_boxes(
                        scatter_xy, candidates, x_margin, y_margin, by_points=False)  # need by_boxes

            # Check for overlapping with - line-segments
            if lines_xyxy is None:
                non_ol = np.zeros((candidates.shape[0],)) == 0
            else:
                non_ol = non_overlapping_lines_to_boxes(
                        lines_xyxy, candidates, x_margin, y_margin, by_lines=False)  # need by_boxes

            # Check for overlapping with - boxes
            if boxes_xyxy is None:
                non_ob = np.zeros((candidates.shape[0],)) == 0
            else:
                non_ob = non_overlapping_boxes_to_boxes(
                        boxes_xyxy, candidates, x_margin, y_margin
                        )

            # Check for overlapping with - ellipses
            if ellipses_xyab is None:
                non_oe = np.zeros((candidates.shape[0],)) == 0
            else:
                non_oe = non_overlapping_boxes_to_ellipses(
                        candidates, ellipses_xyab, x_margin, y_margin
                        )

            # compare with newly created lines
            if (box_lines_xyxy is None or not box_lines_xyxy.size) or not include_new_lines:
                non_ll = np.zeros((candidates.shape[0],)) == 0
            else:
                non_ll = non_overlapping_lines_to_lines(candidates_lines, box_lines_xyxy)

            # compare newly created lines with boxes
            if (box_lines_xyxy is None or not box_lines_xyxy.size) or not include_new_boxes:
                non_lb = np.zeros((candidates.shape[0],)) == 0
            else:
                non_lb = non_overlapping_lines_to_boxes(
                        candidates_lines, box_arr, x_margin, y_margin
                        )

            # compare with newly created boxes
            if box_arr.shape[0] == 0:
                non_orec = np.zeros((candidates.shape[0],)) == 0
            else:
                non_orec = non_overlapping_boxes_to_boxes(box_arr, candidates, x_margin, y_margin)

            if not (x_lims and y_lims):
                inside = np.zeros((candidates.shape[0],)) == 0
            else:
                inside = inside_plot(xmin_bound, ymin_bound, xmax_bound, ymax_bound, candidates)

            # Validate (bitwise_and is the quickest, faster than njit or logical_and)
            ok_candidates = np.where(
                    np.bitwise_and(
                            non_oe, np.bitwise_and(
                                    non_ob, np.bitwise_and(
                                            non_ol, np.bitwise_and(
                                                    non_ll, np.bitwise_and(
                                                            non_lb, np.bitwise_and(
                                                                    non_op, np.bitwise_and(non_orec, inside))
                                                            )
                                                    )
                                            )
                                    )
                            )
                    )[0]
            if len(ok_candidates) > 0:  # must be more than 10% available?
                box_arr, box_lines_xyxy = get_best_candidate('full', box_arr, candidates, h, ii, include_new_lines,
                                                             box_lines_xyxy,
                                                             non_overlapping_boxes, ok_candidates, s, verbose, w,
                                                             x_original, y_original)
                if verbose:
                    make_a_plot(box_arr, box_lines_xyxy, boxes_xyxy, ellipses_xyab,
                                candidates_lines, ok_candidates,
                                True, True, True, True, True)
                continue

            # reduce the conditions of candidacy
            ok_candidates = np.where(
                    np.bitwise_and(
                            non_oe, np.bitwise_and(
                                    non_ob, np.bitwise_and(
                                            non_ol, np.bitwise_and(
                                                    non_ll, np.bitwise_and(
                                                            non_op, np.bitwise_and(non_orec, inside))
                                                    )
                                            )
                                    )
                            )
                    )[0]
            if len(ok_candidates) > 0:
                box_arr, box_lines_xyxy = get_best_candidate('non_lb', box_arr, candidates, h, ii, include_new_lines,
                                                             box_lines_xyxy,
                                                             non_overlapping_boxes, ok_candidates, s, verbose, w,
                                                             x_original, y_original)

                if verbose:
                    make_a_plot(box_arr, box_lines_xyxy, boxes_xyxy, ellipses_xyab,
                                candidates_lines, ok_candidates,
                                True, True, True, True, True)
                continue

            # reduce the conditions of candidacy further
            ok_candidates = np.where(
                    np.bitwise_and(
                            non_oe, np.bitwise_and(
                                    non_ob, np.bitwise_and(
                                            non_ol, np.bitwise_and(
                                                    non_op, np.bitwise_and(non_orec, inside))
                                            )
                                    )
                            )
                    )[0]
            if len(ok_candidates) > 0:
                box_arr, box_lines_xyxy = get_best_candidate('non_ll-non_lb', box_arr, candidates, h, ii,
                                                             include_new_lines, box_lines_xyxy,
                                                             non_overlapping_boxes, ok_candidates, s, verbose, w,
                                                             x_original, y_original)
                if verbose:
                    make_a_plot(box_arr, box_lines_xyxy, boxes_xyxy, ellipses_xyab,
                                candidates_lines, ok_candidates,
                                True, True, True, True, True)
                continue

            if draw_all:
                ok_candidates = np.where(np.bitwise_and(non_orec, inside))[0]
                if len(ok_candidates) > 0:
                    box_arr, box_lines_xyxy = get_best_candidate('last', box_arr, candidates, h, ii, include_new_lines,
                                                                 box_lines_xyxy,
                                                                 non_overlapping_boxes, ok_candidates, s, verbose, w,
                                                                 x_original, y_original)
                    if verbose:
                        make_a_plot(box_arr, box_lines_xyxy, boxes_xyxy, ellipses_xyab,
                                    candidates_lines, ok_candidates,
                                    True, True, True, True, True)
                    continue

            # no free-space can be found, add to the overlapping list
            overlapping_boxes_inds.append(ii)
            if verbose:
                print(f'no space found {ii}: {s}')

    if verbose:
        make_a_plot(box_arr, box_lines_xyxy, boxes_xyxy, ellipses_xyab,
                    candidates_lines, ok_candidates,
                    cand=False, box_lines=True, boxes=True, ellipses=True, found=True)

    return non_overlapping_boxes, overlapping_boxes_inds


def make_a_plot(box_arr, box_lines_xyxy, boxes_xyxy, ellipses_xyab, candidates_lines, ok_candidates,
                cand: bool = False, box_lines: bool = False, boxes: bool = False, ellipses: bool = False,
                found: bool = True):
    """Make a plot of the candidates and found boxes.
    """
    # plot a figure to check the size
    import matplotlib

    matplotlib.use('Qt5Agg')
    # from mpl_toolkits import mplot3d
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Ellipse

    fig = plt.figure(figsize=(10, 8), dpi=100)
    axS = fig.gca()
    if box_lines and box_lines_xyxy is not None:
        for ii in range(box_lines_xyxy.shape[0]):
            row = box_lines_xyxy[ii, :]
            axS.plot(row[::2], row[1::2], linewidth=1)
    if boxes and boxes_xyxy is not None:
        for ii in range(boxes_xyxy.shape[0]):
            row = boxes_xyxy[ii, :]
            axS.add_patch(Rectangle(row[:2], row[2] - row[0], row[3] - row[1],
                                    linewidth=1, fill=False, color='lightgrey'))
    if ellipses and ellipses_xyab is not None:
        for ii in range(ellipses_xyab.shape[0]):
            row = ellipses_xyab[ii, :]
            # convert semi-major to major axes
            axS.add_patch(Ellipse(row[:2], 2 * row[2], 2 * row[3],
                                  linewidth=1, fill=False, color='lightgrey'))
    if found and box_arr is not None:
        for ii in range(box_arr.shape[0]):
            row = box_arr[ii, :]
            axS.add_patch(Rectangle(row[:2], row[2] - row[0], row[3] - row[1], linewidth=1, fill=False))
    if cand:
        for ii in range(candidates_lines[ok_candidates].shape[0]):
            row = candidates_lines[ok_candidates[ii], :]
            axS.plot(row[::2], row[1::2], 'x', linewidth=1, markersize=6)

    plt.show()


def get_best_candidate(code, box_arr, candidates, h, ii, include_new_lines, box_lines_xyxy, non_overlapping_boxes,
                       ok_candidates, s, verbose, w, x_original, y_original):
    """Get the best candidate; this is the closest to the original-point.

    :param box_arr (np.ndarray): 2d array of newly added boxes
    :param candidates (np.ndarray): 2d array of candidate-lines radiating from the original-point
    :param h: height of target-box
    :param ii: counter
    :param include_new_lines (bool): add new candidate-lines
    :param box_lines_xyxy (np.ndarray): 2d array of newly added line-segments in plot.
    :param non_overlapping_boxes: current list of new non-overlapping boxes
    :param ok_candidates (np.ndarray): subset of candidates that are valid positions
    :param s (str): target string
    :param verbose (bool): prints progress
    :param w (float): width of target-box
    :param x_original (float): centre co-ordinate in pixels
    :param y_original (float): centre co-ordinate in pixels
    :return:
    """
    # find the index of the nearest candidate to the original-point, slightly offset to the top-right
    centres = np.tile(np.array([x_original + 2, y_original + 2, 0, 0]).transpose(), (len(ok_candidates), 1))
    offset = candidates[ok_candidates] - centres
    min_dists = np.linalg.norm(offset[:, :2], axis=1)
    ind = np.argmin(min_dists)

    # # plot a figure to check the size
    # import matplotlib
    #
    # matplotlib.use('Qt5Agg')
    # from mpl_toolkits import mplot3d
    # import matplotlib.pyplot as plt
    #
    # fig = plt.figure(figsize=(10, 8), dpi=100)
    # axS = fig.gca()
    #
    # axS.plot(offset[:, 0], offset[:, 1], label = 'Offset')

    best_candidate = candidates[ok_candidates[ind], :]
    box_arr = np.vstack([box_arr, best_candidate])

    non_overlapping_boxes.append(
            (best_candidate[0], best_candidate[1], w, h, s, ii)
            )

    if include_new_lines:
        # add a new line between the symbol and the best candidate position -> to the exclude list
        x0, y0 = best_candidate[0] + w / 2, best_candidate[1] + h / 2
        x1, y1 = (x_original + x0) / 2, (y_original + y0) / 2
        new_line = np.array([[x0, y0, x1, y1]])
        box_lines_xyxy = np.vstack([box_lines_xyxy, new_line]) if box_lines_xyxy.size else new_line
        if box_lines_xyxy.shape[0] > 10:
            # only keep the last few lines to check
            box_lines_xyxy = box_lines_xyxy[1:, :]
        if verbose and code != 'full':
            print(f'--> adding line ({code})  {ii}: {s}   {len(box_lines_xyxy)}: '
                  f'{new_line}     {offset.shape[0]}    {ok_candidates}')

    return box_arr, box_lines_xyxy
