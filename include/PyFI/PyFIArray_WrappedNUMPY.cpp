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

#ifndef _PYFIARRAY_WRAPPEDNUMPY_CPP_GUARD
#define _PYFIARRAY_WRAPPEDNUMPY_CPP_GUARD
/**
    \brief Wrap Numpy calls to be used in c++.
**/


#include "PyFI/PyFIMacros.h"
#include "PyFI/PyFunctionIF.cpp"
#include "PyFI/PyFIArray.cpp"

namespace PyFI
{
namespace Numpy
{

/**
 * Pseudo inverse from the numpy.linalg package.
 * 
 * \param A A 2D Array to be inverted.
 * \return The pseudo inverse of \a A.
 */
template<class T>
Array<T> pinv(Array<T> &A)
{
    PyFI::PyCallable pinv("numpy.linalg", "pinv");
    pinv.SetArg_Array(&A);
    Array<T> *out=NULL;
    pinv.GetReturn_Array(&out);

    /* copy before PyCallable falls out of scope */
    Array<T> out_copy(*out); 
    return out_copy;
}

/** The numpy.linalg.cond() function.
 *
 * To check the condition numbers before running pinv.
 *
 * \param A A 2D Array to be inverted.
 * \return The condition of \a A.
 */
template<class T>
double cond(Array<T> &A)
{
    PyFI::PyCallable cnd("numpy.linalg", "cond");
    cnd.SetArg_Array(&A);
    return cnd.GetReturn_Double();
}

/** 
 * Write an Array to a numpy formatted file.
 *
 * \param fname A standard template library string containing a valid filename.
 * \param A An Array to be written to file.
 */
template<class T>
void writeNPY(const std::string fname, Array<T> &A)
{
    PyFI::PyCallable obj("numpy", "save");
    obj.SetArg_String(fname);
    obj.SetArg_Array(&A);
    obj.Run();
}


/** 
 * Run a 1D numpy.fft on the input Array.
 *
 * \param in An Array reference. 
 * \param forward The FFT direction.
 * \return A new Array containing the transform result.
 */
#define FFT_NUMPY_FORWARD true
#define FFT_NUMPY_BACKWARD false
template<class T>
Array<T> fft1(Array<T> &in, bool forward)
{
    string code;

    if (forward)
    {
        code = "def func(in1):\n"
               "    from numpy.fft import fft, fftshift, ifftshift\n"
               "    return fftshift( fft( ifftshift(in1) ) ).astype(in1.dtype)\n";
    }
    else
    {
        code = "def func(in1):\n"
               "    from numpy.fft import ifft, fftshift, ifftshift\n"
               "    return fftshift( ifft( ifftshift(in1) ) ).astype(in1.dtype)\n";
    }

    PyCallable fft_script(code);
    fft_script.SetArg_Array(&in);
    Array<T> *out=NULL;
    fft_script.GetReturn_Array(&out);

    /* copy before PyCallable falls out of scope */
    Array<T> out_copy(*out); 
    return out_copy;
}

/**
 * Take advantage of the pretty numpy array printing (for supported array
 * types).
 *
 * \param in An Array to be printed to stdout.
 */
template<class T>
void printArray(Array<T> &in)
{
    string code;
    code = "def func(in1):\n"
           "    print(type(in1), in1.dtype, in1.shape)\n"
           "    print(in1)\n";
    PyCallable printer(code);
    printer.SetArg_Array(&in);
    printer.Run();
}


/**
 * Matrix multiplication using the numpy.dot function.
 *
 * \param a input Array
 * \param b input Array
 * \return Array dot product.
 */
template<class T>
inline Array<T> matmult(Array<T> &a, Array<T> &b)
{
    PyCallable m("numpy", "dot");
    m.SetArg_Array(&a);
    m.SetArg_Array(&b);
    Array<T> *out=NULL;
    m.GetReturn_Array(&out);

    /* copy before PyCallable falls out of scope */
    Array<T> out_copy(*out); 
    return out_copy;
}

/**
 * Matrix transpose using the numpy.transpose function.
 *
 * \param a input Array
 * \return A^T
 */
template<class T>
inline Array<T> transpose(Array<T> &a)
{
    PyCallable m("numpy", "transpose");
    m.SetArg_Array(&a);
    Array<T> *out=NULL;
    m.GetReturn_Array(&out);

    /* copy before PyCallable falls out of scope */
    Array<T> out_copy(*out); 
    return out_copy;
}

}// NUMPY
}// PYFI

#endif // GUARD
