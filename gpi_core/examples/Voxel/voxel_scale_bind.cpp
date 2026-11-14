// Author: Guru Krishanmoorthy
// Date: Nov 2026

#include "Voxel/Voxel.hpp"

#include <complex>
#include <iostream>

using namespace Voxel;

// 1. Integer array and integer factor.
Array<int> scale_int(const Array<int>& input, int factor) {
    std::cout << "[C++] scale_int: factor = " << factor << std::endl;
    auto output = input.copy();
    output *= factor;
    return output;
}

void scale_int_inplace(Array<int>& input, int factor) {
    std::cout << "[C++] scale_int_inplace: factor = " << factor << std::endl;
    input *= factor;
}

// 2. Float array and float factor.
Array<float> scale_float(const Array<float>& input, float factor) {
    std::cout << "[C++] scale_float: factor = " << factor << std::endl;
    auto output = input.copy();
    output *= factor;
    return output;
}

void scale_float_inplace(Array<float>& input, float factor) {
    std::cout << "[C++] scale_float_inplace: factor = " << factor << std::endl;
    input *= factor;
}

// 3. Complex array and complex factor.
Array<std::complex<float>> scale_complex(
    const Array<std::complex<float>>& input,
    std::complex<float> factor) {
    std::cout << "[C++] scale_complex: factor = " << factor << std::endl;
    auto output = input.copy();
    output *= factor;
    return output;
}

void scale_complex_inplace(
    Array<std::complex<float>>& input,
    std::complex<float> factor) {
    std::cout << "[C++] scale_complex_inplace: factor = " << factor << std::endl;
    input *= factor;
}

// 4. The same operation, with T replacing the concrete type.
template <typename T>
Array<T> scale(const Array<T>& input, T factor) {
    std::cout << "[C++] scale<T>: factor = " << factor << std::endl;
    auto output = input.copy();
    output *= factor;
    return output;
}

template <typename T>
void scale_inplace(Array<T>& input, T factor) {
    std::cout << "[C++] scale_inplace<T>: factor = " << factor << std::endl;
    input *= factor;
}

PYBIND11_MODULE(voxel_scale, m) {
    m.doc() = "Voxel Scale: copy-based and in-place NumPy scaling through Voxel.";

    m.def("scale_int", &scale_int, "Scale an int32 array without modifying it.");

    m.def("scale_int_inplace", &scale_int_inplace, "Scale a writable int32 array in place.");

    m.def("scale_float", &scale_float, "Scale a float32 array without modifying it.");

    m.def("scale_float_inplace", &scale_float_inplace, "Scale a writable float32 array in place.");

    m.def("scale_complex", &scale_complex, "Scale a complex64 array without modifying it.");

    m.def("scale_complex_inplace", &scale_complex_inplace, "Scale a writable complex64 array in place.");

    m.def("scale", &scale<float>, "Scale a float32 array without modifying it.");

    m.def("scale", &scale<double>, "Scale a float64 array without modifying it.");

    m.def("scale_inplace", &scale_inplace<float>, "Scale a writable float32 array in place.");
    
    m.def("scale_inplace", &scale_inplace<double>, "Scale a writable float64 array in place.");
}
