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
#include <cerrno>

#if defined(_MSC_VER) || defined(_WIN32)
    #include <malloc.h>
    inline int posix_memalign(void** ptr, size_t alignment, size_t size) {
        *ptr = _aligned_malloc(size, alignment);
        return (*ptr != nullptr) ? 0 : ENOMEM;
    }
    #define VOXEL_ALIGNED_FREE _aligned_free
#else
    #define VOXEL_ALIGNED_FREE std::free
#endif

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
void roll_axis_in_place(Voxel::Array<std::complex<T_Real>>& arr, uint64_t axis, int64_t shift_amount) {
    // 1. Strictly use size() API
    if (arr.ndim() == 0 || arr.size(axis) <= 1) return; 

    uint64_t dim_size = arr.size(axis);
    int64_t normalized_shift_amount = (shift_amount % static_cast<int64_t>(dim_size) + static_cast<int64_t>(dim_size)) % static_cast<int64_t>(dim_size);
    if (normalized_shift_amount == 0) return; 

    std::complex<T_Real>* raw_data = arr.get_data();
    const uint64_t* strides = arr.strides();
    const uint64_t axis_stride = strides[axis]; 

    // Calculate number of 1D lines along this axis
    uint64_t num_lines_to_shift = 1;
    for (uint64_t d_idx = 0; d_idx < arr.ndim(); ++d_idx) {
        if (d_idx != axis) num_lines_to_shift *= arr.size(d_idx);
    }

    // 2. FIX: Standard unique_ptr for arrays automatically uses delete[]
    // No custom std::function deleter is required or allowed here.
    std::unique_ptr<std::complex<T_Real>[]> temp_line_buffer_owner = nullptr;
    std::complex<T_Real>* temp_line_buffer = nullptr;

    if (axis_stride != 1) { 
        temp_line_buffer = new std::complex<T_Real>[dim_size];
        temp_line_buffer_owner.reset(temp_line_buffer); 
        if (!temp_line_buffer) {
            throw std::runtime_error("roll_axis_in_place: Failed to allocate temporary buffer.");
        }
    }

    // Pre-compute flat indices for all lines
    std::vector<uint64_t> all_base_flat_indices(num_lines_to_shift); 

    for (uint64_t line_master_idx = 0; line_master_idx < num_lines_to_shift; ++line_master_idx) { 
        uint64_t temp_line_idx = line_master_idx; 
        uint64_t base_flat_idx_val = 0; 
        
        for (uint64_t d_idx = arr.ndim(); d_idx > 0; --d_idx) {
            uint64_t d = d_idx - 1;
            if (d == axis) continue;
            
            uint64_t coord = temp_line_idx % arr.size(d);
            base_flat_idx_val += coord * strides[d];
            temp_line_idx /= arr.size(d);
        }
        all_base_flat_indices[line_master_idx] = base_flat_idx_val; 
    }

    // Perform the actual rotation for each line
    for (uint64_t line_master_idx = 0; line_master_idx < num_lines_to_shift; ++line_master_idx) { 
        uint64_t base_flat_idx = all_base_flat_indices[line_master_idx]; 

        if (axis_stride == 1) {
            std::rotate(raw_data + base_flat_idx, 
                        raw_data + base_flat_idx + (dim_size - normalized_shift_amount), 
                        raw_data + base_flat_idx + dim_size);
        } else {
            // Extract to temp buffer, rotate, write back
            for (uint64_t j = 0; j < dim_size; ++j) {
                temp_line_buffer[j] = raw_data[base_flat_idx + j * axis_stride];
            }
            std::rotate(temp_line_buffer, 
                        temp_line_buffer + (dim_size - normalized_shift_amount), 
                        temp_line_buffer + dim_size);
            for (uint64_t j = 0; j < dim_size; ++j) {
                raw_data[base_flat_idx + j * axis_stride] = temp_line_buffer[j];
            }
        }
    }
}

template<typename T_Real>
void apply_alternating_sign_mask_axis(Voxel::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size() <= 1 || arr.dimensions(axis) <= 1) return;
    
    uint64_t dim_size = arr.dimensions(axis);
    uint64_t stride = arr.strides()[axis];
    uint64_t outer_loops = arr.size() / (dim_size * stride);
    
    std::complex<T_Real>* data = arr.get_data();
    
    // Pure block processing. No division, no modulo, no inner OpenMP threads.
    for (uint64_t outer = 0; outer < outer_loops; ++outer) {
        for (uint64_t d = 0; d < dim_size; ++d) {
            T_Real sign = (d & 1) ? static_cast<T_Real>(-1.0) : static_cast<T_Real>(1.0);
            uint64_t base_idx = outer * (dim_size * stride) + d * stride;
            
            // The compiler will auto-vectorize this tight inner loop
            for (uint64_t i = 0; i < stride; ++i) {
                data[base_idx + i] *= sign;
            }
        }
    }
}

template<typename T_Real>
void fftshift_axis(Voxel::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size(axis) % 2 == 0) {
        apply_alternating_sign_mask_axis(arr, axis);
    } else {
        // fftshift MUST use floor division
        uint64_t dim_size = arr.size(axis);
        int64_t shift_amount = dim_size / 2;  
        roll_axis_in_place(arr, axis, shift_amount);
    }
}

template<typename T_Real>
void ifftshift_axis(Voxel::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size(axis) % 2 == 0) {
        apply_alternating_sign_mask_axis(arr, axis);
    } else {
        // ifftshift MUST use ceiling division
        uint64_t dim_size = arr.size(axis);
        int64_t shift_amount = (dim_size + 1) / 2;  
        roll_axis_in_place(arr, axis, shift_amount);
    }
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
    uint64_t _total_size;
    
    T_Real _fwd_norm_factor;
    T_Real _bwd_norm_factor;
    std::vector<ptrdiff_t> _default_strides_bytes;

    // Track axes by dimension parity
    std::vector<size_t> _even_axes;
    std::vector<size_t> _odd_axes;

    // 64-byte aligned fused mask to cache (-1)^(sum) for all even axes
    struct AlignedDeleter { void operator()(void* p) const { if (p) VOXEL_ALIGNED_FREE(p); } };
    std::unique_ptr<T_Real[], AlignedDeleter> _fused_mask{nullptr, AlignedDeleter()};

    /**
     * @brief Pre-calculates the fused N-Dimensional alternating mask 
     * exclusively for the even-sized axes in the transform.
     */
    void generate_fused_mask() {
        size_t bytes = _total_size * sizeof(T_Real);
        size_t padded = (bytes + 63) & ~63;
        void* raw_ptr = nullptr;
        if (posix_memalign(&raw_ptr, 64, padded) != 0) {
            throw std::runtime_error("FFTPlan: Mask allocation failed.");
        }
        
        _fused_mask.reset(static_cast<T_Real*>(raw_ptr));
        T_Real* mask_ptr = _fused_mask.get();
        
        std::vector<uint64_t> coords(_shape.size(), 0);
        for (uint64_t i = 0; i < _total_size; ++i) {
            uint64_t parity_sum = 0;
            for (size_t ax : _even_axes) {
                parity_sum += coords[ax];
            }
            
            mask_ptr[i] = (parity_sum % 2 == 0) ? static_cast<T_Real>(1.0) : static_cast<T_Real>(-1.0);

            // Increment N-D coordinates
            for (int d = static_cast<int>(_shape.size()) - 1; d >= 0; --d) {
                if (++coords[d] < _shape[d]) break;
                coords[d] = 0;
            }
        }
    }

    /**
     * @brief Applies the cached fused mask for all even axes in one fast SIMD pass.
     */
    void apply_even_mask(Voxel::Array<ComplexT>& arr) const {
        if (_even_axes.empty()) return;
        ComplexT* data = arr.get_data();
        const T_Real* mask = _fused_mask.get();
        uint64_t sz = arr.size(); 
        
        if (arr.is_contiguous()) {
            #pragma omp simd
            for (uint64_t i = 0; i < sz; ++i) {
                data[i] *= mask[i];
            }
        } else {
            // Safe path for sliced views
            std::vector<uint64_t> idx(_shape.size(), 0);
            uint64_t offset = 0;
            for (uint64_t i = 0; i < sz; ++i) {
                data[offset] *= mask[i];
                for (int d = static_cast<int>(_shape.size()) - 1; d >= 0; --d) {
                    if (++idx[d] < _shape[d]) {
                        offset += arr.strides()[d];
                        break;
                    }
                    idx[d] = 0;
                    offset -= arr.strides()[d] * (_shape[d] - 1);
                }
            }
        }
    }

    void execute_pocketfft(Voxel::Array<ComplexT>& arr, bool forward) const {
        T_Real fct = forward ? _fwd_norm_factor : _bwd_norm_factor;

        if (arr.is_contiguous()) {
            // FAST PATH: Zero-allocation using pre-computed vector strides
            pocketfft::c2c(_shape, _default_strides_bytes, _default_strides_bytes, _axes, 
                           forward, arr.get_data(), arr.get_data(), fct, 0); 
        } else {
            // SLOW PATH: Allocate custom vector strides for non-contiguous views
            std::vector<ptrdiff_t> custom_strides(_shape.size());
            for (size_t i = 0; i < _shape.size(); ++i) {
                custom_strides[i] = static_cast<ptrdiff_t>(arr.strides()[i] * sizeof(ComplexT));
            }
            pocketfft::c2c(_shape, custom_strides, custom_strides, _axes, 
                           forward, arr.get_data(), arr.get_data(), fct, 0); 
        }
    }

public:
    // Default constructor
    FFTPlan()
        : _mask_size(0), _total_size(0), _fwd_norm_factor(T_Real(1)), _bwd_norm_factor(T_Real(1)) {}

    // Copy assignment operator
    FFTPlan& operator=(const FFTPlan& other) {
        if (this != &other) {
            _shape = other._shape;
            _axes = other._axes;
            _mask_size = other._mask_size;
            _total_size = other._total_size;
            _fwd_norm_factor = other._fwd_norm_factor;
            _bwd_norm_factor = other._bwd_norm_factor;
            _default_strides_bytes = other._default_strides_bytes;
            _even_axes = other._even_axes;
            _odd_axes = other._odd_axes;
            
            if (other._fused_mask) {
                size_t bytes = _total_size * sizeof(T_Real);
                size_t padded = (bytes + 63) & ~63;
                void* raw_ptr = nullptr;
                if (posix_memalign(&raw_ptr, 64, padded) == 0) {
                    _fused_mask.reset(static_cast<T_Real*>(raw_ptr));
                    std::memcpy(_fused_mask.get(), other._fused_mask.get(), padded);
                }
            } else {
                _fused_mask.reset();
            }
        }
        return *this;
    }

    FFTPlan(const std::vector<uint64_t>& total_array_shape, 
            const std::vector<uint64_t>& transform_dims = {},
            Normalization norm = g_default_normalization) 
    {
        _total_size = 1;
        for (auto d : total_array_shape) {
            _shape.push_back(static_cast<size_t>(d));
            _total_size *= d;
        }

        if (transform_dims.empty()) {
            for (size_t i = 0; i < total_array_shape.size(); ++i) _axes.push_back(i);
        } else {
            for (auto ax : transform_dims) _axes.push_back(static_cast<size_t>(ax));
        }

        _mask_size = 1;
        for (size_t ax : _axes) {
            _mask_size *= _shape[ax];
            
            // Smartly classify axes for shift logic
            if (_shape[ax] % 2 == 0) {
                _even_axes.push_back(ax);
            } else {
                _odd_axes.push_back(ax);
            }
        }

        _fwd_norm_factor = get_normalization_factor<T_Real>(_mask_size, TransformDir::ImageToKspace, norm);
        _bwd_norm_factor = get_normalization_factor<T_Real>(_mask_size, TransformDir::KspaceToImage, norm);

        _default_strides_bytes.resize(_shape.size());
        uint64_t current_stride = 1;
        for (int i = (int)_shape.size() - 1; i >= 0; --i) {
            _default_strides_bytes[i] = static_cast<ptrdiff_t>(current_stride * sizeof(ComplexT));
            current_stride *= _shape[i];
        }

        // Cache the combined mask for all even axes once
        if (!_even_axes.empty()) {
            generate_fused_mask();
        }
    }

    void ImageToKspace(Voxel::Array<ComplexT>& arr, bool perform_shift = true) const {
        if (perform_shift) {
            // Apply cached fused mask for even axes
            apply_even_mask(arr);
            // Apply standard shift (roll) for odd axes
            for (size_t ax : _odd_axes) {
                ifftshift_axis(arr, static_cast<uint64_t>(ax));
            }
        }
        
        execute_pocketfft(arr, true);
        
        if (perform_shift) {
            apply_even_mask(arr);
            for (size_t ax : _odd_axes) {
                fftshift_axis(arr, static_cast<uint64_t>(ax));
            }
        }
    }

    void KspaceToImage(Voxel::Array<ComplexT>& arr, bool perform_shift = true) const {
        if (perform_shift) {
            apply_even_mask(arr);
            for (size_t ax : _odd_axes) {
                ifftshift_axis(arr, static_cast<uint64_t>(ax));
            }
        }
        
        execute_pocketfft(arr, false);
        
        if (perform_shift) {
            apply_even_mask(arr);
            for (size_t ax : _odd_axes) {
                fftshift_axis(arr, static_cast<uint64_t>(ax));
            }
        }
    }

    void Forward(Voxel::Array<ComplexT>& arr, bool perform_shift = true) const {
        ImageToKspace(arr, perform_shift);
    }

    void Backward(Voxel::Array<ComplexT>& arr, bool perform_shift = true) const {
        KspaceToImage(arr, perform_shift);
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