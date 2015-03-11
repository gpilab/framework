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

/**
    \brief A template for the PyFI interface.
 **/

#include "PyFI/PyFI.h" /* PyFI interface, must be the first include */
using namespace PyFI; /* for PyFI::Array */

#include <iostream> /* string */

/* test:
 *  positional args
 *  keyword args
 *  arrays (in and out)
 *  long, double and string primitives (in and out)
 *  copy-mode output
 *  alloc-mode output
 */
PYFI_FUNC(IFtest)
{
    PYFI_START(); /* This must be the first line */

    /***** POSITIONAL ARGS */   
    /* primitives (these are the only types allowed) */
    PYFI_POSARG(int64_t, myint); /* long */
    PYFI_POSARG(double, myfloat);
    PYFI_POSARG(string, mystring);

    /* arrays (example types) */
    PYFI_POSARG(Array<complex<float> >, mycfarr);
    PYFI_POSARG(Array<double>, mydarr);
    PYFI_POSARG(Array<int64_t>, mylarr); /* long array */


    /***** KEYWORD ARGS */
    /* mykwint, default value is 1
     * The hidden variable 'mykwint__default' is auto-generated
     * and set to a value of 1.
     */
    /* primitives (these are the only types allowed) */
    PYFI_KWARG(int64_t, mykwint, 1L); /* long */
    PYFI_KWARG(double, mykwfloat, -0.6);
    PYFI_KWARG(string, mykwstring, "<<< your ad here >>>");

    /* arrays (example types) */
    Array<complex<float> > def_cf(10); /* 1D array default */
    def_cf = (complex<float>) (1.0 + 1j); /* default array values */
    PYFI_KWARG(Array<complex<float> >, mykwcfarr, def_cf);

    Array<double> def_d(2,2);
    def_d = 0.;
    PYFI_KWARG(Array<double>, mykwdarr, def_d);

    Array<int64_t> def_l(2,2,2);
    def_l = 7L;
    PYFI_KWARG(Array<int64_t>, mykwlarr, def_l); /* long array */

    /* NULL-default array example, set the default to an array of zero length */
    PYFI_KWARG(Array<double>, mynullarr, Array<double>());
    long nullCheckPassed = 0;
    if (mynullarr->size() == 0)
        nullCheckPassed = 1;

    /***** PREALLOCATED OUTPUT */
    /* This function does two things:
     *      1) allocates new python memory to be used in THIS c code.
     *      2) sets the given variable as an output.
     * 'arrpreout', pre-allocated with 3D bounds using the ArrayDimensions object (col-major).
     * 'arrpreout' is now in the left-most output position.
     */
    PYFI_SETOUTPUT_ALLOC(Array<double>, arrpreout, ArrayDimensions(2,2,2));

    /* copy an input array size for output */
    //PYFI_SETOUTPUT_ALLOC(Array<double>, arrinsize, mydarr->dims_object());

    /* use a vector to convey dims */
    std::vector<uint64_t> dimsc;
    for (uint64_t i=0; i<mydarr->ndim(); ++i)
        dimsc.push_back( mydarr->dimensions(i) );
    PYFI_SETOUTPUT_ALLOC(Array<double>, arrinsize, dimsc);

    /***** PERFORM */
    /* primitives tests */
    int64_t myoutputint = *mykwint + *myint;
    string myoutstring = "c++ generated string";

    /* array tests */
    *arrpreout = 8.1;

    /* tread as 1D and sqr */
    for (uint64_t i=0; i<mydarr->size(); i++)
        (*arrinsize)(i) = (*mydarr)(i) * (*mydarr)(i);

    /* convenience functions */
    deb; /* just print out the line number for debugging */
    coutv(*myint); /* stringify the name, value, and line number of the variable */
    coutv(def_d); /* also works on arrays */

    /***** COPY MODE OUTPUT */
    /* Any arrays sent out here will have to be copied to the python
     * interpreter memory (which is a time consuming step).  Its best to
     * pre-allocate the memory ahead of time using PYFI_SETOUTPUT_ALLOC().
     */
    PYFI_SETOUTPUT(&myoutputint);  /* need to ref '&' local vars */
    PYFI_SETOUTPUT(myfloat); /* don't need to ref pointers */
    PYFI_SETOUTPUT(mykwfloat);
    PYFI_SETOUTPUT(mykwstring);
    PYFI_SETOUTPUT(&myoutstring);
    PYFI_SETOUTPUT(&nullCheckPassed);

    /* array */
    PYFI_SETOUTPUT(mycfarr);
    PYFI_SETOUTPUT(mylarr);
    PYFI_SETOUTPUT(mykwcfarr);
    PYFI_SETOUTPUT(mykwdarr);
    PYFI_SETOUTPUT(mykwlarr);
    
    PYFI_END(); /* This must be the last line */
}




/* test:
 *  positional args
 *  keyword args
 *  arrays (in and out)
 *  long, double and string primitives (in and out)
 *  copy-mode output
 *  alloc-mode output
 */
PYFI_FUNC(IFtest2)
{
    PYFI_START(); /* This must be the first line */

    /***** POSITIONAL ARGS */   
    PYFI_POSARG(Array<float>, arr); 

    //get1(*arr, 1000);

    coutv(*arr);

    Array<int64_t> asl = arr->as_LONG();
    coutv(asl);

    Array<float> arr_copy(*arr);

    cout << "Printing using PyFI" << endl;
    coutv(arr_copy);
    cout << "Printing using Numpy" << endl;
    Numpy::printArray(arr_copy);

    //arr_copy(1000);
    arr_copy(2) = 3.14159; 

    coutv(arr_copy);
    coutv((arr_copy == (*arr)));
    coutv((arr_copy < 1.1));
    coutv(((float)3.0 > arr_copy));
    
    coutv( (arr_copy.dims_object() == arr->dims_object()));
    coutv( (arr_copy.dims_object() != arr->dims_object()));
    
    PYFI_SETOUTPUT_ALLOC_DIMS(Array<float>, aarr, arr->ndim(), arr->dimensions());

    for (uint64_t i=0; i<aarr->size(); ++i)
        (*aarr)(i) = i;

    Array<float> A(2,2);
    for (uint64_t i=0; i<A.size(); ++i)
        A(i) = i;

    Array<float> Ainv = Numpy::pinv(A);
    coutv(A);
    coutv(Ainv);

    /* use the sqrt function from math */
    PyCallable sqrt("math", "sqrt");
    sqrt.SetArg_Double(2.2);
    coutv(sqrt.GetReturn_Double());

    /* call a function from an external script */
    PyCallable script("embedded_script", "script");
    script.SetArg_Double(2.2);
    script.SetArg_Long(7);

    Array<complex<double> > cf(2,3,4);
    cf = (complex<double>) (6 + 1j);
    coutv(cf);
    script.SetArg_Array(&cf);

    /* get the first two return out */
    coutv(script.GetReturn_Double());
    coutv(script.GetReturn_Long());

    /* then get the array out */
    Array<float> *out=NULL;
    script.GetReturn_Array(&out);
    coutv(*out);

    /* write your own function */
    PyCallable mycode("def func(in1):\n  print(\'in1\', in1)\n  return 1\n");
    mycode.SetArg_Long(777);
    coutv(mycode.GetReturn_Long());

    /* matrix multiplication */
    PyCallable matmult("numpy", "dot");
    matmult.SetArg_Array(&A);
    matmult.SetArg_Array(&A);
    Array<float> *AdotA = NULL;
    matmult.GetReturn_Array(&AdotA);
    cout << "matmult" << endl;
    coutv(A);
    coutv(*AdotA);

    Array<float> AdotA_it(Numpy::matmult(A, A));
    cout << "matmult (pointer)" << endl;
    coutv(A);
    coutv(AdotA_it);

    Array<float> Atr(Numpy::transpose(A));
    Numpy::printArray(A);
    Numpy::printArray(Atr);

    /* try fft */
    Array<complex<float> > f(10,2);
    f = (complex<float>) 1;
    cout << "fft1_numpy\n";
    coutv(Numpy::fft1(f, FFT_NUMPY_FORWARD));
    
    FFTW::fft1(f, f, FFTW_FORWARD);
    coutv(f);

    /*
    for (uint64_t k=0; k<arr_copy.size(2); ++k)
    for (uint64_t j=0; j<arr_copy.size(1); ++j)
    for (uint64_t i=0; i<arr_copy.size(0); ++i)
        cout << arr_copy(i,j,k) << endl;
        */


    /* array insertion */
    /* 1D */
    Array<float> big1(11, 8);
    Array<float> small1(5, 5);
    small1 = 1.0;

    Numpy::printArray(big1);
    Numpy::printArray(small1);

    Numpy::printArray(big1.insert(small1));
    //Numpy::printArray(small1.insert(big1));
    //
    std::vector<double> s(2);
    s[0] = 1.1;
    s[1] = 1.01;

    Array<float> zp = big1.get_resized(s);
    coutv(zp);
    Numpy::printArray(zp);

    std::vector<uint64_t> dc = big1.dimensions_vector();
    coutv(dc);
    dc.resize(1);
    coutv(dc);


    PYFI_SETOUTPUT(&arr_copy);
    cout << "end\n";   
    PYFI_END(); /* This must be the last line */
}

template <class T>
PYFI_FUNC(math)
{
    PYFI_START();

    T val = 1.0/3.0;

    coutv(val);
    coutv(PyFI::Demangle(typeid(T).name()));

    PYFI_END();
}


/* ##############################################################
 *                  MODULE DESCRIPTION
 * ############################################################## */


/* list of functions to be accessible from python */
PYFI_LIST_START_
    PYFI_DESC(IFtest, "test the interface")
    PYFI_DESC(IFtest2, "test the interface")

    /* templated function, this macro allows the declaration of a specific
     * template type. The python function is bound to:
     *      <func name>_<T> where 'T' is the type name.
     *      In this example math_double, math_float, and  math_int 
     *      are available to the python module interface.
     */
    PYFI_T_DESC(math, double, "does calc in double")
    PYFI_T_DESC(math, float, "does calc in float")
    PYFI_T_DESC(math, int, "does calc in int")
PYFI_LIST_END_
