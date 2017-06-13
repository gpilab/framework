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
    \brief A template module for the most common use case.
 **/

#include "PyFI/PyFI.h" /* PyFI interface, must be the first include */
using namespace PyFI; /* for PyFI::Array */

PYFI_FUNC(myfunc)
{
    PYFI_START(); /* This must be the first line */

    /***** ARGS */   
    PYFI_POSARG(double, myfloat);
    PYFI_POSARG(Array<complex<float> >, mycfarr);

    /***** PRE-ALLOCATE OUTPUT */   

    /* SHORTHAND DIMS */
    PYFI_SETOUTPUT_ALLOC(Array<double>, arrpreout1, ArrayDimensions(2,2,2));
    coutv(ArrayDimensions(2,2,2).dimensions_vector());

    /* ARRAY TO DIMS */
    Array<uint64_t> odims(3);
    odims = 2;
    PYFI_SETOUTPUT_ALLOC(Array<double>, arrpreout2, DA(odims));
    coutv(DA(odims).dimensions_vector());
 
    /* COPY DIMS */
    PYFI_SETOUTPUT_ALLOC(Array<double>, arrpreout3, mycfarr->dimensions_vector());
    coutv(mycfarr->dimensions_vector());

    /* MODIFY DIMS */
    std::vector<uint64_t> mdims = mycfarr->dimensions_vector(); // get existing list
    mdims.push_back( 2 ); // add to list
    coutv(mdims);
    mdims.push_back( mycfarr->dimensions(1) ); // add to list
    coutv(mdims);
    mdims.pop_back(); // delete last elem
    coutv(mdims);
    PYFI_SETOUTPUT_ALLOC(Array<double>, arrpreout4, mdims);

    /***** PERFORM */

    /* convenience functions */
    deb; /* just print out the line number for debugging */
    coutv(*mycfarr); /* stringify the name, value, and line number of the variable */
   
    PYFI_END(); /* This must be the last line */
}
/* ##############################################################
 *                  MODULE DESCRIPTION
 * ############################################################## */


/* list of functions to be accessible from python */
PYFI_LIST_START_
    PYFI_DESC(myfunc, "your ad here")
PYFI_LIST_END_
