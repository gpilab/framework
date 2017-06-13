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

#ifndef _BACKTRACE_CPP_GUARD
#define _BACKTRACE_CPP_GUARD
/* from: https://gist.github.com/fmela/591333
 */
#include <execinfo.h>   // for backtrace
#include <dlfcn.h>      // for dladdr
#include <cxxabi.h>     // for __cxa_demangle
 
#include <cstdio>
#include <cstdlib>
#include <string>
#include <sstream>

namespace PyFI
{
 
// This function produces a stack backtrace with demangled function & method names.
std::string Backtrace(int skip = 1)
{
    void *callstack[128];
    //const int nMaxFrames = sizeof(callstack) / sizeof(callstack[0]);
    const int nMaxFrames = 10;
    char buf[1024];
    int nFrames = backtrace(callstack, nMaxFrames);
    char **symbols = backtrace_symbols(callstack, nFrames);
 
    std::ostringstream trace_buf;
    for (int i = skip; i < nFrames; i++) {
        printf("%s\n", symbols[i]);
 
        Dl_info info;
        if (dladdr(callstack[i], &info) && info.dli_sname) {
            char *demangled = NULL;
            int status = -1;
            if (info.dli_sname[0] == '_')
                demangled = abi::__cxa_demangle(info.dli_sname, NULL, 0, &status);
            snprintf(buf, sizeof(buf), "%-3d %*p %s + %zd\n",
                     i, int(2 + sizeof(void*) * 2), callstack[i],
                     status == 0 ? demangled :
                     info.dli_sname == 0 ? symbols[i] : info.dli_sname,
                     (char *)callstack[i] - (char *)info.dli_saddr);
            free(demangled);
        } else {
            snprintf(buf, sizeof(buf), "%-3d %*p %s\n",
                     i, int(2 + sizeof(void*) * 2), callstack[i], symbols[i]);
        }
        trace_buf << buf;
    }
    free(symbols);
    if (nFrames == nMaxFrames)
        trace_buf << "[truncated]\n";
    return trace_buf.str();
}

/* demangle type names
 *  from: http://stackoverflow.com/questions/281818/unmangling-the-result-of-stdtype-infoname
 */
const string Demangle(const char* name) 
{

    int status = -4;

    char* res = abi::__cxa_demangle(name, NULL, NULL, &status);

    const char* const demangled_name = (status==0)?res:name;

    string ret_val(demangled_name);

    free(res);

    return ret_val;
}

}// namespace

#endif // GUARD
