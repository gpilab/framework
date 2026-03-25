/**
 * @file FFTW_WRAPPER.hpp
 * @brief PocketFFT-based multi-dimensional FFT wrapper for Voxel::Array.
 *
 * This header provides FFT functionality via PocketFFT (pocketfft_hdronly.h).
 * The Voxel::FFT namespace is implemented with automatic optimization and zero manual planning.
 *
 * @author Guru Krishnamoorthy
 * @date 2026 March
 */

#pragma once

#include "Array.hpp" 
#include "ArrayMacros.hpp" 
#include "pocketfft_hdronly.h" 
#include <complex>   
#include <vector>
#include <type_traits> 
#include <algorithm> 
#include <cstdlib>

namespace Voxel {
namespace FFT { 

// --- Strongly-Typed Domain Constants ---
// Mapped identically to FFTW_FORWARD (-1) and FFTW_BACKWARD (+1)
enum class TransformDir {
    ImageToKspace = -1,
    KspaceToImage = 1,
    Forward = -1,
    Backward = 1
};

constexpr TransformDir ImageToKspace = TransformDir::ImageToKspace;
constexpr TransformDir KspaceToImage = TransformDir::KspaceToImage;
constexpr TransformDir Forward = TransformDir::Forward;
constexpr TransformDir Backward = TransformDir::Backward;

enum Normalization {
    NORM_NONE,     
    NORM_BACKWARD, 
    NORM_ORTHO     
};

static Normalization g_default_normalization = NORM_BACKWARD;

template<typename T>
T get_normalization_factor(uint64_t N, TransformDir dir, Normalization norm) {
    if (norm == NORM_NONE) return static_cast<T>(1.0);
    if (norm == NORM_BACKWARD) {
        return (dir == TransformDir::KspaceToImage) ? static_cast<T>(1.0 / N) : static_cast<T>(1.0);
    }
    if (norm == NORM_ORTHO) {
        return static_cast<T>(1.0 / std::sqrt(static_cast<double>(N)));
    }
    return static_cast<T>(1.0);
}

// =====================================================================================
// Quadrant Shifting & Utilities
// =====================================================================================

template<typename T_Real>
void apply_alternating_sign_mask_axis(Voxel::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size() <= 1 || arr.dimensions(axis) <= 1) return;
    
    uint64_t dim_size = arr.dimensions(axis);
    uint64_t stride = arr.strides()[axis];
    uint64_t total_size = arr.size();
    
    std::complex<T_Real>* data = arr.get_data();
    
    #pragma omp simd
    for (uint64_t i = 0; i < total_size; ++i) {
        uint64_t idx_along_axis = (i / stride) % dim_size;
        T_Real sign = (idx_along_axis & 1) ? static_cast<T_Real>(-1.0) : static_cast<T_Real>(1.0);
        data[i] *= sign;
    }
}

template<typename T_Real>
void fftshift_axis(Voxel::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.dimensions(axis) % 2 == 0) {
        apply_alternating_sign_mask_axis(arr, axis);
    } else {
        THROW_RUNTIME_ERROR("fftshift_axis: Odd dimensions require memory roll (not supported in fast path).");
    }
}

template<typename T_Real>
void ifftshift_axis(Voxel::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    fftshift_axis(arr, axis); 
}

template<typename T_Real>
void fftshift(Voxel::Array<std::complex<T_Real>>& arr) {
    for (uint64_t d = 0; d < arr.ndim(); ++d) fftshift_axis(arr, d);
}

template<typename T_Real>
void ifftshift(Voxel::Array<std::complex<T_Real>>& arr) {
    for (uint64_t d = 0; d < arr.ndim(); ++d) ifftshift_axis(arr, d);
}


// =====================================================================================
// FFTPlan Class (Now Powered by PocketFFT)
// =====================================================================================

template<typename T_Real>
class FFTPlan {
public:
    using ComplexT = std::complex<T_Real>;

private:
    std::vector<size_t> _shape;
    std::vector<size_t> _axes;
    uint64_t _mask_size;            
    
    T_Real _fwd_norm_factor;
    T_Real _bwd_norm_factor;

    void execute_pocketfft(Voxel::Array<ComplexT>& arr, bool forward) const {
        std::vector<ptrdiff_t> strides_bytes(_shape.size());
        for (size_t i = 0; i < _shape.size(); ++i) {
            strides_bytes[i] = arr.strides()[i] * sizeof(ComplexT);
        }

        T_Real fct = forward ? _fwd_norm_factor : _bwd_norm_factor;
        pocketfft::c2c(_shape, strides_bytes, strides_bytes, _axes, 
                       forward, arr.get_data(), arr.get_data(), fct, 0); 
    }

public:
    FFTPlan(const std::vector<uint64_t>& total_array_shape, 
            const std::vector<uint64_t>& transform_dims = {},
            Normalization norm = g_default_normalization) 
    {
        for (auto d : total_array_shape) _shape.push_back(static_cast<size_t>(d));

        if (transform_dims.empty()) {
            for (size_t i = 0; i < total_array_shape.size(); ++i) _axes.push_back(i);
        } else {
            for (auto ax : transform_dims) _axes.push_back(static_cast<size_t>(ax));
        }

        _mask_size = 1;
        for (size_t ax : _axes) _mask_size *= _shape[ax];

        _fwd_norm_factor = get_normalization_factor<T_Real>(_mask_size, TransformDir::ImageToKspace, norm);
        _bwd_norm_factor = get_normalization_factor<T_Real>(_mask_size, TransformDir::KspaceToImage, norm);
    }

    void ImageToKspace(Voxel::Array<ComplexT>& arr, bool perform_shift = true) const {
        if (perform_shift) {
            for (size_t ax : _axes) apply_alternating_sign_mask_axis(arr, ax);
        }
        execute_pocketfft(arr, true);
        if (perform_shift) {
            for (size_t ax : _axes) apply_alternating_sign_mask_axis(arr, ax);
        }
    }

    void KspaceToImage(Voxel::Array<ComplexT>& arr, bool perform_shift = true) const {
        if (perform_shift) {
            for (size_t ax : _axes) apply_alternating_sign_mask_axis(arr, ax);
        }
        execute_pocketfft(arr, false);
        if (perform_shift) {
            for (size_t ax : _axes) apply_alternating_sign_mask_axis(arr, ax);
        }
    }
};

// =====================================================================================
// Public API Functions
// =====================================================================================

// --- Master N-Dimensional FFT ---
template<typename T_Real>
void fftn(const Voxel::Array<std::complex<T_Real>>& input,
          Voxel::Array<std::complex<T_Real>>& output,
          TransformDir dir,
          std::vector<uint64_t> axes = {}, 
          bool perform_shift = true,
          Normalization norm = g_default_normalization) {

    if (input.ndim() != output.ndim() || input.size() != output.size()) {
        THROW_INVALID_ARGUMENT("FFT::fftn: Input and output arrays must have matching shapes.");
    }
    if (input.size() == 0) return;

    auto contiguous_input = input.contiguous();

    if (axes.empty()) {
        for(uint64_t i = 0; i < contiguous_input.ndim(); ++i) axes.push_back(i);
    }

    FFTPlan<T_Real> temp_plan(contiguous_input.dimensions_vector(), axes, norm);

    bool is_in_place = (contiguous_input.get_data() == output.get_data());
    
    if (!is_in_place) {
        if (!output.is_contiguous()) THROW_INVALID_ARGUMENT("FFT::fftn: Output array must be contiguous for out-of-place transforms.");
        std::copy(contiguous_input.get_data(), contiguous_input.get_data() + contiguous_input.size(), output.get_data());
    }

    if (dir == TransformDir::ImageToKspace) temp_plan.ImageToKspace(output, perform_shift);
    else temp_plan.KspaceToImage(output, perform_shift);
}


// --- 1D FFT Wrapper ---
template<typename T_Real>
void fft1(const Voxel::Array<std::complex<T_Real>>& input,
          Voxel::Array<std::complex<T_Real>>& output,
          TransformDir dir,
          int64_t axis = -1,
          bool perform_shift = true,
          Normalization norm = g_default_normalization) {
    
    uint64_t ndim = input.ndim();
    uint64_t actual_axis = (axis < 0) ? (ndim - 1) : static_cast<uint64_t>(axis);
    if (actual_axis >= ndim) THROW_INVALID_ARGUMENT("FFT::fft1: axis out of range.");
    
    fftn(input, output, dir, {actual_axis}, perform_shift, norm);
}


// --- Deprecated Direct APIs ---
template<typename T_Real>
void fft2(const Voxel::Array<std::complex<T_Real>>& input,
          Voxel::Array<std::complex<T_Real>>& output,
          TransformDir dir, 
          bool perform_shift = true,
          Normalization norm = g_default_normalization) {
    if (input.ndim() < 2) THROW_INVALID_ARGUMENT("FFT::fft2: Input array must be at least 2-dimensional.");
    std::vector<uint64_t> axes = {input.ndim() - 2, input.ndim() - 1};
    fftn(input, output, dir, axes, perform_shift, norm);
}

template<typename T_Real>
void fft3(const Voxel::Array<std::complex<T_Real>>& input,
          Voxel::Array<std::complex<T_Real>>& output,
          TransformDir dir, 
          bool perform_shift = true,
          Normalization norm = g_default_normalization) {
    if (input.ndim() != 3) THROW_INVALID_ARGUMENT("FFT::fft3: Input array must be exactly 3-dimensional.");
    fftn(input, output, dir, {0, 1, 2}, perform_shift, norm);
}


// =====================================================================================
// Allocation-Returning Convenience Wrappers
// =====================================================================================

template<typename T_Real>
Voxel::Array<std::complex<T_Real>> fftn(const Voxel::Array<std::complex<T_Real>>& input, 
                                        TransformDir dir,
                                        std::vector<uint64_t> axes = {}, 
                                        bool perform_shift = true,
                                        Normalization norm = g_default_normalization) {
    Voxel::Array<std::complex<T_Real>> output(input.dimensions_vector());
    fftn(input, output, dir, axes, perform_shift, norm);
    return output;
}

template<typename T_Real>
Voxel::Array<std::complex<T_Real>> fft1(const Voxel::Array<std::complex<T_Real>>& input, 
                                        TransformDir dir,
                                        int64_t axis = -1, 
                                        bool perform_shift = true,
                                        Normalization norm = g_default_normalization) {
    Voxel::Array<std::complex<T_Real>> output(input.dimensions_vector());
    fft1(input, output, dir, axis, perform_shift, norm);
    return output;
}

} // namespace FFT
} // namespace Voxel