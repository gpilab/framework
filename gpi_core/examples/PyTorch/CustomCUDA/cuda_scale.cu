// Author: Guru Krishanmoorthy
// Date: Nov 2026

#include "cuda_scale.h"

#include <algorithm>
#include <stdexcept>
#include <string>

// Each thread starts at a different element, then steps by the total thread count.
__global__ void integer_kernel(int* data, int64_t count, int factor) {
    for (int64_t i = int64_t(blockIdx.x) * blockDim.x + threadIdx.x;
         i < count; i += int64_t(blockDim.x) * gridDim.x) {
        data[i] *= factor;
    }
}

__global__ void float_kernel(float* data, int64_t count, float factor) {
    for (int64_t i = int64_t(blockIdx.x) * blockDim.x + threadIdx.x;
         i < count; i += int64_t(blockDim.x) * gridDim.x) {
        data[i] *= factor;
    }
}

// float2 stores the real and imaginary components.
__global__ void complex_kernel(float2* data, int64_t count, float2 factor) {
    for (int64_t i = int64_t(blockIdx.x) * blockDim.x + threadIdx.x;
         i < count; i += int64_t(blockDim.x) * gridDim.x) {
        float real = data[i].x;
        float imag = data[i].y;
        data[i] = make_float2(real * factor.x - imag * factor.y,
                             real * factor.y + imag * factor.x);
    }
}

// Template last: the same kernel can scale float or double storage.
template <typename T>
__global__ void template_kernel(T* data, int64_t count, T factor) {
    for (int64_t i = int64_t(blockIdx.x) * blockDim.x + threadIdx.x;
         i < count; i += int64_t(blockDim.x) * gridDim.x) {
        data[i] *= factor;
    }
}

int blocks(int64_t count) {
    return int(std::min<int64_t>((count + 255) / 256, 65535));
}

void check_launch() {
    auto error = cudaGetLastError();
    if (error != cudaSuccess) {
        throw std::runtime_error(std::string("CUDA scale launch: ") + cudaGetErrorString(error));
    }
}

void launch_int(int* data, int64_t count, int factor, cudaStream_t stream) {
    integer_kernel<<<blocks(count), 256, 0, stream>>>(data, count, factor);
    check_launch();
}

void launch_float(float* data, int64_t count, float factor, cudaStream_t stream) {
    float_kernel<<<blocks(count), 256, 0, stream>>>(data, count, factor);
    check_launch();
}

void launch_complex(float2* data, int64_t count, float2 factor, cudaStream_t stream) {
    complex_kernel<<<blocks(count), 256, 0, stream>>>(data, count, factor);
    check_launch();
}

void launch_template_float(float* data, int64_t count, float factor, cudaStream_t stream) {
    template_kernel<float><<<blocks(count), 256, 0, stream>>>(data, count, factor);
    check_launch();
}

void launch_template_double(double* data, int64_t count, double factor, cudaStream_t stream) {
    template_kernel<double><<<blocks(count), 256, 0, stream>>>(data, count, factor);
    check_launch();
}
