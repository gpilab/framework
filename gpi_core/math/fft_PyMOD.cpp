/*
 * Copyright (c) 2014, Dignity Health
 * 
 *     The GPI core node library is licensed under
 * either the BSD 3-clause or the LGPL v. 3.
 * 
 *     Under either license, the following additional term applies:
 * 
 *         NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL
 * PURPOSES AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
 * SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
 * PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
 * USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED
 * TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO
 * WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY
 * HIGH RISK OR STRICT LIABILITY ACTIVITIES.
 * 
 *     If you elect to license the GPI core node library under the LGPL the
 * following applies:
 * 
 *         This file is part of the GPI core node library.
 * 
 *         The GPI core node library is free software: you can redistribute it
 * and/or modify it under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 3 of the License,
 * or (at your option) any later version. GPI core node library is distributed
 * in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
 * the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU Lesser General Public License for more details.
 * 
 *         You should have received a copy of the GNU Lesser General Public
 * License along with the GPI core node library. If not, see
 * <http://www.gnu.org/licenses/>.
 */


/**
	\file fft.cpp
	\author Nick Zwart
	\date 2010.05.20

	\brief fftw up to 6D

        Takes in float 2vec data in the fld (io_field.c) format and can zerofill before transforming in any dir
        for up to a 6D set.

 **/

#include "PyFI/PyFI.h"
#include "multiproc/threads.c"
using namespace PyFI; // provides FFTW namespace
using namespace PyFI::FFTW;

#include <pthread.h>
#include <math.h>   // for sqrt(), log(), and sin(), pow()
#include <time.h>   // for getting sys time to the sec

#define NINT(x)  x>=0? (int)(x+0.5): (int)(x-0.5)

/**
	\warning WHILE THREADED, the planning is currently mutexed, so some speed improvements are not seen
**/
void fft1_thread (int *num_threads, int *cur_thread, Array<complex<float> >& in, Array<complex<float> >& out, int *fftDirection)	{
	assert (in.data() != NULL && out.data() != NULL);
	assert (*num_threads > 0);

	uint64_t total_size = in.size();
	uint64_t numreps = total_size / in.size(0);
	uint64_t start = *cur_thread * numreps / *num_threads;
	uint64_t stop = (*cur_thread+1) * numreps / *num_threads;
    uint64_t stride = in.size(0);

	Array<complex<float> > tmp(in.size(0));

	for (uint64_t i=start; i<stop; i++)	
    {
        memcpy(tmp.data(), in.data() + stride * i, stride * sizeof(complex<float> ));
		fft1 (tmp, tmp, *fftDirection);
        memcpy(out.data() + stride * i, tmp.data(), stride * sizeof(complex<float> ));
	}
}
void fft1_threaded (int num_threads, Array<complex<float> > *in, Array<complex<float> > *out, int fftDirection)	
{
	create_threads3 (num_threads, fft1_thread, in, out, &fftDirection);
}
void fft2_thread (int *num_threads, int *cur_thread, Array<complex<float> >& in, Array<complex<float> >& out, int *fftDirection)	
{
	assert (in.data() != NULL && out.data() != NULL);
	assert (*num_threads > 0);

	uint64_t total_size = in.size();
	uint64_t numreps = total_size / (in.size(0) * in.size(1));
	uint64_t start = *cur_thread * numreps / *num_threads;
	uint64_t stop = (*cur_thread+1) * numreps / *num_threads;
    uint64_t stride = in.size(0) * in.size(1);

	Array<complex<float> > tmp(in.size(0), in.size(1));

	for (uint64_t i=start; i<stop; i++)	
    {
        memcpy(tmp.data(), in.data() + stride * i, stride * sizeof(complex<float> ));
		fft2 (tmp, tmp, *fftDirection);
        memcpy(out.data() + stride * i, tmp.data(), stride * sizeof(complex<float> ));
	}
}
void fft2_threaded (int num_threads, Array<complex<float> > *in, Array<complex<float> > *out, int fftDirection)	
{
	create_threads3 (num_threads, fft2_thread, in, out, &fftDirection);
}
void fft3_thread (int *num_threads, int *cur_thread, Array<complex<float> >& in, Array<complex<float> >& out, int *fftDirection)	
{
	assert (in.data() != NULL && out.data() != NULL);
	assert (*num_threads > 0);

	uint64_t total_size = in.size();
	uint64_t numreps = total_size / (in.size(0) * in.size(1) * in.size(2));
	uint64_t start = *cur_thread * numreps / *num_threads;
	uint64_t stop = (*cur_thread+1) * numreps / *num_threads;
    uint64_t stride = in.size(0) * in.size(1) * in.size(2);

	Array<complex<float> > tmp(in.size(0), in.size(1), in.size(2));

	for (uint64_t i=start; i<stop; i++)	
    {
        memcpy(tmp.data(), in.data() + stride * i, stride * sizeof(complex<float> ));
		fft3 (tmp, tmp, *fftDirection);
        memcpy(out.data() + stride * i, tmp.data(), stride * sizeof(complex<float> ));
	}
}
void fft3_threaded (int num_threads, Array<complex<float> > *in, Array<complex<float> > *out, int fftDirection)	
{
	create_threads3 (num_threads, fft3_thread, in, out, &fftDirection);
}




/* FFT
 *
 */
PYFI_FUNC(fftw)
{
    PYFI_START(); /* This must be the first line */

    /***** POSITIONAL ARGS */
    PYFI_POSARG(Array<complex <float> >, in);
    PYFI_POSARG(Array<int64_t>, outdim);

    /***** KEYWORD ARGS */
    PYFI_KWARG(int64_t, dir, 0);  //"fft direction for all transformed dims (0:FORWARD, 1:BACKWARD) (default:0)"
    /* these are the dims to actually perform transform on */
    PYFI_KWARG(int64_t, dim1, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim2, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim3, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim4, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim5, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim6, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim7, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim8, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim9, 0);  //"toggle for fft perform"
    PYFI_KWARG(int64_t, dim10, 0);  //"toggle for fft perform"

    /***** ALLOCATE OUTPUT */
    PYFI_SETOUTPUT_ALLOC(Array<complex <float> >, out, DA(*outdim));

    /***** PERFORM */
	// set the clock timing
	struct timespec ttime;
	double c0 = ttime.tv_sec + 0.000000001 * (uint64_t) ttime.tv_nsec;

    /* fft measurement type */
    int fftMeasureType = 1;// "Measurements made before fft. 1:ESTIMATE, 2:MEASURE, 3:PATIENT, 4:EXHAUSTIVE (default:1)")

    int verbose = 0;
	int num_threads = 8;
	int threads = num_threads;

	//char *choice_flags;
	char *wisdom_file=NULL;

	// create threading
	fftw_init_threads();
	fftw_plan_with_nthreads(threads);
	// import wisdom from a file if specified
	if (wisdom_file != NULL)	
    {
		FILE *wis_import;
		wis_import = fopen(wisdom_file,"r");
		// if the file could not be opened, that's ok we will write it later
		if (wis_import != NULL)	
        {
			fftwf_import_wisdom_from_file(wis_import);
			fclose(wis_import);
		}
	}

    // copy input data into output Array in centered manner
    *out = (complex<float>) 0;
    out->insert(*in);

	int direction = FFTW_FORWARD;
	if (*dir == 1)	
    {
		direction = FFTW_BACKWARD;
	}

    switch ( fftMeasureType )	
    {
	    case 1:
		    global_fftFlags = FFTW_ESTIMATE;
		    break;
	    case 2:
		    global_fftFlags = FFTW_MEASURE;
		    break;
	    case 3:
	    	global_fftFlags = FFTW_PATIENT;
	    	break;
	    case 4:
	    	global_fftFlags = FFTW_EXHAUSTIVE;
	    	break;
	    default:
		printf(_PYFI_RED "fft.c: error, flag choice not found\n" _PYFI_NOC);
		exit(1);
	}

	// more timing stuff
	double cprep = ttime.tv_sec + 0.000000001 * (uint64_t) ttime.tv_nsec;

	// do the fft in every lower direction specified
	if (*dim1 == 1 && *dim2 == 1 && *dim3 == 1)	
    {
 		fft3_threaded (threads, out, out, direction);
		//fft3 (*out, *out, direction);
	}
	else if (*dim1 == 1 && *dim2 == 1)
    {
		//fft2(*out, *out, direction);
		fft2_threaded (threads, out, out, direction);
    }
	else	
    {
		if (*dim1 == 1)
			//fft1 (*out, *out, direction);
			fft1_threaded (threads, out, out, direction);
		if (*dim2 == 1)
			fft1n (*out, *out, direction, 1);
		if (*dim3 == 1)
			fft1n (*out, *out, direction, 2);
	}

	// do the fft in upper directions as specified
	if (*dim4 == 1)
		fft1n (*out, *out, direction, 3);
	if (*dim5 == 1)
		fft1n (*out, *out, direction, 4);
	if (*dim6 == 1)
		fft1n (*out, *out, direction, 5);
  if (*dim7 == 1)
    fft1n (*out, *out, direction, 6);
  if (*dim8 == 1)
    fft1n (*out, *out, direction, 7);
  if (*dim9 == 1)
    fft1n (*out, *out, direction, 8);
  if (*dim10 == 1)
    fft1n (*out, *out, direction, 9);

	// more timing stuff
	//clock_gettime (CLOCK_MONOTONIC, &ttime);
	double cpost = ttime.tv_sec + 0.000000001 * (uint64_t) ttime.tv_nsec;

	// export wisdom to a file if specified
	if (wisdom_file != NULL)	{
		FILE *wis_export;
		wis_export = fopen(wisdom_file,"w");
		if (wis_export != NULL)	{
			fftwf_export_wisdom_to_file(wis_export);
			fclose(wis_export);
		}
		else	
        {
            printf("wisdom file could not be written\n");
		}
	}

	// print the timing stuff if necessary
	double ctime = ttime.tv_sec + 0.000000001 * (uint64_t) ttime.tv_nsec;
	double ccpu = ttime.tv_sec + 0.000000001 * (uint64_t) ttime.tv_nsec;
	if (verbose)	
    {
		printf("Elapsed %3.2f sec, CPU %3.2f sec, Prep %3.2f sec, FFT %3.2f sec, Post %3.2f sec\n", ctime-c0, ccpu, cprep-c0, cpost-cprep, ctime-cpost);
	}

    PYFI_END(); /* This must be the last line */
}

/* ##############################################################
 * ##############################################################
 *                  MODULE DESCRIPTION
 * ##############################################################
 * ############################################################## */


/* list of functions to be accessible from python
 */
PYFI_LIST_START_
    PYFI_DESC(fftw, "FFT routine. Wraps fftw using fft_utils.")
PYFI_LIST_END_
