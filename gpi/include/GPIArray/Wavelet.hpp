/**
 * @file Wavelet.hpp
 * @brief 2D/3D Discrete Wavelet Transform (DWT) and Inverse DWT for complex images.
 * Optimized with Orthogonal Vectorization and Gather-IDWT for maximum SIMD throughput.
 * Exclusively supports Array<std::complex<T>> where T is float or double.
 */
#pragma once

#include "GPIArray/Array.hpp"
#include <cmath>
#include <stdexcept>
#include <vector>
#include <complex>
#include <type_traits>

namespace GPIArray {

template<typename T>
class Wavelet {
    static_assert(std::is_same_v<T, float> || std::is_same_v<T, double>,
                  "Wavelet template parameter T must be float or double. The class operates on Array<std::complex<T>>.");

public:
    using ComplexT = std::complex<T>;

private:
    const uint64_t image_size1;
    const uint64_t image_size2;
    const uint64_t levels;
    const uint64_t wavelet_size1;
    const uint64_t wavelet_size2;
    const bool use_d2_not_d4;
    const std::vector<T> h;
    const std::vector<T> g;
    const uint64_t image_size3;
    const uint64_t wavelet_size3;
    const bool is_3d;
    mutable Array<ComplexT> buffer; 

    static uint64_t pow_2(uint64_t N) { return 1ULL << N; }

    static uint64_t compute_wavelet_size(uint64_t size, uint64_t levels) {
        if (size == 0) return 1;
        uint64_t Nq = static_cast<uint64_t>(2 * std::ceil(static_cast<double>(size) / static_cast<double>(pow_2(levels + 1))));
        return Nq * pow_2(levels);
    }

    /**
     * @brief Performs one level of 3D Discrete Wavelet Transform.
     * Decomposes a volume of size (n1, n2, n3) into 8 octants.
     */
    void dwt3DLevel(Array<ComplexT>& volume, uint64_t n1, uint64_t n2, uint64_t n3) const {
        // 1. Process X and Y dimensions slice-by-slice
        for (uint64_t k = 0; k < n3; ++k) {
            auto slice = volume.slice(S::all(), S::all(), S(k));
            dwt2DLevel(slice, n1, n2);
        }

        // 2. Process the Z dimension (n3)
        ComplexT* img = volume.get_data();
        ComplexT* buf = buffer.get_data();
        uint64_t s1 = volume.strides()[0];
        uint64_t s2 = volume.strides()[1];
        uint64_t s3 = volume.strides()[2]; // Depth stride

        uint64_t half3 = n3 / 2;
        uint64_t flen = h.size();

        // Step A: Filter along Z from volume into the temporary buffer
        for (uint64_t i = 0; i < n1; ++i) {
            for (uint64_t j = 0; j < n2; ++j) {
                ComplexT* in_ptr = img + i * s1 + j * s2;
                ComplexT* out_ptr = buf + i * s1 + j * s2;

                if (flen == 4) { // D4 Filter
                    for (uint64_t k = 0; k < half3 - 1; ++k) {
                        ComplexT v0 = in_ptr[2 * k * s3],     v1 = in_ptr[(2 * k + 1) * s3];
                        ComplexT v2 = in_ptr[(2 * k + 2) * s3], v3 = in_ptr[(2 * k + 3) * s3];
                        out_ptr[k * s3]           = v0 * h[0] + v1 * h[1] + v2 * h[2] + v3 * h[3];
                        out_ptr[(k + half3) * s3] = v0 * g[0] + v1 * g[1] + v2 * g[2] + v3 * g[3];
                    }
                    // Handle periodic boundary for Z-axis
                    uint64_t k = half3 - 1;
                    ComplexT v0 = in_ptr[2 * k * s3], v1 = in_ptr[(2 * k + 1) * s3];
                    ComplexT v2 = in_ptr[0],          v3 = in_ptr[1 * s3];
                    out_ptr[k * s3]           = v0 * h[0] + v1 * h[1] + v2 * h[2] + v3 * h[3];
                    out_ptr[(k + half3) * s3] = v0 * g[0] + v1 * g[1] + v2 * g[2] + v3 * g[3];
                } else { // D2/Haar Filter
                    for (uint64_t k = 0; k < half3; ++k) {
                        ComplexT v0 = in_ptr[2 * k * s3], v1 = in_ptr[(2 * k + 1) * s3];
                        out_ptr[k * s3]           = v0 * h[0] + v1 * h[1];
                        out_ptr[(k + half3) * s3] = v0 * g[0] + v1 * g[1];
                    }
                }
            }
        }

        // Step B: Copy the Z-filtered results from buffer back to the volume
        uint64_t total_elements = n1 * n2 * n3;
        for (uint64_t idx = 0; idx < total_elements; ++idx) {
            img[idx] = buf[idx];
        }
    }

    /**
     * @brief Performs one level of 3D Inverse Discrete Wavelet Transform.
     */
    void idwt3DLevel(Array<ComplexT>& volume, uint64_t n1, uint64_t n2, uint64_t n3) const {
        ComplexT* img = volume.get_data();
        ComplexT* buf = buffer.get_data();
        uint64_t s1 = volume.strides()[0];
        uint64_t s2 = volume.strides()[1];
        uint64_t s3 = volume.strides()[2]; // Stride for the third axis (Z)

        uint64_t half3 = n3 / 2;
        uint64_t flen = h.size();

        // --- PHASE 1: Inverse Transform along the Z-axis ---
        for (uint64_t i = 0; i < n1; ++i) {
            for (uint64_t j = 0; j < n2; ++j) {
                ComplexT* in_ptr = img + i * s1 + j * s2;
                ComplexT* out_ptr = buf + i * s1 + j * s2;

                if (flen == 4) { // D4 Filter logic
                    uint64_t k0 = 0, kp = half3 - 1;
                    ComplexT l0 = in_ptr[k0 * s3],         h0_v = in_ptr[(k0 + half3) * s3];
                    ComplexT lp = in_ptr[kp * s3],         hp = in_ptr[(kp + half3) * s3];
                    out_ptr[(2 * k0) * s3]     = l0 * h[0] + h0_v * g[0] + lp * h[2] + hp * g[2];
                    out_ptr[(2 * k0 + 1) * s3] = l0 * h[1] + h0_v * g[1] + lp * h[3] + hp * g[3];

                    for (uint64_t k = 1; k < half3; ++k) {
                        ComplexT lk = in_ptr[k * s3],       hk = in_ptr[(k + half3) * s3];
                        ComplexT lq = in_ptr[(k - 1) * s3], hq = in_ptr[(k - 1 + half3) * s3];
                        out_ptr[(2 * k) * s3]     = lk * h[0] + hk * g[0] + lq * h[2] + hq * g[2];
                        out_ptr[(2 * k + 1) * s3] = lk * h[1] + hk * g[1] + lq * h[3] + hq * g[3];
                    }
                } else { // D2/Haar Filter logic
                    for (uint64_t k = 0; k < half3; ++k) {
                        ComplexT lk = in_ptr[k * s3];
                        ComplexT hk = in_ptr[(k + half3) * s3];
                        out_ptr[(2 * k) * s3]     = lk * h[0] + hk * g[0];
                        out_ptr[(2 * k + 1) * s3] = lk * h[1] + hk * g[1];
                    }
                }
            }
        }

        uint64_t total_elements = n1 * n2 * n3;
        for (uint64_t idx = 0; idx < total_elements; ++idx) {
            img[idx] = buf[idx];
        }

        // --- PHASE 2: Inverse Transform on each 2D Slice (X-Y) ---
        for (uint64_t k = 0; k < n3; ++k) {
            auto slice = volume.slice(S::all(), S::all(), S(k));
            idwt2DLevel(slice, n1, n2);
        }
    }

    void dwt2DLevel(Array<ComplexT>& image, uint64_t n1, uint64_t n2) const {
        ComplexT* img = image.get_data();
        ComplexT* buf = buffer.get_data();
        uint64_t s1 = image.strides()[0]; 
        uint64_t s2 = image.strides()[1]; 

        uint64_t half2 = n2 / 2;
        uint64_t half1 = n1 / 2;
        uint64_t flen = h.size();

        if (flen == 4) {
            for (uint64_t i = 0; i < n1; ++i) {
                ComplexT* in_row = img + i * s1;
                ComplexT* out_row = buf + i * s1;
                #pragma omp simd
                for (uint64_t j = 0; j < half2 - 1; ++j) {
                    ComplexT v0 = in_row[2*j * s2],     v1 = in_row[(2*j+1) * s2];
                    ComplexT v2 = in_row[(2*j+2) * s2], v3 = in_row[(2*j+3) * s2];
                    out_row[j * s2]         = v0 * h[0] + v1 * h[1] + v2 * h[2] + v3 * h[3];
                    out_row[(j+half2) * s2] = v0 * g[0] + v1 * g[1] + v2 * g[2] + v3 * g[3];
                }
                uint64_t j = half2 - 1;
                ComplexT v0 = in_row[2*j * s2], v1 = in_row[(2*j+1) * s2];
                ComplexT v2 = in_row[0],        v3 = in_row[1 * s2];
                out_row[j * s2]         = v0 * h[0] + v1 * h[1] + v2 * h[2] + v3 * h[3];
                out_row[(j+half2) * s2] = v0 * g[0] + v1 * g[1] + v2 * g[2] + v3 * g[3];
            }
        } else {
            for (uint64_t i = 0; i < n1; ++i) {
                ComplexT* in_row = img + i * s1;
                ComplexT* out_row = buf + i * s1;
                #pragma omp simd
                for (uint64_t j = 0; j < half2; ++j) {
                    ComplexT v0 = in_row[2*j * s2], v1 = in_row[(2*j+1) * s2];
                    out_row[j * s2]         = v0 * h[0] + v1 * h[1];
                    out_row[(j+half2) * s2] = v0 * g[0] + v1 * g[1];
                }
            }
        }

        if (flen == 4) {
            for (uint64_t i = 0; i < half1 - 1; ++i) {
                ComplexT* in_r0 = buf + (2*i) * s1;   ComplexT* in_r1 = buf + (2*i+1) * s1;
                ComplexT* in_r2 = buf + (2*i+2) * s1; ComplexT* in_r3 = buf + (2*i+3) * s1;
                ComplexT* out_L = img + i * s1;       ComplexT* out_H = img + (i+half1) * s1;
                #pragma omp simd
                for (uint64_t j = 0; j < n2; ++j) {
                    ComplexT v0 = in_r0[j * s2], v1 = in_r1[j * s2];
                    ComplexT v2 = in_r2[j * s2], v3 = in_r3[j * s2];
                    out_L[j * s2] = v0 * h[0] + v1 * h[1] + v2 * h[2] + v3 * h[3];
                    out_H[j * s2] = v0 * g[0] + v1 * g[1] + v2 * g[2] + v3 * g[3];
                }
            }
            uint64_t i = half1 - 1;
            ComplexT* in_r0 = buf + (2*i) * s1;   ComplexT* in_r1 = buf + (2*i+1) * s1;
            ComplexT* in_r2 = buf + 0;            ComplexT* in_r3 = buf + 1 * s1;
            ComplexT* out_L = img + i * s1;       ComplexT* out_H = img + (i+half1) * s1;
            #pragma omp simd
            for (uint64_t j = 0; j < n2; ++j) {
                ComplexT v0 = in_r0[j * s2], v1 = in_r1[j * s2];
                ComplexT v2 = in_r2[j * s2], v3 = in_r3[j * s2];
                out_L[j * s2] = v0 * h[0] + v1 * h[1] + v2 * h[2] + v3 * h[3];
                out_H[j * s2] = v0 * g[0] + v1 * g[1] + v2 * g[2] + v3 * g[3];
            }
        } else {
             for (uint64_t i = 0; i < half1; ++i) {
                ComplexT* in_r0 = buf + (2*i) * s1;   ComplexT* in_r1 = buf + (2*i+1) * s1;
                ComplexT* out_L = img + i * s1;       ComplexT* out_H = img + (i+half1) * s1;
                #pragma omp simd
                for (uint64_t j = 0; j < n2; ++j) {
                    ComplexT v0 = in_r0[j * s2], v1 = in_r1[j * s2];
                    out_L[j * s2] = v0 * h[0] + v1 * h[1];
                    out_H[j * s2] = v0 * g[0] + v1 * g[1];
                }
            }
        }
    }

    void idwt2DLevel(Array<ComplexT>& image, uint64_t n1, uint64_t n2) const {
        ComplexT* img = image.get_data();
        ComplexT* buf = buffer.get_data();
        uint64_t s1 = image.strides()[0];
        uint64_t s2 = image.strides()[1];
        uint64_t half1 = n1 / 2;
        uint64_t half2 = n2 / 2;
        uint64_t flen = h.size();

        if (flen == 4) {
            uint64_t i0 = 0, ip = half1 - 1; 
            ComplexT* L_0 = img + i0 * s1; ComplexT* H_0 = img + (i0 + half1) * s1;
            ComplexT* L_p = img + ip * s1; ComplexT* H_p = img + (ip + half1) * s1;
            ComplexT* out_r0 = buf + (2*i0) * s1; ComplexT* out_r1 = buf + (2*i0+1) * s1;
            #pragma omp simd
            for (uint64_t j = 0; j < n2; ++j) {
                ComplexT l0 = L_0[j*s2], h0_v = H_0[j*s2], lp = L_p[j*s2], hp = H_p[j*s2];
                out_r0[j*s2] = l0 * h[0] + h0_v * g[0] + lp * h[2] + hp * g[2];
                out_r1[j*s2] = l0 * h[1] + h0_v * g[1] + lp * h[3] + hp * g[3];
            }
            for (uint64_t i = 1; i < half1; ++i) {
                ComplexT* L_i = img + i * s1;         ComplexT* H_i = img + (i + half1) * s1;
                ComplexT* L_q = img + (i - 1) * s1;   ComplexT* H_q = img + (i - 1 + half1) * s1;
                ComplexT* o_r0 = buf + (2*i) * s1;    ComplexT* o_r1 = buf + (2*i+1) * s1;
                #pragma omp simd
                for (uint64_t j = 0; j < n2; ++j) {
                    ComplexT li = L_i[j*s2], hi = H_i[j*s2], lq = L_q[j*s2], hq = H_q[j*s2];
                    o_r0[j*s2] = li * h[0] + hi * g[0] + lq * h[2] + hq * g[2];
                    o_r1[j*s2] = li * h[1] + hi * g[1] + lq * h[3] + hq * g[3];
                }
            }
        } else {
            for (uint64_t i = 0; i < half1; ++i) {
                ComplexT* L_i = img + i * s1;      ComplexT* H_i = img + (i + half1) * s1;
                ComplexT* out_r0 = buf + (2*i) * s1; ComplexT* out_r1 = buf + (2*i+1) * s1;
                #pragma omp simd
                for (uint64_t j = 0; j < n2; ++j) {
                    out_r0[j*s2] = L_i[j*s2] * h[0] + H_i[j*s2] * g[0];
                    out_r1[j*s2] = L_i[j*s2] * h[1] + H_i[j*s2] * g[1];
                }
            }
        }

        if (flen == 4) {
            for (uint64_t i = 0; i < n1; ++i) {
                ComplexT* in_row = buf + i * s1; ComplexT* out_row = img + i * s1;
                uint64_t j0 = 0, jp = half2 - 1;
                ComplexT l0 = in_row[j0*s2], h0_v = in_row[(j0+half2)*s2], lp = in_row[jp*s2], hp = in_row[(jp+half2)*s2];
                out_row[(2*j0)*s2]   = l0 * h[0] + h0_v * g[0] + lp * h[2] + hp * g[2];
                out_row[(2*j0+1)*s2] = l0 * h[1] + h0_v * g[1] + lp * h[3] + hp * g[3];
                #pragma omp simd
                for (uint64_t j = 1; j < half2; ++j) {
                    ComplexT lj = in_row[j*s2], hj = in_row[(j+half2)*s2], lq = in_row[(j-1)*s2], hq = in_row[(j-1+half2)*s2];
                    out_row[(2*j)*s2]   = lj * h[0] + hj * g[0] + lq * h[2] + hq * g[2];
                    out_row[(2*j+1)*s2] = lj * h[1] + hj * g[1] + lq * h[3] + hq * g[3];
                }
            }
        } else {
            for (uint64_t i = 0; i < n1; ++i) {
                ComplexT* in_row = buf + i * s1; ComplexT* out_row = img + i * s1;
                #pragma omp simd
                for (uint64_t j = 0; j < half2; ++j) {
                    ComplexT lj = in_row[j*s2], hj = in_row[(j+half2)*s2];
                    out_row[(2*j)*s2]   = lj * h[0] + hj * g[0];
                    out_row[(2*j+1)*s2] = lj * h[1] + hj * g[1];
                }
            }
        }
    }

public:
    // --- 2D CONSTRUCTOR (Drop-in compatibility) ---
    Wavelet(uint64_t image_size1_, uint64_t image_size2_, uint64_t levels_, bool use_d2_not_d4_ = false)
        : image_size1(image_size1_), image_size2(image_size2_), levels(levels_),
          wavelet_size1(compute_wavelet_size(image_size1_, levels_)),
          wavelet_size2(compute_wavelet_size(image_size2_, levels_)),
          use_d2_not_d4(use_d2_not_d4_),
          h(use_d2_not_d4_ ? std::vector<T>{static_cast<T>(1.0 / std::sqrt(2.0)), static_cast<T>(1.0 / std::sqrt(2.0))}
                           : std::vector<T>{static_cast<T>((1.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>((3.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>((3.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>((1.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0)))}),
          g(use_d2_not_d4_ ? std::vector<T>{static_cast<T>(1.0 / std::sqrt(2.0)), static_cast<T>(-1.0 / std::sqrt(2.0))}
                           : std::vector<T>{static_cast<T>((1.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>(-(3.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>((3.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>(-(1.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0)))}),
          image_size3(1), wavelet_size3(1), is_3d(false),
          buffer(wavelet_size1, wavelet_size2) {
        if (levels < 1) throw std::runtime_error("Number of levels must be at least 1");
        buffer.fill(ComplexT(0));
    }

    // --- 3D CONSTRUCTOR ---
    Wavelet(uint64_t image_size1_, uint64_t image_size2_, uint64_t image_size3_, uint64_t levels_, bool use_d2_not_d4_ = false)
        : image_size1(image_size1_), image_size2(image_size2_), levels(levels_),
          wavelet_size1(compute_wavelet_size(image_size1_, levels_)),
          wavelet_size2(compute_wavelet_size(image_size2_, levels_)),
          use_d2_not_d4(use_d2_not_d4_),
          h(use_d2_not_d4_ ? std::vector<T>{static_cast<T>(1.0 / std::sqrt(2.0)), static_cast<T>(1.0 / std::sqrt(2.0))}
                           : std::vector<T>{static_cast<T>((1.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>((3.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>((3.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>((1.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0)))}),
          g(use_d2_not_d4_ ? std::vector<T>{static_cast<T>(1.0 / std::sqrt(2.0)), static_cast<T>(-1.0 / std::sqrt(2.0))}
                           : std::vector<T>{static_cast<T>((1.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>(-(3.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>((3.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                            static_cast<T>(-(1.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0)))}),
          image_size3(image_size3_), wavelet_size3(compute_wavelet_size(image_size3_, levels_)),
          is_3d(true),
          buffer(wavelet_size1, wavelet_size2, wavelet_size3) {
        if (levels < 1) throw std::runtime_error("Number of levels must be at least 1");
        buffer.fill(ComplexT(0));
    }

    uint64_t get_wavelet_size1() const { return wavelet_size1; }
    uint64_t get_wavelet_size2() const { return wavelet_size2; }
    uint64_t get_wavelet_size3() const { return wavelet_size3; } 

    Array<ComplexT> forward_transform(const Array<ComplexT>& input) const {
        if (is_3d) {
            Array<ComplexT> padded(wavelet_size1, wavelet_size2, wavelet_size3);
            padded.fill(ComplexT(0));

            uint64_t offset1 = (wavelet_size1 - image_size1) / 2;
            uint64_t offset2 = (wavelet_size2 - image_size2) / 2;
            uint64_t offset3 = (wavelet_size3 - image_size3) / 2;

            uint64_t s1_in = input.strides()[0];
            uint64_t s2_in = input.strides()[1];
            uint64_t s3_in = input.strides()[2]; // Using actual stride for safe memory access
            
            uint64_t s1_pad = padded.strides()[0];
            uint64_t s2_pad = padded.strides()[1];
            uint64_t s3_pad = padded.strides()[2]; 

            for (uint64_t i = 0; i < image_size1; ++i) {
                for (uint64_t j = 0; j < image_size2; ++j) {
                    const ComplexT* __restrict src = input.get_data() + i * s1_in + j * s2_in;
                    ComplexT* __restrict dst = padded.get_data() + (i + offset1) * s1_pad + (j + offset2) * s2_pad + offset3 * s3_pad;
                    
                    // Replaced std::memcpy with stride-aware 1D loop
                    for (uint64_t k = 0; k < image_size3; ++k) {
                        dst[k * s3_pad] = src[k * s3_in];
                    }
                }
            }

            uint64_t current_size1 = wavelet_size1;
            uint64_t current_size2 = wavelet_size2;
            uint64_t current_size3 = wavelet_size3;
            for (uint64_t level = 0; level < levels; ++level) {
                dwt3DLevel(padded, current_size1, current_size2, current_size3);
                current_size1 /= 2;
                current_size2 /= 2;
                current_size3 /= 2;
            }
            return padded;
        } else {
            Array<ComplexT> padded(wavelet_size1, wavelet_size2);
            padded.fill(ComplexT(0));

            uint64_t offset1 = (wavelet_size1 - image_size1) / 2;
            uint64_t offset2 = (wavelet_size2 - image_size2) / 2;

            uint64_t s1_in = input.strides()[0];
            uint64_t s2_in = input.strides()[1];
            
            uint64_t s1_pad = padded.strides()[0];
            uint64_t s2_pad = padded.strides()[1];

            for (uint64_t i = 0; i < image_size1; ++i) {
                const ComplexT* __restrict src = input.get_data() + i * s1_in;
                ComplexT* __restrict dst = padded.get_data() + (i + offset1) * s1_pad + offset2 * s2_pad;
                
                // Replaced std::memcpy with stride-aware 1D loop
                for (uint64_t j = 0; j < image_size2; ++j) {
                    dst[j * s2_pad] = src[j * s2_in];
                }
            }

            uint64_t current_size1 = wavelet_size1;
            uint64_t current_size2 = wavelet_size2;
            for (uint64_t level = 0; level < levels; ++level) {
                dwt2DLevel(padded, current_size1, current_size2);
                current_size1 /= 2;
                current_size2 /= 2;
            }
            return padded;
        }
    }

    Array<ComplexT> inverse_transform(Array<ComplexT>& image) const {
        if (is_3d) {
            for (int64_t level = levels - 1; level >= 0; --level) {
                uint64_t n1 = wavelet_size1 >> level;
                uint64_t n2 = wavelet_size2 >> level;
                uint64_t n3 = wavelet_size3 >> level;
                idwt3DLevel(image, n1, n2, n3);
            }

            Array<ComplexT> cropped(image_size1, image_size2, image_size3);
            uint64_t offset1 = (wavelet_size1 - image_size1) / 2;
            uint64_t offset2 = (wavelet_size2 - image_size2) / 2;
            uint64_t offset3 = (wavelet_size3 - image_size3) / 2;

            uint64_t s1_img = image.strides()[0];
            uint64_t s2_img = image.strides()[1];
            uint64_t s3_img = image.strides()[2];
            
            uint64_t s1_crop = cropped.strides()[0];
            uint64_t s2_crop = cropped.strides()[1];
            uint64_t s3_crop = cropped.strides()[2];

            for (uint64_t i = 0; i < image_size1; ++i) {
                for (uint64_t j = 0; j < image_size2; ++j) {
                    const ComplexT* __restrict src = image.get_data() + (i + offset1) * s1_img + (j + offset2) * s2_img + offset3 * s3_img;
                    ComplexT* __restrict dst = cropped.get_data() + i * s1_crop + j * s2_crop;
                    
                    // Replaced std::memcpy with stride-aware 1D loop
                    for (uint64_t k = 0; k < image_size3; ++k) {
                        dst[k * s3_crop] = src[k * s3_img];
                    }
                }
            }
            return cropped;

        } else {
            for (int64_t level = levels - 1; level >= 0; --level) {
                uint64_t n1 = wavelet_size1 >> level;
                uint64_t n2 = wavelet_size2 >> level;
                idwt2DLevel(image, n1, n2);
            }

            Array<ComplexT> cropped(image_size1, image_size2);
            uint64_t offset1 = (wavelet_size1 - image_size1) / 2;
            uint64_t offset2 = (wavelet_size2 - image_size2) / 2;

            uint64_t s1_img = image.strides()[0];
            uint64_t s2_img = image.strides()[1];
            
            uint64_t s1_crop = cropped.strides()[0];
            uint64_t s2_crop = cropped.strides()[1];

            for (uint64_t i = 0; i < image_size1; ++i) {
                const ComplexT* __restrict src = image.get_data() + (i + offset1) * s1_img + offset2 * s2_img;
                ComplexT* __restrict dst = cropped.get_data() + i * s1_crop;
                
                // Replaced std::memcpy with stride-aware 1D loop
                for (uint64_t j = 0; j < image_size2; ++j) {
                    dst[j * s2_crop] = src[j * s2_img];
                }
            }
            return cropped;
        }
    }

    /**
     * @brief In-place Soft Thresholding using a vector of level-dependent thresholds.
     * Works natively across 2D (3 octants) and 3D (7 octants). 
     */
    void soft_threshold(Array<ComplexT>& coeffs, const std::vector<T>& tau_levels, uint64_t skip_coarsest_levels = 0) const {
        if (tau_levels.size() != levels) {
            throw std::invalid_argument("taus vector size must match the number of wavelet levels.");
        }

        ComplexT* data = coeffs.get_data();
        uint64_t s1 = coeffs.strides()[0];
        uint64_t s2 = coeffs.strides()[1];

        if (is_3d) {
            uint64_t s3 = coeffs.strides()[2]; // Added explicit stride for Z-axis
            auto threshold_block_3d = [&](uint64_t r_start, uint64_t r_end, uint64_t c_start, uint64_t c_end, uint64_t z_start, uint64_t z_end, T tau) {
                if (tau <= static_cast<T>(0.0)) return;
                for (uint64_t i = r_start; i < r_end; ++i) {
                    for (uint64_t j = c_start; j < c_end; ++j) {
                        ComplexT* __restrict row = data + i * s1 + j * s2;
                        #pragma omp simd
                        for (uint64_t k = z_start; k < z_end; ++k) {
                            // Using the explicit Z-stride
                            T re = std::real(row[k * s3]);
                            T im = std::imag(row[k * s3]);
                            T mag = std::sqrt(re * re + im * im);
                            T scale = (mag > tau) ? (static_cast<T>(1.0) - tau / mag) : static_cast<T>(0.0);
                            row[k * s3] = ComplexT(re * scale, im * scale); 
                        }
                    }
                }
            };

            for (uint64_t lvl = 0; lvl < levels; ++lvl) {
                if (lvl < skip_coarsest_levels) continue;

                uint64_t step_up = levels - 1 - lvl; 
                uint64_t cur_s1 = wavelet_size1 >> step_up;
                uint64_t cur_s2 = wavelet_size2 >> step_up;
                uint64_t cur_s3 = wavelet_size3 >> step_up;
                uint64_t prev_s1 = cur_s1 >> 1;
                uint64_t prev_s2 = cur_s2 >> 1;
                uint64_t prev_s3 = cur_s3 >> 1;

                T tau = tau_levels[lvl];

                // 7 Detail Octants
                threshold_block_3d(0, prev_s1, 0, prev_s2, prev_s3, cur_s3, tau); // L L H
                threshold_block_3d(0, prev_s1, prev_s2, cur_s2, 0, prev_s3, tau); // L H L
                threshold_block_3d(0, prev_s1, prev_s2, cur_s2, prev_s3, cur_s3, tau); // L H H
                threshold_block_3d(prev_s1, cur_s1, 0, prev_s2, 0, prev_s3, tau); // H L L
                threshold_block_3d(prev_s1, cur_s1, 0, prev_s2, prev_s3, cur_s3, tau); // H L H
                threshold_block_3d(prev_s1, cur_s1, prev_s2, cur_s2, 0, prev_s3, tau); // H H L
                threshold_block_3d(prev_s1, cur_s1, prev_s2, cur_s2, prev_s3, cur_s3, tau); // H H H
            }

        } else {
            auto threshold_block = [&](uint64_t r_start, uint64_t r_end, uint64_t c_start, uint64_t c_end, T tau) {
                if (tau <= static_cast<T>(0.0)) return; 
                for (uint64_t i = r_start; i < r_end; ++i) {
                    ComplexT* __restrict row = data + i * s1;
                    #pragma omp simd
                    for (uint64_t j = c_start; j < c_end; ++j) {
                        T re = std::real(row[j * s2]);
                        T im = std::imag(row[j * s2]);
                        T mag = std::sqrt(re * re + im * im);
                        T scale = (mag > tau) ? (static_cast<T>(1.0) - tau / mag) : static_cast<T>(0.0);
                        row[j * s2] = ComplexT(re * scale, im * scale); 
                    }
                }
            };

            for (uint64_t lvl = 0; lvl < levels; ++lvl) {
                if (lvl < skip_coarsest_levels) continue;

                uint64_t step_up = levels - 1 - lvl; 
                uint64_t cur_size1 = wavelet_size1 >> step_up;
                uint64_t cur_size2 = wavelet_size2 >> step_up;
                uint64_t prev_size1 = cur_size1 >> 1;
                uint64_t prev_size2 = cur_size2 >> 1;

                T tau = tau_levels[lvl];

                threshold_block(0, prev_size1, prev_size2, cur_size2, tau); // HL
                threshold_block(prev_size1, cur_size1, 0, prev_size2, tau); // LH
                threshold_block(prev_size1, cur_size1, prev_size2, cur_size2, tau); // HH
            }
        }
    }
};


// Abstract Base Class
class IWaveletDenoiser {
public:
    using Complex = std::complex<double>;
    
    virtual ~IWaveletDenoiser() = default; // Essential for virtual classes

    // Pure virtual function
    virtual Array<Complex> denoise(const Array<Complex>& x, 
                                   double tau_scale = 1.0, 
                                   bool cycle_spinning = true) const = 0;

    virtual void print_channel_level_taus() const = 0; // Pure virtual for printing tau values
};

} // namespace GPIArray