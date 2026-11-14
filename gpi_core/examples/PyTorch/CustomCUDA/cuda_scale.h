// Author: Guru Krishanmoorthy
// Date: Nov 2026

#pragma once

#include <cuda_runtime.h>
#include <cstdint>

void launch_int(int* data, int64_t count, int factor, cudaStream_t stream);
void launch_float(float* data, int64_t count, float factor, cudaStream_t stream);
void launch_complex(float2* data, int64_t count, float2 factor, cudaStream_t stream);
void launch_template_float(float* data, int64_t count, float factor, cudaStream_t stream);
void launch_template_double(double* data, int64_t count, double factor, cudaStream_t stream);
