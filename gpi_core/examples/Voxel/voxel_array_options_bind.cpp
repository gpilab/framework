// Author: Guru Krishanmoorthy
// Date: Nov 2026

#include "Voxel/Voxel.hpp"

#include <complex>
#include <iostream>

using namespace Voxel;

// 1. Convert types, add/remove dimensions, resize, and take a strided slice.
Array<double> layout_options() {
    std::cout << "[C++] layout_options" << std::endl;
    auto integers = Array<int>::zeros(2, 3);
    integers.fill(6);
    Array<float> floats(integers);
    Array<double> doubles(floats);
    Array<std::complex<double>> complex_values(doubles);
    std::cout << "Converted int -> float -> double -> complex: "
              << complex_values(1, 2) << std::endl;

    auto expanded = doubles.add_singleton_dimension(0);
    auto squeezed = expanded.squeeze();
    std::cout << "Dimensions: " << doubles.ndim() << " -> " << expanded.ndim()
              << " -> " << squeezed.ndim() << std::endl;

    auto resized = squeezed.copy();
    resized.resize(3, 3);  // New storage: fill it before reading it.
    resized.fill(7.0);
    auto selected = resized.slice(S(0, 3, 2), S(1, 3));
    std::cout << "Selected rows 0 and 2, columns 1 and 2." << std::endl;
    return selected.copy();
}

// 2. Positive inputs keep sqrt/log easy to understand.
Array<float> math_options() {
    std::cout << "[C++] math_options" << std::endl;
    auto values = Array<float>::linspace(1.0f, 6.0f, uint64_t(6), true).reshape(2, 3);
    auto roots = sqrt(values);
    auto exponentials = exp(values);
    auto logarithms = log(values);
    auto sines = sin(values);
    auto cosines = cos(values);
    auto exponents = values.ones_like();
    exponents.fill(2.0f);
    auto squares = pow(values, exponents);
    std::cout << "At input 6: sqrt=" << roots(1, 2)
              << ", exp=" << exponentials(1, 2) << ", log=" << logarithms(1, 2)
              << ", sin=" << sines(1, 2) << ", cos=" << cosines(1, 2)
              << ", square=" << squares(1, 2) << std::endl;

    auto shifted = (values - 2.0f) / 2.0f;
    auto rounded = round(shifted);
    auto floored = floor(shifted);
    auto ceiled = ceil(shifted);
    std::cout << "At -0.5: round=" << rounded(0, 0)
              << ", floor=" << floored(0, 0) << ", ceil=" << ceiled(0, 0) << std::endl;
    return clamp(shifted, 0.0f, 1.0f);
}

Array<bool> mask_options() {
    std::cout << "[C++] mask_options" << std::endl;
    auto values = Array<float>::linspace(1.0f, 6.0f, uint64_t(6), true).reshape(2, 3);
    auto mask = values > 3.0f;
    std::cout << "Counts: >3=" << count(mask)
              << ", >=3=" << count(values >= 3.0f)
              << ", <3=" << count(values < 3.0f)
              << ", <=3=" << count(values <= 3.0f)
              << ", ==3=" << count(values == 3.0f)
              << ", !=3=" << count(values != 3.0f) << std::endl;
    return mask;
}

Array<float> vector_options() {
    std::cout << "[C++] vector_options" << std::endl;
    auto a = Array<float>::linspace(1.0f, 3.0f, uint64_t(3), true);
    auto b = Array<float>::linspace(4.0f, 6.0f, uint64_t(3), true);
    std::cout << "Dot: " << dot(a, b) << std::endl;
    std::cout << "Norms: " << l1norm(a) << ", " << l2norm(a) << ", "
              << linfnorm(a) << ", " << lpnorm(a, 3.0) << std::endl;
    return outer_product(a, b);
}

// 3. A rectangular matrix makes thin/full SVD shapes visibly different.
Array<std::complex<float>> matrix_options() {
    std::cout << "[C++] matrix_options" << std::endl;
    auto a = Array<float>::linspace(1.0f, 6.0f, uint64_t(6), true).reshape(3, 2);
    Array<float> u(3, 2);
    Array<float> s(2);
    Array<float> vh(2, 2);
    LinAlg::svd(a, u, s, vh, LinAlg::Thin);
    std::cout << "Thin U shape: " << u.dimensions(0) << " x " << u.dimensions(1)
              << "; singular values: " << s(0) << ", " << s(1) << std::endl;

    Array<float> full_u(3, 3);
    Array<float> full_s(2);
    Array<float> full_vh(2, 2);
    LinAlg::svd(a, full_u, full_s, full_vh, LinAlg::Full);
    std::cout << "Full U shape: " << full_u.dimensions(0) << " x " << full_u.dimensions(1)
              << "; singular values: " << full_s(0) << ", " << full_s(1) << std::endl;

    Array<float> unused_u;
    Array<float> unused_vh;
    Array<float> only_s(2);
    LinAlg::svd(a, unused_u, only_s, unused_vh, LinAlg::SVDComputeType::SingularValuesOnly);
    std::cout << "Values-only SVD: " << only_s(0) << ", " << only_s(1) << std::endl;

    Array<std::complex<float>> complex_values(a);
    complex_values += std::complex<float>(0.0f, 1.0f);
    return LinAlg::hermitian(complex_values);
}

// 4. Template last: subtraction and division also work for N-dimensional arrays.
template <typename T>
Array<T> subtract_and_divide(const Array<T>& input, T offset, T divisor) {
    std::cout << "[C++] subtract_and_divide<T>" << std::endl;
    return (input - offset) / divisor;
}

PYBIND11_MODULE(voxel_array_options, m) {
    m.doc() = "Grouped layout, math, masks, vectors, and matrix options.";
    m.def("layout_options", &layout_options);
    m.def("math_options", &math_options);
    m.def("mask_options", &mask_options);
    m.def("vector_options", &vector_options);
    m.def("matrix_options", &matrix_options);
    m.def("subtract_and_divide", &subtract_and_divide<float>);
    m.def("subtract_and_divide", &subtract_and_divide<double>);
}
