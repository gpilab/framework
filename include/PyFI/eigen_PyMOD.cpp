/**
    \file BASIC_PYMOD.CPP
    \author Nick Zwart
    \date 2014jul29

    \brief A template module for the most common use case.

 **/

#include "PyFI/PyFI.h" /* PyFI interface, must be the first include */
using namespace PyFI; /* for PyFI::Array */

PYFI_FUNC(pinv)
{
    PYFI_START(); /* This must be the first line */

    /***** ARGS */   
    PYFI_POSARG(Array<float>, A);
    PYFI_POSARG(Array<float>, B);
    EigenWrapper::PseudoInverse(*A,*B);
   
    PYFI_END(); /* This must be the last line */
}
/* ##############################################################
 *                  MODULE DESCRIPTION
 * ############################################################## */


/* list of functions to be accessible from python */
PYFI_LIST_START_
    PYFI_DESC(pinv, "PseudoInverse")
PYFI_LIST_END_
