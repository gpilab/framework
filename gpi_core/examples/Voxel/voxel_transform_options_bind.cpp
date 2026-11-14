// Author: Guru Krishanmoorthy
// Date: Nov 2026

#include "Voxel/Voxel.hpp"

#include <complex>
#include <iostream>

using namespace Voxel;

// 1. Transform only the last axis, leaving the other dimensions unchanged.
Array<std::complex<float>> last_axis_fft(const Array<std::complex<float>>& input) {
    std::cout << "[C++] last_axis_fft" << std::endl;
    auto output = input.empty_like();
    FFT::fftn(input, output, FFT::Forward, {input.ndim() - 1}, false);
    return output;
}

// 2. A small odd-sized image demonstrates Voxel's centered transform.
Array<std::complex<float>> centered_fft_2d() {
    std::cout << "[C++] centered_fft_2d" << std::endl;
    auto line = Array<float>::linspace(1.0f, 9.0f, uint64_t(9), true);
    Array<std::complex<float>> image(line.reshape(3, 3));
    auto output = image.empty_like();
    FFT::fftn(image, output, FFT::Forward, {}, true);
    return output;
}

Array<std::complex<float>> orthonormal_fft(const Array<std::complex<float>>& input) {
    std::cout << "[C++] orthonormal_fft" << std::endl;
    auto output = input.empty_like();
    FFT::fftn(input, output, FFT::Forward, {}, false, FFT::NORM_ORTHO);
    return output;
}

Array<std::complex<float>> unnormalized_roundtrip(const Array<std::complex<float>>& input) {
    std::cout << "[C++] unnormalized_roundtrip" << std::endl;
    auto spectrum = input.empty_like();
    auto output = input.empty_like();
    FFT::fftn(input, spectrum, FFT::Forward, {}, false, FFT::NORM_NONE);
    FFT::fftn(spectrum, output, FFT::Backward, {}, false, FFT::NORM_NONE);
    return output;  // Without normalization, the result is input * input.size().
}

// 3. Create one plan and reuse it for two forward/inverse pairs.
Array<std::complex<float>> planned_roundtrip(const Array<std::complex<float>>& input) {
    std::cout << "[C++] planned_roundtrip" << std::endl;
    FFT::FFTPlan<float> plan(input.dimensions_vector(), {}, FFT::NORM_ORTHO);
    auto output = input.copy();
    plan.Forward(output, false);
    std::cout << "Orthonormal spectrum L2 norm: " << l2norm(output) << std::endl;
    plan.Backward(output, false);
    plan.Forward(output, false);
    plan.Backward(output, false);
    return output;
}

// 4. D4, two levels, 3D padding, different thresholds, and coarse-level skipping.
Array<std::complex<float>> d4_volume(
    const Array<std::complex<float>>& input, float threshold, bool skip_coarse) {
    std::cout << "[C++] d4_volume, threshold=" << threshold
              << ", skip_coarse=" << skip_coarse << std::endl;
    Wavelet<float> wavelet(
        input.dimensions(0), input.dimensions(1), input.dimensions(2), 2, false);
    auto coefficients = wavelet.forward_transform(input);
    std::cout << "Coefficient shape: " << coefficients.dimensions(0) << " x "
              << coefficients.dimensions(1) << " x " << coefficients.dimensions(2) << std::endl;
    wavelet.soft_threshold(coefficients, {threshold, threshold / 2.0f}, skip_coarse);
    return wavelet.inverse_transform(coefficients);
}

PYBIND11_MODULE(voxel_transform_options, m) {
    m.doc() = "FFT axes, centering, normalization, plan reuse, and multilevel 3D D4.";
    m.def("last_axis_fft", &last_axis_fft);
    m.def("centered_fft_2d", &centered_fft_2d);
    m.def("orthonormal_fft", &orthonormal_fft);
    m.def("unnormalized_roundtrip", &unnormalized_roundtrip);
    m.def("planned_roundtrip", &planned_roundtrip);
    m.def("d4_volume", &d4_volume);
}
