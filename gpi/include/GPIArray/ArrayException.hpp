/**
 * @file ArrayException.hpp
 * @brief Exception classes and macros for GPIArray error handling.
 *
 * Defines custom exception types for invalid arguments and runtime errors in GPIArray,
 * with file and line information for debugging. Also provides macros for throwing
 * exceptions with contextual information, and a helper for printing nested exceptions.
 * Includes automated C++ stack trace generation for Linux/macOS.
 * * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#pragma once

#include <stdexcept> // For std::invalid_argument, std::runtime_error
#include <string>
#include <sstream>   // For std::ostringstream
#include <exception> // For std::nested_exception
#include <iostream>  // For std::cerr

// --- OS-Specific Stack Trace Headers ---
#if defined(__APPLE__) || defined(__linux__)
    #include <execinfo.h>
    #include <cstdlib>
    #include <cxxabi.h> // <-- NEW: Required for demangling C++ names
#endif

namespace GPIArray {

// Helper function to grab the C++ call stack and demangle names
inline std::string get_cpp_stacktrace() {
    std::ostringstream oss;
    oss << "\n\n--- C++ Call Stack ---\n";
    
    #if defined(__APPLE__) || defined(__linux__)
        const int max_frames = 64;
        void* callstack[max_frames];
        int frames = backtrace(callstack, max_frames);
        char** symbols = backtrace_symbols(callstack, frames);
        
        if (symbols) {
            // Skip the first 2 frames (get_cpp_stacktrace and ExceptionFormatter)
            for (int i = 2; i < frames; ++i) {
                std::string symbol(symbols[i]);
                
                // Attempt to find the mangled name (which always starts with "_Z")
                size_t start = symbol.find("_Z");
                if (start != std::string::npos) {
                    // Find the end of the mangled name (usually marked by a space, '+', or ')')
                    size_t end = symbol.find_first_of(" +)", start);
                    if (end != std::string::npos) {
                        std::string mangled_name = symbol.substr(start, end - start);
                        
                        // Demangle the name using the C++ ABI
                        int status = -1;
                        char* demangled_name = abi::__cxa_demangle(mangled_name.c_str(), nullptr, nullptr, &status);
                        
                        // If demangling succeeded, replace the gibberish in the string
                        if (status == 0 && demangled_name != nullptr) {
                            symbol.replace(start, end - start, demangled_name);
                            free(demangled_name);
                        }
                    }
                }
                oss << "[Frame " << (i-2) << "] " << symbol << "\n";
            }
            free(symbols);
        }
    #else
        oss << "(C++ Stack traces not natively supported on Windows without DbgHelp)\n";
    #endif
    
    return oss.str();
}

// Helper to format exception message with context
class ExceptionFormatter {
private:
    static std::string format_context(const std::string& message, const char* file, 
                                       long line, const char* function = nullptr) {
        std::ostringstream oss;
        oss << "Error in " << file << ":" << line;
        if (function && function[0] != '\0') {
            oss << " (" << function << ")";
        }
        oss << ": " << message;
        
        // --- INJECT THE STACK TRACE HERE ---
        oss << get_cpp_stacktrace();
        
        return oss.str();
    }

public:
    // Prevent instantiation
    ExceptionFormatter() = delete;

    static std::string build_message(const std::string& message, const char* file, 
                                    long line, const char* function = nullptr) {
        try {
            return format_context(message, file, line, function);
        } catch (...) {
            // Fallback if formatting fails
            return "Exception formatting failed: " + message;
        }
    }
};

// Base exception for common functionality (CRTP pattern avoided for simplicity)
class BaseArrayException : public std::runtime_error, public std::nested_exception {
protected:
    std::string _file;
    long _line;
    std::string _function;
    std::string _original_message;

public:
    BaseArrayException(const std::string& message, const char* file, 
                      long line, const char* function = nullptr) noexcept
        : std::runtime_error(ExceptionFormatter::build_message(message, file, line, function)),
          _file(file ? file : "unknown"),
          _line(line),
          _function(function ? function : ""),
          _original_message(message) {}

    virtual ~BaseArrayException() noexcept = default;

    const std::string& get_file() const noexcept { return _file; }
    long get_line() const noexcept { return _line; }
    const std::string& get_function() const noexcept { return _function; }
    const std::string& get_original_message() const noexcept { return _original_message; }
};

// Exception for invalid arguments (semantic error in API usage)
class ArrayException : public BaseArrayException {
public:
    ArrayException(const std::string& message, const char* file, 
                  long line, const char* function = nullptr) noexcept
        : BaseArrayException(message, file, line, function) {}
    
    virtual ~ArrayException() noexcept = default;
};

// Exception for runtime errors (semantic error during execution)
class RuntimeException : public BaseArrayException {
public:
    RuntimeException(const std::string& message, const char* file, 
                    long line, const char* function = nullptr) noexcept
        : BaseArrayException(message, file, line, function) {}
    
    virtual ~RuntimeException() noexcept = default;
};

// Helper function to print nested exceptions with proper indentation
inline void print_exception(const std::exception& e, int level = 0) noexcept {
    try {
        std::cerr << std::string(level, ' ') << "Exception: " << e.what() << std::endl;
        
        // Try to get additional context from our exception types
        const auto* arr_exc = dynamic_cast<const BaseArrayException*>(&e);
        if (arr_exc && !arr_exc->get_function().empty()) {
            std::cerr << std::string(level + 2, ' ') << "  at " << arr_exc->get_function() << std::endl;
        }
    } catch (...) {
        std::cerr << std::string(level, ' ') << "Exception (unsafe): " << e.what() << std::endl;
    }

    try {
        std::rethrow_if_nested(e);
    } catch (const std::exception& nested_e) {
        print_exception(nested_e, level + 2); // Indent nested exceptions
    } catch (...) {
        try {
            std::cerr << std::string(level + 2, ' ') << "Unknown nested exception" << std::endl;
        } catch (...) {
            // Silent failure if even stderr fails
        }
    }
}

} // namespace GPIArray

// ============================================================================
// Exception Throwing Macros
// ============================================================================
// Note: Macros with __FUNCTION__ provide function context for better debugging

#ifndef THROW_RUNTIME_ERROR
#define THROW_RUNTIME_ERROR(message) \
    throw GPIArray::RuntimeException(message, __FILE__, __LINE__, __FUNCTION__)
#endif

#ifndef THROW_INVALID_ARGUMENT
#define THROW_INVALID_ARGUMENT(message) \
    throw GPIArray::ArrayException(message, __FILE__, __LINE__, __FUNCTION__)
#endif

#ifndef THROW_INDEX_ERROR
#define THROW_INDEX_ERROR(message) \
    throw GPIArray::ArrayException(message, __FILE__, __LINE__, __FUNCTION__)
#endif

// Alternative macros without function names for compatibility with older code
#ifndef THROW_RUNTIME_ERROR_SIMPLE
#define THROW_RUNTIME_ERROR_SIMPLE(message) \
    throw GPIArray::RuntimeException(message, __FILE__, __LINE__)
#endif

#ifndef THROW_INVALID_ARGUMENT_SIMPLE
#define THROW_INVALID_ARGUMENT_SIMPLE(message) \
    throw GPIArray::ArrayException(message, __FILE__, __LINE__)
#endif