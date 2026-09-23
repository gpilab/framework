// test_Array_PYBIND11.cpp
// Unit tests for Voxel::Array core features (creation, shape, access, reshape, transpose, type conversion)
// Author: Guru Krishnamoorthy
// Date: 2026-03-25


#include "Voxel/Voxel.hpp"
#include <vector>
#include <stdexcept>

namespace py = pybind11;
using namespace Voxel;

// Expose linspace for Array<double>
Array<double> test_linspace(double start, double stop, int num, bool endpoint = true) {
    return Array<double>::linspace(start, stop, static_cast<uint64_t>(num), endpoint);
}

// Test: Array creation and shape
std::vector<uint64_t> test_array_shape() {
    Array<float> arr(3, 4, 5);
    return arr.shape();
}

// Test: Element access and assignment
float test_array_set_get() {
    Array<float> arr(2, 2);
    arr(0, 0) = 1.5f;
    arr(1, 1) = 2.5f;
    return arr(0, 0) + arr(1, 1);
}

// Test: Reshape
std::vector<uint64_t> test_array_reshape() {
    Array<float> arr(2, 3, 2);
    auto arr_reshaped = arr.reshape(3, 4);
    return arr_reshaped.shape();
}

// Test: Transpose
std::vector<uint64_t> test_array_transpose() {
    Array<float> arr(2, 3, 4);
    auto arr_transposed = arr.transpose(2, 0, 1);
    return arr_transposed.shape();
}

// Test: Type conversion (astype)
double test_array_astype() {
    Array<float> arr(2);
    arr(0) = 3.14f;
    arr(1) = 2.71f;
    Array<double> arr2 = arr.astype<double>();
    return arr2(0) + arr2(1);
}

PYBIND11_MODULE(test_Array, m) {
    m.def("test_array_shape", &test_array_shape);
    m.def("test_array_set_get", &test_array_set_get);
    m.def("test_array_reshape", &test_array_reshape);
    m.def("test_array_transpose", &test_array_transpose);
    m.def("test_array_astype", &test_array_astype);
    m.def("test_linspace", &test_linspace);
     
}


