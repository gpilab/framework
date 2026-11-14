// Author: Guru Krishanmoorthy
// Date: Nov 2026

#include <torch/extension.h>
#include <c10/cuda/CUDAGuard.h>
#include <c10/cuda/CUDAStream.h>
#include <pybind11/complex.h>
#include <pybind11/iostream.h>

#include "cuda_scale.h"

#include <complex>
#include <iostream>

namespace py = pybind11;

// Raw CUDA pointers need normal, contiguous storage and cannot track gradients.
void check_input(const torch::Tensor& input) {
    TORCH_CHECK(input.is_cpu() || input.is_cuda(), "Use a CPU or CUDA tensor.");
    TORCH_CHECK(!input.requires_grad(), "These starter kernels do not support autograd.");
}

void check_inplace(const torch::Tensor& input) {
    check_input(input);
    TORCH_CHECK(input.is_contiguous() && !input.is_conj() && !input.is_neg(),
                "In-place CUDA examples require contiguous, non-conjugated storage.");
}

// 1. Integer kernel.
void scale_int_inplace(torch::Tensor input, int factor) {
    check_inplace(input);
    TORCH_CHECK(input.scalar_type() == torch::kInt32, "Use int32 input.");
    if (input.numel() == 0) return;
    std::cout << "[C++] integer kernel: " << input.device() << std::endl;
    if (input.is_cuda()) {
        c10::cuda::CUDAGuard guard(input.device());
        auto stream = c10::cuda::getCurrentCUDAStream(input.get_device()).stream();
        launch_int(input.data_ptr<int>(), input.numel(), factor, stream);
    } else {
        input.mul_(factor);
    }
}

torch::Tensor scale_int(torch::Tensor input, int factor) {
    check_input(input);
    auto output = input.contiguous().clone();
    scale_int_inplace(output, factor);
    return output;
}

// 2. Float kernel.
void scale_float_inplace(torch::Tensor input, float factor) {
    check_inplace(input);
    TORCH_CHECK(input.scalar_type() == torch::kFloat32, "Use float32 input.");
    if (input.numel() == 0) return;
    std::cout << "[C++] float kernel: " << input.device() << std::endl;
    if (input.is_cuda()) {
        c10::cuda::CUDAGuard guard(input.device());
        auto stream = c10::cuda::getCurrentCUDAStream(input.get_device()).stream();
        launch_float(input.data_ptr<float>(), input.numel(), factor, stream);
    } else {
        input.mul_(factor);
    }
}

torch::Tensor scale_float(torch::Tensor input, float factor) {
    check_input(input);
    auto output = input.contiguous().clone();
    scale_float_inplace(output, factor);
    return output;
}

// 3. Complex kernel.
void scale_complex_inplace(torch::Tensor input, std::complex<float> factor) {
    check_inplace(input);
    TORCH_CHECK(input.scalar_type() == torch::kComplexFloat, "Use complex64 input.");
    if (input.numel() == 0) return;
    std::cout << "[C++] complex kernel: " << input.device() << std::endl;
    if (input.is_cuda()) {
        c10::cuda::CUDAGuard guard(input.device());
        auto stream = c10::cuda::getCurrentCUDAStream(input.get_device()).stream();
        launch_complex(reinterpret_cast<float2*>(input.data_ptr<c10::complex<float>>()),
                       input.numel(), make_float2(factor.real(), factor.imag()), stream);
    } else {
        input.mul_(c10::complex<float>(factor.real(), factor.imag()));
    }
}

torch::Tensor scale_complex(torch::Tensor input, std::complex<float> factor) {
    check_input(input);
    auto output = input.contiguous().clone();
    scale_complex_inplace(output, factor);
    return output;
}

// 4. Template last: dispatch to float or double CUDA storage.
template <typename T>
void multiply_inplace(torch::Tensor input, T factor) {
    check_inplace(input);
    TORCH_CHECK(input.scalar_type() == torch::kFloat32 || input.scalar_type() == torch::kFloat64,
                "Use float32 or float64 input.");
    if (input.numel() == 0) return;
    if (input.is_cuda()) {
        c10::cuda::CUDAGuard guard(input.device());
        auto stream = c10::cuda::getCurrentCUDAStream(input.get_device()).stream();
        if (input.scalar_type() == torch::kFloat32) {
            launch_template_float(input.data_ptr<float>(), input.numel(), float(factor), stream);
        } else {
            launch_template_double(input.data_ptr<double>(), input.numel(), double(factor), stream);
        }
    } else {
        input.mul_(factor);
    }
}

template <typename T>
void scale_inplace(torch::Tensor input, T factor) {
    multiply_inplace(input, factor);
    if (input.numel() > 0) {
        std::cout << "[C++] template kernel: " << input.device() << std::endl;
    }
}

template <typename T>
torch::Tensor scale(torch::Tensor input, T factor) {
    check_input(input);
    auto output = input.contiguous().clone();
    scale_inplace(output, factor);
    return output;
}

PYBIND11_MODULE(cuda_basics, m) {
    m.doc() = "Beginner CUDA kernels, with LibTorch operations on CPU. No autograd.";
    m.def("scale_int", &scale_int, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_int_inplace", &scale_int_inplace, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_float", &scale_float, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_float_inplace", &scale_float_inplace, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_complex", &scale_complex, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_complex_inplace", &scale_complex_inplace, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale", &scale<double>, py::call_guard<py::scoped_ostream_redirect>());
    m.def("scale_inplace", &scale_inplace<double>, py::call_guard<py::scoped_ostream_redirect>());
    m.def("benchmark_scale_inplace", &multiply_inplace<double>);
}
