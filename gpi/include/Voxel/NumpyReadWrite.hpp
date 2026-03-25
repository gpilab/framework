/**
 * @file NumpyReadWrite.hpp
 * @brief Utilities for reading and writing Voxel::Array<T> objects in NumPy .npy format.
 *
 * This header provides functions to interface Voxel arrays with the NumPy ecosystem via the .npy file format.
 * It uses the cnpy library for serialization and deserialization, enabling seamless data exchange between C++ and Python.
 *
 * Features:
 * - Read a NumPy .npy file into a Voxel::Array<T> with automatic shape and type checking.
 * - Write a Voxel::Array<T> to disk in .npy format, maintaining native Row-Major memory layout.
 * - Handles contiguous and non-contiguous arrays, creating copies as needed for safe serialization.
 * - Provides a utility to check file existence.
 *
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#pragma once

#include "Array.hpp" 
#include "cnpy.h"    
#include <string>
#include <vector>
#include <stdexcept>
#include <type_traits> 
#include <fstream> 

namespace Voxel {
namespace Numpy {

/**
 * @brief Reads a .npy file and converts it into a Voxel::Array<T>.
 *
 * This function uses the cnpy library to load a NumPy file from disk. It then
 * performs a deep copy of the data into a new, contiguous Voxel::Array.
 * Because both NumPy and Voxel use Row-Major (C-contiguous) layout natively,
 * the shapes and memory blocks map 1-to-1.
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

    // Direct mapping: NumPy and Voxel are both C-contiguous (Row-Major)
    std::vector<uint64_t> shape(npy_array.shape.begin(), npy_array.shape.end());

    // Create a new Voxel with the correct dimensions.
    Array<T> result_array(shape);

    // Perform a deep copy of the data from the cnpy buffer to the Voxel.
    const T* source_data = npy_array.data<T>();
    T* dest_data = result_array.get_data();

    if (source_data && dest_data && npy_array.num_bytes() > 0) {
        std::memcpy(dest_data, source_data, npy_array.num_bytes());
    } else if (npy_array.num_vals > 0) {
        throw std::runtime_error("Memory allocation error while reading .npy file.");
    }
    
    return result_array;
}

/**
 * @brief Writes a Voxel::Array<T> to a .npy file.
 *
 * This function saves a Voxel to disk in the NumPy .npy format.
 * If the input Voxel is not contiguous in memory (e.g., it's a view from a 
 * slice or transpose), a contiguous copy is created before saving.
 */
template<typename T>
void write_npy(const Array<T>& data, const std::string& filename) {
    // cnpy::npy_save requires a raw pointer to contiguous data.
    Array<T> contiguous_data = data.is_contiguous() ? data : data.copy();

    // Get the shape as vector<uint64_t> from Voxel
    std::vector<uint64_t> original_shape_uint64 = contiguous_data.dimensions_vector();

    // Convert to vector<size_t> for cnpy compatibility
    std::vector<size_t> numpy_shape(original_shape_uint64.begin(), original_shape_uint64.end());
    
    // If the array is 0D, numpy expects an absolutely empty shape vector.
    if (contiguous_data.ndim() == 0) {
        numpy_shape.clear();
    }

    // Save the data using cnpy
    cnpy::npy_save(filename, contiguous_data.get_data(), numpy_shape);
}

/**
 * @brief Checks if a file exists at the given path.
 */
inline bool file_exists(const std::string& filename) {
    return std::ifstream(filename).good();
}

} // namespace Numpy
} // namespace Voxel
