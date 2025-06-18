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

#ifndef _BASICARRAYIF_CPP_GUARD
#define _BASICARRAYIF_CPP_GUARD

#include <iostream>
#include <map>
#include <typeinfo>
#include <complex>
#include <vector>
#include <type_traits>
using namespace std;


#include <stdio.h>
#include <stdlib.h>
#define _USE_MATH_DEFINES // Windows needs this to get M_PI and other constants
#include <math.h> /* fabs */

#include "PyFI/PyFIMacros.h"

#if defined (__linux__) || defined (__APPLE__)
    #include <execinfo.h>
    #include "PyFI/backtrace.cpp"
#endif

/* allow the user to change this */
#ifndef PYFI_PRINT_ELEMLIMIT
#define PYFI_PRINT_ELEMLIMIT 20
#endif

namespace PyFI
{

/* indexing macros 
 * -in debug mode they will include the file:line operator
 * -in normal mode they will just use the direct indexing operator (faster)
 */
/**
 * \def get1(_arr, _i)
 * A macro that wraps the normal Array indexing methods and provides debugging information such as filename and line number if indexing bounds exceed the limits.
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

/**
 * Simplifies an Array constructor from another defined by another Array.
 */
#define DA(_arr) ArrayDimensions((_arr).size(), (_arr).as_ULONG().data())


/*****************************************************************************/

/**
 * An object that holds Array dimensionality information for constructing Array
 * instances or converting this information between objects such as C-arrays or
 * standard vectors.
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

        /**
         * \return The number of Array dimensions (i.e. rank).
         */
        const uint64_t ndim() const
        {
            return this->_ndim;
        }

        /**
         * \return A pointer to the first element in the dimensions array.
         */
        const uint64_t *dimensions() const
        {
            return this->_dimensions;
        }

        /**
         * \return A standard vector loaded with the elements of the
         * dimensions() array.
         */
        std::vector<uint64_t> dimensions_vector()
        {
            std::vector<uint64_t> out;
            for(uint64_t i=0; i<_ndim; ++i)
                out.push_back(_dimensions[i]);
            return out;
        }

        /**
         * \param i Dimension index.
         * \return The length of the dimension at index \a i.
         */
        const uint64_t dimensions(uint64_t i) const
        {
            if (i < _ndim)
                return this->_dimensions[i];

            PYFI_INT_ERROR("ArrayDimensions.dimensions(): ndim is out of range: input("<<i<<"), max("<<_ndim-1<<")\n\toffending array: ");
        }

        /**
         * Construct an ArrayDimensions object from a standard vector.
         *
         * \param dims A standard vector.
         */
        ArrayDimensions(const std::vector<uint64_t> &dims)
        {
            array_from_dims(dims.size(), dims.data());
        }

        /**
         * Construct an ArrayDimensions object from a C-array.
         *
         * An Array can also be used to construct an ArrayDimensions object
         * via the `DA()` macro, which uses this constructor interface.
         *
         * \code
         * Array<uint64_t> arr(3); // a 1D array
         * arr(0) = 10;
         * arr(1) = 10;
         * arr(2) = 2;
         * DA(arr); // an ArrayDimensions object with dimensions (10,10,2)
         *          // taken from the elements of the Array.
         * \endcode
         *
         * \param ndim The number of dimensions (i.e. rank).
         * \param dimensions A pointer to a C-array containing the dimension
         * lengths.
         */
        ArrayDimensions(uint64_t ndim, uint64_t *dimensions)
        {
            array_from_dims(ndim, dimensions); 
        }

        /**
         * Construct a new ArrayDimensions instance by dimension length (column
         * major ordering).
         *
         * \code
         * ArrayDimensions aDims(10); // dims for a 1D array
         * ArrayDimensions myDims(10,10,2); // dims for a 3D array with the
         *                                  // fastest varying dimension of
         *                                  // length 2.
         * \endcode
         *
         * \param i...n lengths for each dimension.
         */
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

        /**
         * The ArrayDimensions destructor. This frees the contained C-array.
         */
        ~ArrayDimensions()
        {
            free(_dimensions);
        }

        /* -------------------------------------------- overloaded operators */

        /**
         * The equality operator.
         *
         * \return true if the two ArrayDimensions are the same.
         */
        inline bool operator==(const ArrayDimensions &rhs) const // check for equality
        {
            if (this->ndim() != rhs.ndim())
                return false;

            for (uint64_t i=0; i<_ndim; ++i)
                if (this->dimensions(i) != rhs.dimensions(i))
                    return false;
                
            return true;
        }

        /**
         * The equality operator.
         *
         * \return false if the two ArrayDimensions are the same.
         */
        inline bool operator!=(const ArrayDimensions &rhs) const // check for inequality
        {
            return ! (*this == rhs);
        }

}; // ArrayDimensions Class

/*****************************************************************************/

/* cout */
ostream& operator<<(ostream &os, const ArrayDimensions &out)
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

/* 
 * The ALL constant and Slice struct provide Python-like slicing capabilities.
 * ALL is used as a sentinel value to indicate a full slice (i.e., ":").
 * The Slice struct allows specifying start, stop, and step for slicing arrays.
 */
const int ALL = -1;
struct Slice {
    int start;
    int stop;
    int step;

    Slice(int start_, int stop_, int step_ = 1)
        : start(start_), stop(stop_), step(step_) {}

    // full slice shorthand
    Slice() : start(ALL), stop(ALL), step(1) {}
};

/*****************************************************************************/

/**
 * A simple n-D array class that is portable.
 *
 * This array class holds a simple C-array segment with some additional
 * dimension and type information that allows it to be converted to or from
 * a Numpy (NPY) array.  New instances can wrap existing C-array segments or
 * can allocate new memory either from C (via calloc()) or from the Python
 * interpreter (via PyFI::SET_OUTPUT_ALLOC()).
 *
 * The Array class also contains member functions for simplifying indexing,
 * debugging, math operators and other common operations used in signal
 * processing.
 *
 * \todo make it nD, current max is 10.
 * \todo current max indexing is 8
 */
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

        /** 
         * Construct an Array from a standard vector object.
         *
         * \param dims A vector holding the dimension lengths.
         */
        Array(const std::vector<uint64_t> &dims)
        {
            array_from_dims(dims.size(), dims.data());
        }

        /** 
         * Construct an Array from an ArrayDimensions object.
         *
         * \param dmo An ArrayDimensions object holding the dimension lengths.
         */
        Array(const ArrayDimensions &dmo)
        {
            array_from_dims(dmo.ndim(), dmo.dimensions());
        }

        /** 
         * Construct an Array from a C-array.
         *
         * \param ndim The number of dimensions (rank).
         * \param dimensions A pointer to a C-array that holds the lengths of
         *        each dimension.
         */
        Array(uint64_t ndim, uint64_t *dimensions)
        {
            array_from_dims(ndim, dimensions);
        }

        /** 
         * Construct an existing memory segment (i.e. pre-allocated C-array).
         *
         * \param ndim The number of dimensions (rank).
         * \param dimensions A pointer to a C-array that holds the lengths of
         *        each dimension.
         * \param seg_ptr A pointer to the first element of a C-array of the
         *        same \e type as \e this Array.
         */
        Array(uint64_t ndim, uint64_t *dimensions, T *seg_ptr)
        {
            array_from_segment(ndim, dimensions, seg_ptr);
        }

        /**
         * The copy constructor.
         *
         * Construct a copy of another Array instance.
         *
         * \param arr An Array to copy.
         */
        Array(const Array<T> &arr)
        {
            array_from_dims(arr.ndim(), arr.dimensions());
            memcpy(_data, arr.data(), arr.size()*sizeof(T));
        }

        /**
         * Construct and copy the first few dimensions of an Array.
         *
         * \param ndim The number of dimensions to copy starting from the n-th
         *      dimension of \a arr.dimensions().
         * \param arr An Array to copy.
         */
        Array(const uint64_t ndim, const Array<uint64_t> &arr)
        {
            if (ndim > arr.size())
                PYFI_INT_ERROR("Array constructor from dims array: ndim is out of range, input("<<ndim<<"), max("<<arr.size()<<")");

            array_from_dims(ndim, arr.data());
        }

        /**
         * Construct a new Array instance by dimension length (column major
         * ordering).
         *
         * \code
         * Array<float> myArray(10); // a 1D array
         * Array<float> myArray3(10,10,2); // a 3D array with the fastest
         *                                 // varying dimension of length 2.
         * \endcode
         *
         * \param i...n lengths for each dimension.
         */
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

        /**
         * The Array destructor frees all data()-segment and dimensions() array
         * memory.  If the array is wrapping an external segment (i.e.
         * isWrapper()) then only the dimensions() array is free'd.
         */
        ~Array()
        {
            free(_dimensions);
            if (!_wrapper) free(_data);
        }

        /**
         * \return The number of dimensions (or rank) of this Array.
         */
        inline const uint64_t ndim() const
        {
            return this->_ndim;
        }

        /**
         * \return A pointer to the first element of the dimensions() array,
         * which is a standard C-array. 
         */
        inline const uint64_t *dimensions() const
        {
            return this->_dimensions;
        }

        /**
         * \return A standard template library vector object that represents
         * the size and dimensionality of this Array instance.
         */
        std::vector<uint64_t> dimensions_vector()
        {
            std::vector<uint64_t> out;
            for(uint64_t i=0; i<_ndim; ++i)
                out.push_back(_dimensions[i]);
            return out;
        }

        /**
         * \return The length of a specific dimension (indexed by `i`) of this
         * Array.
         */
        inline const uint64_t dimensions(uint64_t i) const
        {
            if (i < _ndim)
                return this->_dimensions[i];

            PYFI_INT_ERROR("Array.dimensions(): ndim is out of range: input("<<i<<"), max("<<_ndim-1<<")\n\toffending array: "<<*this);
        }

        /**
         * \return The length of a specific dimension (indexed by `i`) of this
         * Array.
         */
        inline const uint64_t size(uint64_t i) const
        {
            return dimensions(i);
        }

        /**
         * \return An ArrayDimensions object that represents the size and
         * dimensionality of this Array instance.
         */
        inline ArrayDimensions dims_object()
        {
            ArrayDimensions out(_ndim, _dimensions);
            return out;
        }

        /**
         * \return The total number of elements in this array (if its
         * multi-dimensional then its the number of elements as if it were 1D).
         */
        inline const uint64_t size() const
        {
            return this->_size;
        }

        /**
         * \return A pointer to the first element of the internal C-array
         * segment.
         */
        inline T *data() const
        {
            return this->_data;
        }

        /**
         * \return Whether or not this Array instance is wrapping a data
         * segment that is owned by another piece of code (e.g. Python/Numpy or
         * another Array).
         */
        const bool isWrapper() const
        {
            return this->_wrapper;
        }

        /* indexing w/ file:line DEBUGGING */
        inline T& operator()(uint64_t i, string fn, uint64_t ln)
        {
            uint64_t ind[1];
            ind[0] = i;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(1, ind, fn, ln);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, string fn, uint64_t ln)
        {
            uint64_t ind[2];
            ind[0] = i;
            ind[1] = j;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(2, ind, fn, ln);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, string fn, uint64_t ln)
        {
            uint64_t ind[3];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(3, ind, fn, ln);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, string fn, uint64_t ln)
        {
            uint64_t ind[4];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(4, ind, fn, ln);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, string fn, uint64_t ln)
        {
            uint64_t ind[5];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(5, ind, fn, ln);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, string fn, uint64_t ln)
        {
            uint64_t ind[6];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(6, ind, fn, ln);
            #endif
            return _data[this->index(ind)];
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


        /** 
         * Index the array as if it were a 2D array where `i` indexes all
         * dimensions up to n-1 as if they were concatenated into one dimension
         * and `v` indexes the remaining n-th dimension.
         *
         * \param i One dimensional indexing.
         * \param v Index of the last dimension.
         *
         * \return The data() value at the given index.
         */
        inline T& get1v(uint64_t i, uint64_t v)
        {
            // Declare ind with the actual number of dimensions of the array.
            // This ensures ind[2] (and higher) exists when _ndim > 2.
            // Initialize all elements to 0 to prevent garbage values in unused dimensions.
            uint64_t ind[_ndim]; // Declare ind dynamically based on actual _ndim
            for(uint64_t d = 0; d < _ndim; ++d) {
                ind[d] = 0; // Initialize all indices to 0 by default
            }

            // Map the input arguments 'v' and 'i' to the appropriate dimensions
            // based on the observation that get1v(i, v) corresponds to operator()(v, i)
            // where v is for dim 0, i is for dim 1.
            if (_ndim >= 1) {
                ind[0] = v; // 0th dimension index
            } else {
                PYFI_INT_ERROR("get1v: Array has less than 1 dimension for index 'v'.");
            }
            if (_ndim >= 2) {
                ind[1] = i; // 1st dimension index
            } else {
                PYFI_INT_ERROR("get1v: Array has less than 2 dimensions for index 'i'.");
            }


            #ifdef PYFI_ARRAY_DEBUG
            // check_dim_range should verify against the actual _ndim dimensions being accessed
            // The check_dim_range expects the *array's actual ndim*, not just the count of arguments to get1v.
            check_dim_range(_ndim, ind, "???", 0); // Pass _ndim here
            #endif

            return _data[this->index(ind)]; // Use the updated index() method
        }

        /**
         * Index the array as if it were a 1D array.  If this is a
         * multidimensional array, `i` indexes all dimensions as if they were
         * concatenated into one dimension.  If multiple indices are used they
         * must match the number of dimensions (ndim()) of the Array.
         *
         * For example, an 3D array `arr` can be indexed as a 1D array:
         *
         * \code
         * Array<float> arr(10,10,10);
         * arr(0);
         * arr(999);
         * \endcode
         *
         * Or as a 3D array:
         *
         * \code
         * arr(2,3,4);
         * \endcode
         *
         * In order to use the full debugging features of the Array class the
         * indexing must be done with the 'get<ndim>' macros as shown below:
         *
         * \code
         * get1(arr, 0);
         * get1(arr, 999);
         * get3(arr, 2,3,4);
         * \endcode
         *
         * The 'get' macros automatically add the filename and line number for
         * each indexing call to an array. When compiled in debug mode, any 
         * array faults or exceptions will contain this information.
         *
         * \note The 1-6 dimensional indexing uses direct multiplication
         * operations to reference the index.  For 7 and up dimensions use
         * looped indexing functions which can be a little slower.
         *
         * \param i...n indexes for each dimension.
         *
         * \return The data() value at the given index.
         */
        inline T& operator()(uint64_t i)
        {
            uint64_t ind[1];
            ind[0] = i;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(1, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j)
        {
            uint64_t ind[2];
            ind[0] = i;
            ind[1] = j;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(2, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k)
        {
            uint64_t ind[3];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(3, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l)
        {
            uint64_t ind[4];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(4, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m)
        {
            uint64_t ind[5];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(5, ind, "???", 0);
            #endif

            return _data[this->index(ind)];
        }

        inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n)
        {
            uint64_t ind[6];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(6, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
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

        const inline T& operator()(uint64_t i) const 
        {
            uint64_t ind[1];
            ind[0] = i;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(1, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
        }

        const inline T& operator()(uint64_t i, uint64_t j) const 
        {
            uint64_t ind[2];
            ind[0] = i;
            ind[1] = j;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(2, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
        }

        const inline T& operator()(uint64_t i, uint64_t j, uint64_t k) const 
        {
            uint64_t ind[3];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(3, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
        }

        const inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l) const 
        {
            uint64_t ind[4];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(4, ind, "???", 0);
            #endif
            return _data[this->index(ind)];
        }

        const inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m) const  
        {
            uint64_t ind[5];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(5, ind, "???", 0);
            #endif

            return _data[this->index(ind)];
        }

        const inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n) const 
        {
            uint64_t ind[6];
            ind[0] = i;
            ind[1] = j;
            ind[2] = k;
            ind[3] = l;
            ind[4] = m;
            ind[5] = n;
            #ifdef PYFI_ARRAY_DEBUG
            check_dim_range(6, ind, "???", 0);
            #endif
            return ((_data) + (  ((_dimensions[0] * ((_dimensions[1] * ((_dimensions[2] * ((_dimensions[3] * (_dimensions[4] * (n) + (m))) + (l))) + (k))) + (j))) + (i))) )[0];
        }

        const inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o) const 
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

        const inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p) const 
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

        const inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q) const 
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

        const inline T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q, uint64_t r) const 
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

        /* ------------------ overloaded math operators, ARRAY MATH '=' based*/

        /**
         * Array assignment operator.
         *
         * This an be used to copy the elements of one array to another.
         *
         * \code
         * Array<float> arr1(10);
         * Array<float> arr2(10);
         *
         * arr1 = arr2;
         * \endcode
         *
         * \param arr Must be the same size() as \e this Array.
         *
         * \note This only copies elements because the segment being wrapped
         * might be owned by Python.
         */
        inline Array<T>& operator=(const Array<T> &arr) // copy array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] = arr.data()[i];
            return *this;
        }

        /**
         * Multiplication assignment operator.
         *
         * Does element-wise multiplication.
         *
         * \param arr Must be the same size() as \e this Array.
         */
        inline Array<T>& operator*=(Array<T> &arr) // multiply by array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'*=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] *= arr(i);
            return *this;
        }

        /**
         * Division assignment operator.
         *
         * Does element-wise division.
         *
         * \param arr Must be the same size() as \e this Array.
         *
         * \note debug mode will throw an exception for divide by zeros.
         */
        inline Array<T>& operator/=(Array<T> &arr) // divide by array
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

        /**
         * Subtraction assignment operator.
         *
         * Does element-wise subtraction.
         *
         * \param arr Must be the same size() as \e this Array.
         */
        inline Array<T>& operator-=(Array<T> &arr) // subtract array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'-=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] -= arr(i);
            return *this;
        }

        /**
         * Addition assignment operator.
         *
         * Does element-wise addition.
         *
         * \param arr Must be the same size() as \e this Array.
         */
        inline Array<T>& operator+=(const Array<T> &arr) // add array
        {
            #ifdef PYFI_ARRAY_DEBUG
            if (arr.size() != _size)
                PYFI_INT_ERROR("Array operator \'+=\' is used on different sized arrays, \n\n\tLHS:("<<*this<<"), \n\n\tRHS:("<<arr<<")");
            #endif

            for (uint64_t i=0; i<_size; ++i)
                _data[i] += arr(i);
            return *this;
        }

        /* --------------------------- overloaded math operators, ARRAY MATH */

        /**
         * Multiplication operator.
         *
         * \param arr Must be the same size() as \e this Array.
         * \return element-wise Array product.
         */
        inline Array<T> operator*(const Array<T> &arr) // mult array
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

        /**
         * Division operator.
         *
         * \param arr Must be the same size() as \e this Array.
         * \return element-wise Array division.
         * \note debug mode will throw an exception for divide by zeros.
         */
        inline Array<T> operator/(const Array<T> &arr) // divide array
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

        /**
         * Subtraction operator.
         *
         * \param arr Must be the same size() as \e this Array.
         * \return element-wise Array difference.
         */
        inline Array<T> operator-(const Array<T> &arr) // subtract array
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

        /**
         * Addition operator.
         *
         * \param arr Must be the same size() as \e this Array.
         * \return element-wise Array addition.
         */
        inline Array<T> operator+(const Array<T> &arr) // add array
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

        /* ----------------- overloaded math operators, CONST MATH '=' based */

        /**
         * Assignment operator.
         *
         * \param c a single value to set all elements.
         */
        inline Array<T>& operator=(const T &c) // assign constant
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] = c;
            return *this;
        }

        /** 
         * Sets all values to the constant and implicit casting of \a c.
         *
         * \param c A value.
         */
        inline void set(const T &c)
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] = c;
        }

        /**
         * Multiplication assignment operator.
         *
         * \param c a single value to multiply all elements.
         */
        inline Array<T>& operator*=(const T &c) // mult constant
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] *= c;
            return *this;
        }

        /**
         * Division assignment operator.
         *
         * \param c a single value to divide all elements.
         * \note debug mode will throw an exception for divide by zeros.
         */
        inline Array<T>& operator/=(const T &c) // divide constant
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

        /**
         * Subtraction assignment operator.
         *
         * \param c a single value to subtract from all elements.
         */
        inline Array<T>& operator-=(const T &c) // subtract constant
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] -= c;
            return *this;
        }

        /**
         * Addition assignment operator.
         *
         * \param c a single value to add to all elements.
         */
        inline Array<T>& operator+=(const T &c) // add constant
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] += c;
            return *this;
        }

        /* --------------------------- overloaded math operators, CONST MATH */

        inline Array<T> operator*(const T &c) // mult constant
        {
            Array<T> out(*this);
            for (uint64_t i=0; i<_size; ++i)
                out(i) *= c;
            return out;
        }

        inline Array<T> operator/(const T &c) // divide constant
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

        inline Array<T> operator-(const T &c) // subtract constant
        {
            Array<T> out(*this);
            for (uint64_t i=0; i<_size; ++i)
                out(i) -= c;
            return out;
        }

        inline Array<T> operator+(const T &c) // subtract constant
        {
            Array<T> out(*this);
            for (uint64_t i=0; i<_size; ++i)
                out(i) += c;
            return out;
        }

        /* ----------------------- array masks via inequalities w/ constants */

        /**
         * Boolean equivalence operator.
         *
         * \param c A single value to compare to all elements.
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator==(const T &c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] == c);
            return out;
        }

        /**
         * Boolean non-equivalence operator.
         *
         * \param c A single value to compare to all elements.
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator!=(const T &c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] != c);
            return out;
        }

        /**
         * Boolean less-than or equal-to operator.
         *
         * \param c A single value to compare to all elements.
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator<=(const T &c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] <= c);
            return out;
        }


        /**
         * Boolean greater-than or equal-to operator.
         *
         * \param c A single value to compare to all elements.
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator>=(T c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] >= c);
            return out;
        }

        /**
         * Boolean less-than operator.
         *
         * \param c A single value to compare to all elements.
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator<(const T &c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] < c);
            return out;
        }

        /**
         * Boolean greater-than operator.
         *
         * \param c A single value to compare to all elements.
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator>(const T &c)
        {
            Array<bool> out(this->dims_object());
            for (uint64_t i=0; i<_size; ++i)
                out(i) = (_data[i] > c);
            return out;
        }


        /* -------------------- array masks via inequalities w/ other arrays */

        /**
         * Boolean array equivalence operator.
         *
         * \param arr An Array to compare against (MUST be the same size() as
         * \e this Array).
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator==(const Array<T> &arr)
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

        /**
         * Boolean array non-equivalence operator.
         *
         * \param arr An Array to compare against (MUST be the same size() as
         * \e this Array).
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator!=(const Array<T> &arr)
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

        /**
         * Boolean array greater-than or equal-to operator.
         *
         * \param arr An Array to compare against (MUST be the same size() as
         * \e this Array).
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator>=(const Array<T> &arr)
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

        /**
         * Boolean array less-than or equal-to operator.
         *
         * \param arr An Array to compare against (MUST be the same size() as
         * \e this Array).
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator<=(const Array<T> &arr)
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

        /**
         * Boolean array less-than operator.
         *
         * \param arr An Array to compare against (MUST be the same size() as
         * \e this Array).
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator<(const Array<T> &arr)
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

        /**
         * Boolean array greater-than operator.
         *
         * \param arr An Array to compare against (MUST be the same size() as
         * \e this Array).
         * \return A boolean mask (Array) of the element-wise comparison.
         */
        inline Array<bool> operator>(const Array<T> &arr)
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


        /* ----------------------------------- other math and stat functions */

        /**
         * Array Sum
         *
         * \return The sum of all elements.
         */
        inline T sum() // sum all elems
        {
            T out = 0;
            for (uint64_t i=0; i<_size; ++i)
                out += _data[i];
            return out;
        }

        /**
         * Array Product
         *
         * \return The product of all elements.
         */
        inline T prod() // product of all elems
        {
            T out = 1;
            for (uint64_t i=0; i<_size; ++i)
                out *= _data[i];
            return out;
        }

        /**
         * Array Min
         *
         * \return The Array min value.
         */
        inline T min() // min of all elems
        {
            T out = _data[0];
            for (uint64_t i=1; i<_size; ++i)
                out = std::min(out, _data[i]);
            return out;
        }

        /**
         * Array Max
         *
         * \return The Array max value.
         */
        inline T max() // max of all elems
        {
            T out = _data[0];
            for (uint64_t i=1; i<_size; ++i)
                out = std::max(out, _data[i]);
            return out;
        }

        /**
         * Array Max Magnitude
         *
         * \return The Array max magnitude value (handy for complex Array
         * types).
         */
        inline double max_mag() // max of all elems
        {
            double out = fabs(_data[0]);
            for (uint64_t i=1; i<_size; ++i)
                out = std::max(out, fabs(_data[i]));
            return out;
        }

        /**
         * Sets each element of \e this Array to the absolute value of the
         * element.
         */
        void abs()
        {
            for (uint64_t i=0; i<_size; ++i)
                _data[i] = T(fabs(_data[i]));
        }

        /**
         * Checks for Inf values.
         *
         * \return true if at least one element value is inf.
         */
        bool any_infs()
        {
            for (uint64_t i=0; i<_size; ++i)
                if ( isinf(fabs(_data[i])) )
                    return true;
            return false;
        }

        /**
         * Checks for NaN values.
         *
         * \return true if at least one element value is NaN.
         */
        bool any_nans()
        {
            for (uint64_t i=0; i<_size; ++i)
                if ( isnan(fabs(_data[i])) )
                    return true;
            return false;
        }

        /** 
         * Threshold the data, set all data less than \a thresh equal to \a
         * thresh.
         *
         * \param thresh The threshold value.
         */
        void clamp_min( T thresh )
        {
            for (uint64_t i=0; i<_size; ++i)
                if (_data[i] < thresh)
                    _data[i] = thresh;
        }

        /** 
         * Threshold the data, set all data greater than \a thresh equal to \a
         * thresh.
         *
         * \param thresh The threshold value.
         */
        void clamp_max( T thresh )
        {
            for (uint64_t i=0; i<_size; ++i)
                if (_data[i] > thresh)
                    _data[i] = thresh;
        }

        /** 
         * See if there are any elements with this value. 
         *
         * \param val The value to search for.
         * \return true if the value is present in the Array.
         */
        bool any( T val )
        {
            for (uint64_t i=0; i<_size; ++i)
                if (_data[i] == val)
                    return true;
            return false;
        }

        /**
         * The average of all the elements.
         *
         * \return The average value.
         */
        inline T mean() // average of all elems
        {
            T out = this->sum()/(T)_size;
            return out;
        }

        /**
         * The standard deviation of all elements.
         *
         * \return The standard deviation.
         */
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

        /* ---------------------------------------------------------- recast */

        /**
         * Recast Array as uint64_t.
         *
         * \return Array<uint64_t> with recast elements from \e this Array.
         */
        inline Array<uint64_t> as_ULONG()
        {
            Array<uint64_t> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        /**
         * Recast Array as float.
         *
         * \return Array<float> with recast elements from \e this Array.
         */
        inline Array<float> as_FLOAT()
        {
            Array<float> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        /**
         * Recast Array as complex<float>.
         *
         * \return Array<complex<float> > with recast elements from \e this Array.
         */
        inline Array<complex<float> > as_CFLOAT()
        {
            Array<complex<float> > out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        /**
         * Recast Array as complex<double>.
         *
         * \return Array<complex<double> > with recast elements from \e this Array.
         */
        inline Array<double> as_DOUBLE()
        {
            Array<double> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        /**
         * Recast Array as complex<double>.
         *
         * \return Array<complex<double> > with recast elements from \e this Array.
         */
        inline Array<complex<double> > as_CDOUBLE()
        {
            Array<complex<double> > out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        /**
         * Recast Array as int64_t.
         *
         * \return Array<int64_t> with recast elements from \e this Array.
         */
        inline Array<int64_t> as_LONG()
        {
            Array<int64_t> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        /**
         * Recast Array as int32_t.
         *
         * \return Array<int32_t> with recast elements from \e this Array.
         */
        inline Array<int32_t> as_INT()
        {
            Array<int32_t> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        /**
         * Recast Array as int8_t.
         *
         * \return Array<int8_t> with recast elements from \e this Array.
         */
        inline Array<uint8_t> as_UCHAR()
        {
            Array<uint8_t> out(_ndim, _dimensions);
            for (uint64_t i=0; i<_size; ++i)
                out(i) = _data[i];
            return out;
        }

        Array<T> slice(const std::vector<Slice>& slices) const {
            if (slices.size() != _ndim) {
                PYFI_INT_ERROR("slice() arguments must match array dimensions. Expected " << _ndim << ", got " << slices.size());
            }

            std::vector<uint64_t> new_dims(_ndim);
            std::vector<uint64_t> new_strides(_ndim);
            uint64_t calculated_offset_increase = 0; // Accumulates the offset change from the original array's base address

            for (size_t d = 0; d < _ndim; ++d) {
                const Slice& s = slices[d];
                uint64_t current_dim_len = _dimensions[d];

                long long start = (s.start == PyFI::ALL) ? 0 : s.start;
                long long stop = (s.stop == PyFI::ALL) ? current_dim_len : s.stop;
                long long step = s.step;

                // Handle negative indices (NumPy style)
                if (start < 0) start += current_dim_len;
                if (stop < 0) stop += current_dim_len;

                // Clamp start and stop to valid range
                start = std::max(0LL, std::min(start, (long long)current_dim_len));
                stop = std::max(0LL, std::min(stop, (long long)current_dim_len));

                if (step == 0) {
                    PYFI_INT_ERROR("Slice step cannot be zero.");
                }

                // Calculate the effective length of the new dimension
                long long effective_length = 0;
                if (step > 0) {
                    if (stop > start) {
                        effective_length = (stop - start + step - 1) / step;
                    }
                } else { // Negative step
                    if (stop < start) {
                        effective_length = (start - stop + (-step) - 1) / (-step);
                    }
                }

                new_dims[d] = static_cast<uint64_t>(effective_length);
                new_strides[d] = _strides[d] * std::abs(step); // Adjust stride for the new step
                calculated_offset_increase += start * _strides[d]; // Accumulate offset based on start index
            }

            // Create the new Array object as a view
            Array<T> sliced_array;
            sliced_array._ndim = _ndim; // Same number of dimensions
            sliced_array._dimensions = (uint64_t*)malloc(_ndim * sizeof(uint64_t)); // Allocate and copy new dimensions
            memcpy(sliced_array._dimensions, new_dims.data(), _ndim * sizeof(uint64_t));

            sliced_array._size = 1; // Calculate total size of the new view
            for(uint64_t dim_val : new_dims) {
                sliced_array._size *= dim_val;
            }

            sliced_array._data = _data; // Share the data pointer
            sliced_array._wrapper = true; // Mark as a wrapper/view (does not own data)
            sliced_array._strides = new_strides; // Copy the calculated strides
            sliced_array._offset = _offset + calculated_offset_increase; // Set the new offset

            return sliced_array;
        }

        // New slice_copy method (returns a deep copy)
        Array<T> slice_copy(const std::vector<Slice>& slices) const {
            if (slices.size() != _ndim) {
                PYFI_INT_ERROR("slice_copy() arguments must match array dimensions. Expected " << _ndim << ", got " << slices.size());
            }

            std::vector<uint64_t> new_dims(_ndim);
            std::vector<long long> actual_starts(_ndim);
            std::vector<long long> actual_steps(_ndim);

            for (size_t d = 0; d < _ndim; ++d) {
                const Slice& s = slices[d];
                uint64_t current_dim_len = _dimensions[d];

                long long start = (s.start == PyFI::ALL) ? 0 : s.start;
                long long stop = (s.stop == PyFI::ALL) ? current_dim_len : s.stop;
                long long step = s.step;

                // Handle negative indices (NumPy style)
                if (start < 0) start += current_dim_len;
                if (stop < 0) stop += current_dim_len;

                // Clamp start and stop to valid range
                start = std::max(0LL, std::min(start, (long long)current_dim_len));
                stop = std::max(0LL, std::min(stop, (long long)current_dim_len));

                if (step == 0) {
                    PYFI_INT_ERROR("Slice step cannot be zero.");
                }

                long long effective_length = 0;
                if (step > 0) {
                    if (stop > start) {
                        effective_length = (stop - start + step - 1) / step;
                    }
                } else { // Negative step
                    if (stop < start) {
                        effective_length = (start - stop + (-step) - 1) / (-step);
                    }
                }

                new_dims[d] = static_cast<uint64_t>(effective_length);
                actual_starts[d] = start;
                actual_steps[d] = step;
            }

            // Create the new Array to hold the deep-copied data
            Array<T> copied_array(new_dims); // This constructor will allocate new memory and set _wrapper=false

            // Copy data based on slices (N-dimensional iteration)
            std::vector<uint64_t> current_new_indices(_ndim, 0); // Indices for the new array
            std::vector<uint64_t> current_orig_indices(_ndim); // Corresponding indices in the original array

            // Iterate through the linear indices of the *new* array
            for (uint64_t flat_new_idx = 0; flat_new_idx < copied_array.size(); ++flat_new_idx) {
                // Convert flat_new_idx to current_new_indices (multi-dim index for the new array)
                uint64_t temp_idx = flat_new_idx;
                for (int d = _ndim - 1; d >= 0; --d) { // Assuming column-major for new_dims iteration
                    if (new_dims[d] == 0) { // Handle empty dimensions
                        current_new_indices[d] = 0;
                    } else {
                        current_new_indices[d] = temp_idx % new_dims[d];
                        temp_idx /= new_dims[d];
                    }
                }

                // Map current_new_indices to current_orig_indices using actual_starts and actual_steps
                for (size_t d = 0; d < _ndim; ++d) {
                    current_orig_indices[d] = actual_starts[d] + current_new_indices[d] * actual_steps[d];
                }

                // Calculate the linear index in the original array for the value to copy
                // Use the original array's index method, which correctly uses its _strides and _offset
                uint64_t orig_linear_index = this->index(current_orig_indices.data());

                // Copy the value
                copied_array._data[flat_new_idx] = _data[orig_linear_index];
            }

            return copied_array;
        }


    private:

        uint64_t _ndim;
        uint64_t *_dimensions;
        uint64_t _size;
        bool _wrapper;
        T *_data;
        // NEW MEMBERS for slicing
        std::vector<uint64_t> _strides; // Stores the stride for each dimension
        uint64_t _offset; // Stores the offset into the raw _data array for the current view
        bool _owning; // Indicates if this Array instance owns the _data memory (true for original arrays, false for views)

        /* get the ND index */
        /* get the ND index */
        // In Array::index(uint64_t *ind) const
        inline uint64_t index(uint64_t *ind) const
        {
            uint64_t linear_index = _offset;

            for (uint64_t i = 0; i < _ndim; ++i) {

                // This is the line triggering the error
                if (ind[i] >= _dimensions[i] && _dimensions[i] != 0) {
                    PYFI_INT_ERROR("Index " << ind[i] << " out of bounds for dimension " << i << " (size " << _dimensions[i] << ") in index calculation.");
                }
                linear_index += ind[i] * _strides[i];
            }
            return linear_index;
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
            _size = 1; //
            _strides.resize(ndim); // Initialize strides vector
            uint64_t current_stride = 1; //
            for (uint64_t i = 0; i < ndim; ++i) { //
                _size *= dimensions[i]; //
                _strides[i] = current_stride; // Assuming column-major (Fortran-like) order
                current_stride *= dimensions[i]; //
            }

            /* allocate memory segment, use calloc to set all elem to zero */
            _wrapper = false; //
            _data = (T *)calloc(_size, sizeof(T)); //
            _offset = 0; // Initial offset is 0 for newly allocated arrays
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
            _strides.resize(ndim);
            uint64_t current_stride = 1;
            for (uint64_t i = 0; i < ndim; ++i) {
                _size *= dimensions[i];
                _strides[i] = current_stride;
                current_stride *= dimensions[i];
            }

            /* copy memory segment pointer */
            _wrapper = true;
            _data = seg_ptr;
            _offset = 0; // Initial offset is 0 for wrapped segments (unless specified differently)
        }
        /* check if the Array is empty */

    public:

        /**
         *  Inserts the data from \a in into \e this Array in a centered way by
         *  \e cropping or \e zero-padding
         *
         *  This will insert a \e zero-padded or \e cropped Array into \e
         *  this. This occurs, keeping \b fft in mind. For instance a cropped
         *  version will crop the outer extra data, inserting the center into
         *  \e this. Each dimension is handled independently, therefore allowing
         *  \e cropping in one dimension while \e zero-padding in another.
         *
         *  \param in any Array of the same type as \e this Array.
         *
         *  \return A reference to \e this Array of the same type as \a in, yet
         *  each dimension may independently be resized to a smaller or larger
         *  size. The number of dimensions, ndim(), must match with \a in.
         *
         *  \todo \b min_d: rather than traversing every dimension starting
         *  with the first dimensions, begin with the first dimension that is
         *  resized. This can result in rather large speed improvement,
         *  especially for fields that are not resized. Note that most of the
         *  lines of code that would be affected, have the comment \c min_d
         *  trailing them. 
         *
         *  \todo make a better arbitrary option. The above macro gives a good
         *  example, though it currently doesn't work.
         */
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

        /**
         * Make this array a new dimensionality that has the same total size
         * as the original (i.e. modify the dimensions()).
         *
         * \param idims A standard vector containing the new dimensions (the
         *              dimension size() must match).
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


        /** 
         * Create a new resized array with the contents of THIS array centered.
         *
         * \param idims A standard vector with number of dimensions (ndim()
         * equal to \e this.ndim()).
         *
         * \return A new Array.
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

        /** 
         * Create a new resized array with the contents of THIS array centered.
         *
         * \param scale The factor applied to each of the dimension lengths of
         * \e this array.
         *
         * \return A new Array.
         */
        inline Array<T> get_resized(double scale)
        {
            /* multiply each dimension before storing it */
            std::vector<uint64_t> dims;
            for (uint64_t i=0; i<_ndim; ++i)
                dims.push_back(_dimensions[i]*scale);

            return this->get_resized(dims);
        }

        /** 
         * Create a new resized array with the contents of THIS array centered.
         *
         * \param scale A C-array containing the scale factors applied to each
         * of the dimension lengths of \e this.dimensions() array.
         *
         * \return A new Array.
         */
        inline Array<T> get_resized(double *scale)
        {
            /* copy to vector, multiply scale, assume _ndim size */
            std::vector<uint64_t> dims;
            for (uint64_t i=0; i<_ndim; ++i)
                dims.push_back(scale[i] * _dimensions[i]);

            return this->get_resized(dims);
        }

        /** 
         * Create a new resized array with the contents of THIS array centered.
         *
         * \param scale A standard vector containing the scale factors applied
         * to each of the dimension lengths of \e this.dimensions() array.
         *
         * \return A new Array.
         */
        inline Array<T> get_resized(std::vector<double> scale)
        {
            /* copy to vector, multiply scale, assume _ndim size */
            std::vector<uint64_t> dims;
            for (uint64_t i=0; i<scale.size(); ++i)
                dims.push_back(scale[i] * _dimensions[i]);

            return this->get_resized(dims);
        }

        /** 
         * Create a new resized array with the contents of THIS array centered.
         *
         * \param idims A C-array with length equal to \e this.ndim() which
         * contains the new dimensions of the output Array.
         *
         * \return A new Array.
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

/*****************************************************************************/

/* cout */
template<class T>
ostream& operator<<(ostream &os, const Array<T> &out)
{
    uint64_t elem_limit = PYFI_PRINT_ELEMLIMIT;

    /* print array info */
    // TODO: Demangle doesn't work/exist on Windows
    // os << "Array<" << PyFI::Demangle(typeid(T).name()) << "> " << out.ndim() << "D (";
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
Array<T> operator*(const T &lhs, Array<T> &rhs) // mult constant
{
    Array<T> out(rhs);
    for (uint64_t i=0; i<out.size(); ++i)
        out(i) *= lhs;
    return out;
}

template<class T>
Array<T> operator/(const T &lhs, Array<T> &rhs) // divide constant
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
Array<T> operator-(const T &lhs, Array<T> &rhs) // subtract constant
{
    Array<T> out(rhs);
    for (uint64_t i=0; i<out.size(); ++i)
        out(i) -= lhs;
    return out;
}

template<class T>
Array<T> operator+(const T &lhs, Array<T> &rhs) // subtract constant
{
    Array<T> out(rhs);
    for (uint64_t i=0; i<out.size(); ++i)
        out(i) += lhs;
    return out;
}


/* array masks via inequalities w/ constants */
template<class T>
Array<bool> operator==(const T &lhs, Array<T> &rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs == rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator!=(const T &lhs, Array<T> &rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs != rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator<=(const T &lhs, Array<T> &rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs <= rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator>=(const T &lhs, Array<T> &rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs >= rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator<(const T &lhs, Array<T> &rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs < rhs.data()[i]);
    return out;
}

template<class T>
Array<bool> operator>(const T &lhs, Array<T> &rhs)
{
    Array<bool> out(rhs.dims_object());
    for (uint64_t i=0; i<rhs.size(); ++i)
        out(i) = (lhs > rhs.data()[i]);
    return out;
}


}// namespace

#endif // GUARD
