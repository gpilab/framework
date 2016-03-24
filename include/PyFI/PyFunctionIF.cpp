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


#ifndef _PYFUNCTIONIF_CPP_GUARD
#define _PYFUNCTIONIF_CPP_GUARD
/**
    \brief Functions that make extending and embedding Python into c/c++
    routines, simple.
**/

#include <iostream>
#include <map>
#include <list>
#include <typeinfo>
#include <complex>
using namespace std;

/* PyFunction declaration simplifications */
#include "PyFI/PyFIMacros.h"

/* target array library for numpy translation */
#include "PyFI/PyFIArray.cpp"

namespace PyFI
{

/* for printing out supported types in error msgs */
string supportedTypes()
{
    string ss = _PYFI_YEL "\tPyFI supported Python-builtin/C++-primitive conversions are:\n"
                "\t\tfloat : double\n"
                "\t\tlong : int64_t\n"
                "\t\tstr : std::string\n"
                "\tPyFI supported NUMPY/Array<T> conversions are:\n"
                "\t\tnumpy.float32 : Array<float>\n"
                "\t\tnumpy.float64 : Array<double>\n"
                "\t\tnumpy.complex64 : Array<complex<float> >\n"
                "\t\tnumpy.complex128 : Array<complex<double> >\n"
                "\t\tnumpy.int64 : Array<int64_t>\n"
                "\t\tnumpy.int32 : Array<int32_t>\n"
                "\t\tnumpy.uint8 : Array<uint8_t>\n" _PYFI_NOC;
    return ss;
}



/* determine if given long-type is 8-byte */
#define LONG_BYTESIZE 8
bool isLong(const type_info *type)
{
    if ((*type == typeid(long)) && (sizeof(long) == LONG_BYTESIZE))
        return true;
    if ((*type == typeid(long long)) && (sizeof(long long) == LONG_BYTESIZE))
        return true;
    if ((*type == typeid(long int)) && (sizeof(long int) == LONG_BYTESIZE))
        return true;
    if ((*type == typeid(npy_intp)) && (sizeof(npy_intp) == LONG_BYTESIZE))
        return true;
    if ((*type == typeid(int64_t)) && (sizeof(int64_t) == LONG_BYTESIZE))
        return true;
    return false;
}


/* determine if given array-long-type is 8-byte */
bool isArrayLong_PyFI(const type_info *type)
{
    if ((*type == typeid(PyFI::Array<long>)) && (sizeof(long) == LONG_BYTESIZE))
        return true;
    if ((*type == typeid(PyFI::Array<long long>)) && (sizeof(long long) == LONG_BYTESIZE))
        return true;
    if ((*type == typeid(PyFI::Array<long int>)) && (sizeof(long int) == LONG_BYTESIZE))
        return true;
    if ((*type == typeid(PyFI::Array<npy_intp>)) && (sizeof(npy_intp) == LONG_BYTESIZE))
        return true;
    if ((*type == typeid(PyFI::Array<int64_t>)) && (sizeof(int64_t) == LONG_BYTESIZE))
        return true;
    return false;
}

/* Translate PyFI::Array types to NPY types.
 *  -PyFI::Array types come through the template
 *  interface (i.e. SetPosArg and SetKWArg).
 */
int32_t NPY_type(const type_info *type)
{
    if (*type == typeid(PyFI::Array<float>))
        return NPY_FLOAT32;
    if (*type == typeid(PyFI::Array<double>))
        return NPY_FLOAT64;
    if (*type == typeid(PyFI::Array<int32_t>))
        return NPY_INT32;
    if (isArrayLong_PyFI(type))
        return NPY_INT64;
    if (*type == typeid(PyFI::Array<complex<float> >))
        return NPY_COMPLEX64;
    if (*type == typeid(PyFI::Array<complex<double> >))
        return NPY_COMPLEX128;
    if (*type == typeid(PyFI::Array<uint8_t>))
        return NPY_UINT8;
    else
        return NPY_NOTYPE; /* no conversion possible */
}

/* converting dimensions arrays to npy type and changing between row-major
 * and column-major.  The returned pointer must be freed.
 */
#define _PYFI_REVERSE_ORDER true
#define _PYFI_SAME_ORDER false
#define NPYDIMS_rev(_nd, _dim) PyFI::NPYDims(_nd, _dim, _PYFI_REVERSE_ORDER)
#define NPYDIMS_copy(_nd, _dim) PyFI::NPYDims(_nd, _dim, _PYFI_SAME_ORDER)
npy_intp *NPYDims(const uint64_t ndim, const uint64_t *dims, const bool reverse)
{
    npy_intp *pydims = (npy_intp*)malloc(sizeof(npy_intp)*ndim);
    for (uint64_t i=0; i<ndim; ++i)
    {
        if (reverse)
            pydims[i] = dims[ndim-1-i];
        else
            pydims[i] = dims[i];
    }
    return pydims;
}

#define PYFIDIMS_rev(_nd, _dim) PyFI::PYFIDims(_nd, _dim, _PYFI_REVERSE_ORDER)
#define PYFIDIMS_copy(_nd, _dim) PyFI::PYFIDims(_nd, _dim, _PYFI_SAME_ORDER)
uint64_t *PYFIDims(const int ndim, const npy_intp *dims, const bool reverse)
{
    uint64_t *pydims = (uint64_t*)malloc(sizeof(uint64_t)*ndim);
    for (uint64_t i=0; i<(uint64_t)ndim; ++i)
    {
        if (reverse)
            pydims[i] = dims[(uint64_t)ndim-1-i];
        else
            pydims[i] = dims[i];
    }
    return pydims;
}


/******************************************************************************
 * PARAMETER CLASS
 */

/* Parm_Abstract
 *
 * Functions required for extending to new variable types:
 *      virtual void Convert_In(void) = 0;
 *          Translates an NPY array to whatever array package is needed.
 *              -tests NPY_type() to do specific base-type conversions.
 *              -stores all arrays as a void* pointer.
 *
 *      virtual ~Parm_Abstract(void) {}
 *          Deallocates the target converted arrays.
 *              -tests NPY_type() to determine how to recast void*
 *              -DECREFs any new python object references needed.
 *              Cases:
 *                  -if the array is a full copy
 *                  -if the array is a wrapper of the NPY segment
 *
 *      virtual int NPY_type(void);
 *          Checks typeid(T) of template and converts to
 *              corresponding NPY_<type>.
 *
 * -constructor (input PyObject)
 * -void Convert_In(void)
 *      1) specialized converter from PyObject to ctype, INCREFs are stored.
 * -void *GetVal(void)
 *      1) returns pointer to the converted ctype as void*
 * -destructor
 *      1) deallocate specifics needed by the data type (usually for
 *          specific array types)
 *      2) handle python DECREFs if needed
 */

#define PYIF_PARM_NOTYPE -1
#define PYIF_PARM_INPUT 0
#define PYIF_PARM_OUTPUT 1
#define PYIF_PARM_NPYPRE 2

/**** ABSTRACT ****/
class Parm_Abstract
{
    public:
        Parm_Abstract(string name, const type_info *type)
        {
            this->name = name;
            this->type = type;
            parmobj_type = PYIF_PARM_NOTYPE;
            pyarr_ptr = NULL;
            pyobj_ptr = NULL;
            val = NULL;
            def = NULL;
            pyobj_markedForDECREF = false;
            pyarr_markedForDECREF = false;
        }

        void ConvertPyObj_PyArr(void);
        bool UseDefault(void);
        bool defaultUsed(void);
        bool isParmOutput(void)
        {
            return (parmobj_type == PYIF_PARM_OUTPUT);
        }
        bool isParmInput(void)
        {
            return (parmobj_type == PYIF_PARM_INPUT);
        }
        bool isParmNPYPre(void)
        {
            return (parmobj_type == PYIF_PARM_NPYPRE);
        }
        void Error(string);

        /* getters */
        void *GetVal(void);
        PyObject *GetPyObjPtr(void);
        string GetName(void)
        {
            return this->name;
        }

        /* setters */
        void SetVal(void *);
        void SetPyObjPtr(PyObject *);
        void SetParmType(int32_t type);
        void SetDefault(void *);
        void MarkForDECREF_PyObj(void)
        {
            pyobj_markedForDECREF = true;
        }
        void MarkForDECREF_PyArr(void)
        {
            pyarr_markedForDECREF = true;
        }

        /* functions that need implementation by IF */
        virtual void Convert_In(void) = 0; /* wrap py-data seg with c-type */
        virtual void Convert_Out(void) = 0; /* convert c-type to py-segment */
        virtual void WrapSegWithNPY(void){PYFI_INT_ERROR("WrapSegWithNPY() is not implemented for this type.");} /* wrap a c++ defined segment with an NPY wrapper. */
        virtual ~Parm_Abstract(void)
        {
            /* keep track of refcounts */
            if (pyobj_markedForDECREF) Py_DECREF(pyobj_ptr);
            if (pyarr_markedForDECREF) Py_DECREF(pyarr_ptr);
        }

    protected:
        PyObject *pyobj_ptr; // holds obj to be translated to or from
        PyObject *pyarr_ptr; // holds npy-PyArrayObject when ensuring contiguity
        const type_info *type; // c-type info
        void *def; // holds user defined default c-object, for kwargs
        void *val; // holds translated c-object
        int32_t parmobj_type; // pre-allocated array, input, output
        bool pyobj_markedForDECREF; // ref accounting
        bool pyarr_markedForDECREF; // ref accounting
        string name; // for reporting purposes
};

void Parm_Abstract::Error(string msg)
{
    stringstream ss;

    if (parmobj_type == PYIF_PARM_NPYPRE)
        ss << "PreAlloc Output Arg \'" << name << "\': " << msg;
    else if (parmobj_type == PYIF_PARM_INPUT)
        ss << "Input Arg \'" << name << "\': " << msg;
    else if (parmobj_type == PYIF_PARM_OUTPUT)
        ss << "Output Arg \'" << name << "\': " << msg;
    else
        ss << " \'" << name << "\': " << msg;

    PyErr_Format(PyExc_RuntimeError,"%s", ss.str().c_str());
    throw PYIF_EXCEPTION;
}

PyObject *Parm_Abstract::GetPyObjPtr(void)
{
    return pyobj_ptr;
}

void Parm_Abstract::SetParmType(int32_t type)
{
    parmobj_type = type;
}

bool Parm_Abstract::UseDefault(void)
{
    if ((pyobj_ptr == NULL) && isParmInput())
        return true;
    else
        return false;
}

bool Parm_Abstract::defaultUsed(void)
{
    if (val == def) return true;
    else return false;
}

void Parm_Abstract::SetPyObjPtr(PyObject *in)
{
    pyobj_ptr = in;
}

void Parm_Abstract::SetDefault(void *in)
{
    def = in;
}

void Parm_Abstract::SetVal(void *in)
{
    val = in;
}

void *Parm_Abstract::GetVal(void)
{
    return val;
}

void Parm_Abstract::ConvertPyObj_PyArr(void)
{
    /* check if array has already been set */
    if (pyarr_ptr != NULL)
        Error("PyFI: ConvertPyObj_PyArr() pyarr_ptr has already been set (memory leak).");

    int32_t pytype = PyArray_TYPE((PyArrayObject *)pyobj_ptr);

    /* Returned object is either new or a new reference.
     * -in either case a DECREF is needed when finished.
     */
    pyarr_ptr = PyArray_FROM_OTF(pyobj_ptr, pytype, NPY_ARRAY_IN_ARRAY);
    if (pyarr_ptr == NULL)
        Error("PyFI: ConvertPyObj_PyArr() unable to translate/import PyArray from pyobj_ptr.");

    MarkForDECREF_PyArr(); /* tell destructor to DECREF this array */
}

/**** STRING ****/
class Parm_STRING: public Parm_Abstract
{
    public:
        Parm_STRING(string name, const type_info *type) : Parm_Abstract(name, type) {}
        ~Parm_STRING(void) {} /* borrowed ref, not needed */
        void Convert_In(void);
        void Convert_Out(void);

    protected:
        string local_val;
};

void Parm_STRING::Convert_In(void)
{
    if (UseDefault())
    {
        val = def;
    }
    else
    {
        local_val = string(PyUnicode_AS_DATA(pyobj_ptr));
        val = (void *)&local_val;
    }
}

void Parm_STRING::Convert_Out(void)
{
    /* new ref */
    pyobj_ptr = PyUnicode_FromString((*(string *)val).c_str());
}

/**** DOUBLE ****/
class Parm_DOUBLE : public Parm_Abstract
{
    public:
        Parm_DOUBLE(string name, const type_info *type) : Parm_Abstract(name, type) {}
        ~Parm_DOUBLE(void) {} /* borrowed ref, not needed */
        void Convert_In(void);
        void Convert_Out(void);

    protected:
        double local_val;
};

void Parm_DOUBLE::Convert_In(void)
{
    if (UseDefault())
    {
        val = def;
    }
    else
    {
        local_val = PyFloat_AsDouble(pyobj_ptr);
        val = (void *)&local_val;
    }
}

void Parm_DOUBLE::Convert_Out(void)
{
    /* new ref */
    pyobj_ptr = PyFloat_FromDouble(*(double *)val);
}



/**** LONG ****/
class Parm_LONG : public Parm_Abstract
{
    public:
        Parm_LONG(string name, const type_info *type) : Parm_Abstract(name, type) {}
        ~Parm_LONG(void) {} /* borrowed ref, not needed */
        void Convert_In(void);
        void Convert_Out(void);

    protected:
        int64_t local_val;
};

void Parm_LONG::Convert_In(void)
{
    if (UseDefault())
    {
        val = def;
    }
    else
    {
        local_val = PyLong_AsLong(pyobj_ptr);
        val = (void *)&local_val;
    }
}

void Parm_LONG::Convert_Out(void)
{
    /* new ref */
    pyobj_ptr = PyLong_FromLong(*(int64_t *)val);
}


/**** BASICARRAY ****/
class Parm_BASICARRAY: public Parm_Abstract
{
    public:
        Parm_BASICARRAY(string name, const type_info *type) : Parm_Abstract(name, type) {}
        ~Parm_BASICARRAY(void);
        void Convert_In(void); /* wrap NPY Array with PyFI::Array */
        void Convert_Out(void); /* copy PyFI::Array to NPY Array */
        void WrapSegWithNPY(void); /* wrap a c++ defined segment with an NPY wrapper. */
        int32_t NPY_type(void);
};

/* Should only be used to pass c++ defined data to an embedded python call. 
 * -Python won't free the array segment b/c NPY doesn't 'own' it.
 */
void Parm_BASICARRAY::WrapSegWithNPY(void)
{
    /* Wrap mode
     * The input was of a non-python based memory
     * segment so it needs to be wrapped by NPY.
     *
     * this generates a new ref for the pyobj_ptr that
     * will be passed to the output tuple.
     */
    if (NPY_type() == NPY_COMPLEX64)
    {
        PyFI::Array<complex<float> > *local_ptr = (PyFI::Array<complex<float> >*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNewFromData((int) (local_ptr->ndim()), pydims, NPY_type(), (void*)(local_ptr->data()));
        free(pydims);
    }
    else if (NPY_type() == NPY_COMPLEX128)
    {
        PyFI::Array<complex<double> > *local_ptr = (PyFI::Array<complex<double> >*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNewFromData((int) (local_ptr->ndim()), pydims, NPY_type(), (void*)(local_ptr->data()));

        free(pydims);
    }
    else if (NPY_type() == NPY_FLOAT32)
    {
        PyFI::Array<float> *local_ptr = (PyFI::Array<float>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNewFromData((int) (local_ptr->ndim()), pydims, NPY_type(), (void*)(local_ptr->data()));
        free(pydims);
    }
    else if (NPY_type() == NPY_FLOAT64)
    {
        PyFI::Array<double> *local_ptr = (PyFI::Array<double>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNewFromData((int) (local_ptr->ndim()), pydims, NPY_type(), (void*)(local_ptr->data()));
        free(pydims);
    }
    else if (NPY_type() == NPY_INT32)
    {
        PyFI::Array<int32_t> *local_ptr = (PyFI::Array<int32_t>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNewFromData((int) (local_ptr->ndim()), pydims, NPY_type(), (void*)(local_ptr->data()));
        free(pydims);
    }
    else if (NPY_type() == NPY_INT64)
    {
        PyFI::Array<int64_t> *local_ptr = (PyFI::Array<int64_t>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNewFromData((int) (local_ptr->ndim()), pydims, NPY_type(), (void*)(local_ptr->data()));
        free(pydims);
    }
    else if (NPY_type() == NPY_UINT8)
    {
        PyFI::Array<uint8_t> *local_ptr = (PyFI::Array<uint8_t>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNewFromData((int) (local_ptr->ndim()), pydims, NPY_type(), (void*)(local_ptr->data()));
        free(pydims);
    }
    else
    {
        Error("PyCallable: WrapSegWithNPY(): array type not specified in Parm_Abstract::NPY_type()");
    }

}



void Parm_BASICARRAY::Convert_Out(void)
{
    /* Copy mode
     * The input was of a non-python based memory
     * segment so it needs to be copied to one.
     *
     * this generates a new ref for the pyobj_ptr that
     * will be passed to the output tuple.
     */
    if (NPY_type() == NPY_COMPLEX64)
    {
        PyFI::Array<complex<float> > *local_ptr = (PyFI::Array<complex<float> >*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNew((int) (local_ptr->ndim()), pydims, NPY_type());
        memcpy(PYFI_PyArray_BYTES(pyobj_ptr), local_ptr->data(), (local_ptr->size())*sizeof(complex<float>));
        free(pydims);
    }
    else if (NPY_type() == NPY_COMPLEX128)
    {
        PyFI::Array<complex<double> > *local_ptr = (PyFI::Array<complex<double> >*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNew((int) (local_ptr->ndim()), pydims, NPY_type());
        memcpy(PYFI_PyArray_BYTES(pyobj_ptr), local_ptr->data(), (local_ptr->size())*sizeof(complex<double>));
        free(pydims);
    }
    else if (NPY_type() == NPY_FLOAT32)
    {
        PyFI::Array<float> *local_ptr = (PyFI::Array<float>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNew((int) (local_ptr->ndim()), pydims, NPY_type());
        memcpy(PYFI_PyArray_BYTES(pyobj_ptr), local_ptr->data(), (local_ptr->size())*sizeof(float));
        free(pydims);
    }
    else if (NPY_type() == NPY_FLOAT64)
    {
        PyFI::Array<double> *local_ptr = (PyFI::Array<double>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNew((int) (local_ptr->ndim()), pydims, NPY_type());
        memcpy(PYFI_PyArray_BYTES(pyobj_ptr), local_ptr->data(), (local_ptr->size())*sizeof(double));
        free(pydims);
    }
    else if (NPY_type() == NPY_INT32)
    {
        PyFI::Array<int32_t> *local_ptr = (PyFI::Array<int32_t>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNew((int) (local_ptr->ndim()), pydims, NPY_type());
        memcpy(PYFI_PyArray_BYTES(pyobj_ptr), local_ptr->data(), (local_ptr->size())*sizeof(int32_t));
        free(pydims);
    }
    else if (NPY_type() == NPY_INT64)
    {
        PyFI::Array<int64_t> *local_ptr = (PyFI::Array<int64_t>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNew((int) (local_ptr->ndim()), pydims, NPY_type());
        memcpy(PYFI_PyArray_BYTES(pyobj_ptr), local_ptr->data(), (local_ptr->size())*sizeof(int64_t));
        free(pydims);
    }
    else if (NPY_type() == NPY_UINT8)
    {
        PyFI::Array<uint8_t> *local_ptr = (PyFI::Array<uint8_t>*)val;
        /* copy and reverse dimensions */
        npy_intp *pydims = NPYDIMS_rev(local_ptr->ndim(), local_ptr->dimensions());
        pyobj_ptr = PyArray_SimpleNew((int) (local_ptr->ndim()), pydims, NPY_type());
        memcpy(PYFI_PyArray_BYTES(pyobj_ptr), local_ptr->data(), (local_ptr->size())*sizeof(uint8_t));

        free(pydims);
    }
    else
    {
        Error("PyFI: Convert_Out() array type not specified in Parm_Abstract::NPY_type()");
    }

}

/* Translate PyFI::Array types to NPY types.
 *  -PyFI::Array types come through the template
 *  interface (i.e. SetPosArg and SetKWArg).
 */
int32_t Parm_BASICARRAY::NPY_type(void)
{
    return PyFI::NPY_type(type);
}

Parm_BASICARRAY::~Parm_BASICARRAY(void)
{
    /* Recast and delete, if the default arg was used,
     * the default was passed to 'val' so don't free.
     * The PyFI::Array<> knows whether its wrapping an
     * external segment or not, so its always safe to delete. */
    if (!defaultUsed() && !isParmOutput())
    {
        if (NPY_type() == NPY_COMPLEX64)
            delete((PyFI::Array<complex<float> >*)val);

        else if (NPY_type() == NPY_COMPLEX128)
            delete((PyFI::Array<complex<double> >*)val);

        else if (NPY_type() == NPY_FLOAT32)
            delete((PyFI::Array<float>*)val);

        else if (NPY_type() == NPY_FLOAT64)
            delete((PyFI::Array<double>*)val);

        else if (NPY_type() == NPY_INT32)
            delete((PyFI::Array<int32_t>*)val);

        else if (NPY_type() == NPY_INT64)
            delete((PyFI::Array<int64_t>*)val);

        else if (NPY_type() == NPY_UINT8)
            delete((PyFI::Array<uint8_t>*)val);

        else
            cout << "~Parm_BASICARRAY() ERROR: cannot find associated destructor.\n";
    }
}

/* Wrap an NPY data segment within a BASICARRAY class type */
void Parm_BASICARRAY::Convert_In(void)
{
    /* for kwarg default */
    if (UseDefault())
    {
        /* TODO: error check that default is the right type */
        val = def;
        return;
    }

    /* Ensure the passed object type is the same as
     * the type specified in the interface.
     */
    if (NPY_type() == NPY_NOTYPE)
        Error("PyFI: Convert_In() array type not specified in Parm_Abstract::NPY_type()");

    /* Translate pyobj to array and get local copies of array info. */
    ConvertPyObj_PyArr();
    PyArrayObject *local_ptr = (PyArrayObject *)pyarr_ptr;
    int32_t pytype = PyArray_TYPE(local_ptr);
    uint64_t ndim = PyArray_NDIM(local_ptr);
    void *seg_ptr = PYFI_PyArray_BYTES(local_ptr);
    uint64_t *dimensions = PYFIDIMS_rev(PyArray_NDIM(local_ptr), PyArray_DIMS(local_ptr));

    /* Check that input array type matches IF requested type */
    if (!(pytype == NPY_type()))
        Error(_PYFI_RED "PyFI: Convert_In() input Python array type doesn't match FuncIF type." _PYFI_NOC);

    /* translate and check type */
    if (NPY_type() == NPY_COMPLEX64)
    {
        PyFI::Array<complex<float> > *arr_ptr = new PyFI::Array<complex<float> >(ndim,
                dimensions, (complex<float>*)seg_ptr);
        val = (void *)arr_ptr;
    }
    else if (NPY_type() == NPY_COMPLEX128)
    {
        PyFI::Array<complex<double> > *arr_ptr = new PyFI::Array<complex<double> >(ndim,
                dimensions, (complex<double>*)seg_ptr);
        val = (void *)arr_ptr;
    }
    else if (NPY_type() == NPY_FLOAT32)
    {
        PyFI::Array<float> *arr_ptr = new PyFI::Array<float>(ndim, dimensions, (float *)seg_ptr);
        val = (void *)arr_ptr;
    }
    else if (NPY_type() == NPY_FLOAT64)
    {
        PyFI::Array<double> *arr_ptr = new PyFI::Array<double>(ndim, dimensions, (double *)seg_ptr);
        val = (void *)arr_ptr;
    }
    else if (NPY_type() == NPY_INT32)
    {
        PyFI::Array<int32_t> *arr_ptr = new PyFI::Array<int32_t>(ndim, dimensions, (int32_t *)seg_ptr);
        val = (void *)arr_ptr;
    }
    else if (NPY_type() == NPY_INT64)
    {
        PyFI::Array<int64_t> *arr_ptr = new PyFI::Array<int64_t>(ndim, dimensions, (int64_t *)seg_ptr);
        val = (void *)arr_ptr;
    }
    else if (NPY_type() == NPY_UINT8)
    {
        PyFI::Array<uint8_t> *arr_ptr = new PyFI::Array<uint8_t>(ndim, dimensions, (uint8_t *)seg_ptr);
        val = (void *)arr_ptr;
    }
    else
    {
        Error("PyFI: Convert_In() input array type doesn't match IF type.");
    }

    free(dimensions);
}


/******************************************************************************
 * INTERFACE CLASS
 */

/* Generic Python IO Interface Class
 *
 * input:
 * -constructor
 *      1) takes arg and kwarg from python interface
 *      2) checks for valid pytuple and pydict
 * -setters
 *      -SetPosArg_<type>()
 *      -SetKWArg_<type>()
 *      1) get postional/kwarg, name, ctype, and default values
 *      2) populates a 'new' Parm_Abstract derivative with this data
 *      -load: (now combined with set)
 *      1) confirms the list of set args matches the python input
 *      2) calls all parm.Convert_In() and raises any python exceptions
 *      3) throws exception on failure
 *      4) handles internal Py-exceptions by checking PyErr_Occurred()
 *          -uses c++ exception handling.
 *      -void *Get(string name) (now combined with set)
 *      1) returns pointer to data of interest by referencing 'name'
 *          from the stl::map
 *      2) #defines can be used to cast the data appropriately
 * -destructor
 *      1) call delete on all stl::map'd objects.
 *
 * output:
 * 1) Sets up output tuple given input pointers (positional).
 * 2) Keeps a list of Python memory created for NPY output.
 *      -frees memory not used in output
 */
class FuncIF
{
    public:
        FuncIF(PyObject *, PyObject *);
        ~FuncIF(void);

        /**** INPUT */
        bool Error(void);
        void Error(string);
        string LongToString(int64_t);
        Parm_Abstract *NewParm(string, const type_info *type);

        /* getters */
        void *GetPosArg(string);
        void *GetKWArg(string);

        /* set/get */
        template <class T> void PosArg(T **);
        template <class T> void KWArg(T **, string, void *);

        /* setters */
        template <class T> void SetArg_default(string, void *, int32_t);

        /* New functions to create for other array types: */
        virtual Parm_Abstract *SetArg_extended(string, const type_info *type);

        /**** OUTPUT */
        /* using FuncIF::SetOutput; // In derived classes use this for overload */
        template <class T> void SetOutput(T *);
        template <class T> void SetOutput(T **, const uint64_t, const uint64_t *);
        template <class T> void SetOutput(T **, const uint64_t, const PyFI::Array<uint64_t> &);
        template <class T> void SetOutput(T **, const ArrayDimensions &);

        PyObject *Output(void);

    protected:
        /**** INPUT */
        map<string, Parm_Abstract *> arg_dict; 
        map<string, Parm_Abstract *> kwarg_dict;
        map<string, Parm_Abstract *>::iterator dict_itr;
        PyObject *args;
        PyObject *kwargs;
        uint64_t nargs;
        uint64_t nkwargs;
        uint64_t cur_arg;

        /**** OUTPUT */
        list<Parm_Abstract *> out_lst;
        list<Parm_Abstract *>::iterator out_itr;
};





FuncIF::FuncIF(PyObject *args_ptr, PyObject *kwargs_ptr)
{
    /**** INPUT */
    /* check the existence of each arg input type */
    if (args_ptr == NULL || !PyTuple_Check(args_ptr))
    {
        Error("PyFI: FuncIF() invalid arg tuple.");
        nargs = 0;
        return;
    }

    if (kwargs_ptr != NULL && !PyDict_Check(kwargs_ptr))
    {
        Error("PyFI: FuncIF() invalid kwarg dict.");
        nkwargs = 0;
        return;
    }

    /* take a copy of the input python tuple/dict */
    args   = args_ptr;
    kwargs = kwargs_ptr;

    /* get arg list sizes */
    nargs = PyTuple_GET_SIZE(args);
    nkwargs = (kwargs == NULL) ? 0 : PyDict_Size(kwargs);
    cur_arg = 0;
}

/* Call all mapped object destructors. */
FuncIF::~FuncIF()
{
    /* Positional Args */
    for (dict_itr = arg_dict.begin(); dict_itr != arg_dict.end(); ++dict_itr)
        delete(*dict_itr).second;

    /* Keyword Args */
    for (dict_itr = kwarg_dict.begin(); dict_itr != kwarg_dict.end(); ++dict_itr)
        delete(*dict_itr).second;

    /* Output Parms */
    for (out_itr = out_lst.begin(); out_itr != out_lst.end(); ++out_itr)
        delete *out_itr;
}

bool FuncIF::Error(void)
{
    if (PyErr_Occurred()) return true;
    else return false;
}

void FuncIF::Error(string msg)
{
    PyErr_Format(PyExc_RuntimeError,"%s", msg.c_str());
    throw PYIF_EXCEPTION;
}

void *FuncIF::GetPosArg(string name)
{
    /* positional arg search */
    dict_itr = arg_dict.find(name);
    if (dict_itr != arg_dict.end())
    {
        return (dict_itr->second->GetVal());
    }

    /* if control reaches this, then its an error */
    stringstream ss;
    ss << _PYFI_RED "PyFI: Input Arg \'" << name << "\': " << "GetPosArg() requested Arg not found.\n" _PYFI_NOC <<supportedTypes();
    Error(ss.str());

    return NULL;
}
void *FuncIF::GetKWArg(string name)
{
    /* keyword arg search */
    dict_itr = kwarg_dict.find(name);
    if (dict_itr != kwarg_dict.end())
    {
        return (dict_itr->second->GetVal());
    }

    /* if control reaches this, then its an error */
    stringstream ss;
    ss << _PYFI_RED "PyFI: Input Arg \'" << name << "\': " << "GetKWArg() requested Arg not found.\n" _PYFI_NOC <<supportedTypes();
    Error(ss.str());

    return NULL;
}

/* convert position number to string */
string FuncIF::LongToString(int64_t pos)
{
    stringstream ss;
    ss << pos;
    return ss.str();
}

template <class T>
void FuncIF::PosArg(T **out_ptr)
{
    string name = LongToString(cur_arg);

    /* Make sure the user isn't causing a mem leak */
    if (*out_ptr != NULL)
    {
        stringstream ss;
        ss << "PyFI: Input Arg \'" << name << "\': " << "PosArg() input ptr is not NULL (possible memory leak).";
        Error(ss.str());
    }

    SetArg_default<T>(name, NULL, PYIF_POSITIONAL_ARG);

    *out_ptr = (T *) GetPosArg(name);

    cur_arg++; /* increment for the next SetPosArg() and GetPosArg() combo */
}

template <class T>
void FuncIF::KWArg(T **ptr, string name, void *def)
{
    if (*ptr != NULL)
    {
        stringstream ss;
        ss << "PyFI: Input Arg \'" << name << "\': " << "KWArg() input ptr is not NULL (possible memory leak).";
        Error(ss.str());
    }

    SetArg_default<T>(name, def, PYIF_KEYWORD_ARG);

    *ptr = (T *) GetKWArg(name);
}

/* translates typeid into associated parm-object */
Parm_Abstract *FuncIF::NewParm(string name, const type_info *type)
{
    /* Determine which parm obj to instantiate. */
    Parm_Abstract *parm_ptr = NULL;
    if (*type == typeid(double))
        parm_ptr = new Parm_DOUBLE(name, type);
    else if (*type == typeid(string))
        parm_ptr = new Parm_STRING(name, type);
    else if (isLong(type))
        parm_ptr = new Parm_LONG(name, type);
    else if (NPY_type(type) != NPY_NOTYPE)
        parm_ptr = new Parm_BASICARRAY(name, type);
    else
    {
        parm_ptr = SetArg_extended(name, type);
    }

    if (parm_ptr == NULL)
    {
        stringstream ss;
        ss << _PYFI_RED "PyFI: Arg \'" << name << "\' (zero-based if PosArg): NewParm() requested typeid \'"
           << PyFI::Demangle(type->name()) << "\' not supported.\n" _PYFI_NOC <<supportedTypes();
        Error(ss.str());
    }

    return parm_ptr;
}

template <class T>
void FuncIF::SetArg_default(string name, void *def, int32_t argType)
{
    /* use template to pass type */
    const type_info *type = &typeid(T);

    /* Determine which parm obj to instantiate. */
    Parm_Abstract *parm_ptr = NewParm(name, type);
    parm_ptr->SetParmType(PYIF_PARM_INPUT);

    /* See if the Python interface has the correct positional
     * or keyword argument to bind to. */
    PyObject *pyobj_ptr = NULL; /* if there are no kwargs then this will be null */
    if (argType == PYIF_POSITIONAL_ARG)
    {
        /* borrow ref */
        pyobj_ptr = PyTuple_GetItem(args, cur_arg);
        if (Error())
        {
            stringstream ss;
            ss << _PYFI_RED "PyFI: Input Arg \'" << name << "\': Failed to retrieve from positional input." _PYFI_NOC;
            if (cur_arg >= nargs) ss << _PYFI_RED " Exceeded input arg index: requested(" << cur_arg << "), max(" << nargs-1 << ")" _PYFI_NOC;
            Error(ss.str());
        }
    }
    else if ((kwargs != NULL) && (argType == PYIF_KEYWORD_ARG))
    {
        /* returns NULL if key is not present, borrows ref */
        pyobj_ptr = PyDict_GetItemString(kwargs, name.c_str());
    }
    parm_ptr->SetPyObjPtr(pyobj_ptr);

    /* Store argument parm in the associated list based on argType
     *  -This keeps track of the wrapped segment so that when
     *   the interface falls out of scope, the destructor of
     *   each wrapper can be called (and potentially each segment
     *   copy, if a wrapper was not possible or if NPY chose to
     *   provide a new ref).
     */
    if (argType == PYIF_POSITIONAL_ARG)
    {
        arg_dict[name] = parm_ptr;
    }
    else // PYIF_KEYWORD_ARG
    {
        parm_ptr->SetDefault(def);
        kwarg_dict[name] = parm_ptr;
    }

    /* Check for Conversion errors */
    parm_ptr->Convert_In();
    if (Error()) throw PYIF_EXCEPTION;
}

Parm_Abstract *FuncIF::SetArg_extended(string name, const type_info *type)
{
    Parm_Abstract *parm_ptr = NULL;

    /* this is where the 'type' will be checked against the new type
     * and a new Parm_Abstract : derivative will be instantiated.

    if (*type == typeid( MyNewType<T> ) )
        parm_ptr = new MyNewType(name, type);

     */

    return parm_ptr;
}

/* Copy Mode Output
 * For array data, an NPY array is allocated through python calls,
 * then the passed array data is copied to the NPY segment.
 */
template <class T>
void FuncIF::SetOutput(T *out_ptr)
{
    /* use template to pass type */
    const type_info *type = &typeid(T);
    string name = LongToString(out_lst.size());

    if (out_ptr == NULL)
    {
        stringstream ss;
        ss << "PyFI: Output Arg \'" << name << "\': " <<
           "SetOutput() ptr is NULL, there is no valid data type to pass.";
        Error(ss.str());
    }

    /* Determine which parm obj to instantiate. */
    Parm_Abstract *parm_ptr = NewParm(name, type);
    parm_ptr->SetParmType(PYIF_PARM_OUTPUT);
    parm_ptr->SetVal(out_ptr);
    parm_ptr->Convert_Out(); /* new pyobject ref */
    out_lst.push_back(parm_ptr);
}

/* Pre-Allocation Output
 * Allocates Numpy memory for use within the routine,
 * and saves a copy-procedure at the end when 'Output'
 * is built.
 *
 * Allocates the NPY memory segment, then wraps it using
 * the array library object (in this case PyFI::Array).
 */
template <class T>
void FuncIF::SetOutput(T **out_ptr, const uint64_t ndim, const uint64_t *dimensions)
{
    /* use template to pass type */
    const type_info *type = &typeid(T);
    string name = LongToString(out_lst.size());

    if (*out_ptr != NULL)
    {
        stringstream ss;
        ss << "PyFI: PreAlloc Output Arg \'" << name << "\': " <<
           "SetOutput() ptr is not NULL (possible memory leak).";
        Error(ss.str());
    }

    /* copy to native npy_intp type */
    npy_intp *pydims = NPYDIMS_rev(ndim, dimensions);

    /* Determine which parm obj to instantiate. */
    Parm_Abstract *parm_ptr = NewParm(name, type);
    parm_ptr->SetParmType(PYIF_PARM_NPYPRE);
    parm_ptr->SetPyObjPtr(PyArray_SimpleNew((int) ndim, pydims, NPY_type(type))); /* new ref */
    parm_ptr->Convert_In();
    out_lst.push_back(parm_ptr);

    /* send ptr back to user for use in algorithm */
    *out_ptr = (T *) parm_ptr->GetVal();

    free(pydims);
}

/* Pre-Allocation Output #2
 * Allocates Numpy memory for use within the routine,
 * and saves a copy-procedure at the end when 'Output'
 * is built.
 *
 * Allocates the NPY memory segment, then wraps it using
 * the array library object (in this case PyFI::Array).
 */
template <class T>
void FuncIF::SetOutput(T **out_ptr, const uint64_t ndim, const PyFI::Array<uint64_t> &dimensions)
{
    /* use template to pass type */
    const type_info *type = &typeid(T);
    string name = LongToString(out_lst.size());

    if (*out_ptr != NULL)
    {
        stringstream ss;
        ss << "PyFI: PreAlloc Output Arg \'" << name << "\': " <<
           "SetOutput() ptr is not NULL (possible memory leak).";
        Error(ss.str());
    }

    /* copy to native npy_intp type */
    npy_intp *pydims = NPYDIMS_rev(ndim, dimensions.data());

    /* Determine which parm obj to instantiate. */
    Parm_Abstract *parm_ptr = NewParm(name, type);
    parm_ptr->SetParmType(PYIF_PARM_NPYPRE);
    parm_ptr->SetPyObjPtr(PyArray_SimpleNew((int) ndim, pydims, NPY_type(type))); /* new ref */
    parm_ptr->Convert_In();
    out_lst.push_back(parm_ptr);

    /* send ptr back to user for use in algorithm */
    *out_ptr = (T *) parm_ptr->GetVal();

    free(pydims);
}

/* Pre-Allocation Output #3
 * Allocates Numpy memory for use within the routine,
 * and saves a copy-procedure at the end when 'Output'
 * is built.
 *
 * Allocates the NPY memory segment, then wraps it using
 * the array library object (in this case PyFI::Array).
 */
template <class T>
void FuncIF::SetOutput(T **out_ptr, const ArrayDimensions &dims_obj)
{
    /* use template to pass type */
    const type_info *type = &typeid(T);
    string name = LongToString(out_lst.size());

    if (*out_ptr != NULL)
    {
        stringstream ss;
        ss << "PyFI: PreAlloc Output Arg \'" << name << "\': " <<
           "SetOutput() ptr is not NULL (possible memory leak).";
        Error(ss.str());
    }

    uint64_t ndim = dims_obj.ndim();

    /* copy to native npy_intp type */
    npy_intp *pydims = NPYDIMS_rev(dims_obj.ndim(), dims_obj.dimensions());

    /* Determine which parm obj to instantiate. */
    Parm_Abstract *parm_ptr = NewParm(name, type);
    parm_ptr->SetParmType(PYIF_PARM_NPYPRE);
    parm_ptr->SetPyObjPtr(PyArray_SimpleNew((int) ndim, pydims, NPY_type(type))); /* new ref */
    parm_ptr->Convert_In();
    out_lst.push_back(parm_ptr);

    /* send ptr back to user for use in algorithm */
    *out_ptr = (T *) parm_ptr->GetVal();

    free(pydims);
}




/* 1) Assemble the output single-variable or tuple (as necessary).
 *      PyTuple_New()
 *      PyTuple_SetItem()
 * 2) Pass result to Py_BuildValue() for a return object.
 * 3) Mark output objects as USED so they don't get DECREF'd by
 *    their destructor.
 */
PyObject *FuncIF::Output(void)
{
    /* The list was built in the output order
     * so just build the tuple directly from
     * the list. */
    uint64_t num_elem = out_lst.size();

    /* if no output ptrs have been saved */
    if (num_elem == 0)
    {
        return Py_BuildValue(""); /* None */
    }

    /* if only one argument, then don't wrap in a tuple */
    else if (num_elem == 1)
    {
        out_itr = out_lst.begin();
        return Py_BuildValue("N", (*out_itr)->GetPyObjPtr());
    }

    /* more than one output */
    else
    {
        uint64_t pos=0; /* current tuple position */
        PyObject *out_tup = PyTuple_New(num_elem); /* new tup ref */
        for (out_itr = out_lst.begin(); out_itr != out_lst.end(); ++out_itr)
        {
            /* steals ref */
            if (PyTuple_SetItem(out_tup, pos, (*out_itr)->GetPyObjPtr()) != 0)
            {
                stringstream ss;
                ss << "PyFI: Output() failed to set item #" << pos << " in output tuple.";
                Error(ss.str());
            }
            ++pos;
        }
        return Py_BuildValue("N", out_tup);
    }

    return NULL; /* failure */
}

/******************************************************************************
 * PY-CALLABLE CLASS
 *
 * Make a simple interface object to a python callable.
 *  -array translation is done by wrapping the given segment into a numpy array.
 *  -this is embedding python
 *  -all array pointers will be deleted when the object falls out of scope.
 */

/* Mutex for py-calls within threads.
 *  http://www.codevate.com/blog/7-concurrency-with-embedded-python-in-a-multi-threaded-c-application 
 */
#define _PYFI_PYCALLABLE_ACQUIRE_GIL _gstate = PyGILState_Ensure();
#define _PYFI_PYCALLABLE_RELEASE_GIL PyGILState_Release(_gstate);

#define _PYCALLABLE_SUCCESS 0
#define _PYCALLABLE_FAILED  1

/**
 * A simple interface object to a Python callable.
 *
 * This provides Python functions to the C/C++ environment with minimal setup.
 * The PyCallable object essentially does 3 things: 1 the numeric array
 * translation is handled between Numpy and the Array object, 2 embeds the
 * Python interpreter and 3 all array pointers are destructed when the
 * PyCallable object falls out of scope.
 *
 * An example a matrix transpose using the numpy.transpose function:
 * \code
 * Array<double> A(5,10); // matrix to be transposed
 *
 * PyCallable tp("numpy", "transpose"); // setup the transpose function
 *
 * tp.SetArg_Array(&A); // push 'A' onto the arg list to be passed to numpy.transpose(*arg)
 *
 * Array<T> *out=NULL;
 * tp.GetReturn_Array(&out); // exec Python and pop the result from the return list
 * \endcode
 */
class PyCallable
{
    private:

        /* thread safety */
        PyGILState_STATE _gstate; 

        PyObject *_pModule;
        PyObject *_pFunc;
        PyObject *_pArgList;
        PyObject *_pValue;
        uint64_t _pValue_index;

        bool _hasBeenRun;
        bool _user_code;
        string _code; /* user input code */

        /* hold input and output arrays */
        list<Parm_Abstract *> _arrays;
        list<Parm_Abstract *>::iterator _arrays_itr;

    public:
        /** 
         * The "module-function" constructor.
         *
         * Run an existing function from the given module & function supplied
         * in each string.
         *
         * \code
         * // C-code...
         * PyCallable myPinv("scipy.linalg", "pinv");
         *
         * # Under the hood in Python...
         * from scipy.linalg import pinv
         * \endcode
         *
         * \param module The Python accessible module name (e.g.
         * "scipy.linalg").
         * \param function The function implemented by that module (e.g.
         * "pinv").
         */
        PyCallable(const string module, const string function)
        {
            _pModule = NULL;
            _pFunc = NULL;
            _pArgList = NULL;
            _pValue = NULL;
            _pValue_index = 0;
            _user_code = false;
            _hasBeenRun = false;

            /* NOTE: not sure if GIL can be acquired
             * before python is started. */
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            StartPython();            
            Load_PyMod(module);
            Load_PyMod_Function(function);
            _PYFI_PYCALLABLE_RELEASE_GIL
        }

        /**
         * The "script-as-a-string" constructor.
         *
         * Run a Python script from a supplied string.  The script must define
         * a function named "func".  This function will be executed by
         * PyCallable and if it returns the output will be made available via
         * the GetReturn_<type>() member functions.
         *
         * \code
         * // Define the python code in a string, taking care to include line
         * // endings and correct indentation.
         * string code = "def func(in1):\n"
         *               "    from numpy.fft import fft, fftshift, ifftshift\n"
         *               "    return fftshift( fft( ifftshift(in1) ) ).astype(in1.dtype)\n";
         * PyCallable fft_script(code);
         * \endcode
         *
         * \param code 
         */
        PyCallable(const string code)
        {
            _pModule = NULL;
            _pFunc = NULL;
            _pArgList = NULL;
            _pValue = NULL;
            _pValue_index = 0;
            _user_code = true;
            _code = code;
            _hasBeenRun = false;

            /* NOTE: not sure if GIL can be acquired
             * before python is started. */
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            StartPython();            
            _PYFI_PYCALLABLE_RELEASE_GIL
        }

        /**
         * The destructor frees all input arguments, generated arrays, and
         * unloads any Python modules and functions.
         */
        ~PyCallable()
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL

            /* delete wrappers first */
            FreeArrays();

            FreeInputArgs();
            FreeReturnValues();
            Unload_PyFunction();
            Unload_PyMod();

            _PYFI_PYCALLABLE_RELEASE_GIL
        }

        /**
         * Resets the input and output args for a new run.
         */
        void Reset(void)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL

            FreeArrays();
            FreeInputArgs();
            FreeReturnValues();
            _hasBeenRun = false;

            _PYFI_PYCALLABLE_RELEASE_GIL
        }

        /**
         * Runs the Python code assembled by the constructor.
         *
         * \note This is only necessary if a GetReturn_<type>() function is
         * not going to be called or if the actual Python code execution time
         * is crucial.
         */
        void Run(void)
        {
            if (_hasBeenRun)
                return;

            _PYFI_PYCALLABLE_ACQUIRE_GIL
            if (_user_code)
            {
                RunUserCode();
                _hasBeenRun = true;
            }
            else
            {
                RunPyFunction(); 
                _hasBeenRun = true;
            }
            _PYFI_PYCALLABLE_RELEASE_GIL
        }

    private:

        void gc(void)
        {
            PyRun_SimpleString("import gc; gc.collect()\n");
        }

        void FreeArrays(void)
        {
            /* delete wrappers first */
            for (_arrays_itr = _arrays.begin(); _arrays_itr != _arrays.end(); ++_arrays_itr)
                delete *_arrays_itr;
        }

        void *__import_array(void)
        {
            import_array(); /* required for using numpy arrays */
            return NULL;
        }

        /* 1) check if python has been initialized
        * 2) initialize numpy
        */
        void StartPython(void)
        {
            /* initialize interpreter ONLY if needed */
            if (Py_IsInitialized() == 0)
            {
                Py_Initialize();
                __import_array(); /* required for using numpy arrays */
            }
            /*
            else
            {
                cout << "\n\nPython is already started.\n\n";
            }
            */
        }

        /* Allow the loading of one python module per projectPy session.
        *  -stores module ptr in global var
        */
        void Load_PyMod(const string modName)
        {
            /* get module ptr */
            if (_pModule == NULL)
            {
                _pModule = PyImport_ImportModule(modName.c_str());

                /* print python errors */
                if (PyErr_Occurred()) PyErr_Print();

                if (_pModule == NULL)
                {
                    PYFI_INT_ERROR("PyCallable: Load_PyMod(): "<<modName<<" failed to load.\n");
                }
            }
        }

        /* Allow the loading of one python function from the loaded module */
        void Load_PyMod_Function(const string funcName)
        {
            if (_pModule != NULL)
            {
                if (_pFunc == NULL)
                {
                    /* get a handle to the function */
                    _pFunc = PyObject_GetAttrString(_pModule, funcName.c_str());

                    /* check that function exists and that its not just a python object */
                    if (!(_pFunc && PyCallable_Check(_pFunc)))
                    {
                        Py_XDECREF(_pFunc);
                        if (PyErr_Occurred()) PyErr_Print();
                        PYFI_INT_ERROR("PyCallable: Load_PyMod_Function(): cannot find function \'"<<funcName<<"\'\n");
                    }
                }
            }
            else
            {
                PYFI_INT_ERROR("PyCallable: Load_PyMod_Function(): No module loaded.\n");
            }
        }

        /* Just a simple wrapper that internally uses the global function ptr.
        *  -a NULL ptr is allowed if no args are needed.
        */
        void RunUserCode(void)
        {
            PyObject *local_args = NULL;

            /* only assemble input port if there is data */
            if (_pArgList != NULL)
            {
                /* build parameter port list into a tuple so that
                * it can be passed to the python function */
                local_args = PyList_AsTuple(_pArgList);
            }

            /* make sure the output port is clear */
            if (_pValue != NULL)
                Py_CLEAR(_pValue);

            /* get global ref */
            PyObject *main_mod = PyImport_AddModule("__main__");
            PyObject *pGlobal = PyModule_GetDict(main_mod);

            /* Create a new module object */
            _pModule = PyModule_New("PYFI_EMBEDDED_MOD");
            PyModule_AddStringConstant(_pModule, "__file__", "");
            PyObject *pLocal = PyModule_GetDict(_pModule);

            /* load the code as if it where a file */
            PyObject *tmp = PyRun_String(_code.c_str(), Py_file_input, pGlobal, pLocal);

            /* run the py-function, user code must implement 'func' */
            _pFunc = PyObject_GetAttrString(_pModule, "func");

            /* run the py-function */
            _pValue = PyObject_CallObject(_pFunc, local_args);

            /* print python errors */
            if (PyErr_Occurred()) PyErr_Print();

            /* remove the argument encompassing tuple used for
            * passing the port list form c to the py-function */
            Py_CLEAR(local_args);
            Py_DECREF(tmp);
        }


        /* Just a simple wrapper that internally uses the global function ptr.
        *  -a NULL ptr is allowed if no args are needed.
        */
        void RunPyFunction(void)
        {
            PyObject *local_args = NULL;

            /* only assemble input port if there is data */
            if (_pArgList != NULL)
            {
                /* build parameter port list into a tuple so that
                * it can be passed to the python function */
                local_args = PyList_AsTuple(_pArgList);
            }

            /* make sure the output port is clear */
            if (_pValue != NULL)
                Py_CLEAR(_pValue);

            /* run the py-function */
            _pValue = PyObject_CallObject(_pFunc, local_args);

            /* print python errors */
            if (PyErr_Occurred()) PyErr_Print();

            /* remove the argument encompassing tuple used for
            * passing the port list form c to the py-function */
            Py_CLEAR(local_args);
        }

        /* free the args by releasing the tuple thats holding them */
        void FreeInputArgs(void)
        {
            if (_pArgList != NULL)
                Py_CLEAR(_pArgList);
            _pArgList = NULL;
        }

        /* free the returns by releasing the tuple thats holding them */
        void FreeReturnValues(void)
        {
            if (_pValue != NULL)
                Py_CLEAR(_pValue);
            _pValue = NULL;

            /* return index to zero for the next
            * set of return values */
            _pValue_index = 0;
        }

        /* unload python module from memory */
        void Unload_PyMod(void)
        {
            if (_pModule == NULL)
                PYFI_INT_ERROR("PyCallable: Unload_PyMod: The module ptr is already empty!\n");

            Py_CLEAR(_pModule);
        }

        /* unload python module from memory */
        void Unload_PyFunction(void)
        {
            if (_pFunc == NULL)
                PYFI_INT_ERROR("PyCallable: Unload_PyFunction: The function ptr is already empty!\n");
            Py_CLEAR(_pFunc);
        }

        /* Retrieve python objects from py-function return value
        * in the order in which they are asked for.
        *  -helper routine for specific data types
        */
        PyObject *_GetReturn_Item(void)
        {

            /* Run the python code if it hasn't already run. */
            this->Run();

            PyObject *curVal = NULL;

            /* check return value */
            if (_pValue != NULL)
            {
                /* if its not a tuple, then its probably a single return value 
                 * so just use the appropriate getter.
                 */
                if (!PyTuple_CheckExact(_pValue))
                    return(_pValue);

                uint64_t pVal_len = PyTuple_Size(_pValue);

                /* make sure the requested index exists */
                if (_pValue_index < pVal_len)
                {
                    /* returns borrowed ref, so no need to decref curVal */
                    curVal = PyTuple_GetItem(_pValue, _pValue_index);
                    _pValue_index++;
                    return(curVal);
                }
                else
                {
                    /* the user is requesting outputs that don't exist */
                    PYFI_INT_ERROR("PyCallable: _GetReturn_Item: Too many output items requested, there is "<<pVal_len<<" return value(s).\n");
                    return NULL;
                }
            }

            /* if return value doesn't exist, then throw error */
            PYFI_INT_ERROR("PyCallable: _GetReturn_Item: Empty output port at index "<<_pValue_index);
            return NULL;
        }

        /*
        * This only checks that the array is contiguous and writable and
        * dies otherwise.
        */
        PyObject *NPYarrayFromNPYOTFPyArg(PyObject *in, int reqs)
        {
            if (in == NULL)
                PYFI_INT_ERROR("PyCallable: NPYarrayFromNPYOTFPyArg: return is NULL.\n");

            int type = PyArray_TYPE((PyArrayObject *)in); /* get data type */
            PyObject *out=NULL;

            /* returned object is either new or a new reference */
            out = PyArray_FROM_OTF(in, type, reqs);
            if (out == NULL)
                PYFI_INT_ERROR("PyCallable: NPYarrayFromNPYOTFPyArg: PyArray was not imported.");

            return(out);
        }

        /* convert position number to string */
        string LongToString(int64_t pos)
        {
            stringstream ss;
            ss << pos;
            return ss.str();
        }

        /* translates typeid into associated parm-object */
        Parm_Abstract *NewParm(string name, const type_info *type)
        {
            /* Determine which parm obj to instantiate. */
            Parm_Abstract *parm_ptr = NULL;
            parm_ptr = new Parm_BASICARRAY(name, type);

            if (parm_ptr == NULL)
            {
                PYFI_INT_ERROR(_PYFI_RED "PyCallable: NewParm: requested typeid not found for Arg #"<<name<<"(zero based)." _PYFI_NOC << supportedTypes());
            }

            return parm_ptr;
        }

    public:

        /** 
         * Push a string onto the argument list that will be sent to the
         * function defined in the constructor.
         *
         * \param in A string argument to be passed to Python code.
         */
        void SetArg_String(const string in)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            /* create a new tuple if needed */
            if (_pArgList == NULL)
            {
                _pArgList = PyList_New(0);
            }

            /* convert to python string */
            PyObject *pItem = PyUnicode_FromString(in.c_str());

            /* add to list */
            if (PyList_Append(_pArgList, pItem) != _PYCALLABLE_SUCCESS)
            {
                PYFI_INT_ERROR("PyCallable: SetArg_String: Failed to append to arg list.\n");
            }
            Py_DECREF(pItem);
            _PYFI_PYCALLABLE_RELEASE_GIL
        }

        /** 
         * Push an integer onto the argument list that will be sent to the
         * function defined in the constructor.
         *
         * \param in An integer argument to be passed to Python code.
         */
        void SetArg_Long(const int64_t in)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            /* create a new tuple if needed */
            if (_pArgList == NULL)
            {
                _pArgList = PyList_New(0);
            }

            /* convert to python string */
            PyObject *pItem = PyLong_FromLong(in);

            /* add to list */
            if (PyList_Append(_pArgList, pItem) != _PYCALLABLE_SUCCESS)
            {
                PYFI_INT_ERROR("PyCallable: SetArg_Long: Failed to append to arg list.\n");
            }
            Py_DECREF(pItem);
            _PYFI_PYCALLABLE_RELEASE_GIL
        }

        /** 
         * Push an double precision float onto the argument list that will be
         * sent to the function defined in the constructor.
         *
         * \param in An double precision float argument to be passed to Python
         * code.
         */
        void SetArg_Double(double in)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            /* create a new tuple if needed */
            if (_pArgList == NULL)
            {
                _pArgList = PyList_New(0);
            }

            /* convert to python string */
            PyObject *pItem = PyFloat_FromDouble(in);

            /* add to list */
            if (PyList_Append(_pArgList, pItem) != _PYCALLABLE_SUCCESS)
            {
                PYFI_INT_ERROR("PyCallable: SetArg_Double: Failed to append to arg list.\n");
            }
            Py_DECREF(pItem);
            _PYFI_PYCALLABLE_RELEASE_GIL
        }

        /** 
         * Push an Array onto the argument list that will be sent to the
         * function defined in the constructor.  This will convert to a Numpy
         * array in Python.
         *
         * \param in An Array argument to be passed to Python code.
         */
        template<class T>
        void SetArg_Array(T *out_ptr)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            /* create a new tuple if needed */
            if (_pArgList == NULL)
            {
                _pArgList = PyList_New(0);
            }

            /* use template to pass type */
            const type_info *type = &typeid(T);
            string name = "input Array<T>";

            if (out_ptr == NULL)
            {
                PYFI_INT_ERROR("PyCallable: SetArg_Array: input ptr is NULL.");
            }

            /* Determine which parm obj to instantiate. */
            Parm_Abstract *parm_ptr = NewParm(name, type);
            parm_ptr->SetParmType(PYIF_PARM_OUTPUT); /* use parm destructor */
            parm_ptr->SetVal(out_ptr);
            parm_ptr->WrapSegWithNPY(); /* new pyobject ref wrapper */
            _arrays.push_back(parm_ptr);

            PyObject *pItem = parm_ptr->GetPyObjPtr();

            /* add to arg list */
            if (PyList_Append(_pArgList, pItem) != _PYCALLABLE_SUCCESS)
            {
                PYFI_INT_ERROR("PyCallable: SetArg_Array: Failed to append to arg list.\n");
            }
            Py_DECREF(pItem);

            _PYFI_PYCALLABLE_RELEASE_GIL
        }

        /* This should probably be a private method since it returns a Python
         * object which is of no immediate use. */
        PyObject *GetReturn_NPYarray(void)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            PyObject *curVal = _GetReturn_Item();
            _PYFI_PYCALLABLE_RELEASE_GIL

            /* c-string */
            if (curVal != NULL)
            {
                /* TODO: this should be changed to memcpy the string
                * to a malloc'd buffer so that it can be free'd by
                * calling function, not sure what the behavior will
                * be for this as it is. */
                _PYFI_PYCALLABLE_ACQUIRE_GIL
                PyObject *out = NPYarrayFromNPYOTFPyArg(curVal, NPY_ARRAY_IN_ARRAY);
                _PYFI_PYCALLABLE_RELEASE_GIL
                return(out);
            }

            /* if non of these are the case */
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            PYFI_INT_ERROR("PyCallable: GetReturn_NPYarray: Return value is not convertible.\n");
            _PYFI_PYCALLABLE_RELEASE_GIL
            return NULL;
        }

        /** 
         * Pop an Array off of the return-list object that will be sent back to
         * the PyCallable defined in the C-code.  This will convert a Numpy
         * array to an Array object.
         *
         * \note If Run() hasen't been called yet, the first GetReturn_<type>()
         * function will automatically call it.
         *
         * \return Array
         */
        template<class T>
        void GetReturn_Array(T **out_ptr)
        {
            string name = LongToString(_pValue_index);

            /* Make sure the user isn't causing a mem leak */
            if (*out_ptr != NULL)
            {
                PYFI_INT_ERROR("PyCallable: GetReturn_Array(): passed ptr is not NULL (possible memory leak) for out-arg #"<<_pValue_index<<" (zero-based).");
            }

            /* translate npy type */
            const type_info *type = &typeid(T);

            /* Determine which parm obj to instantiate. */
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            Parm_Abstract *parm_ptr = NewParm(name, type);
            parm_ptr->SetParmType(PYIF_PARM_OUTPUT); /* use parm destructor */
            parm_ptr->SetPyObjPtr(_GetReturn_Item());
            parm_ptr->Convert_In();           
            _PYFI_PYCALLABLE_RELEASE_GIL

            *out_ptr = (T *) parm_ptr->GetVal();

            _arrays.push_back(parm_ptr);
        }

        /** 
         * Pop a string off of the return-list object that will be sent back to
         * the PyCallable defined in the C-code.
         *
         * \note If Run() hasen't been called yet, the first GetReturn_<type>()
         * function will automatically call it.
         *
         * \return standard library string
         */
        string GetReturn_String(void)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            PyObject *curVal = _GetReturn_Item();
            _PYFI_PYCALLABLE_RELEASE_GIL

            /* c-string */
            if (curVal != NULL)
            {
                /* TODO: this should be changed to memcpy the string
                * to a malloc'd buffer so that it can be free'd by
                * calling function, not sure what the behavior will
                * be for this as it is. */
                _PYFI_PYCALLABLE_ACQUIRE_GIL
                string out = PyUnicode_AS_DATA(curVal);
                _PYFI_PYCALLABLE_RELEASE_GIL
                return(out);
            }

            /* if non of these are the case */
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            PYFI_INT_ERROR("PyCallable: GetReturn_String: Return value is not convertible.\n");
            _PYFI_PYCALLABLE_RELEASE_GIL
            return NULL;
        }

        /** 
         * Pop a long integer off of the return-list object that will be sent
         * back to the PyCallable defined in the C-code.
         *
         * \note If Run() hasen't been called yet, the first GetReturn_<type>()
         * function will automatically call it.
         *
         * \return an int64_t long integer type
         */
        int64_t GetReturn_Long(void)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            PyObject *curVal = _GetReturn_Item();
            _PYFI_PYCALLABLE_RELEASE_GIL

            /* c-string */
            if (curVal != NULL)
            {
                /* TODO: this should be changed to memcpy the string
                * to a malloc'd buffer so that it can be free'd by
                * calling function, not sure what the behavior will
                * be for this as it is. */
                _PYFI_PYCALLABLE_ACQUIRE_GIL
                int64_t out = PyLong_AsLong(curVal);
                _PYFI_PYCALLABLE_RELEASE_GIL
                return(out);
            }

            /* if non of these are the case */
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            PYFI_INT_ERROR("PyCallable: GetReturn_Long: Return value is not convertible.\n");
            _PYFI_PYCALLABLE_RELEASE_GIL
            return _PYCALLABLE_FAILED;
        }

        /** 
         * Pop a double precision float off of the return-list object that will
         * be sent back to the PyCallable defined in the C-code.
         *
         * \note If Run() hasen't been called yet, the first GetReturn_<type>()
         * function will automatically call it.
         *
         * \return a double precision float
         */
        double GetReturn_Double(void)
        {
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            PyObject *curVal = _GetReturn_Item();
            _PYFI_PYCALLABLE_RELEASE_GIL

            /* c-string */
            if (curVal != NULL)
            {
                /* TODO: this should be changed to memcpy the string
                * to a malloc'd buffer so that it can be free'd by
                * calling function, not sure what the behavior will
                * be for this as it is. */
                _PYFI_PYCALLABLE_ACQUIRE_GIL
                double out = PyFloat_AsDouble(curVal);
                _PYFI_PYCALLABLE_RELEASE_GIL
                return(out);
            }

            /* if non of these are the case */
            _PYFI_PYCALLABLE_ACQUIRE_GIL
            PYFI_INT_ERROR("PyCallable: GetReturn_Double: Return value is not convertible.\n");
            _PYFI_PYCALLABLE_RELEASE_GIL
            return _PYCALLABLE_FAILED;
        }
}; // PyCallable class



}// namespace

#endif // GUARD
