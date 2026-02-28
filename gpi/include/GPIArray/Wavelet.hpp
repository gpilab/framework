/**
 * @file Wavelet.hpp
 * @brief 2D Discrete Wavelet Transform (DWT) and Inverse DWT for complex images.
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
    mutable Array<ComplexT> buffer; 

    static uint64_t pow_2(uint64_t N) { return 1ULL << N; }

    static uint64_t compute_wavelet_size(uint64_t size, uint64_t levels) {
        if (size == 0) return 1;
        uint64_t Nq = static_cast<uint64_t>(2 * std::ceil(static_cast<double>(size) / static_cast<double>(pow_2(levels + 1))));
        return Nq * pow_2(levels);
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
    Wavelet(uint64_t image_size1_, uint64_t image_size2_, uint64_t levels_, bool use_d2_not_d4_ = false)
        : image_size1(image_size1_), image_size2(image_size2_), levels(levels_),
          wavelet_size1(compute_wavelet_size(image_size1_, levels_)),
          wavelet_size2(compute_wavelet_size(image_size2_, levels_)),
          use_d2_not_d4(use_d2_not_d4_),
          h(use_d2_not_d4 ? std::vector<T>{static_cast<T>(1.0 / std::sqrt(2.0)), static_cast<T>(1.0 / std::sqrt(2.0))}
                          : std::vector<T>{static_cast<T>((1.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                           static_cast<T>((3.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                           static_cast<T>((3.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                           static_cast<T>((1.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0)))}),
          g(use_d2_not_d4 ? std::vector<T>{static_cast<T>(1.0 / std::sqrt(2.0)), static_cast<T>(-1.0 / std::sqrt(2.0))}
                          : std::vector<T>{static_cast<T>((1.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                           static_cast<T>(-(3.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                           static_cast<T>((3.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                           static_cast<T>(-(1.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0)))}),
          buffer(wavelet_size1, wavelet_size2) {
        if (levels < 1) throw std::runtime_error("Number of levels must be at least 1");
        buffer.fill(ComplexT(0));
    }

    uint64_t get_wavelet_size1() const { return wavelet_size1; }
    uint64_t get_wavelet_size2() const { return wavelet_size2; }

    Array<ComplexT> forward_transform(const Array<ComplexT>& input) const {
        Array<ComplexT> padded(wavelet_size1, wavelet_size2);
        padded.fill(ComplexT(0));

        uint64_t offset1 = (wavelet_size1 - image_size1) / 2;
        uint64_t offset2 = (wavelet_size2 - image_size2) / 2;

        for (uint64_t i = 0; i < image_size1; ++i) {
            const ComplexT* __restrict src = input.get_data() + i * input.strides()[0];
            ComplexT* __restrict dst = padded.get_data() + (i + offset1) * padded.strides()[0] + offset2;
            std::memcpy(dst, src, image_size2 * sizeof(ComplexT));
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

    Array<ComplexT> inverse_transform(Array<ComplexT>& image) const {
        for (int64_t level = levels - 1; level >= 0; --level) {
            uint64_t n1 = wavelet_size1 >> level;
            uint64_t n2 = wavelet_size2 >> level;
            idwt2DLevel(image, n1, n2);
        }

        Array<ComplexT> cropped(image_size1, image_size2);
        uint64_t offset1 = (wavelet_size1 - image_size1) / 2;
        uint64_t offset2 = (wavelet_size2 - image_size2) / 2;

        for (uint64_t i = 0; i < image_size1; ++i) {
            const ComplexT* __restrict src = image.get_data() + (i + offset1) * image.strides()[0] + offset2;
            ComplexT* __restrict dst = cropped.get_data() + i * cropped.strides()[0];
            std::memcpy(dst, src, image_size2 * sizeof(ComplexT));
        }
        return cropped;
    }

    /**
     * @brief In-place Soft Thresholding using a vector of level-dependent thresholds.
     * tau_levels[0] is applied to the coarsest detail, tau_levels[levels-1] to the finest detail.
     */
    void soft_threshold(Array<ComplexT>& coeffs, const std::vector<T>& tau_levels, uint64_t skip_coarsest_levels = 0) const {
        if (tau_levels.size() != levels) {
            throw std::invalid_argument("taus vector size must match the number of wavelet levels.");
        }

        ComplexT* data = coeffs.get_data();
        uint64_t s1 = coeffs.strides()[0];

        auto threshold_block = [&](uint64_t r_start, uint64_t r_end, uint64_t c_start, uint64_t c_end, T tau) {
            if (tau <= static_cast<T>(0.0)) return; // Skip if threshold is zero
            for (uint64_t i = r_start; i < r_end; ++i) {
                ComplexT* __restrict row = data + i * s1;
                #pragma omp simd
                for (uint64_t j = c_start; j < c_end; ++j) {
                    T re = std::real(row[j]);
                    T im = std::imag(row[j]);
                    T mag = std::sqrt(re * re + im * im);
                    T scale = (mag > tau) ? (static_cast<T>(1.0) - tau / mag) : static_cast<T>(0.0);
                    row[j] = ComplexT(re * scale, im * scale); 
                }
            }
        };

        // Level 0 is the coarsest detail band (closest to the LL corner)
        // Level `levels - 1` is the finest detail band (the largest blocks)
        for (uint64_t lvl = 0; lvl < levels; ++lvl) {
            if (lvl < skip_coarsest_levels) continue;

            uint64_t step_up = levels - 1 - lvl; 
            uint64_t cur_size1 = wavelet_size1 >> step_up;
            uint64_t cur_size2 = wavelet_size2 >> step_up;
            uint64_t prev_size1 = cur_size1 >> 1;
            uint64_t prev_size2 = cur_size2 >> 1;

            T tau = tau_levels[lvl];

            // HL Block (Top-Right)
            threshold_block(0, prev_size1, prev_size2, cur_size2, tau);
            // LH Block (Bottom-Left)
            threshold_block(prev_size1, cur_size1, 0, prev_size2, tau);
            // HH Block (Bottom-Right)
            threshold_block(prev_size1, cur_size1, prev_size2, cur_size2, tau);
        }
    }
};

} // namespace GPIArray