// Author: Guru Krishanmoorthy
// Date: Nov 2026

#include <torch/extension.h>
#include <pybind11/complex.h>
#include <pybind11/iostream.h>

#include <complex>
#include <iostream>

namespace py = pybind11;

// 1. Integer factor.
torch::Tensor scale_int(torch::Tensor input, int factor) {
    std::cout << "[C++] scale_int: device = " << input.device() << std::endl;
    return input * factor;
}

void scale_int_inplace(torch::Tensor input, int factor) {
    std::cout << "[C++] scale_int_inplace: device = " << input.device() << std::endl;
    input.mul_(factor);
}

// 2. Float factor.
torch::Tensor scale_float(torch::Tensor input, float factor) {
    std::cout << "[C++] scale_float: device = " << input.device() << std::endl;
    return input * factor;
}

void scale_float_inplace(torch::Tensor input, float factor) {
    std::cout << "[C++] scale_float_inplace: device = " << input.device() << std::endl;
    input.mul_(factor);
}

// 3. Convert the Python-compatible complex factor to LibTorch's scalar type.
torch::Tensor scale_complex(torch::Tensor input, std::complex<float> factor) {
    std::cout << "[C++] scale_complex: device = " << input.device() << std::endl;
    return input * c10::complex<float>(factor.real(), factor.imag());
}

void scale_complex_inplace(torch::Tensor input, std::complex<float> factor) {
    std::cout << "[C++] scale_complex_inplace: device = " << input.device() << std::endl;
    input.mul_(c10::complex<float>(factor.real(), factor.imag()));
}

// Keep console output out of the timed benchmark region.
void benchmark_scale_inplace(torch::Tensor input, double factor) {
    input.mul_(factor);
}

// 4. Template last. T is the factor type; Tensor keeps its runtime dtype.
template <typename T>
torch::Tensor scale(torch::Tensor input, T factor) {
    std::cout << "[C++] scale<T>: device = " << input.device() << std::endl;
    return input * factor;
}

template <typename T>
void scale_inplace(torch::Tensor input, T factor) {
    std::cout << "[C++] scale_inplace<T>: device = " << input.device() << std::endl;
    input.mul_(factor);
}

PYBIND11_MODULE(libtorch_basics, m) {
    m.doc() = "Starter LibTorch scaling functions for CPU and GPU tensors.";

    // The guards route std::cout to Python stdout and the GPI console.
    m.def("scale_int", &scale_int, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_int_inplace", &scale_int_inplace, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_float", &scale_float, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_float_inplace", &scale_float_inplace, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_complex", &scale_complex, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_complex_inplace", &scale_complex_inplace, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale", &scale<double>, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_inplace", &scale_inplace<double>, py::call_guard<py::scoped_ostream_redirect>());
    m.def("benchmark_scale_inplace", &benchmark_scale_inplace);
}
