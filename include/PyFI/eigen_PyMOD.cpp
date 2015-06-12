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
    \file EIGEN_PYMOD.CPP
    \author Ashley Anderson
    \date 2015mar11

    \brief Basic Python wrapping for Eigen PyFI functions. 

 **/

#include "PyFI/PyFI.h" /* PyFI interface, must be the first include */
using namespace PyFI; /* for PyFI::Array */
PYFI_FUNC(printmat)
{
    PYFI_START(); /* This must be the first line */

    /***** ARGS */   
    PYFI_POSARG(Array<double>, A);
    PyFEigen::PrintArrayAsEigenMat(*A);
    PYFI_END(); /* This must be the last line */
}

PYFI_FUNC(pinv)
{
    PYFI_START(); /* This must be the first line */

    /***** ARGS */   
    PYFI_POSARG(Array<double>, A);
    std::vector<uint64_t> dims = A->dimensions_vector();
    int m = dims[0];
    int n = dims[1];
    PYFI_SETOUTPUT_ALLOC(Array<double>, B, ArrayDimensions(n, m));
    PyFEigen::PseudoInverse(*A,*B);
   
    PYFI_END(); /* This must be the last line */
}

PYFI_FUNC(dot)
{
    PYFI_START(); /* This must be the first line */

    /***** POSITIONAL ARGS */   
    PYFI_POSARG(Array<double>, A); 
    std::vector<uint64_t> dims = A->dimensions_vector();
    int m = dims[1];
    // int n = dims[0];

    PYFI_POSARG(Array<double>, B); 
    dims = B->dimensions_vector();
    // int n_ = dims[1];
    int p = dims[0];

    // TODO: check here if n == n_

    PYFI_SETOUTPUT_ALLOC(Array<double>, C, ArrayDimensions(p,m));

    PyFEigen::MMult(*A, *B, *C);

    PYFI_END(); /* This must be the last line */
}

PYFI_FUNC(solve)
{
    PYFI_START(); /* This must be the first line */

    /***** POSITIONAL ARGS */   
    PYFI_POSARG(Array<double>, A); 
    std::vector<uint64_t> dims = A->dimensions_vector();
    // int m = dims[1];
    int n = dims[0];

    PYFI_POSARG(Array<double>, B); 
    dims = B->dimensions_vector();
    // int m_ = dims[1];
    int p = dims[0];

    // TODO: check here if m == m_

    PYFI_SETOUTPUT_ALLOC(Array<double>, X, ArrayDimensions(p,n));

    PyFEigen::MLDivide(*A, *B, *X);

    PYFI_END(); /* This must be the last line */
}
/* ##############################################################
 *                  MODULE DESCRIPTION
 * ############################################################## */


/* list of functions to be accessible from python */
PYFI_LIST_START_
    PYFI_DESC(printmat, "Convert to Eigen Mat and Print")
    PYFI_DESC(pinv, "PseudoInverse")
    PYFI_DESC(dot, "Matrix multiplication")
    PYFI_DESC(solve, "Least Squares Solver (SVD)")
PYFI_LIST_END_
