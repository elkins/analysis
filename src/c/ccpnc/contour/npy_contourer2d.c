/*
======================COPYRIGHT/LICENSE START==========================

npy_contourer2d.c: Part of the CcpNmr Analysis program

Copyright (C) 2011 Wayne Boucher and Tim Stevens (University of Cambridge)

=======================================================================

The CCPN license can be found in ../../../license/CCPN.license.

======================COPYRIGHT/LICENSE END============================

for further information, please contact :

- CCPN website (http://www.ccpn.ac.uk/)

- email: ccpn@bioc.cam.ac.uk

- contact the authors: wb104@bioc.cam.ac.uk, tjs23@cam.ac.uk
=======================================================================

If you are using this software for academic purposes, we suggest
quoting the following references:

===========================REFERENCE START=============================
R. Fogh, J. Ionides, E. Ulrich, W. Boucher, W. Vranken, J.P. Linge, M.
Habeck, W. Rieping, T.N. Bhat, J. Westbrook, K. Henrick, G. Gilliland,
H. Berman, J. Thornton, M. Nilges, J. Markley and E. Laue (2002). The
CCPN project: An interim report on a data model for the NMR community
(Progress report). Nature Struct. Biol. 9, 416-418.

Wim F. Vranken, Wayne Boucher, Tim J. Stevens, Rasmus
H. Fogh, Anne Pajon, Miguel Llinas, Eldon L. Ulrich, John L. Markley, John
Ionides and Ernest D. Laue (2005). The CCPN Data Model for NMR Spectroscopy:
Development of a Software Pipeline. Proteins 59, 687 - 696.

===========================REFERENCE END===============================

*/

#include "Python.h"

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION    // so that warnings avoided
#include "arrayobject.h"
#include "npy_defns.h"

/*
  Module: Contourer2d

  Function:
    contourer(dataArray, levels)
    Input:
      dataArray = 2D NumPy array of [y][x] values
      levels = the values at which one is finding contours (whether > 0 or < 0)
      they ought to be increasing if > 0 and decreasing if < 0 (not checked)
      they have to be either always increasing or always decreasing
    Output:
      Python list (an entry for each level) of lists of polylines
      A polyline is a 2D NumPy array of size [nv][2]
      where nv = number of vertices in polyline
      The first index is the vertex number and
      the second index is 0 for x and 1 for y
*/

// define a global object(cheating for the minute)
static PyObject *gl_object_list;
static int numIndices = 0;
static int numVertices = 0;
static int numColours = 0;
static int indexCount = 0;
static int vertexCount = 0;
static int colourCount = 0;
static int lastIndex = 0;
static int lastVertex = 0;
static PyArrayObject *indexing;
static PyArrayObject *vertices;
static PyArrayObject *colours;
static unsigned int *indexPTR;
static float32 *vertexPTR;
static float32 *colourPTR;

#define CONTOUR_NALLOC 50 /* allocate vertices in this size bunch */

static PyObject *ErrorObject; /* locally-raised exception */

typedef struct _Contour_vertex {
    float x[2];
    struct _Contour_vertex *v1; /* previous vertex (NULL if none) */
    struct _Contour_vertex *v2; /* next vertex (NULL if none) */
    CcpnBool visited;           /* = CCPN_FALSE if not visited, CCPN_TRUE if visited */
} * Contour_vertex;

typedef struct _Contour_vertices {
    int nvertices;                /* number of vertices */
    int nalloc;                   /* size of each block of vertices allocated */
    int nblocks;                  /* number of blocks allocated */
    Contour_vertex *vertex_store; /* vertex store, ceil(nvertices/nalloc) long */
    /* above used to speed up allocation of vertices */
    /* allocate lots in one go and then use one after the other */
    /* so access via vertex i = vertex_store[i/nalloc] + (i%nalloc) */

    /* below are things added to make contouring faster if more than one level */
    CcpnBool are_levels_increasing;

    /* allocate below to be of size max_nrows x max_ncols to save hassle */

    /* old = range set by previous level */
    int nrows_old;        /* number of rows need to examine */
    int *row_old;         /* the rows, length nrows_old */
    int *ncol_ranges_old; /* the number of column ranges in a given row */
    int **col_start_old;  /* the start column for a given range */
    int **col_end_old;    /* the end column for a given range */

    /* new = range set by current level */
    int nrows_new;        /* number of rows need to examine */
    int *row_new;         /* the rows, length nrows_new */
    int *ncol_ranges_new; /* the number of column ranges in a given row */
    int **col_start_new;  /* the start column for a given range */
    int **col_end_new;    /* the end column for a given range */
} * Contour_vertices;

static Contour_vertices new_contour_vertices(PyArrayObject *data, int nlevels, CcpnBool are_levels_increasing) {
    int i;
    Contour_vertices contour_vertices;
    int npoints0 = PyArray_DIM(data, 1);
    int npoints1 = PyArray_DIM(data, 0);
    int ncols = MAX(1, npoints0 / 2);
    // int ncols = npoints0;

    MALLOC_NEW(contour_vertices, struct _Contour_vertices, 1);

    contour_vertices->nvertices = 0;
    contour_vertices->nalloc = CONTOUR_NALLOC;
    contour_vertices->nblocks = 0;
    contour_vertices->vertex_store = NULL;

    contour_vertices->are_levels_increasing = are_levels_increasing;

    contour_vertices->nrows_old = npoints1 - 1;
    MALLOC_NEW(contour_vertices->row_old, int, npoints1);
    MALLOC_NEW(contour_vertices->ncol_ranges_old, int, npoints1);
    MALLOC_NEW(contour_vertices->col_start_old, int *, npoints1);
    MALLOC_NEW(contour_vertices->col_end_old, int *, npoints1);
    for (i = 0; i < npoints1; i++) {
        contour_vertices->row_old[i] = i;
        contour_vertices->ncol_ranges_old[i] = 1;
        MALLOC_NEW(contour_vertices->col_start_old[i], int, ncols);
        MALLOC_NEW(contour_vertices->col_end_old[i], int, ncols);
        contour_vertices->col_start_old[i][0] = 0;
        contour_vertices->col_end_old[i][0] = npoints0;
    }

    // TBD: should not need _new variables if nlevels = 1 but crashes if do not have them
    // if (nlevels > 1)
    {
        contour_vertices->nrows_new = 0;
        MALLOC_NEW(contour_vertices->row_new, int, npoints1);
        MALLOC_NEW(contour_vertices->ncol_ranges_new, int, npoints1);
        MALLOC_NEW(contour_vertices->col_start_new, int *, npoints1);
        MALLOC_NEW(contour_vertices->col_end_new, int *, npoints1);
        for (i = 0; i < npoints1; i++) {
            MALLOC_NEW(contour_vertices->col_start_new[i], int, ncols);
            MALLOC_NEW(contour_vertices->col_end_new[i], int, ncols);
        }
    }

    return contour_vertices;
}

static void delete_contour_vertices(Contour_vertices vertices, int nlevels, int npoints1) {
    int i;

    if (!vertices) return;

    for (i = 0; i < vertices->nblocks; i++) FREE(vertices->vertex_store[i], struct _Contour_vertex);

    FREE(vertices->vertex_store, Contour_vertex);

    FREE(vertices->row_old, int);
    FREE(vertices->ncol_ranges_old, int);
    FREE2(vertices->col_start_old, int, npoints1);
    FREE2(vertices->col_end_old, int, npoints1);

    // TBD: should not need _new variables if nlevels = 1 but crashes if do not have them
    // if (nlevels > 1)
    {
        FREE(vertices->row_new, int);
        FREE(vertices->ncol_ranges_new, int);
        FREE2(vertices->col_start_new, int, npoints1);
        FREE2(vertices->col_end_new, int, npoints1);
    }

    FREE(vertices, struct _Contour_vertices);
}

#define NEITHER     0
#define START_RANGE 1
#define END_RANGE   2

static void update_new_range(Contour_vertices contour_vertices, int x, int y, int rangeType) {
    int ncol_ranges;
    int *col_start, *col_end;
    int nrows_new = contour_vertices->nrows_new;
    int *row_new = contour_vertices->row_new;
    int *ncol_ranges_new = contour_vertices->ncol_ranges_new;
    int **col_start_new = contour_vertices->col_start_new;
    int **col_end_new = contour_vertices->col_end_new;

    if ((nrows_new == 0) || (row_new[nrows_new - 1] != y)) {
        /* new row */
        row_new[nrows_new] = y;
        ncol_ranges_new[nrows_new] = 0;
        contour_vertices->nrows_new = ++nrows_new;
    }

    col_start = col_start_new[nrows_new - 1];
    col_end = col_end_new[nrows_new - 1];

    if ((x == 0) || (rangeType == START_RANGE)) {
        /* new range */
        ncol_ranges = ncol_ranges_new[nrows_new - 1];
        col_start[ncol_ranges] = x;
        col_end[ncol_ranges] = -1;
        ncol_ranges_new[nrows_new - 1] = ++ncol_ranges;
    }

    /* deal with case x = npoints0-1 later */
    if (rangeType == END_RANGE) {
        ncol_ranges = ncol_ranges_new[nrows_new - 1];

        // col_end[ncol_ranges-1] = x+1;
        col_end[ncol_ranges - 1] = x + 2;
    }
}

static void check_end_range(Contour_vertices contour_vertices, int npoints0) {
    int nrows_new = contour_vertices->nrows_new;
    int ncol_ranges, *col_end;

    if (nrows_new > 0) {
        ncol_ranges = contour_vertices->ncol_ranges_new[nrows_new - 1];
        col_end = contour_vertices->col_end_new[nrows_new - 1];
        if ((ncol_ranges > 0) && (col_end[ncol_ranges - 1] == -1)) col_end[ncol_ranges - 1] = npoints0;
    }
}

static void swap_old_new(Contour_vertices contour_vertices) {
    contour_vertices->nrows_old = contour_vertices->nrows_new;
    SWAP(contour_vertices->row_old, contour_vertices->row_new, int *);
    SWAP(contour_vertices->ncol_ranges_old, contour_vertices->ncol_ranges_new, int *);
    SWAP(contour_vertices->col_start_old, contour_vertices->col_start_new, int **);
    SWAP(contour_vertices->col_end_old, contour_vertices->col_end_new, int **);
    contour_vertices->nrows_new = 0;
}

static Contour_vertex new_vertex(Contour_vertices contour_vertices) {
    int nvertices = contour_vertices->nvertices;
    int nalloc = contour_vertices->nalloc;
    int nblocks = contour_vertices->nblocks, block;
    Contour_vertex v;

    block = nvertices / nalloc;
    if (block >= nblocks) /* time for a new block of storage */
    {
        if (nblocks == 0) {
            MALLOC_NEW(contour_vertices->vertex_store, Contour_vertex, 1);
        } else {
            REALLOC_NEW(contour_vertices->vertex_store, Contour_vertex, nblocks + 1);
        }

        MALLOC_NEW(contour_vertices->vertex_store[nblocks], struct _Contour_vertex, nalloc);
        contour_vertices->nblocks++;
    }

    v = contour_vertices->vertex_store[block] + (nvertices % nalloc);
    contour_vertices->nvertices++;

    v->v1 = v->v2 = NULL;
    v->visited = CCPN_FALSE;

    return v;
}

#define INTERPOLATE(a, b) ((level - (a)) / ((b) - (a)))

static Contour_vertex new_vertex0(Contour_vertices contour_vertices, float level, float d1, float d2, int x, int y) {
    Contour_vertex v;

    CHECK_NULL(v = new_vertex(contour_vertices));

    v->x[0] = x + INTERPOLATE(d1, d2);
    v->x[1] = y;

    return v;
}

static Contour_vertex new_vertex1(Contour_vertices contour_vertices, float level, float d1, float d2, int x, int y) {
    Contour_vertex v;

    CHECK_NULL(v = new_vertex(contour_vertices));

    v->x[0] = x;
    v->x[1] = y + INTERPOLATE(d1, d2);

    return v;
}

#define NEW_VERTEX0(v, d1, d2, x, y) \
    if (!(v = new_vertex0(contour_vertices, level, d1, d2, x, y))) return CCPN_ERROR;

#define NEW_VERTEX1(v, d1, d2, x, y) \
    if (!(v = new_vertex1(contour_vertices, level, d1, d2, x, y))) return CCPN_ERROR;

typedef CcpnStatus (*New_edge_func)(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                                    float data_old1, float data_new0, float data_new1, Contour_vertex *v_row,
                                    Contour_vertex *p_v_col, int x, int y);

/* 0 0
   0 0 */
static CcpnStatus no_edge00(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                            float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                            int x, int y) {
    if (more_levels && (x == 0) && !contour_vertices->are_levels_increasing) update_new_range(contour_vertices, x, y, NEITHER);

    return CCPN_OK;
}

/* 0 0
   0 1 */
static CcpnStatus new_edge01(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_old;

    NEW_VERTEX1(v_col, data_old1, data_new1, x + 1, y);

    v_old = v_row[x];
    v_old->v1 = v_col;
    v_col->v2 = v_old;
    *p_v_col = v_col;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? START_RANGE : NEITHER);

    return CCPN_OK;
}

/* 1 1
   1 0 */
static CcpnStatus new_edge32(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_old;

    NEW_VERTEX1(v_col, data_old1, data_new1, x + 1, y);

    v_old = v_row[x];
    v_old->v2 = v_col;
    v_col->v1 = v_old;
    *p_v_col = v_col;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? NEITHER : START_RANGE);

    return CCPN_OK;
}

/* 0 1
   0 0 */
static CcpnStatus new_edge02(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_new;

    NEW_VERTEX0(v_new, data_new0, data_new1, x, y + 1);
    NEW_VERTEX1(v_col, data_old1, data_new1, x + 1, y);

    v_row[x] = v_new;
    v_new->v2 = v_col;
    v_col->v1 = v_new;
    *p_v_col = v_col;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? START_RANGE : NEITHER);

    return CCPN_OK;
}

/* 1 0
   1 1 */
static CcpnStatus new_edge31(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_new;

    NEW_VERTEX0(v_new, data_new0, data_new1, x, y + 1);
    NEW_VERTEX1(v_col, data_old1, data_new1, x + 1, y);

    v_row[x] = v_new;
    v_new->v1 = v_col;
    v_col->v2 = v_new;
    *p_v_col = v_col;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? NEITHER : START_RANGE);

    return CCPN_OK;
}

/* 0 1
   0 1 */
static CcpnStatus new_edge03(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_old, v_new;

    NEW_VERTEX0(v_new, data_new0, data_new1, x, y + 1);

    v_old = v_row[x];
    v_row[x] = v_new;
    v_old->v1 = v_new;
    v_new->v2 = v_old;

    if (more_levels)
        update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? START_RANGE : END_RANGE);

    return CCPN_OK;
}

/* 1 0
   1 0 */
static CcpnStatus new_edge30(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_old, v_new;

    NEW_VERTEX0(v_new, data_new0, data_new1, x, y + 1);

    v_old = v_row[x];
    v_row[x] = v_new;
    v_old->v2 = v_new;
    v_new->v1 = v_old;

    if (more_levels)
        update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? END_RANGE : START_RANGE);

    return CCPN_OK;
}

/* 0 0
   1 0 */
static CcpnStatus new_edge10(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_old;

    v_col = *p_v_col;
    v_old = v_row[x];
    v_old->v2 = v_col;
    v_col->v1 = v_old;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? END_RANGE : NEITHER);

    return CCPN_OK;
}

/* 1 1
   0 1 */
static CcpnStatus new_edge23(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_old;

    v_col = *p_v_col;
    v_old = v_row[x];
    v_old->v1 = v_col;
    v_col->v2 = v_old;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? NEITHER : END_RANGE);

    return CCPN_OK;
}

/* 0 0
   1 1 */
static CcpnStatus new_edge11(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_new;

    NEW_VERTEX1(v_new, data_old1, data_new1, x + 1, y);

    v_col = *p_v_col;
    v_col->v1 = v_new;
    v_new->v2 = v_col;
    *p_v_col = v_new;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? NEITHER : NEITHER);

    return CCPN_OK;
}

/* 1 1
   0 0 */
static CcpnStatus new_edge22(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_new;

    NEW_VERTEX1(v_new, data_old1, data_new1, x + 1, y);

    v_col = *p_v_col;
    v_col->v2 = v_new;
    v_new->v1 = v_col;
    *p_v_col = v_new;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? NEITHER : NEITHER);

    return CCPN_OK;
}

/* 0 1
   1 0 */
static CcpnStatus new_edge12(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_new, v, v_old;
    float d, d1, d2, d3, d4;

    d1 = data_old0;
    d2 = data_old1;
    d3 = data_new0;
    d4 = data_new1;

    NEW_VERTEX0(v, d3, d4, x, y + 1);
    NEW_VERTEX1(v_new, d2, d4, x + 1, y);

    d = (d1 + d2 + d3 + d4) / 4;

    v_col = *p_v_col;
    v_old = v_row[x];
    if (d > level) {
        v_col->v1 = v;
        v->v2 = v_col;
        v_new->v1 = v_old;
        v_old->v2 = v_new;
    } else {
        v_col->v1 = v_old;
        v_old->v2 = v_col;
        v_new->v1 = v;
        v->v2 = v_new;
    }

    v_row[x] = v;
    *p_v_col = v_new;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? NEITHER : NEITHER);

    return CCPN_OK;
}

/* 1 0
   0 1 */
static CcpnStatus new_edge21(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_new, v, v_old;
    float d, d1, d2, d3, d4;

    d1 = data_old0;
    d2 = data_old1;
    d3 = data_new0;
    d4 = data_new1;

    NEW_VERTEX0(v, d3, d4, x, y + 1);
    NEW_VERTEX1(v_new, d2, d4, x + 1, y);

    d = (d1 + d2 + d3 + d4) / 4;

    v_col = *p_v_col;
    v_old = v_row[x];
    if (d > level) {
        v_col->v2 = v_old;
        v_old->v1 = v_col;
        v_new->v2 = v;
        v->v1 = v_new;
    } else {
        v_col->v2 = v;
        v->v1 = v_col;
        v_new->v2 = v_old;
        v_old->v1 = v_new;
    }

    v_row[x] = v;
    *p_v_col = v_new;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? NEITHER : NEITHER);

    return CCPN_OK;
}

/* 0 1
   1 1 */
static CcpnStatus new_edge13(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_new;

    NEW_VERTEX0(v_new, data_new0, data_new1, x, y + 1);

    v_col = *p_v_col;
    v_row[x] = v_new;
    v_col->v1 = v_new;
    v_new->v2 = v_col;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? NEITHER : END_RANGE);

    return CCPN_OK;
}

/* 1 0
   0 0 */
static CcpnStatus new_edge20(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                             float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                             int x, int y) {
    Contour_vertex v_col, v_new;

    NEW_VERTEX0(v_new, data_new0, data_new1, x, y + 1);

    v_col = *p_v_col;
    v_row[x] = v_new;
    v_col->v2 = v_new;
    v_new->v1 = v_col;

    if (more_levels) update_new_range(contour_vertices, x, y, contour_vertices->are_levels_increasing ? END_RANGE : NEITHER);

    return CCPN_OK;
}

/* 1 1
   1 1 */
static CcpnStatus no_edge33(Contour_vertices contour_vertices, float level, CcpnBool more_levels, float data_old0,
                            float data_old1, float data_new0, float data_new1, Contour_vertex *v_row, Contour_vertex *p_v_col,
                            int x, int y) {
    if (more_levels && (x == 0) && contour_vertices->are_levels_increasing) update_new_range(contour_vertices, x, y, NEITHER);

    return CCPN_OK;
}

#define N 4

#define GET_DATA(j0, j1)     (*((float32 *)PyArray_GETPTR2(data, (j1), (j0))))
#define GET_DATA0(j0, j1)    (*((float32 *)PyArray_GETPTR2(data0, j0, j1)))
#define GET_DATA1(j0, j1)    (*((float32 *)PyArray_GETPTR2(data1, j0, j1)))
#define DATA_ABOVE_LEVEL(d)  (((d) > level) ? 1 : 0)
#define DATA_ABOVE_LEVEL2(d) (((d) > level) ? 2 : 0)

static CcpnStatus update_bounds(PyArrayObject *data0, PyArrayObject *data1) {
    // get the dimensions
    int npointsi = PyArray_DIM(data0, 0);
    int npointsj = PyArray_DIM(data0, 1);
    int npointsi1 = PyArray_DIM(data1, 0);
    int npointsj1 = PyArray_DIM(data1, 1);
    int size = npointsi * npointsj;
    npy_float32 v0, v1, v0min, v0max, v1min, v1max, sum;

    // check that the arrays are the same size
    if ((npointsi != npointsi1) || (npointsj != npointsj1)) return CCPN_OK;

    // generate pointers to the numpy c data
    npy_float32 *p0 = (npy_float32 *)PyArray_DATA(data0);
    npy_float32 *p1 = (npy_float32 *)PyArray_DATA(data1);

    // NOTE:ED - use c indexing to access the array, MUST be an npy_float32 array
    for (int ii = 0; ii < size; ii++) {
        v0 = p0[ii];
        v1 = p1[ii];
        v0max = MAX(v0, 0.0);
        v0min = MIN(v0, 0.0);
        v1max = MAX(v1, 0.0);
        v1min = MIN(v1, 0.0);
        p0[ii] = MAX(v0max, v1max) + MIN(v0min, v1min);
    }

    //    // iterate through the array in pyArray method
    //    for (int ii=0; ii < npointsi; ii++)
    //        for (int jj=0; jj < npointsj; jj++)
    //        {
    //            v0 = GET_DATA0(ii, jj);
    //            v1 = GET_DATA1(ii, jj);
    //            v0max = MAX(v0, 0.0);
    //            v0min = MIN(v0, 0.0);
    //            v1max = MAX(v1, 0.0);
    //            v1min = MIN(v1, 0.0);
    //            PyArray_SETITEM(data0, PyArray_GETPTR2(data0, ii, jj), PyFloat_FromDouble(MAX(v0max, v1max) + MIN(v0min,
    //            v1min)));
    //        }
    return CCPN_OK;
}

static CcpnStatus find_vertices(Contour_vertices contour_vertices, float level, PyArrayObject *data, CcpnBool more_levels) {
    int npoints0 = PyArray_DIM(data, 1);
    int npoints1 = PyArray_DIM(data, 0);
    int i0, i1, r, c;
    CcpnBool b_old, b_new;
    float d_old, d_old0, d_old1, d_new, d_new0, d_new1;
    Contour_vertex *v_row, v_col;
    static New_edge_func *new_edge, edge_func;
    static New_edge_func new_edge_func[N][N] = {{no_edge00, new_edge01, new_edge02, new_edge03},
                                                {new_edge10, new_edge11, new_edge12, new_edge13},
                                                {new_edge20, new_edge21, new_edge22, new_edge23},
                                                {new_edge30, new_edge31, new_edge32, no_edge33}};
    int nrows_old = contour_vertices->nrows_old;
    int *row_old = contour_vertices->row_old;
    int *ncol_ranges_old = contour_vertices->ncol_ranges_old;
    int **col_start_old = contour_vertices->col_start_old;
    int **col_end_old = contour_vertices->col_end_old;
    int *col_start, *col_end;

    if ((nrows_old < 1) || (npoints0 < 2) || (npoints1 < 2)) return CCPN_OK;

    MALLOC(v_row, Contour_vertex, npoints0 - 1);

    /* first do vertices along bottom row, but this only needed if first row is i1=0 */

    r = 0;
    i1 = row_old[r];
    if (i1 == 0) {
        col_start = col_start_old[r];
        col_end = col_end_old[r];

        for (c = 0; c < ncol_ranges_old[r]; c++) {
            i0 = col_start[c];
            d_old = GET_DATA(i0, i1);
            b_old = DATA_ABOVE_LEVEL(d_old);

            for (i0 = col_start[c]; i0 < col_end[c] - 1; i0++) {
                d_new = GET_DATA(i0 + 1, i1);
                b_new = DATA_ABOVE_LEVEL(d_new);

                if (b_old ^ b_new) /* i.e. b_old != b_new */
                {
                    NEW_VERTEX0(v_row[i0], d_old, d_new, i0, i1);
                    b_old = b_new;
                }

                d_old = d_new;
            }
        }
    }

    for (r = 0; r < nrows_old; r++) {
        i1 = row_old[r];
        col_start = col_start_old[r];
        col_end = col_end_old[r];

        for (c = 0; c < ncol_ranges_old[r]; c++) {
            i0 = col_start[c];
            d_old0 = GET_DATA(i0, i1);
            d_new0 = GET_DATA(i0, i1 + 1);
            b_old = DATA_ABOVE_LEVEL(d_old0) + DATA_ABOVE_LEVEL2(d_new0);

            if ((b_old == 1) || (b_old == 2)) NEW_VERTEX1(v_col, d_old0, d_new0, i0, i1);

            new_edge = new_edge_func[b_old];
            for (i0 = col_start[c] + 1; i0 < col_end[c]; i0++) {
                d_old1 = GET_DATA(i0, i1);
                d_new1 = GET_DATA(i0, i1 + 1);
                b_new = DATA_ABOVE_LEVEL(d_old1) | DATA_ABOVE_LEVEL2(d_new1);

                edge_func = new_edge[b_new];
                CHECK_STATUS((edge_func)(contour_vertices, level, more_levels, d_old0, d_old1, d_new0, d_new1, v_row, &v_col,
                                         i0 - 1, i1));

                /*
                        if ((edge_func != no_edge00) && (edge_func != no_edge33))
                        {
                */
                b_old = b_new;
                new_edge = new_edge_func[b_old];
                /*
                        }
                */

                d_old0 = d_old1;
                d_new0 = d_new1;
            }
        }

        check_end_range(contour_vertices, npoints0);
    }

    FREE(v_row, Contour_vertex);

    return CCPN_OK;
}

static CcpnStatus process_chain(PyObject *contours, Contour_vertex v) {
    int i, k, nvertices, typenum = NPY_FLOAT;
    npy_intp dims[2];
    Contour_vertex vv;
    PyArrayObject *polyline;

    nvertices = 1;
    for (vv = v; vv->v1 && (vv->v1 != v); vv = vv->v1) {
        nvertices++;
        vv->visited = CCPN_TRUE;
    }

    vv->visited = CCPN_TRUE;

    for (v = v->v2; v && (v != vv); v = v->v2) {
        nvertices++;
        v->visited = CCPN_TRUE;
    }

    /*
        dims[0] = nvertices;
        dims[1] = 2;
        polyline = (PyArrayObject *) PyArray_SimpleNew(2, dims, typenum);
    */
    dims[0] = 2 * nvertices;
    polyline = (PyArrayObject *)PyArray_SimpleNew(1, dims, typenum);
    if (!polyline) return CCPN_ERROR;

    if (PyList_Append(contours, (PyObject *)polyline) != 0) return CCPN_ERROR;

    Py_DECREF(polyline);

    for (i = k = 0, v = vv; i < nvertices; i++, v = v->v2) {
        /*
         *((float *) (PyArray_GETPTR2(polyline, i, 0))) = v->x[0];
         *((float *) (PyArray_GETPTR2(polyline, i, 1))) = v->x[1];
         */
        *((float *)(PyArray_GETPTR1(polyline, k++))) = v->x[0];
        *((float *)(PyArray_GETPTR1(polyline, k++))) = v->x[1];
    }

    // ejb - keep a count of the number of indices/vertices
    numIndices += 2 * nvertices;
    numVertices += nvertices;

    return CCPN_OK;
}

static CcpnStatus process_chains(PyObject *contours, Contour_vertices contour_vertices) {
    int i;
    int nvertices = contour_vertices->nvertices;
    int nalloc = contour_vertices->nalloc;
    Contour_vertex v;
    Contour_vertex *vertex_store = contour_vertices->vertex_store;

    for (i = 0; i < nvertices; i++) {
        v = vertex_store[i / nalloc] + i % nalloc;
        v->visited = CCPN_FALSE;
    }

    for (i = 0; i < nvertices; i++) {
        v = vertex_store[i / nalloc] + i % nalloc;

        if (v->visited) continue;

        CHECK_STATUS(process_chain(contours, v));
    }

    return CCPN_OK;
}

static void fillContours(PyArrayObject *contours, PyArrayObject *lineColour) {
    int i, col, z, k, l, contCount = PyList_GET_SIZE(contours);
    int lineCount, fromSize, endIndex, contourCount;
    PyObject *this_contour_list;
    PyArrayObject *thisLine;
    float32 *fromArray;
    float32 *fromColour = PyArray_DATA(lineColour);

    for (l = 0; l < contCount; l++) {
        this_contour_list = PyList_GET_ITEM(contours, l);
        contourCount = PyList_GET_SIZE(this_contour_list);

        for (k = 0; k < contourCount; k++) {
            thisLine = (PyArrayObject *)PyList_GET_ITEM(this_contour_list, k);
            lineCount = PyArray_SIZE(thisLine);
            // point to the first element in this contour line
            fromArray = (float32 *)PyArray_DATA(thisLine);

            //            // duh - used lineCount in wrong place
            //            indexPTR[indexCount++] = lineCount;

            endIndex = lastIndex;
            for (i = 0, z = 0; i < (int)(lineCount / 2); i++) {
                indexPTR[indexCount++] = lastIndex++;
                indexPTR[indexCount++] = lastIndex;
                vertexPTR[vertexCount++] = fromArray[z++];
                vertexPTR[vertexCount++] = fromArray[z++];

                // copy the colour across
                for (col = 0; col < 4; col++) {
                    colourPTR[colourCount + col] = fromColour[col];
                }
                colourCount += 4;
            }
            indexPTR[indexCount - 1] = endIndex;
        }
        fromColour += 4;
    }
}

static PyObject *calculate_contours(PyArrayObject *data, PyArrayObject *levels) {
    int l, nlevels = PyArray_DIM(levels, 0), npoints1 = PyArray_DIM(data, 0);
    float level, prev_level;
    CcpnBool more_levels, are_levels_increasing;
    PyObject *contours_list, *contourlevel_list;
    Contour_vertices contour_vertices;

    if (nlevels > 1) {
        prev_level = *((float32 *)PyArray_GETPTR1(levels, 0));
        level = *((float32 *)PyArray_GETPTR1(levels, 1));
        are_levels_increasing = (prev_level <= level);

        for (l = 2; l < nlevels; l++) {
            prev_level = level;
            level = *((float32 *)PyArray_GETPTR1(levels, l));
            if (are_levels_increasing) {
                if (prev_level > level) RETURN_OBJ_ERROR("levels initially increasing but later decrease");
            } else {
                if (prev_level < level) RETURN_OBJ_ERROR("levels initially decreasing but later increase");
            }
        }
    } else {
        are_levels_increasing = CCPN_TRUE; /* arbitrary and irrelevant */
    }

    contour_vertices = new_contour_vertices(data, nlevels, are_levels_increasing);
    if (!contour_vertices) RETURN_OBJ_ERROR("allocating vertex memory");

    contours_list = PyList_New(0);
    if (!contours_list) {
        delete_contour_vertices(contour_vertices, nlevels, npoints1);
        RETURN_OBJ_ERROR("allocating contours_list memory");
    }

    for (l = 0; l < nlevels; l++) {
        contourlevel_list = PyList_New(0);
        if (!contourlevel_list) {
            Py_DECREF(contours_list);
            delete_contour_vertices(contour_vertices, nlevels, npoints1);
            RETURN_OBJ_ERROR("allocating contourlevel_list memory");
        }

        if (PyList_Append(contours_list, contourlevel_list) != 0) {
            Py_DECREF(contours_list);
            delete_contour_vertices(contour_vertices, nlevels, npoints1);
            RETURN_OBJ_ERROR("appending contourlevel_list to contours_list");
        }
        Py_DECREF(contourlevel_list);

        more_levels = (l < nlevels - 1);
        level = *((float32 *)PyArray_GETPTR1(levels, l));
        contour_vertices->nvertices = 0;

        if (find_vertices(contour_vertices, level, data, more_levels) == CCPN_ERROR) {
            Py_DECREF(contours_list);
            delete_contour_vertices(contour_vertices, nlevels, npoints1);
            RETURN_OBJ_ERROR("allocating vertex memory");
        }

        if (contour_vertices->nvertices == 0) break;

        if (process_chains(contourlevel_list, contour_vertices) == CCPN_ERROR) {
            Py_DECREF(contours_list);
            delete_contour_vertices(contour_vertices, nlevels, npoints1);
            RETURN_OBJ_ERROR("processing contourlevel_list");
        }

        if (more_levels) swap_old_new(contour_vertices);
    }

    delete_contour_vertices(contour_vertices, nlevels, npoints1);

    return contours_list;
}

static PyObject *contourer(PyObject *self, PyObject *args) {
    PyArrayObject *data_obj, *levels_obj;
    PyObject *contours;

    if (!PyArg_ParseTuple(args, "O!O!", &PyArray_Type, &data_obj, &PyArray_Type, &levels_obj))
        RETURN_OBJ_ERROR("need arguments: dataArray, levels ]");

    if (PyArray_TYPE(data_obj) != NPY_FLOAT) RETURN_OBJ_ERROR("dataArray needs to be array of floats");

    if (PyArray_NDIM(data_obj) != 2) RETURN_OBJ_ERROR("dataArray needs to be NumPy array with ndim 2");

    if (PyArray_TYPE(levels_obj) != NPY_FLOAT) RETURN_OBJ_ERROR("levelsArray needs to be array of floats");

    if (PyArray_NDIM(levels_obj) != 1) RETURN_OBJ_ERROR("levelsArray needs to be NumPy array with ndim 1");

    contours = calculate_contours(data_obj, levels_obj);

    return contours;
}

static PyObject *newList(int size) {
    PyObject *list = PyList_New(size);
    if (!list) {
        RETURN_OBJ_ERROR("allocating list memory");
    }
    return list;
}

/* not used
static PyArrayObject *newArrayList(size) {
    PyListObject *list;
    list = PyList_New(size);
    if (!list) {
        RETURN_OBJ_ERROR("allocating list memory");
    }
    return list;
}*/

static PyObject *appendFloatList(PyObject *list, double value) {
    if (PyList_Append(list, PyFloat_FromDouble((double)value)) != 0) {
        RETURN_OBJ_ERROR("appending item to list");
    }
    return NULL;
}

static PyObject *contourerGLList(PyObject *self, PyObject *args) {
    PyObject *dataArrays;
    PyArrayObject *dataArray, *posLevels, *posColour;
    PyArrayObject *negLevels, *negColour;
    PyObject *contours_list;
    //    PyObject *pos_cont_list, *neg_cont_list;
    int arr, flatten = 0;

    //    PyArrayObject *colours;

    // define an empty array to pass out
    contours_list = newList(1);

    // assumes that the parameters are all numpy arrays
    if (!PyArg_ParseTuple(args, "O!O!O!O!O!|i", &PyTuple_Type, &dataArrays, &PyArray_Type, &posLevels, &PyArray_Type,
                          &negLevels, &PyArray_Type, &posColour, &PyArray_Type, &negColour, &flatten))

        RETURN_OBJ_ERROR(
            "need arguments: dataArrays, posLevels, negLevels, posColour, negColour, optional flatten = True/False");

    //    if (PyArray_TYPE(dataArray) != NPY_FLOAT)
    //        RETURN_OBJ_ERROR("dataArray needs to be array of floats");
    //
    //    if (PyArray_NDIM(dataArray) != 2)
    //        RETURN_OBJ_ERROR("dataArray needs to be NumPy array with ndim 2");

    if (PyArray_TYPE(posLevels) != NPY_FLOAT) RETURN_OBJ_ERROR("posLevels needs to be array of floats");

    if (PyArray_NDIM(posLevels) != 1) RETURN_OBJ_ERROR("posLevels needs to be NumPy array with ndim 1");

    if (PyArray_TYPE(negLevels) != NPY_FLOAT) RETURN_OBJ_ERROR("negLevels needs to be array of floats");

    if (PyArray_NDIM(negLevels) != 1) RETURN_OBJ_ERROR("negLevels needs to be NumPy array with ndim 1");

    if (PyArray_TYPE(posColour) != NPY_FLOAT32) RETURN_OBJ_ERROR("posColour needs to be array of floats");

    if (PyArray_NDIM(posColour) != 1) RETURN_OBJ_ERROR("posColour needs to be NumPy array with ndim 1");

    if (PyArray_TYPE(negColour) != NPY_FLOAT32) RETURN_OBJ_ERROR("negColour needs to be array of floats");

    if (PyArray_NDIM(negColour) != 1) RETURN_OBJ_ERROR("negColour needs to be NumPy array with ndim 1");

    if (flatten != 0 && flatten != 1) RETURN_OBJ_ERROR("flatten must be True/False");

    //    npy_intp dims[1] = {24};
    //    colours = (PyArrayObject *) PyArray_SimpleNew(1, dims, NPY_FLOAT32);
    //    if (!colours)
    //    	return CCPN_ERROR;

    // initialise the index/vertex count
    numIndices = 0;
    numVertices = 0;
    numColours = 0;

    indexCount = 0;
    vertexCount = 0;
    colourCount = 0;

    int numArrays = PyTuple_GET_SIZE(dataArrays);
    // PyObject *pos_cont_list[numArrays], *neg_cont_list[numArrays];

    PyObject *pos_cont_list, *neg_cont_list;
    PyArrayObject *posCont, *negCont;
    pos_cont_list = newList(0);
    neg_cont_list = newList(0);

    if ((numArrays > 1) && (flatten)) {
        for (int ii = 1; ii < numArrays; ii++)
            update_bounds((PyArrayObject *)PyTuple_GET_ITEM(dataArrays, 0), (PyArrayObject *)PyTuple_GET_ITEM(dataArrays, ii));
        numArrays = 1;
    }

    for (arr = 0; arr < numArrays; arr++) {
        dataArray = (PyArrayObject *)PyTuple_GET_ITEM(dataArrays, arr);

        // get the positive contours_list
        // pos_cont_list[arr] = calculate_contours(dataArray, posLevels);
        // neg_cont_list[arr] = calculate_contours(dataArray, negLevels);

        PyList_Append(pos_cont_list, calculate_contours(dataArray, posLevels));
        PyList_Append(neg_cont_list, calculate_contours(dataArray, negLevels));
    }

    npy_intp dims[1] = {numIndices};
    indexing = (PyArrayObject *)PyArray_SimpleNew(1, dims, NPY_UINT32);
    if (!indexing) RETURN_OBJ_ERROR("Cannot create index array");

    dims[0] = 2 * numVertices;
    vertices = (PyArrayObject *)PyArray_SimpleNew(1, dims, NPY_FLOAT32);
    if (!vertices) RETURN_OBJ_ERROR("Cannot create vertex array");

    dims[0] = 4 * numVertices;
    colours = (PyArrayObject *)PyArray_SimpleNew(1, dims, NPY_FLOAT32);
    if (!colours) RETURN_OBJ_ERROR("Cannot create colour array");

    indexPTR = PyArray_GETPTR1(indexing, 0);
    vertexPTR = PyArray_GETPTR1(vertices, 0);
    colourPTR = PyArray_GETPTR1(colours, 0);
    lastIndex = 0;
    lastVertex = 0;

    for (arr = 0; arr < numArrays; arr++) {
        // fill the new arrays
        // fillContours(pos_cont_list[arr], posColour);
        // fillContours(neg_cont_list[arr], negColour);

        posCont = (PyArrayObject *)PyList_GET_ITEM(pos_cont_list, arr);
        negCont = (PyArrayObject *)PyList_GET_ITEM(neg_cont_list, arr);

        fillContours(posCont, posColour);
        fillContours(negCont, negColour);
    }

    PyObject *ind = PyLong_FromDouble(numIndices);
    PyObject *vect = PyLong_FromDouble(numVertices);

    gl_object_list = newList(5);
    PyList_SET_ITEM(gl_object_list, 0, ind);
    PyList_SET_ITEM(gl_object_list, 1, vect);
    PyList_SET_ITEM(gl_object_list, 2, (PyObject *)indexing);
    PyList_SET_ITEM(gl_object_list, 3, (PyObject *)vertices);
    PyList_SET_ITEM(gl_object_list, 4, (PyObject *)colours);

    return gl_object_list;

    //    // get the start/size of the numpy array
    //    float32 *levelPTR = PyArray_GETPTR1(colours,0);
    //    int sizeColours = (float32 *) PyArray_SIZE(colours);
    //
    ////    for (int i=0; i < sizeColours; i++, levelPTR++)
    ////    {
    ////        // fast memory accessing :)
    ////        *levelPTR = i+32;
    ////    }
    //
    //    for (int i=0; i < sizeColours; i++)
    //    {
    //        // fast memory accessing :)
    //        levelPTR[i] = i+15.765;
    //    }
    //
    //    PyList_SET_ITEM(contours_list, 0, colours);
    //
    //    return contours_list;
}

static char contourer_doc[] = "Create 2D contours for spectral data";
static char contourerGLList_doc[] = "Convert 2D contours to glList";

static struct PyMethodDef Contourer_type_methods[] = {
    {"contourer2d", (PyCFunction)contourer, METH_VARARGS, contourer_doc},
    {"contourerGLList", (PyCFunction)contourerGLList, METH_VARARGS, contourerGLList_doc},
    {NULL, NULL, 0, NULL}};

struct module_state {
    PyObject *error;
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "Contourer2d", NULL, sizeof(struct module_state), Contourer_type_methods, NULL, NULL, NULL, NULL};

PyMODINIT_FUNC PyInit_Contourer2d(void) {
    PyObject *module;

#ifdef WIN32
    Contourer.ob_type = &PyType_Type;
#endif
    /* create the module and add the functions */
    module = PyModule_Create(&moduledef);

    import_array(); /* needed for numpy, otherwise it crashes */

    /* create exception object and add to module */
    ErrorObject = PyErr_NewException("Contourer2d.error", NULL, NULL);
    Py_INCREF(ErrorObject);

    PyModule_AddObject(module, "error", ErrorObject);

    if (module == NULL) return NULL;

    struct module_state *st = (struct module_state *)PyModule_GetState(module);

    st->error = PyErr_NewException("Contourer2d.error", NULL, NULL);
    if (st->error == NULL) {
        Py_DECREF(module);
        return NULL;
    }

    /* check for errors */
    if (PyErr_Occurred()) Py_FatalError("can't initialize module Contourer2d");

    return module;
}
