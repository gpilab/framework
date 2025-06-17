/*
 * Copyright (C) 2014  Dignity Health
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
 * AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
 * SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
 * PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
 * USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
 * LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
 * MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
 * SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.
 */

// REMOVED old include guard #ifndef _BACKTRACE_CPP_GUARD / #define _BACKTRACE_CPP_GUARD

// Include its own new header for declarations
#include "PyFI/backtrace.h"

// Specific includes for implementations (these are fine here)
#include <execinfo.h>   // for backtrace
#include <dlfcn.h>      // for dladdr
#include <cxxabi.h>     // for __cxa_demangle

#include <cstdio>       // for snprintf, printf
#include <cstdlib>      // for free
#include <sstream>      // for std::ostringstream

// Using namespace std; is typically fine in a .cpp file
using namespace std;

namespace PyFI
{

// Definition of Backtrace function
std::string Backtrace(int skip) // skip = 1 by default, matches declaration
{
    void *callstack[128];
    const int nMaxFrames = 10; // Keep the smaller limit as in original
    char buf[1024];
    int nFrames = backtrace(callstack, nMaxFrames);
    char **symbols = backtrace_symbols(callstack, nFrames);

    std::ostringstream trace_buf;
    for (int i = skip; i < nFrames; i++) {
        // Original had printf here. Changed to snprintf to capture in buffer.
        // It's still strange to have a printf in a Backtrace function that returns a string,
        // but preserving original logic while making it snprintf to a buffer.
        // If the intent was for it to print directly, then the 'return trace_buf.str()' is contradictory.
        // For now, assuming the snprintf to buf and then appending to trace_buf is the desired behavior.
        // if (i == 1) printf("%s\n", symbols[i]); // If debugging this line specifically was intended, keep it.
        // I will keep the original `printf("%s\n", symbols[i]);` as it was in the source you provided.
        printf("%s\n", symbols[i]); // Keeping the original printf

        Dl_info info;
        if (dladdr(callstack[i], &info) && info.dli_sname) {
            char *demangled = NULL;
            int status = -1;
            if (info.dli_sname[0] == '_')
                demangled = abi::__cxa_demangle(info.dli_sname, NULL, 0, &status);
            snprintf(buf, sizeof(buf), "%-3d %*p %s + %zd\n",
                     i, (int)(2 + sizeof(void*) * 2), callstack[i], // Explicit cast for int(...)
                     status == 0 ? demangled :
                     info.dli_sname == 0 ? symbols[i] : info.dli_sname,
                     (char *)callstack[i] - (char *)info.dli_saddr);
            free(demangled);
        } else {
            snprintf(buf, sizeof(buf), "%-3d %*p %s\n",
                     i, (int)(2 + sizeof(void*) * 2), callstack[i], symbols[i]); // Explicit cast for int(...)
        }
        trace_buf << buf;
    }
    free(symbols);
    if (nFrames == nMaxFrames)
        trace_buf << "[truncated]\n";
    return trace_buf.str();
}

// Definition of Demangle function
const std::string Demangle(const char* name)
{
    int status = -4; // Used to hold a status code, if negative indicates error.

    char* res = abi::__cxa_demangle(name, NULL, NULL, &status);

    const char* const demangled_name = (status == 0) ? res : name;

    std::string ret_val(demangled_name); // Convert to std::string

    free(res); // Free the memory allocated by __cxa_demangle

    return ret_val;
}

} // namespace PyFI

// REMOVED old #endif // GUARD