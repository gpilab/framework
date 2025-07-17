
/**
 * @file NumpyReadWrite.hpp
 * @brief Utilities for reading and writing GPIArray::Array<T> objects in NumPy .npy format.
 *
 * This header provides functions to interface GPIArray arrays with the NumPy ecosystem via the .npy file format.
 * It uses the cnpy library for serialization and deserialization, enabling seamless data exchange between C++ and Python.
 *
 * Features:
 *   - Read a NumPy .npy file into a GPIArray::Array<T> with automatic shape and type checking.
 *   - Write a GPIArray::Array<T> to disk in .npy format, ensuring correct memory layout and shape reversal.
 *   - Handles contiguous and non-contiguous arrays, creating copies as needed for safe serialization.
 *   - Provides a utility to check file existence.
 *
 * Typical use cases include scientific computing, machine learning, and data analysis workflows that require interoperability
 * between C++ and Python/NumPy.
 *
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#ifndef GPIARRAY_NUMPY_READWRITE_HPP
#define GPIARRAY_NUMPY_READWRITE_HPP

#include "Array.hpp" // Main GPIArray header
#include "cnpy.h"    // Header for the cnpy library
#include <string>
#include <vector>
#include <stdexcept>
#include <algorithm> // For std::reverse
#include <type_traits> // For std::is_same
#include <fstream> // For std::ifstream

namespace GPIArray {
namespace Numpy {

/**
 * @brief Reads a .npy file and converts it into a GPIArray::Array<T>.
 *
 * This function uses the cnpy library to load a NumPy file from disk. It then
 * performs a deep copy of the data into a new, contiguous GPIArray::Array.
 * The shape of the array is automatically reversed to match the typical
 * C++ (column-major-like) memory layout convention from Python's row-major layout.
 *
 * @tparam T The data type of the array elements (e.g., float, double, std::complex<float>).
 * @param filename The path to the .npy file.
 * @return A GPIArray::Array<T> containing the data from the file.
 * @throws std::runtime_error if the file cannot be opened, or if the data type
 * in the file does not match the specified template type T.
 */
template<typename T>
Array<T> read_npy(const std::string& filename) {
    // Load the .npy file using cnpy
    cnpy::NpyArray npy_array = cnpy::npy_load(filename);

    // Check if the data type in the file matches the requested type T
    if (npy_array.word_size != sizeof(T)) {
        throw std::runtime_error("Data type mismatch: The type in the .npy file (word size " +
                                 std::to_string(npy_array.word_size) +
                                 ") does not match the requested type T (word size " +
                                 std::to_string(sizeof(T)) + ").");
    }

    // Get the shape from the loaded npy array.
    // NumPy/cnpy use row-major order, so we reverse the shape for GPIArray's
    // column-major-like convention.
    std::vector<uint64_t> shape(npy_array.shape.begin(), npy_array.shape.end());
    std::reverse(shape.begin(), shape.end());

    // Create a new GPIArray with the correct dimensions.
    // This allocates the necessary memory.
    Array<T> result_array(shape);

    // Perform a deep copy of the data from the cnpy buffer to the GPIArray.
    // cnpy loads the entire file into a char* buffer.
    const T* source_data = npy_array.data<T>();
    T* dest_data = result_array.get_data();

    if (source_data && dest_data) {
        std::memcpy(dest_data, source_data, npy_array.num_bytes());
    } else if (npy_array.num_vals > 0) {
        // Throw an error if there should be data but pointers are null
        throw std::runtime_error("Memory allocation error while reading .npy file.");
    }
    
    return result_array;
}

/**
 * @brief Writes a GPIArray::Array<T> to a .npy file.
 *
 * This function saves a GPIArray to disk in the NumPy .npy format.
 * The array's shape is reversed before saving to conform to the standard
 * row-major order used by NumPy. If the input GPIArray is not contiguous
 * in memory (e.g., it's a view from a slice or transpose), a contiguous
 * copy is created before saving.
 *
 * @tparam T The data type of the array elements (e.g., float, double, std::complex<float>).
 * @param data The GPIArray::Array<T> to be saved.
 * @param filename The path where the .npy file will be saved.
 */
template<typename T>
void write_npy(const Array<T>& data, const std::string& filename) {
    // cnpy::npy_save requires a raw pointer to contiguous data.
    // If our array is a non-contiguous view, we must create a contiguous copy first.
    Array<T> contiguous_data = data.is_contiguous() ? data : data.copy();

    // Get the shape as vector<uint64_t> from GPIArray
    std::vector<uint64_t> original_shape_uint64 = contiguous_data.dimensions_vector();

    // *** FIX: Convert to vector<size_t> for cnpy ***
    std::vector<size_t> numpy_shape(original_shape_uint64.begin(), original_shape_uint64.end());
    
    // Reverse it for NumPy's row-major standard.
    std::reverse(numpy_shape.begin(), numpy_shape.end());

    // If the array is 0D, numpy expects an empty shape vector.
    if (contiguous_data.ndim() == 0) {
        numpy_shape.clear();
    }

    // Save the data using cnpy
    cnpy::npy_save(filename, contiguous_data.get_data(), numpy_shape);
}

/**
 * @brief Checks if a file exists at the given path.
 *
 * @param filename The path to the file.
 * @return true if the file exists, false otherwise.
 */
inline bool file_exists(const std::string& filename) {
    return std::ifstream(filename).good();
}

} // namespace Numpy
} // namespace GPIArray

#endif // GPIARRAY_NUMPY_READWRITE_HPP
