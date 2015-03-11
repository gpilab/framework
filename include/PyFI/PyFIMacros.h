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


#ifndef _PYFIMACROS_CPP_GUARD
#define _PYFIMACROS_CPP_GUARD
/**
    \brief Macros that simplify extending python.
**/


/* function pointer helper
 */
template <class T>
inline T __PYFI_itself(T arg)
{
    return arg;
}

/* Types
 * -not yet used
 */
/*
#define PYFI_CHAR int8_t
#define PYFI_UCHAR uint8_t
#define PYFI_INT int32_t
#define PYFI_UINT uint32_t
#define PYFI_LONG int64_t
#define PYFI_ULONG uint64_t
#define PYFI_FLOAT float
#define PYFI_DOUBLE double
*/

/* Forced Retype
 *  -translate the usual types to supported types
 */
//#define long int64_t
//#define int  int32_t

/* ARGUMENT TYPES */
#define PYIF_EXCEPTION -1
#define PYIF_POSITIONAL_ARG 0
#define PYIF_KEYWORD_ARG 1

/* Simple macros for debugging. */
/* stdout color */
#define _PYFI_YEL     "\e[93m"
#define _PYFI_RED     "\e[31m"
#define _PYFI_NOC     "\e[39m"

#define coutv(var) cout << __FILE__ << ":" << __LINE__ << "\t"<< #var \
                        << " = " << var << "\n"
#define deb cout << "debug: " << __FILE__ << ":" << __LINE__ << "\n"
#define couterr(var) cout << "\n" << _PYFI_RED << __FILE__ << ":" << __LINE__ << " -- ERROR -- " << var << "\n" << _PYFI_NOC
#define _PYFI_flerr _PYFI_RED << __FILE__ << ":" << __LINE__ << " -- ERROR -- "

/* Shortcuts
 */
#define PYFI_FUNC(_nam) static PyObject *_nam (PyObject *self, PyObject *_pyfi_args, PyObject *_pyfi_keywds)
#define PYFI_PARSEINPUT() PyFI::FuncIF __pyfi(_pyfi_args, _pyfi_keywds);
#define PYFI_POSARG(_typ, _arg) _typ *_arg=NULL; __pyfi.PosArg(&_arg);
#define PYFI_KWARG(_typ, _arg, _dval) _typ *_arg=NULL, _arg ## __default=_dval; __pyfi.KWArg(&_arg, #_arg, &_arg ## __default);
#define PYFI_ERROR(_str) __pyfi.Error(_str);
#define PYFI_INT_ERROR(_msgos) { ostringstream __os; __os << _PYFI_flerr << _msgos << _PYFI_NOC; PyErr_Format(PyExc_RuntimeError,"%s", __os.str().c_str()); throw PYIF_EXCEPTION; }
#define PYFI_SETOUTPUT_ALLOC_DIMS(_typ, _arg, _ndim, _dims) _typ *_arg=NULL; __pyfi.SetOutput(&_arg, _ndim, _dims);
#define PYFI_SETOUTPUT_ALLOC(_typ, _arg, _do) _typ *_arg=NULL; __pyfi.SetOutput(&_arg, _do);
#define PYFI_SETOUTPUT(_arg) __pyfi.SetOutput(_arg);
#define PYFI_OUTPUT() __pyfi.Output();

#define PYFI_TRY() try {
#define PYFI_CATCH() } catch (...) { return NULL; }

#define PYFI_ARRAY_DEBUG_WARNING cout << "PYFI_ARRAY_DEBUG is ON: " << __FILE__ << endl;

#ifdef PYFI_ARRAY_DEBUG
    #define PYFI_START() PYFI_TRY() PYFI_PARSEINPUT(); PYFI_ARRAY_DEBUG_WARNING
    #define PYFI_END() PYFI_ARRAY_DEBUG_WARNING; return PYFI_OUTPUT(); PYFI_CATCH() 
#else
    #define PYFI_START() PYFI_TRY() PYFI_PARSEINPUT()
    #define PYFI_END() return PYFI_OUTPUT(); PYFI_CATCH()
#endif

/* MethodDef Shortcuts
 */
#define PYFI_FUNCLIST static PyMethodDef Methods[]
#define PYFI_FUNCDESC(_nam, _desc) { #_nam, (PyCFunction) _nam, METH_VARARGS|METH_KEYWORDS, _desc }
#define PYFI_FUNCDESC_TEMPLATE(_nam, _tmpl, _desc) { #_nam "_" #_tmpl, (PyCFunction) __PYFI_itself(_nam <_tmpl>), METH_VARARGS|METH_KEYWORDS, _desc }
#define PYFI_FUNCDESC_TERM() {NULL, NULL, 0, NULL}

#define PYFI_METHOD_TABLE(_nam_str) static struct PyModuleDef __pyfimstruct = { PyModuleDef_HEAD_INIT, _nam_str, NULL, -1, Methods };

/* avoid this numpy macro return issue */
void *numpy_import_array(void)
{
    import_array();
    return NULL;
}

/* PyMODINIT_FUNC stringifications
 */
#define STR_MOD_NAME1(_x) #_x
#define STR_MOD_NAME(_x) STR_MOD_NAME1(_x)
#define MAKE_FN_NAME(_x) PyMODINIT_FUNC PyInit_ ## _x (void)
#define FUNCTION_NAME(_x) MAKE_FN_NAME(_x)
#define PYFI_MODINIT()      \
    FUNCTION_NAME(MOD_NAME) \
    {                       \
        PyObject *m;        \
        m = PyModule_Create(&__pyfimstruct); \
        if (m == NULL)      \
            return NULL;         \
        numpy_import_array();     \
        return m; \
    }


/* further simplify mod delcarations */
#define PYFI_LIST_START_ PYFI_FUNCLIST = {
#define PYFI_LIST_END_   PYFI_FUNCDESC_TERM() }; PYFI_METHOD_TABLE(STR_MOD_NAME(MOD_NAME)); PYFI_MODINIT();
#define PYFI_DESC(_nam, _desc) PYFI_FUNCDESC(_nam, _desc),
#define PYFI_T_DESC(_nam, _tmpl, _desc) PYFI_FUNCDESC_TEMPLATE(_nam, _tmpl, _desc),


#endif // GUARD
