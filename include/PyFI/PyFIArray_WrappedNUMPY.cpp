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
 *   MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
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

/* use the numpy.linalg.pinv() function */
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


/* use the numpy.linalg.cond() function 
 * to check the condition numbers before running pinv.
 */
template<class T>
double cond(Array<T> &A)
{
    PyFI::PyCallable cnd("numpy.linalg", "cond");
    cnd.SetArg_Array(&A);
    return cnd.GetReturn_Double();
}

/* dump array
 */
template<class T>
void writeNPY(const std::string fname, Array<T> &A)
{
    PyFI::PyCallable obj("numpy", "save");
    obj.SetArg_String(fname);
    obj.SetArg_Array(&A);
    obj.Run();
}


/* make a numpy fft for 1st dim */
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

/* take advantage of the pretty numpy array printing (for supported array types).
 */
template<class T>
void printArray(Array<T> &in)
{
    string code;
    code = "def func(in1):\n"
           "    print type(in1), in1.dtype, in1.shape\n"
           "    print in1\n";
    PyCallable printer(code);
    printer.SetArg_Array(&in);
    printer.Run();
}


/* matrix multiplication */
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

/* matrix transpose*/
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
