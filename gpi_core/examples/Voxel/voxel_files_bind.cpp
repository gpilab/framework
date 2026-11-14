// Author: Guru Krishanmoorthy
// Date: Nov 2026

#include "Voxel/Voxel.hpp"

#include <complex>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace Voxel;

// Protect existing files and fail before cnpy tries to use an invalid FILE pointer.
void prepare_file(const std::string& filename) {
    if (Numpy::file_exists(filename)) {
        throw std::runtime_error("Choose a new filename; this example does not overwrite files.");
    }
    std::ofstream file(filename, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Cannot create NumPy file: " + filename);
    }
}

// 1. Integer file.
Array<int> integer_file(const Array<int>& input, const std::string& filename) {
    std::cout << "[C++] integer_file" << std::endl;
    prepare_file(filename);
    Numpy::write_npy(input, filename);
    return Numpy::read_npy<int>(filename);
}

// 2. Float file.
Array<float> float_file(const Array<float>& input, const std::string& filename) {
    std::cout << "[C++] float_file" << std::endl;
    prepare_file(filename);
    Numpy::write_npy(input, filename);
    return Numpy::read_npy<float>(filename);
}

// 3. Complex file.
Array<std::complex<float>> complex_file(
    const Array<std::complex<float>>& input, const std::string& filename) {
    std::cout << "[C++] complex_file" << std::endl;
    prepare_file(filename);
    Numpy::write_npy(input, filename);
    return Numpy::read_npy<std::complex<float>>(filename);
}

// 4. Template last: read back exactly the dtype that was just written.
template <typename T>
Array<T> roundtrip_file(const Array<T>& input, const std::string& filename) {
    std::cout << "[C++] roundtrip_file<T>" << std::endl;
    prepare_file(filename);
    Numpy::write_npy(input, filename);
    return Numpy::read_npy<T>(filename);
}

PYBIND11_MODULE(voxel_files, m) {
    m.doc() = "NumPy file round trips using new filenames; existing files are not overwritten.";
    m.def("integer_file", &integer_file);
    m.def("float_file", &float_file);
    m.def("complex_file", &complex_file);
    m.def("roundtrip_file", &roundtrip_file<float>);
    m.def("roundtrip_file", &roundtrip_file<double>);
    m.def("roundtrip_file", &roundtrip_file<std::complex<float>>);
    m.def("roundtrip_file", &roundtrip_file<std::complex<double>>);
}
