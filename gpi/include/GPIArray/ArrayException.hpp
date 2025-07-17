/**
 * @file ArrayException.hpp
 * @brief Exception classes and macros for GPIArray error handling.
 *
 * Defines custom exception types for invalid arguments and runtime errors in GPIArray,
 * with file and line information for debugging. Also provides macros for throwing
 * exceptions with contextual information, and a helper for printing nested exceptions.
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#ifndef GPIARRAY_ARRAY_EXCEPTION_HPP
#define GPIARRAY_ARRAY_EXCEPTION_HPP

#include <stdexcept> // For std::invalid_argument, std::runtime_error
#include <string>
#include <sstream>   // For std::ostringstream
#include <exception> // For std::nested_exception
#include <iostream>  // For std::cerr

namespace GPIArray {

class ArrayException : public std::invalid_argument, public std::nested_exception {
private:
    std::string _file;
    long _line;
    std::string _message;

public:
    ArrayException(const std::string& message, const char* file, long line)
        : std::invalid_argument(build_message(message, file, line)),
          _file(file),
          _line(line),
          _message(message) {}

    // Overload for what() to ensure consistent message for top-level printing
    const char* what() const noexcept override {
        return std::invalid_argument::what();
    }

    const std::string& get_file() const { return _file; }
    long get_line() const { return _line; }
    const std::string& get_original_message() const { return _message; }

private:
    static std::string build_message(const std::string& message, const char* file, long line) {
        std::ostringstream oss;
        oss << "Error in " << file << ":" << line << ": " << message;
        return oss.str();
    }
};

// New class for runtime errors
class RuntimeException : public std::runtime_error, public std::nested_exception {
private:
    std::string _file;
    long _line;
    std::string _message;

public:
    RuntimeException(const std::string& message, const char* file, long line)
        : std::runtime_error(build_message(message, file, line)),
          _file(file),
          _line(line),
          _message(message) {}

    const char* what() const noexcept override {
        return std::runtime_error::what();
    }

    const std::string& get_file() const { return _file; }
    long get_line() const { return _line; }
    const std::string& get_original_message() const { return _message; }

private:
    static std::string build_message(const std::string& message, const char* file, long line) {
        std::ostringstream oss;
        oss << "Error in " << file << ":" << line << ": " << message;
        return oss.str();
    }
};

// Helper function to print nested exceptions
void print_exception(const std::exception& e, int level = 0) {
    std::cerr << std::string(level, ' ') << "Exception: " << e.what() << std::endl;
    try {
        std::rethrow_if_nested(e);
    } catch (const std::exception& nested_e) {
        print_exception(nested_e, level + 2); // Indent nested exceptions
    } catch (...) {
        std::cerr << std::string(level + 2, ' ') << "Unknown nested exception" << std::endl;
    }
}

} // namespace GPIArray

// Define the THROW_RUNTIME_ERROR macro
#ifndef THROW_RUNTIME_ERROR
#define THROW_RUNTIME_ERROR(message) throw GPIArray::RuntimeException(message, __FILE__, __LINE__)
#endif

// Define THROW_INVALID_ARGUMENT and THROW_INDEX_ERROR if they are not already defined elsewhere.
// This provides a consistent place for these macros if they use ArrayException.
#ifndef THROW_INVALID_ARGUMENT
#define THROW_INVALID_ARGUMENT(message) throw GPIArray::ArrayException(message, __FILE__, __LINE__)
#endif

#ifndef THROW_INDEX_ERROR
#define THROW_INDEX_ERROR(message) throw GPIArray::ArrayException(message, __FILE__, __LINE__)
#endif

#endif // GPIARRAY_ARRAY_EXCEPTION_HPP