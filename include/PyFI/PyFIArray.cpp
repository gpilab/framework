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

#ifndef _BASICARRAYIF_CPP_GUARD
#define _BASICARRAYIF_CPP_GUARD
/**
    \brief A simple nD array class that is portable.
        TODO: make it nD, current max is 10.
**/

#include <iostream>
#include <map>
#include <typeinfo>
#include <complex>
#include <vector>
using namespace std;

#include <execinfo.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h> /* fabs */

#include "PyFI/PyFIMacros.h"
#include "PyFI/backtrace.cpp"

/* allow the user to change this */
#ifndef PYFI_PRINT_ELEMLIMIT
#define PYFI_PRINT_ELEMLIMIT 20
#endif


/* indexing macros 
 * -in debug mode they will include the file:line operator
 * -in normal mode they will just use the direct indexing operator (faster)
 */
#ifdef PYFI_ARRAY_DEBUG
    #define get1(_arr, _i) (_arr)(_i,__FILE__,__LINE__)
    #define get2(_arr, _i, _j) (_arr)(_i, _j,__FILE__,__LINE__)
    #define get3(_arr, _i, _j, _k) (_arr)(_i, _j, _k,__FILE__,__LINE__)
    #define get4(_arr, _i, _j, _k, _l) (_arr)(_i, _j, _k, _l,__FILE__,__LINE__)
    #define get5(_arr, _i, _j, _k, _l, _m) (_arr)(_i, _j, _k, _l, _m,__FILE__,__LINE__)
    #define get6(_arr, _i, _j, _k, _l, _m, _n) (_arr)(_i, _j, _k, _l, _m, _n,__FILE__,__LINE__)
    #define get7(_arr, _i, _j, _k, _l, _m, _n, _o) (_arr)(_i, _j, _k, _l, _m, _n, _o,__FILE__,__LINE__)
    #define get8(_arr, _i, _j, _k, _l, _m, _n, _o, _p) (_arr)(_i, _j, _k, _l, _m, _n, _o, _p,__FILE__,__LINE__)
    #define get9(_arr, _i, _j, _k, _l, _m, _n, _o, _p, _q) (_arr)(_i, _j, _k, _l, _m, _n, _o, _p, _q,__FILE__,__LINE__)
    #define get10(_arr, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r) (_arr)(_i, _j, _k, _l, _m, _n, _o, _p, _q, _r,__FILE__,__LINE__)

#else
    #define get1(_arr, _i) (_arr)(_i)
    #define get2(_arr, _i, _j) (_arr)(_i, _j)
    #define get3(_arr, _i, _j, _k) (_arr)(_i, _j, _k)
    #define get4(_arr, _i, _j, _k, _l) (_arr)(_i, _j, _k, _l)
    #define get5(_arr, _i, _j, _k, _l, _m) (_arr)(_i, _j, _k, _l, _m)
    #define get6(_arr, _i, _j, _k, _l, _m, _n) (_arr)(_i, _j, _k, _l, _m, _n)
    #define get7(_arr, _i, _j, _k, _l, _m, _n, _o) (_arr)(_i, _j, _k, _l, _m, _n, _o)
    #define get8(_arr, _i, _j, _k, _l, _m, _n, _o, _p) (_arr)(_i, _j, _k, _l, _m, _n, _o, _p)
    #define get9(_arr, _i, _j, _k, _l, _m, _n, _o, _p, _q) (_arr)(_i, _j, _k, _l, _m, _n, _o, _p, _q)
    #define get10(_arr, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r) (_arr)(_i, _j, _k, _l, _m, _n, _o, _p, _q, _r)

#endif

/* simplify Array constructor from another Array */
#define DA(_arr) ArrayDimensions((_arr).size(), (_arr).as_ULONG().data())


namespace PyFI
{


/**********************************************************************************************
 * ARRAYDIMENSIONS CLASS
 * Brief: A simple helper for constructing PyFI arrays with a single object param.
 * Its basically a simple dimensions container that is not an Array Object itself.
 */
class ArrayDimensions
{
    private:
        uint64_t _ndim;
        uint64_t *_dimensions;

        /* allocate new memory */
        void array_from_dims(const uint64_t ndim, const uint64_t *dimensions)
        {
            /* copy dimension info */
            _ndim = ndim;
            _dimensions = (uint64_t*)malloc(ndim*sizeof(uint64_t));
            memcpy(_dimensions, dimensions, ndim*sizeof(uint64_t));
        }

    public:
        const uint64_t ndim() const
        {
            return this->_ndim;
        }

        const uint64_t *dimensions() const
        {
            return this->_dimensions;
        }

        std::vector<uint64_t> dimensions_vector()
        {
            std::vector<uint64_t> out;
            for(uint64_t i=0; i<_ndim; ++i)
                out.push_back(_dimensions[i]);
            return out;
        }

        const uint64_t dimensions(uint64_t i) const
        {
            if (i < _ndim)
                return this->_dimensions[i];

            PYFI_INT_ERROR("ArrayDimensions.dimensions(): ndim is out of range: input("<<i<<"), max("<<_ndim-1<<")\n\toffending array: ");
        }

        /* allocate from vector */
        ArrayDimensions(const std::vector<uint64_t> &dims)
        {
            array_from_dims(dims.size(), dims.data());
        }

        ArrayDimensions(uint64_t ndim, uint64_t *dimensions)
        {
            array_from_dims(ndim, dimensions); 
        }

        /* Construct arrays by dim length, COL_MAJOR ordering */
        ArrayDimensions(uint64_t i)
        {
            uint64_t dims[1];
            dims[0] = i;
            array_from_dims(1, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j)
        {
            uint64_t dims[2];
            dims[0] = i;
            dims[1] = j;
            array_from_dims(2, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j, uint64_t k)
        {
            uint64_t dims[3];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            array_from_dims(3, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l)
        {
            uint64_t dims[4];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            array_from_dims(4, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m)
        {
            uint64_t dims[5];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            array_from_dims(5, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n)
        {
            uint64_t dims[6];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            dims[5] = n;
            array_from_dims(6, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o)
        {
            uint64_t dims[7];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            dims[5] = n;
            dims[6] = o;
            array_from_dims(7, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p)
        {
            uint64_t dims[8];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            dims[5] = n;
            dims[6] = o;
            dims[7] = p;
            array_from_dims(8, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q)
        {
            uint64_t dims[9];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            dims[5] = n;
            dims[6] = o;
            dims[7] = p;
            dims[8] = q;
            array_from_dims(9, dims);
        }

        ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q, uint64_t r)
        {
            uint64_t dims[10];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            dims[5] = n;
            dims[6] = o;
            dims[7] = p;
            dims[8] = q;
            dims[9] = r;
            array_from_dims(10, dims);
        }

        ~ArrayDimensions()
        {
            free(_dimensions);
        }

        /* overloaded operators */
        inline bool operator==(const ArrayDimensions &rhs) const // check for equality
        {
            if (this->ndim() != rhs.ndim())
                return false;

            for (uint64_t i=0; i<_ndim; ++i)
                if (this->dimensions(i) != rhs.dimensions(i))
                    return false;
                
            return true;
        }

        /* overloaded operators */
        inline bool operator!=(const ArrayDimensions &rhs) const // check for inequality
        {
            return ! (*this == rhs);
        }

}; // ArrayDimensions Class

/* cout */
ostream& operator<<(ostream& os, const ArrayDimensions& out)
{
    /* print array info */
    os << "ArrayDimensions " << out.ndim() << "D (";
    for(uint64_t i=0; i<out.ndim(); ++i)
    {
        os << out.dimensions()[i];
        if (i < (out.ndim()-1))
            os << " x ";
    }
    os << ")";
    return os;
}




/**********************************************************************************************
 * BASICARRAY CLASS
 * Brief: This is a default class that can be used to convert NPY arrays.  It stores the
 * number of dimensions (ndim) and dimensions array required to generate NPY arrays.
 * The dimensions are stored in C-ordering (row-major).
 *
 * In the event that an array library is not available, for installation or licensing
 * reasons, this array class can be used.
 *
 * The constructor currently supports the allocation of new memory or can be used to wrap
 * an existing data segment.
 */

/* Stores a basic c-array with some extra dimension info from NPY arrays */
template<class T>
class Array
{
    public:

        /* empty constructor */
        Array()
        {
            _size = 0;
            _dimensions = NULL;
            _ndim = 0;
            _wrapper = 0;
            _data = NULL;
        }

        /* allocate from vector */
        Array(const std::vector<uint64_t> &dims)
        {
            array_from_dims(dims.size(), dims.data());
        }

        /* array object constructor */
        Array(const ArrayDimensions &dmo)
        {
            array_from_dims(dmo.ndim(), dmo.dimensions());
        }

        /* allocate new memory */
        Array(uint64_t ndim, uint64_t *dimensions)
        {
            array_from_dims(ndim, dimensions);
        }

        /* wrap an existing memory segment */
        Array(uint64_t ndim, uint64_t *dimensions, T *seg_ptr)
        {
            array_from_segment(ndim, dimensions, seg_ptr);
        }

        /* copy constructor */
        Array(const Array<T> &arr)
        {
            array_from_dims(arr.ndim(), arr.dimensions());
            memcpy(_data, arr.data(), arr.size()*sizeof(T));
        }

        /* from dims array */
        Array(const uint64_t ndim, const Array<uint64_t> &arr)
        {
            if (ndim > arr.size())
                PYFI_INT_ERROR("Array constructor from dims array: ndim is out of range, input("<<ndim<<"), max("<<arr.size()<<")");

            array_from_dims(ndim, arr.data());
        }

        /* Construct arrays by dim length, COL_MAJOR ordering */
        Array(uint64_t i)
        {
            uint64_t dims[1];
            dims[0] = i;
            array_from_dims(1, dims);
        }

        Array(uint64_t i, uint64_t j)
        {
            uint64_t dims[2];
            dims[0] = i;
            dims[1] = j;
            array_from_dims(2, dims);
        }

        Array(uint64_t i, uint64_t j, uint64_t k)
        {
            uint64_t dims[3];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            array_from_dims(3, dims);
        }

        Array(uint64_t i, uint64_t j, uint64_t k, uint64_t l)
        {
            uint64_t dims[4];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            array_from_dims(4, dims);
        }

        Array(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m)
        {
            uint64_t dims[5];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            array_from_dims(5, dims);
        }

        Array(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n)
        {
            uint64_t dims[6];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            dims[5] = n;
            array_from_dims(6, dims);
        }

        Array(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o)
        {
            uint64_t dims[7];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            dims[5] = n;
            dims[6] = o;
            array_from_dims(7, dims);
        }

        Array(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p)
        {
            uint64_t dims[8];
            dims[0] = i;
            dims[1] = j;
            dims[2] = k;
            dims[3] = l;
            dims[4] = m;
            dims[5] = n;
            dims[6] = o;
            dims[7] = p;
            array_from_dims(8, dims);
        }

        ~Array()
        {
            free(_dimensions);
            if (!_wrapper) free(_data);
        }

        inline const uint64_t ndim() const
        {
            return this->_ndim;
        }

        inline const uint64_t *dimensions() const
        {
            return this->_dimensions;
        }

        std::vector<uint64_t> dimensions_vector()
        {
            std::vector<uint64_t> out;
            for(uint64_t i=0; i<_ndim; ++i)
                out.push_back(_dimensions[i]);
            return out;
        }

        inline const uint64_t dimensions(uint64_t i) const
        {
            if (i < _ndim)
                return this->_dimensions[i];

            PYFI_INT_ERROR("Array.dimensions(): ndim is out of range: input("<<i<<"), max("<<_ndim-1<<")\n\toffending array: "<<*this);
        }

        inline const uint64_t size(uint64_t i) const
        {
            return dimensions(i);
        }

        inline ArrayDimensions dims_object()
        {
            ArrayDimensions out(_ndim, _dimensions);
            return out;
        }

        inline const uint64_t size() const
        {
            return this->_size;
        }

        inline T *data() const
        {
            return this->_data;
        }

        const bool isWrapper() const
        {
            return this->_wrapper;
        }

        /* indexing w/ file:line DEBUGGING */
        inline T& operator()(uint64_t i, string fn, uint64_t ln)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[1];
            ind[0] = i;
            check_dim_range(1, ind, fn, ln);
            #endif
            return _data[i];
        }

        inline T& operator()(uint64_t i, uint64_t j, string fn, uint64_t ln)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[2];
            ind[0] = i;
            ind[1] = j;
            check_dim_range(2, ind, fn, ln);
            #endif
            return _data[_dimensions[0]*(j) + (i)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, string fn, uint64_t ln)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[3];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            check_dim_range(3, ind, fn, ln);
            #endif
            return ((_data)[ (_dimensions[0] * (_dimensions[1]*(k) + (j)) ) + (i) ]);
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, string fn, uint64_t ln)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[4];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            check_dim_range(4, ind, fn, ln);
            #endif
            return ((_data)[ (_dimensions[0] * ((_dimensions[1] * (_dimensions[2]*(l) + (k))) + (j))) + (i)]);
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, string fn, uint64_t ln)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[5];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            check_dim_range(5, ind, fn, ln);
            #endif
            return ( (_data) + (((_dimensions[0] * ((_dimensions[1] * ((_dimensions[2] * (_dimensions[3] * (m) + (l))) + (k))) + (j))) + (i))) )[0];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, string fn, uint64_t ln)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[6];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            check_dim_range(6, ind, fn, ln);
            #endif
            return ((_data) + (  ((_dimensions[0] * ((_dimensions[1] * ((_dimensions[2] * ((_dimensions[3] * (_dimensions[4] * (n) + (m))) + (l))) + (k))) + (j))) + (i))) )[0];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, string fn, uint64_t ln)
        {
            uint64_t ind[7];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            ind[6] = o;

            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(7, ind, fn, ln);
            #endif

            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, string fn, uint64_t ln)
        {
            uint64_t ind[8];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            ind[6] = o;
            ind[7] = p;

            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(8, ind, fn, ln);
            #endif

            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q, string fn, uint64_t ln)
        {
            uint64_t ind[9];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            ind[6] = o;
            ind[7] = p;
            ind[8] = q;

            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(9, ind, fn, ln);
            #endif

            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q, uint64_t r, string fn, uint64_t ln)
        {
            uint64_t ind[10];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            ind[6] = o;
            ind[7] = p;
            ind[8] = q;
            ind[9] = r;

            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(10, ind, fn, ln);
            #endif

            return _data[this->index(ind)];
        }


        /* indexing 
         * -for 1-6D use direct index equations
         * -for 7-10D use looped index() function (little slower)
         */

        /* pretend the last dimension is a vector */
        inline T& get1v(uint64_t i, uint64_t v)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[1];
            ind[0] = _dimensions[0]*(i) + (v);
            check_dim_range(1, ind, "???", 0);
            #endif
            return _data[_dimensions[0]*(i) + (v)];
        }

        inline T& operator()(uint64_t i)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[1];
            ind[0] = i;
            check_dim_range(1, ind, "???", 0);
            #endif
            return _data[i];
        }

        inline T& operator()(uint64_t i, uint64_t j)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[2];
            ind[0] = i;
            ind[1] = j;
            check_dim_range(2, ind, "???", 0);
            #endif
            return _data[_dimensions[0]*(j) + (i)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[3];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            check_dim_range(3, ind, "???", 0);
            #endif
            return ((_data)[ (_dimensions[0] * (_dimensions[1]*(k) + (j))) + (i) ]);
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[4];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            check_dim_range(4, ind, "???", 0);
            #endif
            return ((_data)[ (_dimensions[0] * ((_dimensions[1] * (_dimensions[2]*(l) + (k))) + (j))) + (i)]);
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[5];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            check_dim_range(5, ind, "???", 0);
            #endif

            return ( (_data) + (((_dimensions[0] * ((_dimensions[1] * ((_dimensions[2] * (_dimensions[3] * (m) + (l))) + (k))) + (j))) + (i))) )[0];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n)
        {
            #ifdef PYFI_ARRAY_DEBUG
            uint64_t ind[6];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            check_dim_range(6, ind, "???", 0);
            #endif
            return ((_data) + (  ((_dimensions[0] * ((_dimensions[1] * ((_dimensions[2] * ((_dimensions[3] * (_dimensions[4] * (n) + (m))) + (l))) + (k))) + (j))) + (i))) )[0];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o)
        {
            uint64_t ind[7];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            ind[6] = o;

            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(7, ind, "???", 0);
            #endif

            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p)
        {
            uint64_t ind[8];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            ind[6] = o;
            ind[7] = p;

            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(8, ind, "???", 0);
            #endif

            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q)
        {
            uint64_t ind[9];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            ind[6] = o;
            ind[7] = p;
            ind[8] = q;

            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(9, ind, "???", 0);
            #endif

            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q, uint64_t r)
        {
            uint64_t ind[10];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            ind[6] = o;
            ind[7] = p;
            ind[8] = q;
            ind[9] = r;

            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(10, ind, "???", 0);
            #endif

            return _data[this->index(ind)];
        }

        /* overloaded math operators, ARRAY MATH '=' based*/
        /* this only copies elements b/c the segment being wrapped might be owned by python */
        inline Array<T>& operator=(const Array<T>& arr) // copy array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] = arr.data()[i];
            return *this;
        }

        inline Array<T>& operator*=(Array<T> arr) // multiply by array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'*=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] *= arr(i);
            return *this;
        }

        inline Array<T>& operator/=(Array<T> arr) // divide by array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'/=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
            {
                #ifdef PYFI_ARRAY_DEBUG
                if (arr(i) == 0)
                {
                    PYFI_INT_ERROR("Array operator \'/=\' divide by zero, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");                       
                }
                #endif
                _data[i] /= arr(i);
            }
            return *this;
        }

        inline Array<T>& operator-=(Array<T> arr) // subtract array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'-=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] -= arr(i);
            return *this;
        }

        inline Array<T>& operator+=(Array<T> arr) // add array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'+=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] += arr(i);
            return *this;
        }

        /* overloaded math operators, ARRAY MATH */
        inline Array<T> operator*(Array<T> arr) // mult array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'*\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<T> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i] * arr(i);
            return out;
        }

        inline Array<T> operator/(Array<T> arr) // divide array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'/\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<T> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
            {
                #ifdef PYFI_ARRAY_DEBUG
                if (arr(i) == 0)
                {
                    PYFI_INT_ERROR("Array operator \'/\' divide by zero, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");                       
                }
                #endif
                out(i) = _data[i] / arr(i);
            }
            return out;
        }

        inline Array<T> operator-(Array<T> arr) // subtract array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'-\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<T> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i] - arr(i);
            return out;
        }

        inline Array<T> operator+(Array<T> arr) // add array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'+\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<T> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i] + arr(i);
            return out;
        }

        /* overloaded math operators, CONST MATH '=' based */
        inline Array<T>& operator=(T c) // assign constant
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] = c;
            return *this;
        }

        /* for setting all values to the constant and implicit casting of c */
        inline void set(T c)
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] = c;
        }

        inline Array<T>& operator*=(T c) // mult constant
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] *= c;
            return *this;
        }

        inline Array<T>& operator/=(T c) // divide constant
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (c == 0)
            {
                PYFI_INT_ERROR("Array operator \'/=\' divide by zero, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<c<<")");                       
            }
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] /= c;
            return *this;
        }

        inline Array<T>& operator-=(T c) // subtract constant
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] -= c;
            return *this;
        }

        inline Array<T>& operator+=(T c) // add constant
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] += c;
            return *this;
        }

        /* overloaded math operators, CONST MATH */
        inline Array<T> operator*(T c) // mult constant
        {
            Array<T> out(*this);
            for (uint64_t i=0; i<_size; ++i)
                out(i) *= c;
            return out;
        }

        inline Array<T> operator/(T c) // divide constant
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (c == 0)
            {
                PYFI_INT_ERROR("Array operator \'/\' divide by zero, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<c<<")");
            }
            #endif

            Array<T> out(*this);
            for (uint64_t i=0; i<_size; ++i)
                out(i) /= c;
            return out;
        }

        inline Array<T> operator-(T c) // subtract constant
        {
            Array<T> out(*this);
            for (uint64_t i=0; i<_size; ++i)
                out(i) -= c;
            return out;
        }

        inline Array<T> operator+(T c) // subtract constant
        {
            Array<T> out(*this);
            for (uint64_t i=0; i<_size; ++i)
                out(i) += c;
            return out;
        }

        /* array masks via inequalities w/ constants */
        inline Array<bool> operator==(T c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] == c);
            return out;
        }

        inline Array<bool> operator!=(T c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] != c);
            return out;
        }

        inline Array<bool> operator<=(T c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] <= c);
            return out;
        }

        inline Array<bool> operator>=(T c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] >= c);
            return out;
        }

        inline Array<bool> operator<(T c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] < c);
            return out;
        }

        inline Array<bool> operator>(T c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] > c);
            return out;
        }


        /* array masks via inequalities w/ other arrays */
        inline Array<bool> operator==(Array<T> arr)
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'==\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] == arr.data()[i]);
            return out;
        }

        inline Array<bool> operator!=(Array<T> arr)
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'!=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] != arr.data()[i]);
            return out;
        }

        inline Array<bool> operator>=(Array<T> arr)
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'>=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] >= arr.data()[i]);
            return out;
        }

        inline Array<bool> operator<=(Array<T> arr)
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'<=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] <= arr.data()[i]);
            return out;
        }

        inline Array<bool> operator<(Array<T> arr)
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'<\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] < arr.data()[i]);
            return out;
        }

        inline Array<bool> operator>(Array<T> arr)
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'>\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] > arr.data()[i]);
            return out;
        }


        /* other math and stat functions */
        inline T sum() // sum all elems
        {
            T out = 0;
            for (uint64_t i=0; i<_size; ++i)
                out += _data[i];
            return out;
        }

        inline T prod() // product of all elems
        {
            T out = 1;
            for (uint64_t i=0; i<_size; ++i)
                out *= _data[i];
            return out;
        }

        inline T min() // min of all elems
        {
            T out = _data[0];
            for (uint64_t i=1; i<_size; ++i)
                out = std::min(out, _data[i]);
            return out;
        }

        inline T max() // max of all elems
        {
            T out = _data[0];
            for (uint64_t i=1; i<_size; ++i)
                out = std::max(out, _data[i]);
            return out;
        }

        inline double max_mag() // max of all elems
        {
            double out = fabs(_data[0]);
            for (uint64_t i=1; i<_size; ++i)
                out = std::max(out, fabs(_data[i]));
            return out;
        }

        /* make all elements the absolute value */
        void abs()
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] = T(fabs(_data[i]));
        }

        /* check for inf values */
        bool any_infs()
        {
            for (uint64_t i=0; i<_size; ++i)
                if ( isinf(fabs(_data[i])) )
                    return true;
            return false;
        }

        /* check for inf values */
        bool any_nans()
        {
            for (uint64_t i=0; i<_size; ++i)
                if ( isnan(fabs(_data[i])) )
                    return true;
            return false;
        }

        /* threshold the data, set all data less than thresh
         * equal to thresh */
        void clamp_min( T thresh )
        {
            for (uint64_t i=0; i<_size; ++i)
                if (_data[i] < thresh)
                    _data[i] = thresh;
        }

        /* threshold the data, set all data greater than thresh
         * equal to thresh */
        void clamp_max( T thresh )
        {
            for (uint64_t i=0; i<_size; ++i)
                if (_data[i] > thresh)
                    _data[i] = thresh;
        }

        /* see if there are any elements with this value. */
        bool any( T val )
        {
            for (uint64_t i=0; i<_size; ++i)
                if (_data[i] == val)
                    return true;
            return false;
        }

        inline T mean() // average of all elems
        {
            T out = this->sum()/(T)_size;
            return out;
        }

        inline T stddev() // standard deviation of all elems
        {
            T avg = this->mean();
            T sum = 0;
            T sub = 0;
            for (uint64_t i=1; i<_size; ++i)
                sub = _data[i] - avg;
                sum += sub * sub;
            return (std::sqrt((sum/(T)_size)));
        }

        /* recast */
        inline Array<uint64_t> as_ULONG()
        {
            Array<uint64_t> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        inline Array<float> as_FLOAT()
        {
            Array<float> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        inline Array<complex<float> > as_CFLOAT()
        {
            Array<complex<float> > out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        inline Array<double> as_DOUBLE()
        {
            Array<double> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        inline Array<complex<double> > as_CDOUBLE()
        {
            Array<complex<double> > out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        inline Array<int64_t> as_LONG()
        {
            Array<int64_t> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        inline Array<int32_t> as_INT()
        {
            Array<int32_t> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        inline Array<uint8_t> as_UCHAR()
        {
            Array<uint8_t> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

    private:

        uint64_t _ndim;
        uint64_t *_dimensions;
        uint64_t _size;
        bool _wrapper;
        T *_data;

        /* get the ND index */
        inline uint64_t index(uint64_t *ind)
        {
            uint64_t n=ind[_ndim-1];
            for (int64_t i=_ndim-2; i>=0; --i)
            {
                n *= _dimensions[i];
                n += ind[i];
            }
            return n;
        }

        /* check local dims agains input dims */
        inline void check_dim_range(uint64_t ndim, uint64_t *indices, string fn, uint64_t ln)
        {
            /* check 1D access */
            if (ndim == 1)
            {
                if (indices[0] >= _size)
                {
                    PYFI_INT_ERROR(endl << Backtrace() << "\nArray: check range: index out of range for 1D indexing, input("<<indices[0]<<"), max("<<_size-1<<")\n\toffending array: "<<*this<<endl<<fn<<":"<<ln);
                }
                return;
            }

            /* arrays can be accessed as 1D */
            if ((ndim != _ndim) && (ndim != 1))
            {
                PYFI_INT_ERROR(endl << Backtrace() << "Array: check range: the number of dims do not match: input("<<ndim<<"D), this array("<<_ndim<<"D)\n\toffending array: "<<*this<<endl<<fn<<":"<<ln);
            }

            for (uint64_t i=0; i<_ndim; ++i)
            {
                if (indices[i] >= _dimensions[i])
                {
                    PYFI_INT_ERROR(endl << Backtrace() << "Array: check range: index out of range for dim("<<i<<"), input("<<indices[i]<<"), max("<<_dimensions[i]-1<<")\n\toffending array: "<<*this<<endl<<fn<<":"<<ln);
                }
            }
        }

        /* allocate new memory */
        void array_from_dims(const uint64_t ndim, const uint64_t *dimensions)
        {
            #ifdef PYFI_ARRAY_DEBUG
            //cout << " (PYFI_ARRAY_DEBUG ON) ";
            #endif

            /* copy dimension info */
            _ndim = ndim;
            _dimensions = (uint64_t*)malloc(ndim*sizeof(uint64_t));
            memcpy(_dimensions, dimensions, ndim*sizeof(uint64_t));

            /* calculate total array size (elem) */
            _size = 1;
            for (uint64_t i=0; i<ndim; ++i)
                (_size) *= dimensions[i];

            /* allocate memory segment, use calloc to set all elem to zero */
            _wrapper = false;
            _data = (T *)calloc(_size, sizeof(T));
        }

        /* wrap an existing memory segment */
        void array_from_segment(const uint64_t ndim, const uint64_t *dimensions, T *seg_ptr)
        {
            #ifdef PYFI_ARRAY_DEBUG
            //cout << " (PYFI_ARRAY_DEBUG ON) ";
            #endif

            /* copy dimension info */
            _ndim = ndim;
            _dimensions = (uint64_t *)malloc(ndim*sizeof(uint64_t));
            memcpy(_dimensions, dimensions, ndim*sizeof(uint64_t));

            /* calculate total array size (elem) */
            _size = 1;
            for (uint64_t i=0; i<ndim; ++i)
                _size *= dimensions[i];

            /* copy memory segment pointer */
            _wrapper = true;
            _data = seg_ptr;
        }

    public:

        /**
            \author Ken Johnson - ken.johnson@asu.edu
            \brief Inserts the data from \a in into \a out in a centered way by \e cropping or \e zero-padding

            This will insert a \e zero-padded or \e cropped \a AVSfield into \a out. This
                occurs, keeping \b fft in mind. For instance a cropped version will crop the
                outer extra data, inserting the center into \a out. Each dimension is handled
                independently, therefore allowing \e cropping in one dimension while
                \e zero-padding in another.

            \param in Any AVSfield

            \param out An AVSfield of the same type as \a in, yet each dimension may
                independently be resized to a smaller or larger size. The number of
                dimensions, \a ndim, and \a veclen must agree with \a in.

            \todo \b min_d: rather than traversing every dimension starting with the first dimensions,
                begin with the first dimension that is resized. This can result in rather
                large speed improvement, especially for fields that are not resized. Note
                that most of the lines of code that would be affected, have the
                comment \c //TODO:min_d trailing them.
            \todo make a better arbitrary option. The above macro gives a good example, though
                it currently doesn't work.

            NRZ: modified from Ken's insert_data()
        **/
        Array<T>& insert(Array<T> &in)
        {
            if (&in == this)
                PYFI_INT_ERROR("Array.insert(): the input cannot be the same as the output.");

            if (in.ndim() != _ndim)
                PYFI_INT_ERROR("Array.insert(): the input and output array dimensionality must be the same (i.e. ndim()).");

            // declare and allocate index array cur
            uint64_t *cur = NULL; // current index of the input field 'in'
            cur = (uint64_t *) malloc(in.ndim() * sizeof(uint64_t));
            assert(cur != NULL);

            // declare and allocate index array cur_out
            uint64_t *cur_out = NULL; // current index of the output field 'out'
            cur_out = (uint64_t *) malloc(in.ndim() * sizeof(uint64_t));
            assert(cur != NULL);

            // set the index arrays to initial values
            for (uint64_t i=0; i<in.ndim(); i++)
            {
                cur[i] = 0;
                cur_out[i] = 0;
                if (in.dimensions(i) > _dimensions[i])
                {
                    cur[i] = (in.dimensions(i) - _dimensions[i] + _dimensions[i] % 2) / 2;
                }
                else if (in.dimensions(i) < _dimensions[i])
                {
                    cur_out[i] = (_dimensions[i] - in.dimensions(i) + in.dimensions(i) % 2) / 2;
                }
            }

            // size is the size of the memcpy that will occur
            uint64_t size = std::min(in.dimensions(0), _dimensions[0]);  //TODO:min_d
            size *= sizeof(T);

            // if the fields are 1-D execute and return otherwise infinite while loop occurs below
            if (in.ndim() == 1)
            {
                // the debug will get rid of the arbitrary problem, however it must be still cast to something
                memcpy(_data+cur_out[0], in.data()+cur[0], size);

                free(cur);
                free(cur_out);
                cur = cur_out = NULL;
                return *this;
            }

            do
            {
                // do the actual insertion
                // the debug will get rid of the arbitrary problem, however it must be still cast to something
                memcpy(_data+this->index(cur_out), in.data()+in.index(cur), size);

                // increment index to next location
                cur[1]++; //TODO:min_d
                cur_out[1]++; //TODO:min_d

                // correct current in and out index (ie when index is out of bounds)
                // inifinte while loop occurs if ndim = 1 hence code above do loop
                uint64_t i = 1; //TODO:min_d
                while (i+1 < in.ndim() && (cur[i] >= in.dimensions(i) || cur_out[i] >= _dimensions[i]))
                {
                    cur[i] = cur_out[i] = 0;
                    if (in.dimensions(i) > _dimensions[i])
                    {
                        cur[i] = (in.dimensions(i) - _dimensions[i] + _dimensions[i] % 2) / 2; // replicated from above
                    }
                    else if (in.dimensions(i) < _dimensions[i])
                    {
                        cur_out[i] = (_dimensions[i] - in.dimensions(i) + in.dimensions(i) % 2) / 2; // replicated from above
                    }
                    cur[i+1]++;
                    cur_out[i+1]++;
                    i++;
                }

                // break the loop when necessary
                if (cur[in.ndim() -1] >= in.dimensions(in.ndim() -1) ||
                        cur_out[_ndim -1] >= _dimensions[_ndim -1])
                {
                    break; // or return
                }
            }
            while (1);

            // don't forget to free the index arrays
            free(cur);
            free(cur_out);
            cur = cur_out = NULL;

            return *this;
        }

        /* Make this array a new dimensionality that has the same total size
         * as the original.
         */
        void reshape(std::vector<uint64_t>& idims)
        {
            uint64_t isize = 1;
            for (uint64_t i=0; i<idims.size(); ++i)
                isize *= idims[i];

            if (isize == _size)
            {
                free(_dimensions);
                _dimensions = (uint64_t*)malloc(idims.size()*sizeof(uint64_t));
                for (uint64_t i=0; i<idims.size(); ++i)
                    _dimensions[i] = idims[i];
                _ndim = idims.size();
            }
            else
            {
                ArrayDimensions err(idims);
                PYFI_INT_ERROR("reshape() input dimensions ("<<err<<") dont have the same size as THIS array: "<< *this);
            }
        }


        /* Create a new resized array with the contents of THIS array centered.
         * -this is the master function
         */
        inline Array<T> get_resized(std::vector<uint64_t> idims)
        {
            if (idims.size() != _ndim)
                PYFI_INT_ERROR("Array.get_resized(): input ndims don't match Array.ndim(); makes no sense.");

            for (uint64_t i=0; i<_ndim; ++i)
                if (idims[i] <= 0)
                    PYFI_INT_ERROR("Array.get_resized(): dims["<<i<<"] is <= 0; makes no sense.");
                
            Array<T> out(idims);
            out.insert(*this);
            return out;
        }

        /* Create a new resized array with the contents of THIS array centered.
         * -uniform dim scaling
         */
        inline Array<T> get_resized(double scale)
        {
            /* multiply each dimension before storing it */
            std::vector<uint64_t> dims;
            for (uint64_t i=0; i<_ndim; ++i)
                dims.push_back(_dimensions[i]*scale);

            return this->get_resized(dims);
        }

        /* Create a new resized array with the contents of THIS array centered.
         * -non-uniform scale
         */
        inline Array<T> get_resized(double *scale)
        {
            /* copy to vector, multiply scale, assume _ndim size */
            std::vector<uint64_t> dims;
            for (uint64_t i=0; i<_ndim; ++i)
                dims.push_back(scale[i] * _dimensions[i]);

            return this->get_resized(dims);
        }

        /* Create a new resized array with the contents of THIS array centered.
         * -non-uniform scale
         */
        inline Array<T> get_resized(std::vector<double> scale)
        {
            /* copy to vector, multiply scale, assume _ndim size */
            std::vector<uint64_t> dims;
            for (uint64_t i=0; i<scale.size(); ++i)
                dims.push_back(scale[i] * _dimensions[i]);

            return this->get_resized(dims);
        }

        /* Create a new resized array with the contents of THIS array centered.
         */
        inline Array<T> get_resized(uint64_t *idims)
        {
            /* copy to vector, assume _ndim size */
            std::vector<uint64_t> dims;
            for (uint64_t i=0; i<_ndim; ++i)
                dims.push_back(idims[i]);

            return this->get_resized(dims);
        }

}; // Array class



/* cout */
template<class T>
ostream& operator<<(ostream& os, const Array<T>& out)
{
    uint64_t elem_limit = PYFI_PRINT_ELEMLIMIT;

    /* print array info */
    os << "Array<" << PyFI::Demangle(typeid(T).name()) << "> " << out.ndim() << "D (";
    for(uint64_t i=0; i<out.ndim(); ++i)
    {
        os << out.dimensions()[i];
        if (i < (out.ndim()-1))
            os << " x ";
    }
    os << ")" << endl;
    os << "\twrapper: " << out.isWrapper() << endl;


    /* print element values */
    if (out.size() > elem_limit)
    {
        os << "\tdata = \n\t\t";
        /* starting elems */
        for(uint64_t i=0; i<elem_limit/2; ++i)
        {
            os << "[" << i << "]:" << out.data()[i] << ", ";
        }

        os << ".....\n\t\t\t.....";

        /* ending elems */
        for(uint64_t i=out.size()-elem_limit/2; i<out.size(); ++i)
        {
            os << "[" << i << "]:" << out.data()[i];
            if (i < (out.size()-1))
                os << ", ";
        }

    }
    else
    {
        os << "\tdata = \n\t\t";
        /* print it all */
        for(uint64_t i=0; i<out.size(); ++i)
        {
            os << "[" << i << "]:" << out.data()[i];
            if (i < (out.size()-1))
                os << ", ";
        }
    }

    return os;
}

/* other primitive operator overloads for LHS */
template<class T>
Array<T> operator*(const T &lhs, Array<T> rhs) // mult constant
{
    Array<T> out(rhs);
    for (uint64_t i=0; i<out.size(); ++i)
        out(i) *= lhs;
    return out;
}

template<class T>
Array<T> operator/(const T &lhs, Array<T> rhs) // divide constant
{
    Array<T> out(rhs);
    for (uint64_t i=0; i<out.size(); ++i)
    {
        #ifdef PYFI_ARRAY_DEBUG
        if (out(i) == 0)
        {
            PYFI_INT_ERROR("Array operator \'/\' divide by zero, \n\n\tLHS:("<<lhs<<"), \n\n\tRHS:("<<rhs<<")");                       
        }
        #endif

        out(i) = lhs/out(i);
    }
    return out;
}

template<class T>
Array<T> operator-(const T &lhs, Array<T> rhs) // subtract constant
{
    Array<T> out(rhs);
    for (uint64_t i=0; i<out.size(); ++i)
        out(i) -= lhs;
    return out;
}

template<class T>
Array<T> operator+(const T &lhs, Array<T> rhs) // subtract constant
{
    Array<T> out(rhs);
    for (uint64_t i=0; i<out.size(); ++i)
        out(i) += lhs;
    return out;
}


/* array masks via inequalities w/ constants */
template<class T>
Array<bool> operator==(const T &lhs, Array<T> rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs == rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator!=(const T &lhs, Array<T> rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs != rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator<=(const T &lhs, Array<T> rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs <= rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator>=(const T &lhs, Array<T> rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs >= rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator<(const T &lhs, Array<T> rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs < rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator>(const T &lhs, Array<T> rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs > rhs.data()[i]);
    return out;
}


}// namespace

#endif // GUARD
