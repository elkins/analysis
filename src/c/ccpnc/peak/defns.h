
/*
======================COPYRIGHT/LICENSE START==========================

defns.h: Part of the CcpNmr Analysis program

Copyright (C) 2003-2010 Wayne Boucher and Tim Stevens (University of Cambridge)

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
#ifndef _incl_defns
#define _incl_defns

#include <stdio.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#ifndef WIN32
#include <sys/types.h>
#endif /* WIN32 */

#define  READ		"r"
#define  WRITE		"w"
#define  APPEND		"a"
#define  READ_UPDATE	"r+"
#define  WRITE_UPDATE	"w+"
#define  BINARY_READ	"rb"
#define  BINARY_WRITE	"wb"
#define  BINARY_READ_UPDATE	"r+b"
#define  BINARY_WRITE_UPDATE	"w+b"

#ifndef  CCPN_TRUE
#define  CCPN_TRUE   1
#endif

#ifndef  CCPN_FALSE
#define  CCPN_FALSE  0
#endif

#ifndef  SEEK_SET
#define  SEEK_SET  0
#define  SEEK_CUR  1
#define  SEEK_END  2
#endif

#ifndef  MIN
#define  MIN(a, b)  (((a) < (b)) ? (a) : (b))
#endif
#ifndef  MAX
#define  MAX(a, b)  (((a) > (b)) ? (a) : (b))
#endif

#define  ABS(a)  (((a) < 0) ? -(a) : (a))

#define  SIGN(a)  (((a) < 0) ? -1 : 1)
#define  SIGN2(a, b)  (((b) >= 0) ? ABS(a) : -ABS(a))

#define  FLOOR(x) \
(((x) == (int) (x)) ? (int) (x) : ((x) >= 0  ?  (int) (x)  :  (- 1 - ((int) (-(x))))))

#define  CEILING(x)  (- FLOOR(-(x)))

#define  NEAREST_INTEGER(a)  (FLOOR((a) + 0.5))

#define  SWAP(a, b, type) \
	 {   type  SWAP_TMP;  SWAP_TMP = a;  a = b;  b = SWAP_TMP;  }

#define  SWAP3(a, b, c, type) \
	 {   type  SWAP_TMP;  SWAP_TMP = a;  a = b;  b = c;  c = SWAP_TMP;  }

#define  FLUSH  {   fflush(stdout);  fflush(stderr);   }

#define  OPEN_FOR_READING(fp, name) \
	 (((fp) = fopen((name), READ)) == NULL)

#define  OPEN_FOR_WRITING(fp, name) \
	 (((fp) = fopen((name), WRITE)) == NULL)

#define  OPEN_FOR_BINARY_READING(fp, name) \
	 (((fp) = fopen((name), BINARY_READ)) == NULL)

#define  OPEN_FOR_BINARY_WRITING(fp, name) \
	 (((fp) = fopen((name), BINARY_WRITE)) == NULL)

#define  OPEN_FOR_BINARY_READ_UPDATE(fp, name) \
	 (((fp) = fopen((name), BINARY_READ_UPDATE)) == NULL)

#define  OPEN_FOR_BINARY_WRITE_UPDATE(fp, name) \
	 (((fp) = fopen((name), BINARY_WRITE_UPDATE)) == NULL)

#define  CHECK_OPEN_FOR_READING(fp, name) \
	 {   if (OPEN_FOR_READING(fp, name)) \
	     {   sprintf(error_msg, "opening '%s' for reading", name); \
		 return  CCPN_ERROR;   }   }

#define  CHECK_OPEN_FOR_BINARY_READING(fp, name) \
	 {   if (OPEN_FOR_BINARY_READING(fp, name)) \
	     {   sprintf(error_msg, "opening '%s' for reading", name); \
		 return  CCPN_ERROR;   }   }

#define  CHECK_OPEN_FOR_BINARY_WRITING(fp, name) \
	 {   if (OPEN_FOR_BINARY_WRITING(fp, name)) \
	     {   sprintf(error_msg, "opening '%s' for writing", name); \
		 return  CCPN_ERROR;   }   }

#define  CHECK_OPEN_FOR_WRITING(fp, name) \
	 {   if (OPEN_FOR_WRITING(fp, name)) \
	     {   sprintf(error_msg, "opening '%s' for writing", name); \
		 return  CCPN_ERROR;   }   }

#define  FCLOSE(fp)  {   if (fp)  fclose(fp);  fp = (FILE *) NULL;   }

#ifdef  MALLOC
#undef  MALLOC
#endif
#define  MALLOC(ptr, type, num) \
	 {   if ( ((ptr)=(type *) malloc((unsigned) ((num)*sizeof(type)))) \
	           == NULL )  return  CCPN_ERROR;   }
             

#define  MALLOC_NEW(ptr, type, num) \
	 {   if ( ((ptr)=(type *) malloc((unsigned) ((num)*sizeof(type)))) \
	           == NULL )  return  NULL;   }

#define  STRING_MALLOC_COPY(string1, string2) \
	 {   int Len = strlen(string2) + 1; \
	     MALLOC(string1, char, Len); \
	     strcpy(string1, string2);   }

#define  STRING_MALLOC_NEW(string1, string2) \
	 {   int Len = strlen(string2) + 1; \
	     MALLOC_NEW(string1, char, Len); \
	     strcpy(string1, string2);   }

#define  MALLOC2(ptr, type, num1, num2) \
	 {   int LOOP_IDX; \
	     MALLOC(ptr, type *, num1); \
	     for (LOOP_IDX = 0; LOOP_IDX < num1; LOOP_IDX++) \
		 MALLOC((ptr)[LOOP_IDX], type, num2);   }

#define  MALLOC_ZERO(ptr, type, num) \
	 {   int LOOP_IDX; \
	     if ( ((ptr)=(type *) malloc((unsigned) ((num)*sizeof(type)))) \
	           				== NULL )  return  CCPN_ERROR; \
	     for (LOOP_IDX = 0; LOOP_IDX < (num); LOOP_IDX++)  (ptr)[LOOP_IDX] = (type) NULL;   }

#define  MALLOC2_ZERO(ptr, type, num1, num2) \
	 {   int J; \
	     MALLOC(ptr, type *, num1); \
	     for (J = 0; J < num1; J++) \
		 MALLOC_ZERO((ptr)[J], type, num2);   }

#ifdef  FREE
#undef  FREE
#endif
#define  FREE(ptr, type) \
	 {   if ((ptr) != (type *) NULL) \
	     {   free((type *) (ptr));  (ptr) = (type *) NULL;   }   }

#define  FREE2(ptr, type, num) \
	 {   int LOOP_IDX; \
	     if ((ptr) != (type **) NULL) \
	     {   for (LOOP_IDX = 0; LOOP_IDX < num; LOOP_IDX++) \
	             FREE((ptr)[LOOP_IDX], type); \
	     	 FREE(ptr, type *);   }   }

#ifdef  REALLOC
#undef  REALLOC
#endif
#define  REALLOC(ptr, type, num) \
	 {   type *Ptr; \
	     if ( ((Ptr)=(type *) realloc((ptr), \
		    (unsigned)((num)*sizeof(type)))) \
	               == NULL )  return  CCPN_ERROR;  else  ptr = Ptr;   }

#define  REALLOC_NEW(ptr, type, num) \
	 {   type *Ptr; \
	     if ( ((Ptr)=(type *) realloc((ptr), \
		    (unsigned)((num)*sizeof(type)))) \
	               == NULL )  return  NULL;  else  ptr = Ptr;   }

#define  ZERO_VECTOR(v, n) \
	 {   int  LOOP_IDX;  for (LOOP_IDX = 0; LOOP_IDX < (n); LOOP_IDX++)  (v)[LOOP_IDX] = 0;   }

#define  SUBTRACT_VECTORS(v1, v2, v3, n) \
	 {   int  LOOP_IDX;  for (LOOP_IDX = 0; LOOP_IDX < (n); LOOP_IDX++)  (v1)[LOOP_IDX] = (v2)[LOOP_IDX]-(v3)[LOOP_IDX];   }

#define  ADD_VECTORS(v1, v2, v3, n) \
	 {   int  LOOP_IDX;  for (LOOP_IDX = 0; LOOP_IDX < (n); LOOP_IDX++)  (v1)[LOOP_IDX] = (v2)[LOOP_IDX]+(v3)[LOOP_IDX];   }

#define  SCALE_VECTOR(v1, v2, s, n) \
	 {   int  LOOP_IDX;  for (LOOP_IDX = 0; LOOP_IDX < (n); LOOP_IDX++)  (v1)[LOOP_IDX] = (s)*(v2)[LOOP_IDX];   }

#define  INNER_PRODUCT(d, v1, v2, n) \
	 {   int  LOOP_IDX;  d = 0; \
	     for (LOOP_IDX = 0; LOOP_IDX < (n); LOOP_IDX++)  d += (v1)[LOOP_IDX]*(v2)[LOOP_IDX];   }

#define  VECTOR_PRODUCT(d, v, n) \
	 {   int  LOOP_IDX;  d = 1; \
	     for (LOOP_IDX = 0; LOOP_IDX < (n); LOOP_IDX++)  d *= (v)[LOOP_IDX];   }

#define  CROSS_PRODUCT(v1, v2, v3) \
	 {   (v1)[0] = (v2)[1]*(v3)[2] - (v2)[2]*(v3)[1]; \
	     (v1)[1] = (v2)[2]*(v3)[0] - (v2)[0]*(v3)[2]; \
	     (v1)[2] = (v2)[0]*(v3)[1] - (v2)[1]*(v3)[0];   }

#define  NEGATE_VECTOR(v1, v2, n) \
	 {   int  LOOP_IDX;  for (LOOP_IDX = 0; LOOP_IDX < (n); LOOP_IDX++)  (v1)[LOOP_IDX] = - (v2)[LOOP_IDX];   }

#define  COPY_VECTOR(v1, v2, n) \
	 {   int  LOOP_IDX;  for (LOOP_IDX = 0; LOOP_IDX < (n); LOOP_IDX++)  (v1)[LOOP_IDX] = (v2)[LOOP_IDX];   }

#define  COPY_VECTOR_FROM_TOP(v1, v2, n) \
	 {   int  LOOP_IDX;  for (LOOP_IDX = (n)-1; LOOP_IDX >= 0; LOOP_IDX--)  (v1)[LOOP_IDX] = (v2)[LOOP_IDX];   }

#define  INDEX_OF_ARRAY(index, array, cumul, n) \
	 {   INNER_PRODUCT(index, array, cumul, n);  }

#define  ARRAY_OF_INDEX(array, index, cumul, n) \
	 {   int LOOP_IDX; long Ind = index; \
	     for (LOOP_IDX = (n)-1; LOOP_IDX >= 0; LOOP_IDX--) \
	     {   array[LOOP_IDX] = Ind / cumul[LOOP_IDX];  Ind %= cumul[LOOP_IDX];   }   }

#define  CUMULATIVE(cumul, array, total, n) \
	 {   int LOOP_IDX;  total = 1; \
	     for (LOOP_IDX = 0; LOOP_IDX < n; LOOP_IDX++) \
	     {   (cumul)[LOOP_IDX] = total;  total *= (array)[LOOP_IDX];   }   }

#define  BLOCK(point, size)  ((int) (1 + ((point) - 1)/(size)))

#define  BLOCKS(blocks, points, size, n) \
	 {   int LOOP_IDX; \
	     for (LOOP_IDX = 0; LOOP_IDX < n; LOOP_IDX++) \
	     {   (blocks)[LOOP_IDX] = BLOCK((points)[LOOP_IDX], (size)[LOOP_IDX]);   }   }

#define  STRIP_LEADING_SPACE(string) \
	 {   char *Ptr1 = string, *Ptr2 = string; \
	     while (*Ptr2 && isspace(*Ptr2))  Ptr2++; \
	     while (*Ptr2)  *Ptr1++ = *Ptr2++;  *Ptr1 = 0;   }

#define  STRIP_TRAILING_SPACE(string) \
	 {   if (strlen(string)) \
	     {   char *Ptr = string + strlen(string) - 1; \
		 while ((Ptr >= string) && isspace(*Ptr))  Ptr--; \
		 *++Ptr = 0;   };   }

#define  STRIP_SPACE(string) \
	{   STRIP_LEADING_SPACE(string);   STRIP_TRAILING_SPACE(string);   }

#define  STRIP_CARRIAGE_RETURN(string) \
	 {   char *Ptr; \
	     if ((Ptr = strchr(string, '\n')) != NULL)  *Ptr = 0;   }

/* use stdout instead of stderr so that Unix novices */
/* do not lose output when running jobs in background */
#define  ERROR_AND_EXIT(message) \
	 {   fprintf(stdout, "Fatal error: %s\n", message);  exit  (1);   }

#define  ERROR_AND_RETURN_ERROR(message) \
	 {   char Msg[200]; \
	     sprintf(Msg, "Error: %s", message); \
	     print_error_message(Msg);  return  CCPN_ERROR;   }

#define  ERROR_AND_RETURN(message) \
	 {   char Msg[200]; \
	     sprintf(Msg, "Error: %s", message); \
	     print_error_message(Msg);  return;   }

#define  RETURN_ERROR_MSG(message) \
	 {   sprintf(error_msg, message);  return  CCPN_ERROR;   }

#define  RETURN_ERROR_MSG_NULL(message) \
	 {   sprintf(error_msg, message);  return  NULL;   }

#define  RETURN_WITH_ERROR(msg, fmt, vars) \
	 {   sprintf(msg, fmt, vars);  return  CCPN_ERROR;   }

#define  ERROR_AND_ABORT(message) \
	 {   fprintf(stderr, "Error: %s\n", message);  abort();   }

#define  ASSERT(expression, message) \
	 {   if (!(expression)) \
	     {   char  full_message[LINE_SIZE]; \
		 sprintf(full_message, "Assertion '%s' failed\n", message); \
		 ERROR_AND_ABORT(full_message);   }   }

#define  CHECK_STATUS(status) \
	 {   if ((status) == CCPN_ERROR)  return  CCPN_ERROR;   }

#define  CHECK_NULL(null) \
	 {   if (!(null))  return NULL;   }

#define  CHECK_STATUS_NULL(status) \
	 {   if ((status) == CCPN_ERROR)  return  NULL;   }

#define  CHECK_NULL_STATUS(null) \
	 {   if (!(null))  return  CCPN_ERROR;   }

#define  CHECK_OK(status) \
	 {   CcpnStatus S;  if ((S = (status)) != CCPN_OK)  return  S;   }

typedef enum { CCPN_OK, CCPN_ERROR } CcpnStatus;
typedef int CcpnBool;

/* TBD: more general */
typedef float float32;

#endif /* _incl_defns */
