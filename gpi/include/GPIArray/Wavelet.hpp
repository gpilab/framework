#pragma once

#include "Array.hpp"
#include <cmath>
#include <stdexcept>
#include <vector>
#include <complex>
#include <type_traits> // Required for std::is_same_v and std::conditional_t

namespace GPIArray {

template<typename T>
class Wavelet {
private:
    // Define RealPrecisionType based on T
    using RealPrecisionType = typename std::conditional_t<
        std::is_same_v<T, std::complex<float>> || std::is_same_v<T, float>,
        float,
        double
    >;

    // Restrict T to float, double, std::complex<float> or std::complex<double>
    static_assert(
        std::is_same_v<T, float> ||
        std::is_same_v<T, double> ||
        std::is_same_v<T, std::complex<float>> ||
        std::is_same_v<T, std::complex<double>>,
        "Wavelet only supports float, double, std::complex<float> or std::complex<double>"
    );

    const uint64_t image_size1;  // Original image size, direction 1
    const uint64_t image_size2;  // Original image size, direction 2
    const uint64_t levels;       // Number of DWT levels
    const uint64_t wavelet_size1; // Computed power of 2, direction 1
    const uint64_t wavelet_size2; // Computed power of 2, direction 2
    const bool use_d2_not_d4;    // Use Haar (D2) instead of D4
    const std::vector<RealPrecisionType> h;      // Low-pass filter coefficients
    const std::vector<RealPrecisionType> g;      // High-pass filter coefficients
    mutable Array<T> buffer;      // Internal buffer for transforms, mutable for const methods

    // Helper to calculate 2^N for integer N
    static uint64_t pow_2(uint64_t N) {
        return 1ULL << N;
    }

    // Compute wavelet size based on the WaveletComp logic
    static uint64_t compute_wavelet_size(uint64_t size, uint64_t levels) {
        if (size == 0) return 1;
        // This logic matches the WaveletComp implementation.
        // It finds a size that is a multiple of 2^levels and ensures
        // the coarsest level (Nq) is even.
        uint64_t Nq = static_cast<uint64_t>(2 * std::ceil(static_cast<double>(size) / static_cast<double>(pow_2(levels + 1))));
        return Nq * pow_2(levels);
    }

    // Helper for periodic indexing
    int64_t mod(int64_t a, int64_t n) const {
        return (a % n + n) % n;
    }

    // 1D DWT for a single row/column
    void dwt1D(const Array<T>& input, Array<T>& output, uint64_t n) const {
        if (n < 4) { // D4 requires at least 4 points
            // For smaller sizes, just copy input to output to avoid errors
            for(uint64_t i = 0; i < n; ++i) output(i) = input(i);
            return;
        }
        if (input.size() != n || output.size() != n) {
            throw std::runtime_error("Input/output size mismatch in 1D DWT");
        }

        uint64_t half = n / 2;
        for (uint64_t i = 0; i < half; ++i) {
            T low = T(0), high = T(0); // Initialize with T(0) for both real and complex types
            for (uint64_t k = 0; k < h.size(); ++k) {
                int64_t idx = mod(2 * i + k, n);
                low += static_cast<T>(h[k]) * input(idx); // Cast h[k] to T
                high += static_cast<T>(g[k]) * input(idx); // Cast g[k] to T
            }
            output(i) = low;
            output(i + half) = high;
        }
    }

    // 1D IDWT for a single row/column
    void idwt1D(const Array<T>& input, Array<T>& output, uint64_t n) const {
        if (n < 4) { // D4 requires at least 4 points
             // For smaller sizes, just copy input to output to avoid errors
            for(uint64_t i = 0; i < n; ++i) output(i) = input(i);
            return;
        }
        if (input.size() != n || output.size() != n) {
            throw std::runtime_error("Input/output size mismatch in 1D IDWT");
        }

        output.fill(T(0)); // Initialize with T(0) for both real and complex types
        uint64_t half = n / 2;
        for (uint64_t i = 0; i < half; ++i) {
            for (uint64_t k = 0; k < h.size(); ++k) {
                int64_t out_idx = mod(2 * i + k, n);
                // Cast h[k] and g[k] to T before multiplication
                output(out_idx) += static_cast<T>(h[k]) * input(i);
                output(out_idx) += static_cast<T>(g[k]) * input(i + half);
            }
        }
    }


    // 2D DWT for one level
    void dwt2DLevel(Array<T>& image, uint64_t n1, uint64_t n2) const {
        Array<T> temp_row_in(n2);
        Array<T> temp_row_out(n2);
        
        // Rows
        for (uint64_t i = 0; i < n1; ++i) {
            for (uint64_t j = 0; j < n2; ++j) temp_row_in(j) = image(i, j);
            dwt1D(temp_row_in, temp_row_out, n2);
            for (uint64_t j = 0; j < n2; ++j) buffer(i, j) = temp_row_out(j);
        }

        Array<T> temp_col_in(n1);
        Array<T> temp_col_out(n1);

        // Columns
        for (uint64_t j = 0; j < n2; ++j) {
            for (uint64_t i = 0; i < n1; ++i) temp_col_in(i) = buffer(i, j);
            dwt1D(temp_col_in, temp_col_out, n1);
            for (uint64_t i = 0; i < n1; ++i) image(i, j) = temp_col_out(i);
        }
    }

    // 2D IDWT for one level
    void idwt2DLevel(Array<T>& image, uint64_t n1, uint64_t n2) const {
        Array<T> temp_col_in(n1);
        Array<T> temp_col_out(n1);
        
        // Columns
        for (uint64_t j = 0; j < n2; ++j) {
            for (uint64_t i = 0; i < n1; ++i) temp_col_in(i) = image(i, j);
            idwt1D(temp_col_in, temp_col_out, n1);
            for (uint64_t i = 0; i < n1; ++i) buffer(i, j) = temp_col_out(i);
        }

        Array<T> temp_row_in(n2);
        Array<T> temp_row_out(n2);

        // Rows
        for (uint64_t i = 0; i < n1; ++i) {
            for (uint64_t j = 0; j < n2; ++j) temp_row_in(j) = buffer(i, j);
            idwt1D(temp_row_in, temp_row_out, n2);
            for (uint64_t j = 0; j < n2; ++j) image(i, j) = temp_row_out(j);
        }
    }

public:
    // Constructor with image sizes, levels, and wavelet type
    Wavelet(uint64_t image_size1_, uint64_t image_size2_, uint64_t levels_, bool use_d2_not_d4_ = false)
        : image_size1(image_size1_),
          image_size2(image_size2_),
          levels(levels_),
          wavelet_size1(compute_wavelet_size(image_size1_, levels_)),
          wavelet_size2(compute_wavelet_size(image_size2_, levels_)),
          use_d2_not_d4(use_d2_not_d4_),
          h(use_d2_not_d4 ? std::vector<RealPrecisionType>{static_cast<RealPrecisionType>(1.0 / std::sqrt(2.0)), static_cast<RealPrecisionType>(1.0 / std::sqrt(2.0))}
                          : std::vector<RealPrecisionType>{static_cast<RealPrecisionType>((1.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                                           static_cast<RealPrecisionType>((3.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                                           static_cast<RealPrecisionType>((3.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                                           static_cast<RealPrecisionType>((1.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0)))}),
          g(use_d2_not_d4 ? std::vector<RealPrecisionType>{static_cast<RealPrecisionType>(1.0 / std::sqrt(2.0)), static_cast<RealPrecisionType>(-1.0 / std::sqrt(2.0))}
                          : std::vector<RealPrecisionType>{static_cast<RealPrecisionType>((1.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                                           static_cast<RealPrecisionType>(-(3.0 - std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                                           static_cast<RealPrecisionType>((3.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0))),
                                                           static_cast<RealPrecisionType>(-(1.0 + std::sqrt(3.0)) / (4.0 * std::sqrt(2.0)))}),
          buffer(wavelet_size1, wavelet_size2) {
        if (image_size1 == 0 || image_size2 == 0) {
            throw std::runtime_error("Image sizes must be greater than 0");
        }
        if (levels < 1) {
            throw std::runtime_error("Number of levels must be at least 1");
        }
        if ((1ULL << levels) > wavelet_size1 || (1ULL << levels) > wavelet_size2) {
             throw std::runtime_error("Image size too small for the number of levels");
        }
        buffer.fill(T(0));
    }

    // Forward transform: Zero-pad input image and apply multi-level DWT
    Array<T> forward_transform(const Array<T>& input) const {
        if (input.ndim() != 2 || input.dimensions(0) != image_size1 || input.dimensions(1) != image_size2) {
            throw std::runtime_error("Input must be a 2D array of size " + std::to_string(image_size1) + "x" + std::to_string(image_size2));
        }

        // Create padded array
        Array<T> padded(wavelet_size1, wavelet_size2);
        padded.fill(T(0));

        // Symmetric zero-padding
        uint64_t offset1 = (wavelet_size1 - image_size1) / 2;
        uint64_t offset2 = (wavelet_size2 - image_size2) / 2;
        for (uint64_t i = 0; i < image_size1; ++i) {
            for (uint64_t j = 0; j < image_size2; ++j) {
                padded(i + offset1, j + offset2) = input(i, j);
            }
        }

        // Apply multi-level DWT
        uint64_t current_size1 = wavelet_size1;
        uint64_t current_size2 = wavelet_size2;
        for (uint64_t level = 0; level < levels; ++level) {
            dwt2DLevel(padded, current_size1, current_size2);
            current_size1 /= 2;
            current_size2 /= 2;
        }

        return padded;
    }

    // Inverse transform: Apply multi-level IDWT and crop to image_size
    Array<T> inverse_transform(Array<T>& image) const {
        if (image.ndim() != 2 || image.dimensions(0) != wavelet_size1 || image.dimensions(1) != wavelet_size2) {
            throw std::runtime_error("Input must be a 2D array of size " + std::to_string(wavelet_size1) + "x" + std::to_string(wavelet_size2));
        }

        for (int64_t level = levels - 1; level >= 0; --level) {
            uint64_t n1 = wavelet_size1 >> level;
            uint64_t n2 = wavelet_size2 >> level;
            idwt2DLevel(image, n1, n2);
        }

        // Crop to original image size
        Array<T> cropped(image_size1, image_size2);
        uint64_t offset1 = (wavelet_size1 - image_size1) / 2;
        uint64_t offset2 = (wavelet_size2 - image_size2) / 2;
        for (uint64_t i = 0; i < image_size1; ++i) {
            for (uint64_t j = 0; j < image_size2; ++j) {
                cropped(i, j) = image(i + offset1, j + offset2);
            }
        }

        return cropped;
    }

    // Getters for class properties
    uint64_t get_image_size1() const { return image_size1; }
    uint64_t get_image_size2() const { return image_size2; }
    uint64_t get_levels() const { return levels; }
    uint64_t get_wavelet_size1() const { return wavelet_size1; }
    uint64_t get_wavelet_size2() const { return wavelet_size2; }
    bool get_use_d2_not_d4() const { return use_d2_not_d4; }
};

} // namespace GPIArray