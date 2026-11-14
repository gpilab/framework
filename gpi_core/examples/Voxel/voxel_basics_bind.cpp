// Author: Guru Krishanmoorthy
// Date: Nov 2026

#include "Voxel/Voxel.hpp"

#include <complex>
#include <iostream>

using namespace Voxel;

// 1. Integers: create, index, copy, add, multiply, and reduce a 1D array.
Array<int> integer_1d() {
    std::cout << "[C++] integer_1d" << std::endl;
    auto values = Array<int>::zeros(6);
    for (size_t i = 0; i < values.size(); i++) {
        values(i) = i + 1;
    }

    auto ones = values.ones_like();
    auto result = values.copy();
    result += ones;
    result *= 2;
    std::cout << "Sum: " << sum(result) << ", min: " << min(result)
              << ", max: " << max(result) << std::endl;
    return result;
}

// 2. Floats: reshape, slice, transpose, broadcast, flatten, and statistics.
Array<float> real_2d() {
    std::cout << "[C++] real_2d" << std::endl;
    auto line = Array<float>::linspace(0.0f, 5.0f, uint64_t(6), true);
    auto values = line.reshape(2, 3);

    auto first_row = values.slice(S(0), S::all());
    first_row += 10.0f;  // A slice is a view: this also changes values.
    auto transposed = values.transpose(1, 0);
    std::cout << "Transpose shape: " << transposed.dimensions(0)
              << " x " << transposed.dimensions(1) << std::endl;

    auto offsets = Array<float>::ones(3);
    auto result = values + offsets;  // Add a 1D vector to each 2D row.
    auto flat = result.flatten();
    std::cout << "Flattened size: " << flat.size()
              << ", mean: " << mean(result)
              << ", sample stdev: " << stdev(result) << std::endl;
    return result;
}

// 3. Complex numbers: create a 3D array and examine its components.
Array<std::complex<float>> complex_3d() {
    std::cout << "[C++] complex_3d" << std::endl;
    Array<std::complex<float>> values(2, 2, 2);
    values.fill(std::complex<float>(3.0f, 4.0f));

    auto real_values = real(values);
    auto imaginary_values = imag(values);
    auto magnitudes = abs(values);
    auto phases = angle(values);
    std::cout << "Each value has real: " << real_values(0, 0, 0)
              << ", imaginary: " << imaginary_values(0, 0, 0)
              << ", magnitude: " << magnitudes(0, 0, 0)
              << ", phase (radians): " << phases(0, 0, 0) << std::endl;
    return conj(values);
}

// 4. Matrices: multiplication, solving systems, SVD, and PCA.
Array<float> matrix_2d() {
    std::cout << "[C++] matrix_2d" << std::endl;
    Array<float> a(2, 2);
    a(0, 0) = 1.0f;
    a(0, 1) = 2.0f;
    a(1, 0) = 3.0f;
    a(1, 1) = 4.0f;

    auto elementwise = a * a;
    auto transposed = a.transpose(1, 0);
    auto product = LinAlg::matmul(a, transposed);
    std::cout << "Element-wise (0,1): " << elementwise(0, 1)
              << ", matrix product (0,1): " << product(0, 1) << std::endl;

    Array<float> rhs(2, 1);
    rhs.fill(1.0f);
    auto cholesky_solution = LinAlg::solve_cholesky(product, rhs);
    std::cout << "Cholesky solution: " << cholesky_solution(0, 0) << ", "
              << cholesky_solution(1, 0) << std::endl;

    Array<float> u(2, 2);
    Array<float> singular_values(2);
    Array<float> vh(2, 2);
    LinAlg::svd(a, u, singular_values, vh, LinAlg::Thin);
    std::cout << "Singular values: " << singular_values(0) << ", "
              << singular_values(1) << std::endl;

    Array<float> components(2, 2);
    Array<float> variances(2);
    LinAlg::pca(a, components, variances);
    std::cout << "PCA variances: " << variances(0) << ", " << variances(1) << std::endl;
    return product;
}

// 5. FFT: all dimensions, in NumPy's unshifted frequency order.
Array<std::complex<float>> fft_example(
    const Array<std::complex<float>>& input, bool inverse) {
    std::cout << "[C++] fft_example, inverse = " << inverse << std::endl;
    auto output = input.empty_like();
    if (inverse) {
        FFT::fftn(input, output, FFT::Backward, {}, false);
    } else {
        FFT::fftn(input, output, FFT::Forward, {}, false);
    }
    return output;
}

// 6. Wavelets: one Haar level, optional thresholding, and reconstruction.
Array<std::complex<float>> wavelet_example(
    const Array<std::complex<float>>& input, float threshold) {
    std::cout << "[C++] wavelet_example, threshold = " << threshold << std::endl;
    Wavelet<float> wavelet(input.dimensions(0), input.dimensions(1), 1, true);
    auto coefficients = wavelet.forward_transform(input);
    wavelet.soft_threshold(coefficients, {threshold});
    return wavelet.inverse_transform(coefficients);
}

// 7. Template last: the same arithmetic works with any number of dimensions.
template <typename T>
Array<T> array_template(const Array<T>& input, T factor) {
    std::cout << "[C++] array_template<T>, dimensions = " << input.ndim() << std::endl;
    auto output = input.copy();
    output += input;
    output *= factor;
    std::cout << "Sum: " << sum(output) << ", mean: " << mean(output) << std::endl;
    return output;
}

PYBIND11_MODULE(voxel_basics, m) {
    m.doc() = "Multidimensional Voxel walkthroughs, from integers to templates.";
    m.def("integer_1d", &integer_1d);
    m.def("real_2d", &real_2d);
    m.def("complex_3d", &complex_3d);
    m.def("matrix_2d", &matrix_2d);
    m.def("fft_example", &fft_example);
    m.def("wavelet_example", &wavelet_example);
    m.def("array_template", &array_template<float>);
    m.def("array_template", &array_template<double>);
}
