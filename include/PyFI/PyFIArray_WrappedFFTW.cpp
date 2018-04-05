/*
 *   Copyright (C) 2014  Dignity Health
 *
 *   This program is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU Lesser General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU Lesser General Public License for more details.
 *
 *   You should have received a copy of the GNU Lesser General Public License
 *   along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *   NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
 *   AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
 *   SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
 *   PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
 *   USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
 *   LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
 *   MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
 *   SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.
 */

/**
	\file fft_utils.cpp
	\author Ryan Robison
	\author Ken Johnson - ken.johnson@asu.edu
	\date 01/24/2014
	\version $Id$

	\brief fft_utils provide simple fft routines for R2 Arrays.

	The following files are required for use with fft_utils.c
		- fftw3.h    	(included in fft_utils.h)

	when compilation is performed, the following flags must be included
		-lfftw3
		-lfftw3f
		-lpthread -lfftw3f_threads -lfftw3_threads (optional)

	\section Description
		The following library of functions generate a fft plan for
		use with the fftw3 library, perform data shifting, and excecute the fft
		plan. These functions can perform a forward or inverse fft and apply the
		appropriate scaling, handle odd or even length data sets, and handle float
		or double field inputs through the use the appropriate fft library (fftw
		or fftwf). In short, the user doesn't have to do anything except pass the
		appropriate parameters.
		- fft1 performs a 1D fft on the first dimension of an n dimensional array
		- fft2 performs a 2D fft on the first two dimensions of an n dimensional array
		- fft3 performs a 3D fft on the first three dimensions of an n dimensional array
		- fft1n performs a 1D fft on a user specified dimension of an n
			dimensional array (the user should specify dimension 0 for the first
			dimension according to C convention).

		For a forward transform (FFTW_FORWARD)
		\f[ X[k] = \sum_{n=0}^{N-1} x[n] e^{-jk(2\pi/N)n} \f]

		For an inverse transform (FFTW_BACKWARD)
		\f[ x[n] = \frac{1}{N} \sum_{k=0}^{N-1} X[k] e^{jk(2\pi/N)n} \f]

		\f[ X (k_1,k_2) = \sum_{n_1=0}^{N_1-1}\sum_{n_2=0}^{N_2-1}
			x(n_1,n_2)
			e^{-j\frac{2\pi}{N_1}n_1 k_1}
			e^{-j\frac{2\pi}{N_2}n_2 k_2}	\f]

		\f[ x(n_1,n_2) = \frac{1}{N_1 N_2} \sum_{k_1=0}^{N_1 -1}
			\sum_{k_2=0}^{N_2 -1} X (k_1,k_2) e^{j\frac{2\pi}{N_1}n_1 k_1}
			e^{j\frac{2\pi}{N_2}n_2 k_2}	\f]

		\f[ X (\mathbf{k}) = \sum_{\mathbf{n} \in R_{\mathbf{N}}}
			x(\mathbf{n}) e^{-j\mathbf{k}^T (2\pi \mathbf{N}^{-1})\mathbf{n}}	\f]

		\f[ x(\mathbf{n}) = \frac{1}{|\det \mathbf{N} |}
			\sum_{\mathbf{k} \in R_{\mathbf{n}}}
			X(\mathbf{k}) e^{j\mathbf{k}^T (2\pi \mathbf{N}^{-1})\mathbf{n}}	\f]

	\section Usage
		The user can call on any of the four following fft functions as
		shown in the following examples:
			- fft1(in,out,FFTW_FORWARD)	    :1D forward fft on dimension 1
			- fft2(in,out,FFTW_BACKWARD)    :2D inverse fft on dimensions 1 & 2
			- fft3(in,out,FFTW_BACKWARD)    :3D inverse fft on dimensions 1-3
			- fft1n(in,out,FFTW_FORWARD, 1) :1D forward fft on second dimension

		The user can also call on any of the supporting functions seperately. This
		is useful, for example, in cases in which the user is in need of shifting
		or scaling functions but wants to generate and excecute their own specific
		plan.

		The following global flags can be changed by the user:
		- global_fftFlags is type unsigned. It represents the level of planning
			efficiency that will be used by fftw in generating the plan. OPTIONS:
			FFTW_ESTIMATE (default), FFTW_MEASURE, FFTW_PATIENT, FFTW_WISDOM (not
			yet implemented).
		- global_shiftMode is type int. It specifies whether or not to use data
			shifting with the fft. OPTIONS: SHIFT_ON (default), SHIFT_OFF.

	\note FFTW is not thread safe. Problems are avoided here by locking a mutex
		before fftw calls are made, which will inherently slow down the FFTs. The exception is
		that the execute command is thread safe, if performed on datasets that use different
		memory. If full speed is desired when threading, then custom fftw calls must be made,
		creating plans before threading.

**/

#ifndef _PYFIARRAY_WRAPPEDFFTW_CPP_GUARD
#define _PYFIARRAY_WRAPPEDFFTW_CPP_GUARD

#include "PyFI/PyFIMacros.h"
#include "PyFI/PyFunctionIF.cpp"
#include "PyFI/PyFIArray.cpp"

#include <math.h>
#include <fftw3.h>
#include <string.h>
#include <inttypes.h>


/* pthreads is included for threading mutexes to protect fftw_plan creation.
 * There is no threaded code here.
 * TODO: Create a macro case for the mutex calls when excluding pthread.h is
 *          necessary (i.e. for the R2 reconstructor platform).
 */
#include <pthread.h>
// #include <boost/thread.hpp>

namespace PyFI
{

namespace FFTW
{



#define beforeFFT   	676546
#define afterFFT    	323547
#define SHIFT_ON    	754321
#define SHIFT_OFF   	237387

// stdout color
#ifdef _WIN32
    #define _fftw_PYFI_RED     "0x1B[31m"
    #define _fftw_PYFI_NOC     "0x1B[39m"
#else
    #define _fftw_PYFI_RED     "\e[31m"
    #define _fftw_PYFI_NOC     "\e[39m"
#endif

pthread_mutex_t _fftw_mutex =  PTHREAD_MUTEX_INITIALIZER;
// boost::mutex _fftw_mutex;

unsigned global_fftFlags = FFTW_ESTIMATE;
int global_shiftMode = SHIFT_ON;

/* Begin supporting functions ***************************************************/

/* Begin check_arrays function *************************************************
    * Functions: check_arrays
    * created by : Ryan Robison 2/28/2006
    * Last modified by : Ryan Robison 01/24/2014

    * Description: check_arrays is responsible for making sure that the all
      required criteria are met to perform the called fft function. The input
      and output arrays must be valid, of float or double or complex float or
      complex double type, the same size, complex or of vector length 2, and of 
      sufficient dimensionality for the called fft function. The passed 
      fftDirection must also be valid.

    * Parameters: in, out, numberDimensions, fftDirection, functionName
	* in is of Array<T> type and represents the array upon which
	the fft will be performed.
	* out is of Array<T> type and represents the array to which the
	result of the fft will be written. (in CAN BE EQUAL TO out).
	* numberDimensions is of int type and represents the number of
	dimensions required to perform the called fft function.
	* fftDirection if of int type and represents the direction of fft. It
	can be set equal to one of two constants (FFTW_FORWARD for a forward fft
	or FFTW_BACKWARD for an inverse fft) as pre-defined by the FFTW library.
	* functionName is of type char* and is the name of the called fft
	function. It is used in certain error messages.

    * Usage: the following is an example of how check_array is used:
	*check_array(in,out,2,FFTW_FORWARD,"fft2");

    * TO DO: display the calling function and line number in the error message.
*******************************************************************************/
template <class T>
void check_array(Array<T>& in, Array<T>& out, uint64_t numberDimensions, int fftDirection, const char *functionName)
{
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));

	// make certian that the input parameters are valid
	assert (in.data() != NULL && out.data() != NULL);
	if (fftDirection != FFTW_FORWARD && fftDirection != FFTW_BACKWARD)
    {
		fprintf (stderr, _fftw_PYFI_RED "for %s the fft direction must be FFTW_FORWARD or " "FFTW_BACKWARD\n" _fftw_PYFI_NOC, functionName);
		exit (1);
	}

	// make certain that the field type is real or double
	if (typeid(T) != typeid(float) && typeid(T) != typeid(double) && typeid(T) != typeid(complex<float>) && typeid(T) != typeid(complex<double>))
    {
		fprintf (stderr, _fftw_PYFI_RED "%s requires the array type to be float or double\n" _fftw_PYFI_NOC, functionName);
		exit (1);
	}

	// make certain that data is complex or the vector length is 2
	if (typeid(T) != typeid(complex <float>) && typeid(T) != typeid(complex <double>) && in.size(0) != 2)
    {
		fprintf (stderr, _fftw_PYFI_RED "%s requires complex data or the vector size to be 2\n" _fftw_PYFI_NOC, functionName);
		exit (1);
	}

	// make certain that the arrays are of the same dimensionality
	if ((in.ndim() != out.ndim()) || (in.dims_object() != out.dims_object()))
    {
		fprintf (stderr, _fftw_PYFI_RED "%s requires the input and output fields to be " "the same size\n" _fftw_PYFI_NOC, functionName);
		exit (1);
	}

	// check to make sure dimensionality is sufficient
	if ((is_complex && in.ndim() < numberDimensions) || (!is_complex && in.ndim() < numberDimensions + 1))
    {
		fprintf (stderr, _fftw_PYFI_RED "the input passed into %s needs to have a minimum of %lu dimensions\n" _fftw_PYFI_NOC, functionName, (unsigned long) numberDimensions);
		exit (1);
	}

    return;
}

/* Begin scaling function *****************************************************
    * Functions: fft_scale
    * Created by : Ryan Robison 2/28/2006
    * Last modified by : Ryan Robison 01/24/2014

    * Description: Provide the scaling for the inverse fft (i.e.
      when the fft direction is FFTW_BACKWARD).

    * Parameters: toBeScaled, scale
	* toBeScaled is of Array<T> type and represents the array on which an
	inverse fft has been performed.
	* scale is of double type and is the scale value to be applied to
	toBeScaled. The scaling for the 1D fft is 1/N, that for the 2D fft is
	1/(N*M), and so forth. For the arbitrary dimension 1D fft the scaling is
	1/N where N is the size of the dimension upon which the fft is being
	performed.

*******************************************************************************/
template<class T>
void fft_scale (Array<T>& toBeScaled, double scale)
{
	uint64_t i;
    for(i = 0; i < toBeScaled.size(); i++)
    {
        toBeScaled(i) *= scale;
    }

    return;
}


/* Begin out-of-place shift functions *****************************************
    * Functions: shift1, shift2, shift3, shift1n
    * created by : Ryan Robison, Ken Johnson 2/28/2006
    * Last modified by : Ryan Robison 01/23/2014
    */

/**
 * These functions perform an out-of-place shift on R2 Arrays. Both odd and
 * even length data sets are accounted for. In k-space, the DC value is
 * commonly placed at the middle point. In order to perform the fft using FFTW,
 * the DC value needs to be shifted to the first index (i.e. (0,0) for a 2D
 * data set). Upon completion of the fft, the first index needs to be shifted
 * back to the middle point. (This shifting is also required when going from
 * image space to k-space.) For even length data sets, the same shift can be
 * used before and after the fft operation. However, odd length data sets
 * require a different shift before and after the fft operation.
 *
 * \param shiftIn is of Array<T> type and represents the array for which shifting
 *         needs to be done.
 * \param shiftOut is of Array<T> type and represents the field to which the shifted
 * data will be written. (FOR OUT-OF-PLACE SHIFTING, shiftOut CANNOT BE EQUAL
 * TO shiftIn.)
 * \param position is of int type and represents the position of the shift in respect
 * to the fft operation. Position can be set equal to beforeFFT or afterFFT
 * which are predefined constants (see fft_utils.hpp).
 *
 * Usage: the following are examples of how the functions are used:
 * \code
 * shift1(in,out,beforeFFT); // 1D shift performed before fft
 * shift2(in,out,afterFFT); // 2D shift performed after fft
 * \endcode
 */
template<class T>
void shift1 (Array<T>& shiftIn, Array<T>& shiftOut, int position)
{
//  shift1 performs an out-of-place shift on the first dimension of the array
	uint64_t numShifts, readIndex, writeIndex, midPoint1 = 0, memSizeLeft = 0, memSizeRight = 0;
    uint64_t sizeDim1, vectorSize, shiftSize, i_start;
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));

    if(is_complex)
    {
	    sizeDim1 = shiftIn.size(0);
        vectorSize = 1;
    }
    else
    {
	    sizeDim1 = shiftIn.size(1);
	    vectorSize = 2;
    }

	// memory size and index location for the memcpy operation are dependent on
	// the position variable
	if (position == beforeFFT) 
    {
		midPoint1 = floor (sizeDim1 / 2.0);
		memSizeLeft = floor (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
		memSizeRight = ceil (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
	}
	else if (position == afterFFT) 
    {
		midPoint1 = ceil (sizeDim1 / 2.0);
		memSizeLeft = ceil (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
		memSizeRight = floor (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
	}

	// calculate size of data to be shifted and the required number of shifts
	shiftSize = sizeDim1;
	numShifts = 1;
    if(is_complex) 
        i_start = 1;
    else
        i_start = 2;
	for (uint64_t i = i_start; i < shiftIn.ndim(); i++)
    {
		numShifts *= shiftIn.size(i);
	}

	// perform shifting on data set
	for (uint64_t i = 0; i < numShifts; i++) 
    {
		readIndex = vectorSize * i * shiftSize;
		writeIndex = vectorSize * (i * shiftSize + sizeDim1 - midPoint1);
		memcpy (shiftOut.data() + writeIndex, shiftIn.data() + readIndex, memSizeLeft);

		readIndex = vectorSize * (i * shiftSize + midPoint1);
		writeIndex = vectorSize * i * shiftSize;
		memcpy (shiftOut.data() + writeIndex, shiftIn.data() + readIndex, memSizeRight);
	}
}

/**
 * 2D array shift (see shift1()).
 */
template<class T>
void shift2(Array<T>& shiftIn, Array<T>& shiftOut, int position)
{
//  shift2 performs an out-of-place shift on the first two dimensions of the array.
	uint64_t numShifts, readIndex, writeIndex, yindex1, yindex2; 
    uint64_t midPoint1 = 0, midPoint2 = 0, memSizeLeft = 0, memSizeRight = 0;
    uint64_t sizeDim1, sizeDim2, vectorSize, shiftSize, i_start;
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));

    if(is_complex)
    {
	    sizeDim1 = shiftIn.size(0);
	    sizeDim2 = shiftIn.size(1);
        vectorSize = 1;
    }
    else
    {
	    sizeDim1 = shiftIn.size(1);
	    sizeDim2 = shiftIn.size(2);
        vectorSize = 2;
    }

	// data size and index location for the memcpy operation are dependent on
	// the position variable
	if (position == beforeFFT)
    {
		midPoint1 = floor (sizeDim1 / 2.0);
		midPoint2 = floor (sizeDim2 / 2.0);
		memSizeLeft = floor (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
		memSizeRight = ceil (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
	}
	else if (position == afterFFT)
    {
		midPoint1 = ceil (sizeDim1 / 2.0);
		midPoint2 = ceil (sizeDim2 / 2.0);
		memSizeLeft = ceil (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
		memSizeRight = floor (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
	}

	// calculate size of data to be shifted and the required number of shifts
	shiftSize = sizeDim1 * sizeDim2;
	numShifts = 1;
    if(is_complex) 
        i_start = 2;
    else
        i_start = 3;
	for (uint64_t i = i_start; i < shiftIn.ndim(); i++)
    {
		numShifts *= shiftIn.size(i);
	}

	// perform shifting on data set
	for (uint64_t i = 0; i < numShifts; i++)
    {
		for (uint64_t j = 0; j < sizeDim2; j++)
        {
			yindex1 = vectorSize * (i * shiftSize + j * sizeDim1);
			yindex2 = vectorSize * (i * shiftSize + ((j + midPoint2) % sizeDim2) * sizeDim1);

			readIndex = yindex2;
			writeIndex = yindex1 + vectorSize * (sizeDim1 - midPoint1);
			memcpy (shiftOut.data() + writeIndex, shiftIn.data() + readIndex, memSizeLeft);

			readIndex = yindex2 + vectorSize * midPoint1;
			writeIndex = yindex1;
			memcpy (shiftOut.data() + writeIndex, shiftIn.data() + readIndex, memSizeRight);
		}
	}
}

/**
 * 3D array shift (see shift1()).
 */
template<class T>
void shift3 (Array<T>& shiftIn, Array<T>& shiftOut, int position)
{
//  shift3 performs an out-of-place shift on the first three dimensions of the array
	uint64_t numShifts, readIndex, writeIndex, yindex1, yindex2, zindex1, zindex2; 
    uint64_t midPoint1 = 0, midPoint2 = 0, midPoint3 = 0, memSizeLeft = 0, memSizeRight = 0;
    uint64_t sizeDim1, sizeDim2, sizeDim3, vectorSize, shiftSize, i_start;
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));

    if(is_complex)
    {
	    sizeDim1 = shiftIn.size(0);
	    sizeDim2 = shiftIn.size(1);
	    sizeDim3 = shiftIn.size(2);
        vectorSize = 1;
    }
    else
    {
	    sizeDim1 = shiftIn.size(1);
	    sizeDim2 = shiftIn.size(2);
	    sizeDim3 = shiftIn.size(3);
        vectorSize = 2;
    }

	// data size and index location for the memcpy operation are dependent on
	// the position variable
	if (position == beforeFFT)
    {
		midPoint1 = floor (sizeDim1 / 2.0);
		midPoint2 = floor (sizeDim2 / 2.0);
		midPoint3 = floor (sizeDim3 / 2.0);
		memSizeLeft = floor (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
		memSizeRight = ceil (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
	}
	else if (position == afterFFT)
    {
		midPoint1 = ceil (sizeDim1 / 2.0);
		midPoint2 = ceil (sizeDim2 / 2.0);
		midPoint3 = ceil (sizeDim3 / 2.0);
		memSizeLeft = ceil (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
		memSizeRight = floor (sizeDim1 / 2.0) * sizeof(T) * vectorSize;
	}

	// calculate size of data to be shifted and the required number of shifts
	shiftSize = sizeDim1 * sizeDim2 * sizeDim3;
	numShifts = 1;
    if(is_complex) 
        i_start = 3;
    else
        i_start = 4;
	for (uint64_t i = i_start; i < shiftIn.ndim(); i++)
    {
		numShifts *= shiftIn.size(i);
	}

	// perform shifting on data set
	for (uint64_t i = 0; i < numShifts; i++)
    {
		for (uint64_t k = 0; k < sizeDim3; k++)
        {
			zindex1 = vectorSize * (i * shiftSize + k * sizeDim1 * sizeDim2);
			zindex2 = vectorSize * (i * shiftSize + ((k + midPoint3) % sizeDim3) * sizeDim1 * sizeDim2);
			for (uint64_t j = 0; j < sizeDim2; j++)
            {
				yindex1 = vectorSize * j * sizeDim1;
				yindex2 = vectorSize * ((j + midPoint2) % sizeDim2) * sizeDim1;

				readIndex = zindex2 + yindex2;
				writeIndex = zindex1 + yindex1 + vectorSize * (sizeDim1 - midPoint1);
				memcpy (shiftOut.data() + writeIndex, shiftIn.data() + readIndex, memSizeLeft);

				readIndex = zindex2 + yindex2 + vectorSize * midPoint1;
				writeIndex = zindex1 + yindex1;
				memcpy (shiftOut.data() + writeIndex, shiftIn.data() + readIndex, memSizeRight);
			}
		}
	}
}

/**
 * 1D array shift in any dimension (see shift1()).
 */
template<class T>
void shift1n (Array<T>& shiftIn, Array<T>& shiftOut, int position, uint64_t fftDim)
{
//  shift1nf performs an out-of-place shift on a specified dimension of the array
	uint64_t numShifts, readIndex, writeIndex, stride;
    uint64_t midPoint = 0, memSizeLeft = 0, memSizeRight = 0;
    uint64_t sizeDim, vectorSize, shiftSize, i_start;
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));

	// calculate size of data to be shifted and the required number of shifts
    if(is_complex)
    {
        vectorSize = 1;
    }
    else
    {
        fftDim = fftDim + 1;
	    vectorSize = 2;
    }

	sizeDim = shiftIn.size(fftDim);


	stride = 1;
    if(is_complex) 
        i_start = 0;
    else
        i_start = 1;
	for (uint64_t i = i_start; i < fftDim; i++)
    {
		stride *= shiftIn.size(i);
	}
	shiftSize = stride * shiftIn.size(fftDim);
	numShifts = 1;
	for (uint64_t i = fftDim + 1; i < shiftIn.ndim(); i++)
    {
		numShifts *= shiftIn.size(i);
	}

	// data size and index location for the memcpy operation are dependent on
	// the position variable
	if (position == beforeFFT)
    {
		midPoint = floor (sizeDim / 2.0) * stride;
		memSizeLeft = floor (sizeDim / 2.0) * sizeof(T) * vectorSize * stride;
		memSizeRight = ceil (sizeDim / 2.0) * sizeof(T) * vectorSize * stride;
	}
	else if (position == afterFFT)
    {
		midPoint = ceil (sizeDim / 2.0) * stride;
		memSizeLeft = ceil (sizeDim / 2.0) * sizeof(T) * vectorSize * stride;
		memSizeRight = floor (sizeDim / 2.0) * sizeof(T) * vectorSize * stride;
	}

	// perform shifting on data set
	for (uint64_t i = 0; i < numShifts; i++) 
    {
		readIndex = vectorSize * i * shiftSize;
		writeIndex = vectorSize * (i * shiftSize + sizeDim * stride - midPoint);
		memcpy (shiftOut.data() + writeIndex, shiftIn.data() + readIndex, memSizeLeft);

		readIndex = vectorSize * (i * shiftSize + midPoint);
		writeIndex = vectorSize * i * shiftSize;
		memcpy (shiftOut.data() + writeIndex, shiftIn.data() + readIndex, memSizeRight);
	}
}

/* End supporting functions **************************************************/

/* Begin of fft main functions ***********************************************/
/*
	\author Ken Johnson - ken.johnson@asu.edu
	\author Ryan Robison
	\date 2/27/2006
    \modified 01/23/2014
*/

/**
 * These functions perform the called fft on the data. They are responsible for
 * generating the fft plan (for FFTW), calling on the appropriate shifting
 * functions, and executing the fft plan (using FFTW functions). The fftw
 * advanced interface is used for fft1, fft2, and fft3, while the fftw guru
 * interface is used for fft1n. If the global_shiftMode flag is set to
 * SHIFT_OFF, the following functions will perform an fft without shifting the
 * data. 
 * 
 * \param in Represents the array upon which the fft will be performed.
 * \param out Represents the array to which the result of the fft will be
 * written. (in CAN BE EQUAL TO out).
 * \param fftDirection Represents the direction of fft. It can be set equal to
 * one of two constants (FFTW_FORWARD for a forward fft or FFTW_BACKWARD for an
 * inverse fft) as pre-defined by the FFTW library.
*/
template<class T>
void fft1 (Array<T>& in, Array<T>& out, int fftDirection)
{
//  fft1 performs a 1D fft on the first dimension of an array.
	int dist, howmany, dims[1]; // required int by fft IF
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));
    bool is_double = (typeid(T) == typeid(double) || typeid(T) == typeid(complex<double>));
    double scale;
	fftwf_plan planF;
	fftw_plan planD;

	// check input parameters
	check_array (in, out, 1, fftDirection, "fft1");

	// Allocate temp array
	Array<T> temp(in.dims_object());

	// arrange the dimensions appropriately for use with fftw
    if(is_complex)
    {
	    dims[0] = (int) in.size(0);
	    dist = dims[0]; // distance between successive ffts
	    howmany = (int) in.size() / dims[0];	// number of ffts to be performed
    }
    else
    {
        dims[0] = (int) in.size(1);
	    dist = dims[0]; // distance between successive ffts
	    howmany = (int) (in.size()/2) / dist;	// number of ffts to be performed
    }


	// generate plan according to fftw advanced interface
	pthread_mutex_lock(&_fftw_mutex);
	// _fftw_mutex.lock();
    if(is_double)
    {
	    planD = fftw_plan_many_dft (1, dims, howmany, reinterpret_cast<fftw_complex*> (temp.data()), NULL, 1, dist, reinterpret_cast<fftw_complex*> (temp.data()), NULL, 1, dist, fftDirection, global_fftFlags);
    }
    else
    {
	    planF = fftwf_plan_many_dft (1, dims, howmany, reinterpret_cast<fftwf_complex*> (temp.data()), NULL, 1, dist, reinterpret_cast<fftwf_complex*> (temp.data()), NULL, 1, dist, fftDirection, global_fftFlags);
    }
	pthread_mutex_unlock(&_fftw_mutex);
    // _fftw_mutex.unlock();
	
	// call shifting routines (if SHIFT_ON) and execute fft
	if (global_shiftMode == SHIFT_ON)
		shift1 (in, temp, beforeFFT);
	else
		memcpy (temp.data(), in.data(), 2 * in.size() * sizeof (T));

    if(is_double)
	    fftw_execute (planD);
    else
	    fftwf_execute (planF);

	if (global_shiftMode == SHIFT_ON)
		shift1 (temp, out, afterFFT);
    else
		memcpy (out.data(), temp.data(), 2 * in.size() * sizeof (T));

	// destroy allocated memory
	pthread_mutex_lock(&_fftw_mutex);
	// _fftw_mutex.lock();
    if(is_double)
	    fftw_destroy_plan (planD);
    else
	    fftwf_destroy_plan (planF);
	pthread_mutex_unlock(&_fftw_mutex);
	// _fftw_mutex.unlock();

	// scale fft result if inverse fft is performed
	if (fftDirection == FFTW_BACKWARD) 
    {
		scale = 1. / dist;
		fft_scale (out, scale);
	}

    return;
}

/**
 * 2D fft (see fft1).
 */
template<class T>
void fft2 (Array<T>& in, Array<T>& out, int fftDirection)
{
//  fft2 performs a 2D fft on the first two dimensions of an array
	int dist, howmany, dims[2]; // required int by fft IF
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));
    bool is_double = (typeid(T) == typeid(double) || typeid(T) == typeid(complex<double>));
    double scale;
	fftwf_plan planF;
	fftw_plan planD;

	// check input parameters
	check_array (in, out, 2, fftDirection, "fft2");

	// Allocate temp array
	Array<T> temp(in.dims_object());

	// arrange the dimensions appropriately for use with fftw
    if(is_complex)
    {
	    dims[0] = (int) in.size(1);
	    dims[1] = (int) in.size(0);
	    dist = dims[0] * dims[1]; // distance between successive ffts
	    howmany = (int) in.size() / dist;	// number of ffts to be performed
    }
    else
    {
        dims[0] = (int) in.size(2);
        dims[1] = (int) in.size(1);
	    dist = dims[0] * dims[1]; // distance between successive ffts
	    howmany = ((int) in.size()/2) / dist;	// number of ffts to be performed
    }
	

	// generate plan according to fftw advanced interface
	pthread_mutex_lock(&_fftw_mutex);
	// _fftw_mutex.lock();
    if(is_double)
    {
	    planD = fftw_plan_many_dft (2, dims, howmany, reinterpret_cast<fftw_complex*> (temp.data()), NULL, 1, dist, reinterpret_cast<fftw_complex*> (temp.data()), NULL, 1, dist, fftDirection, global_fftFlags);
    }
    else
    {
	    planF = fftwf_plan_many_dft (2, dims, howmany, reinterpret_cast<fftwf_complex*> (temp.data()), NULL, 1, dist, reinterpret_cast<fftwf_complex*> (temp.data()), NULL, 1, dist, fftDirection, global_fftFlags);
    }
	pthread_mutex_unlock(&_fftw_mutex);
	// _fftw_mutex.unlock();

	// call shifting routines (if SHIFT_ON) and execute fft
	if (global_shiftMode == SHIFT_ON)
		shift2 (in, temp, beforeFFT);
	else
		memcpy (temp.data(), in.data(), 2 * in.size() * sizeof (T));

    if(is_double)
	    fftw_execute (planD);
    else
	    fftwf_execute (planF);

	if (global_shiftMode == SHIFT_ON)
		shift2 (temp, out, afterFFT);
    else
		memcpy (out.data(), temp.data(), 2 * in.size() * sizeof (T));

	// destroy allocated memory
	pthread_mutex_lock(&_fftw_mutex);
	// _fftw_mutex.lock();
    if(is_double)
	    fftw_destroy_plan (planD);
    else
	    fftwf_destroy_plan (planF);
	pthread_mutex_unlock(&_fftw_mutex);
	// _fftw_mutex.unlock();

	// scale fft result if inverse fft is performed
	if (fftDirection == FFTW_BACKWARD) 
    {
		scale = 1. / dist;
		fft_scale (out, scale);
	}

    return;
}

/**
 * 3D fft (see fft1).
 */
template<class T>
void fft3 (Array<T>& in, Array<T>& out, int fftDirection)
{
//  fft3 performs a 3D fft on the first three dimensions of an array
	int dist, howmany, dims[3]; // required int by fft IF
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));
    bool is_double = (typeid(T) == typeid(double) || typeid(T) == typeid(complex<double>));
    double scale;
	fftwf_plan planF;
	fftw_plan planD;

	// check input parameters
	check_array (in, out, 3, fftDirection, "fft3");

	// Allocate temp array
	Array<T> temp(in.dims_object());

	// arrange the dimensions appropriately for use with fftw
    if(is_complex)
    {
	    dims[0] = (int) in.size(2);
	    dims[1] = (int) in.size(1);
	    dims[2] = (int) in.size(0);
	    dist = dims[0] * dims[1] * dims[2]; // distance between successive ffts
	    howmany = (int) in.size() / dist;	// number of ffts to be performed
    }
    else
    {
        dims[0] = (int) in.size(3);
        dims[1] = (int) in.size(2);
        dims[2] = (int) in.size(1);
	    dist = dims[0] * dims[1] * dims[2]; // distance between successive ffts
	    howmany = ((int) in.size()/2) / dist;	// number of ffts to be performed
    }
	

	// generate plan according to fftw advanced interface
	pthread_mutex_lock(&_fftw_mutex);
	// _fftw_mutex.lock();
    if(is_double)
    {
	    planD = fftw_plan_many_dft (3, dims, howmany, reinterpret_cast<fftw_complex*> (temp.data()), NULL, 1, dist, reinterpret_cast<fftw_complex*> (temp.data()), NULL, 1, dist, fftDirection, global_fftFlags);
    }
    else
    {
	    planF = fftwf_plan_many_dft (3, dims, howmany, reinterpret_cast<fftwf_complex*> (temp.data()), NULL, 1, dist, reinterpret_cast<fftwf_complex*> (temp.data()), NULL, 1, dist, fftDirection, global_fftFlags);
    }
	pthread_mutex_unlock(&_fftw_mutex);
	// _fftw_mutex.unlock();
	
	// call shifting routines (if SHIFT_ON) and execute fft
	if (global_shiftMode == SHIFT_ON)
		shift3 (in, temp, beforeFFT);
	else
		memcpy (temp.data(), in.data(), 2 * in.size() * sizeof (T));

    if(is_double)
	    fftw_execute (planD);
    else
	    fftwf_execute (planF);

	if (global_shiftMode == SHIFT_ON)
		shift3 (temp, out, afterFFT);
    else
		memcpy (out.data(), temp.data(), 2 * in.size() * sizeof (T));

	// destroy allocated memory
	pthread_mutex_lock(&_fftw_mutex);
	// _fftw_mutex.lock();
    if(is_double)
	    fftw_destroy_plan (planD);
    else
	    fftwf_destroy_plan (planF);
	pthread_mutex_unlock(&_fftw_mutex);
    // _fftw_mutex.unlock();

	// scale fft result if inverse fft is performed
	if (fftDirection == FFTW_BACKWARD) 
    {
		scale = 1. / dist;
		fft_scale (out, scale);
	}

    return;
}

/**
 * 1D fft in any dimension (see fft1).
 */
template<class T>
void fft1n (Array<T>& in, Array<T>& out, int fftDirection, uint64_t fftDim)
{
//  fft1 performs a 1D fft on the first dimension of an array.
	uint64_t N, index, stride, i_start;
    bool is_complex = (typeid(T) != typeid(float) && typeid(T) != typeid(double));
    bool is_double = (typeid(T) == typeid(double) || typeid(T) == typeid(complex<double>));
    double scale;
	fftwf_plan planF;
	fftw_plan planD;
	fftwf_iodim dims;
	fftwf_iodim howmany_dims[20];

	// check input parameters
	check_array (in, out, fftDim, fftDirection, "fft1");

	// Allocate temp array
	Array<T> temp(in.dims_object());

	//  *** create guru parameters **
    if(is_complex)
    {
        N = in.size(fftDim);
        i_start = 0;
    }
    else
    {
        N = in.size(fftDim + 1);
        i_start = 1;
    }

	stride = 1;
	for (uint64_t i = i_start; i < fftDim + i_start; i++)
    {
		stride *= in.size(i);
	}

	dims.n = (int) N;
	dims.is = dims.os = (int) stride;

	index = 0;
	stride = 1;
	for (uint64_t i = i_start; i < in.ndim(); i++)
    {
		howmany_dims[index].n = (int) in.size(i);
		howmany_dims[index].is = howmany_dims[index].os = (int) stride;

		stride *= in.size(i);
		if (i != fftDim)
			index++;
	}
	// *** end guru parameters **

	// generate plan according to fftw guru interface
	pthread_mutex_lock(&_fftw_mutex);
	// _fftw_mutex.lock();
    if(is_double)
    {
	    planD = fftw_plan_guru_dft (1, &dims, (int) (in.ndim() - i_start - 1), howmany_dims, reinterpret_cast<fftw_complex*> (temp.data()), reinterpret_cast<fftw_complex*> (temp.data()), fftDirection, global_fftFlags);
    }
    else
    {
	    planF = fftwf_plan_guru_dft (1, &dims, (int) (in.ndim() - i_start - 1), howmany_dims, reinterpret_cast<fftwf_complex*> (temp.data()), reinterpret_cast<fftwf_complex*> (temp.data()), fftDirection, global_fftFlags);
    }
	pthread_mutex_unlock(&_fftw_mutex);
    // _fftw_mutex.unlock();

	// call shifting routines (if SHIFT_ON) and execute fft
	if (global_shiftMode == SHIFT_ON)
		shift1n (in, temp, beforeFFT, fftDim);
	else
		memcpy (temp.data(), in.data(), 2 * in.size() * sizeof (T));

    if(is_double)
	    fftw_execute (planD);
    else
    {
	    fftwf_execute (planF);
    }

	if (global_shiftMode == SHIFT_ON)
		shift1n (temp, out, afterFFT, fftDim);
    else
		memcpy (out.data(), temp.data(), 2 * in.size() * sizeof (T));

	// destroy allocated memory
	pthread_mutex_lock(&_fftw_mutex);
	// _fftw_mutex.lock();
    if(is_double)
	    fftw_destroy_plan (planD);
    else
    {
	    fftwf_destroy_plan (planF);
    }
    pthread_mutex_unlock(&_fftw_mutex);
	// _fftw_mutex.unlock();

	// scale fft result if inverse fft is performed
	if (fftDirection == FFTW_BACKWARD) 
    {
		scale = 1. / N;
		fft_scale (out, scale);
	}
    return;
}

/* End of fft main functions **************************************************/

} // namespace
} // namespace

#endif // GUARD
