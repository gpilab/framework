/**
 * @file FFTW_WRAPPER.hpp
 * @brief FFTW-based multi-dimensional FFT and DCT wrapper for GPIArray::Array.
 *
 * This header provides the GPIArray::FFTW namespace, which implements efficient multi-dimensional
 * Fast Fourier Transform (FFT), Inverse FFT, Discrete Cosine Transform (DCT), and related operations
 * for GPIArray::Array containers using the FFTW library.
 *
 * Features:
 * - Strongly-typed Domain Transforms (ImageToKspace, KspaceToImage)
 * - Master fftn wrapper that intelligently routes to 1D, ND, or Batched plans based on `axes`
 * - Type-safe FFTW integration for std::complex<float> and std::complex<double>
 * - In-place and out-of-place transforms with dynamic normalization
 * - DCT-II (forward) and DCT-III (inverse) for real-valued 2D arrays
 * - Thread-safe FFTW plan creation/destruction via global mutex
 * - FFTPlan class for persistent FFTW plan management and repeated transforms
 *
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */

#ifndef GPIArray_FFTW_HPP
#define GPIArray_FFTW_HPP

#include <fftw3.h> 
#include "Array.hpp" 
#include "ArrayMacros.hpp" 
#include <complex>   
#include <vector>
#include <numeric>   
#include <type_traits> 
#include <algorithm> 
#include <cstdio>    
#include <string>    
#include <mutex>     
#include <iostream>  
#include <cstring>   

namespace GPIArray {

namespace FFTW { 

// --- Strongly-Typed Domain Constants ---
enum class TransformDir {
    ImageToKspace = FFTW_FORWARD,
    KspaceToImage = FFTW_BACKWARD
};

// Expose them directly to the FFTW namespace for clean syntax
constexpr TransformDir ImageToKspace = TransformDir::ImageToKspace;
constexpr TransformDir KspaceToImage = TransformDir::KspaceToImage;

enum Normalization {
    NORM_NONE,     // No scaling (Forward: 1, Backward: 1)
    NORM_BACKWARD, // Standard (Forward: 1, Backward: 1/N)
    NORM_ORTHO     // Orthonormal (Forward: 1/sqrt(N), Backward: 1/sqrt(N))
};

static Normalization g_default_normalization = NORM_BACKWARD;

static std::mutex g_fftw_plan_mutex;

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

// --- Type Traits ---
template<typename ComplexT>
struct FFTWPrecisionTraits;

template<>
struct FFTWPrecisionTraits<std::complex<double>> {
    using FFTWComplexType = fftw_complex;
    using PlanType = fftw_plan;
    using PlanFunction1D = decltype(&fftw_plan_dft_1d);
    using PlanFunction2D = decltype(&fftw_plan_dft_2d);
    using PlanFunction3D = decltype(&fftw_plan_dft_3d);
    using PlanFunctionND = decltype(&fftw_plan_many_dft);
    using ExecuteFunction = decltype(&fftw_execute);
    using ExecuteDFTFunction = decltype(&fftw_execute_dft);
    using DestroyPlanFunction = decltype(&fftw_destroy_plan);

    static constexpr PlanFunction1D plan_dft_1d = fftw_plan_dft_1d;
    static constexpr PlanFunction2D plan_dft_2d = fftw_plan_dft_2d;
    static constexpr PlanFunction3D plan_dft_3d = fftw_plan_dft_3d;
    static constexpr PlanFunctionND plan_dft_ = fftw_plan_many_dft;
    static constexpr ExecuteFunction execute = fftw_execute;
    static constexpr ExecuteDFTFunction execute_dft = fftw_execute_dft;
    static constexpr DestroyPlanFunction destroy_plan = fftw_destroy_plan;
};

template<>
struct FFTWPrecisionTraits<std::complex<float>> {
    using FFTWComplexType = fftwf_complex;
    using PlanType = fftwf_plan;
    using PlanFunction1D = decltype(&fftwf_plan_dft_1d);
    using PlanFunction2D = decltype(&fftwf_plan_dft_2d);
    using PlanFunction3D = decltype(&fftwf_plan_dft_3d);
    using PlanFunctionND = decltype(&fftwf_plan_many_dft);
    using ExecuteFunction = decltype(&fftwf_execute);
    using ExecuteDFTFunction = decltype(&fftwf_execute_dft);
    using DestroyPlanFunction = decltype(&fftwf_destroy_plan);

    static constexpr PlanFunction1D plan_dft_1d = fftwf_plan_dft_1d;
    static constexpr PlanFunction2D plan_dft_2d = fftwf_plan_dft_2d;
    static constexpr PlanFunction3D plan_dft_3d = fftwf_plan_dft_3d;
    static constexpr PlanFunctionND plan_dft_ = fftwf_plan_many_dft;
    static constexpr ExecuteFunction execute = fftwf_execute;
    static constexpr ExecuteDFTFunction execute_dft = fftwf_execute_dft;
    static constexpr DestroyPlanFunction destroy_plan = fftwf_destroy_plan;
};

template<typename T_Real>
struct FFTWRealPrecisionTraits;

template<>
struct FFTWRealPrecisionTraits<double> {
    using PlanType = fftw_plan;
    using PlanFunction2D = decltype(&fftw_plan_r2r_2d);
    using ExecuteFunction = decltype(&fftw_execute);
    using DestroyPlanFunction = decltype(&fftw_destroy_plan);

    static constexpr PlanFunction2D plan_r2r_2d = fftw_plan_r2r_2d;
    static constexpr ExecuteFunction execute = fftw_execute;
    static constexpr DestroyPlanFunction destroy_plan = fftw_destroy_plan;
};

template<>
struct FFTWRealPrecisionTraits<float> {
    using PlanType = fftwf_plan;
    using PlanFunction2D = decltype(&fftwf_plan_r2r_2d);
    using ExecuteFunction = decltype(&fftwf_execute);
    using DestroyPlanFunction = decltype(&fftwf_destroy_plan);

    static constexpr PlanFunction2D plan_r2r_2d = fftwf_plan_r2r_2d;
    static constexpr ExecuteFunction execute = fftwf_execute;
    static constexpr DestroyPlanFunction destroy_plan = fftwf_destroy_plan;
};


// =====================================================================================
// Quadrant Shifting & Utilities
// =====================================================================================

template<typename T_Real>
void roll_axis_in_place(GPIArray::Array<std::complex<T_Real>>& arr, uint64_t axis, int64_t shift_amount) {
    if (arr.ndim() == 0 || arr.dimensions(axis) <= 1) return; 

    uint64_t dim_size = arr.dimensions(axis);
    int64_t normalized_shift_amount = (shift_amount % dim_size + dim_size) % dim_size;
    if (normalized_shift_amount == 0) return; 

    std::complex<T_Real>* raw_data = arr.get_data();
    const uint64_t* strides = arr.strides();
    const uint64_t axis_stride = strides[axis]; 

    uint64_t num_lines_to_shift = 1;
    for (uint64_t d_idx = 0; d_idx < arr.ndim(); ++d_idx) {
        if (d_idx != axis) num_lines_to_shift *= arr.dimensions(d_idx);
    }

    std::unique_ptr<std::complex<T_Real>[], std::function<void(std::complex<T_Real>*)>> temp_line_buffer_owner = nullptr;
    std::complex<T_Real>* temp_line_buffer = nullptr;

    if (axis_stride != 1) { 
        if constexpr (std::is_same_v<T_Real, float>) {
            temp_line_buffer = static_cast<std::complex<T_Real>*>(fftwf_malloc(dim_size * sizeof(std::complex<T_Real>)));
            temp_line_buffer_owner = std::unique_ptr<std::complex<T_Real>[], std::function<void(std::complex<T_Real>*)>>(
                reinterpret_cast<std::complex<T_Real>*>(temp_line_buffer), [](std::complex<T_Real>* p){ fftwf_free(p); });
        } else { 
            temp_line_buffer = static_cast<std::complex<T_Real>*>(fftw_malloc(dim_size * sizeof(std::complex<T_Real>)));
            temp_line_buffer_owner = std::unique_ptr<std::complex<T_Real>[], std::function<void(std::complex<T_Real>*)>>(
                reinterpret_cast<std::complex<T_Real>*>(temp_line_buffer), [](std::complex<T_Real>* p){ fftw_free(p); });
        }
        if (!temp_line_buffer) THROW_RUNTIME_ERROR("Failed to allocate temporary buffer for non-contiguous roll_axis_in_place.");
    }

    std::vector<uint64_t> all_base_flat_indices(num_lines_to_shift); 
    std::vector<uint64_t> current_coords_builder(arr.ndim()); 

    for (uint64_t line_master_idx = 0; line_master_idx < num_lines_to_shift; ++line_master_idx) { 
        uint64_t temp_line_idx = line_master_idx; 
        uint64_t base_flat_idx_val = 0; 
        for (uint64_t d_idx = 0; d_idx < arr.ndim(); ++d_idx) { 
            if (d_idx == axis) { 
                current_coords_builder[d_idx] = 0; 
            } else { 
                current_coords_builder[d_idx] = temp_line_idx % arr.dimensions(d_idx); 
                temp_line_idx /= arr.dimensions(d_idx); 
                base_flat_idx_val += current_coords_builder[d_idx] * strides[d_idx]; 
            }
        }
        all_base_flat_indices[line_master_idx] = base_flat_idx_val; 
    }

    for (uint64_t line_master_idx = 0; line_master_idx < num_lines_to_shift; ++line_master_idx) { 
        uint64_t base_flat_idx = all_base_flat_indices[line_master_idx]; 

        if (axis_stride == 1) { 
            std::complex<T_Real>* line_start_ptr = raw_data + base_flat_idx;
            std::rotate(line_start_ptr, line_start_ptr + normalized_shift_amount, line_start_ptr + dim_size);
        } else { 
            for (uint64_t i_line_elem = 0; i_line_elem < dim_size; ++i_line_elem) { 
                temp_line_buffer[i_line_elem] = raw_data[base_flat_idx + i_line_elem * axis_stride]; 
            }
            std::rotate(temp_line_buffer, temp_line_buffer + normalized_shift_amount, temp_line_buffer + dim_size);
            for (uint64_t i_line_elem = 0; i_line_elem < dim_size; ++i_line_elem) { 
                raw_data[base_flat_idx + i_line_elem * axis_stride] = temp_line_buffer[i_line_elem]; 
            }
        }
    }
}

template<typename T_Real>
void fftshift(GPIArray::Array<std::complex<T_Real>>& arr) {
    if (arr.size() <= 1) return;
    for (uint64_t d = 0; d < arr.ndim(); ++d) {
        int64_t shift_amount = arr.dimensions(d) / 2; 
        roll_axis_in_place(arr, d, shift_amount); 
    }
}

template<typename T_Real>
void ifftshift(GPIArray::Array<std::complex<T_Real>>& arr) {
    if (arr.size() <= 1) return;
    for (uint64_t d = 0; d < arr.ndim(); ++d) {
        int64_t shift_amount = (arr.dimensions(d) + 1) / 2; 
        roll_axis_in_place(arr, d, shift_amount); 
    }
}

template<typename T_Real>
void fftshift_axis(GPIArray::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size() <= 1 || arr.dimensions(axis) <= 1) return;
    int64_t shift_amount = arr.dimensions(axis) / 2; 
    roll_axis_in_place(arr, axis, shift_amount);
}

template<typename T_Real>
void ifftshift_axis(GPIArray::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size() <= 1 || arr.dimensions(axis) <= 1) return;
    int64_t shift_amount = (arr.dimensions(axis) + 1) / 2; 
    roll_axis_in_place(arr, axis, shift_amount);
}

template<typename T_Real>
void apply_alternating_sign_mask_axis(GPIArray::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size() <= 1 || arr.dimensions(axis) <= 1) return;
    
    uint64_t dim_size = arr.dimensions(axis);
    uint64_t stride = arr.strides()[axis];
    uint64_t total_size = arr.size();
    
    std::complex<T_Real>* data = arr.get_data();
    std::vector<T_Real> mask(total_size);
    
    for (uint64_t i = 0; i < total_size; ++i) {
        uint64_t idx_along_axis = (i / stride) % dim_size;
        mask[i] = (idx_along_axis % 2 == 0) ? static_cast<T_Real>(1.0) : static_cast<T_Real>(-1.0);
    }
    for (uint64_t i = 0; i < total_size; ++i) data[i] *= mask[i];
}


// =====================================================================================
// FFTPlan Class 
// =====================================================================================

template<typename T_Real>
class FFTPlan {
public:
    using ComplexT = std::complex<T_Real>;
    using Traits = FFTWPrecisionTraits<ComplexT>;
    using FFTWComplexType = typename Traits::FFTWComplexType;
    using FFTWPlan = typename Traits::PlanType;

private:
    std::vector<int> _fft_dims;      
    FFTWPlan _forward_plan = nullptr;
    FFTWPlan _backward_plan = nullptr;
    unsigned int _plan_flags;
    uint64_t _mask_size;            
    uint64_t _total_elements;       
    
    // Custom deleter to ensure the mask memory is freed correctly using FFTW's allocator
    struct FFTWMaskDeleter {
        void operator()(void* p) const {
            if constexpr (std::is_same_v<T_Real, float>) fftwf_free(p);
            else fftw_free(p);
        }
    };
    
    // The mask is now perfectly aligned for SIMD AVX registers
    std::unique_ptr<T_Real[], FFTWMaskDeleter> _alternating_mask{nullptr, FFTWMaskDeleter()};
    
    bool _use_optimized_shift = false;
    Normalization _norm_method;

    T_Real _fwd_norm_factor;
    T_Real _bwd_norm_factor;
    
    // OPTIMIZATION: Cache normalization checks to avoid floating-point comparisons in hot paths
    bool _fwd_is_unity_norm = false;
    bool _bwd_is_unity_norm = false;

    inline void apply_fused_mask_and_norm(GPIArray::Array<ComplexT>& arr, TransformDir dir) const {
        ComplexT* __restrict data = arr.get_data();
        const T_Real* __restrict mask_ptr = _alternating_mask.get();
        const T_Real factor = (dir == TransformDir::ImageToKspace) ? _fwd_norm_factor : _bwd_norm_factor;

        for (uint64_t offset = 0; offset < _total_elements; offset += _mask_size) {
            #pragma omp simd // Safe, single-threaded AVX vectorization 
            for (uint64_t i = 0; i < _mask_size; ++i) {
                // Fuses mask and scaling into a single hardware instruction
                data[offset + i] *= (mask_ptr[i] * factor);
            }
        }
    }

    inline void apply_mask_only(GPIArray::Array<ComplexT>& arr) const {
        ComplexT* __restrict data = arr.get_data();
        const T_Real* __restrict mask_ptr = _alternating_mask.get();

        for (uint64_t offset = 0; offset < _total_elements; offset += _mask_size) {
            #pragma omp simd // Safe, single-threaded AVX vectorization
            for (uint64_t i = 0; i < _mask_size; ++i) {
                data[offset + i] *= mask_ptr[i];
            }
        }
    }

    bool check_all_dims_even() const {
        for (int dim : _fft_dims) if (dim % 2 != 0) return false;
        return true;
    }

    static bool are_axis_indices(const std::vector<uint64_t>& total_array_shape,
                                   const std::vector<uint64_t>& candidate_indices) {
        if (candidate_indices.empty()) return false;
        uint64_t ndim = total_array_shape.size();
        for (uint64_t val : candidate_indices) {
            if (val >= ndim) return false;  
        }
        return true;  
    }

    void generate_alternating_mask() {
        if (!_use_optimized_shift) return; 
        
        // Allocate mask with strict SIMD alignment via fftw_malloc
        if constexpr (std::is_same_v<T_Real, float>) {
            _alternating_mask.reset(static_cast<T_Real*>(fftwf_malloc(_mask_size * sizeof(T_Real))));
        } else {
            _alternating_mask.reset(static_cast<T_Real*>(fftw_malloc(_mask_size * sizeof(T_Real))));
        }

        T_Real* mask_ptr = _alternating_mask.get();
        
        // Iterative flat-index parity — no recursion, no std::function overhead
        for (uint64_t i = 0; i < _mask_size; ++i) {
            // Parity of flat index = XOR of all digit parities in mixed-radix representation
            uint64_t tmp = i;
            uint64_t parity = 0;
            for (int d = (int)_fft_dims.size() - 1; d >= 0; --d) {
                parity += tmp % _fft_dims[d];
                tmp    /= _fft_dims[d];
            }
            mask_ptr[i] = (parity & 1) ? T_Real(-1.0) : T_Real(1.0);
        }
    }

public:
    FFTPlan(const std::vector<uint64_t>& total_array_shape, 
                   unsigned int plan_flags = FFTW_MEASURE, 
                   const std::vector<uint64_t>& transform_dims = {},
                   Normalization norm = g_default_normalization)
        : _plan_flags(plan_flags), _norm_method(norm) {
        
        std::vector<uint64_t> target_dims;
        if (transform_dims.empty()) {
            target_dims = total_array_shape;
        } else if (are_axis_indices(total_array_shape, transform_dims)) {
            for (uint64_t axis : transform_dims) target_dims.push_back(total_array_shape[axis]);
        } else {
            target_dims = transform_dims;
        }
        
        _mask_size = 1;
        for (uint64_t d : target_dims) {
            _fft_dims.push_back(static_cast<int>(d));
            _mask_size *= d;
        }

        _total_elements = 1;
        for (uint64_t d : total_array_shape) _total_elements *= d;
        int howmany = static_cast<int>(_total_elements / _mask_size);

        _fwd_norm_factor = get_normalization_factor<T_Real>(_mask_size, TransformDir::ImageToKspace, _norm_method);
        _bwd_norm_factor = get_normalization_factor<T_Real>(_mask_size, TransformDir::KspaceToImage, _norm_method);
        
        // OPTIMIZATION: Pre-compute normalization checks to eliminate floating-point ops in hot paths
        _fwd_is_unity_norm = (std::abs(_fwd_norm_factor - 1.0) < 1e-9);
        _bwd_is_unity_norm = (std::abs(_bwd_norm_factor - 1.0) < 1e-9);

        _use_optimized_shift = check_all_dims_even();
        generate_alternating_mask();

        // OPTIMIZATION: Only allocate _mask_size instead of _total_elements for plan creation
        // Dramatically reduces heap pressure for batched transforms (howmany > 1)
        FFTWComplexType* dummy;
        size_t dummy_alloc_bytes = _mask_size * sizeof(ComplexT);
        if constexpr (std::is_same_v<T_Real, float>) dummy = (FFTWComplexType*)fftwf_malloc(dummy_alloc_bytes);
        else dummy = (FFTWComplexType*)fftw_malloc(dummy_alloc_bytes);

        {
            std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);

            if (howmany == 1) {
                // --- SPECIALIZED PLANS: Transforming the entire contiguous array ---
                // NOTE: FFTW_UNALIGNED removed to force maximum AVX execution speeds
                if (_fft_dims.size() == 1) {
                    _forward_plan = Traits::plan_dft_1d(_fft_dims[0], dummy, dummy, FFTW_FORWARD, _plan_flags);
                    _backward_plan = Traits::plan_dft_1d(_fft_dims[0], dummy, dummy, FFTW_BACKWARD, _plan_flags);
                } 
                else if (_fft_dims.size() == 2) {
                    _forward_plan = Traits::plan_dft_2d(_fft_dims[0], _fft_dims[1], dummy, dummy, FFTW_FORWARD, _plan_flags);
                    _backward_plan = Traits::plan_dft_2d(_fft_dims[0], _fft_dims[1], dummy, dummy, FFTW_BACKWARD, _plan_flags);
                } 
                else if (_fft_dims.size() == 3) {
                    _forward_plan = Traits::plan_dft_3d(_fft_dims[0], _fft_dims[1], _fft_dims[2], dummy, dummy, FFTW_FORWARD, _plan_flags);
                    _backward_plan = Traits::plan_dft_3d(_fft_dims[0], _fft_dims[1], _fft_dims[2], dummy, dummy, FFTW_BACKWARD, _plan_flags);
                } 
                else {
                    // Fallback for 4D+ Whole-Array
                    _forward_plan = Traits::plan_dft_((int)_fft_dims.size(), _fft_dims.data(), howmany,
                        dummy, NULL, 1, (int)_mask_size, dummy, NULL, 1, (int)_mask_size, 
                        FFTW_FORWARD, _plan_flags);
                    _backward_plan = Traits::plan_dft_((int)_fft_dims.size(), _fft_dims.data(), howmany,
                        dummy, NULL, 1, (int)_mask_size, dummy, NULL, 1, (int)_mask_size, 
                        FFTW_BACKWARD, _plan_flags);
                }
            } 
            else {
                // --- BATCHED PLANS: Transforming inner axes ---
                _forward_plan = Traits::plan_dft_((int)_fft_dims.size(), _fft_dims.data(), howmany,
                    dummy, NULL, 1, (int)_mask_size, dummy, NULL, 1, (int)_mask_size, 
                    FFTW_FORWARD, _plan_flags);

                _backward_plan = Traits::plan_dft_((int)_fft_dims.size(), _fft_dims.data(), howmany,
                    dummy, NULL, 1, (int)_mask_size, dummy, NULL, 1, (int)_mask_size, 
                    FFTW_BACKWARD, _plan_flags);
            }
        }

        if constexpr (std::is_same_v<T_Real, float>) fftwf_free(dummy); else fftw_free(dummy);
        if (!_forward_plan || !_backward_plan) THROW_RUNTIME_ERROR("FFTPlan: Plan creation failed.");
    }

    ~FFTPlan() {
        std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);
        if (_forward_plan) Traits::destroy_plan(_forward_plan);
        if (_backward_plan) Traits::destroy_plan(_backward_plan);
    }

    void ImageToKspace(GPIArray::Array<ComplexT>& arr, bool perform_shift = true) const {
        if (perform_shift) {
            if (_use_optimized_shift) apply_mask_only(arr);
            else FFTW::ifftshift<T_Real>(arr);
        }

        Traits::execute_dft(_forward_plan, reinterpret_cast<FFTWComplexType*>(arr.get_data()), 
                            reinterpret_cast<FFTWComplexType*>(arr.get_data()));

        if (perform_shift && _use_optimized_shift) {
            // OPTIMIZATION: Use pre-computed flag instead of floating-point comparison
            if (_fwd_is_unity_norm) {
                apply_mask_only(arr);
            } else {
                apply_fused_mask_and_norm(arr, TransformDir::ImageToKspace); 
            }
        } else {
            if (perform_shift) FFTW::fftshift<T_Real>(arr);
            if (!_fwd_is_unity_norm) arr *= _fwd_norm_factor;
        }
    }

    void KspaceToImage(GPIArray::Array<ComplexT>& arr, bool perform_shift = true) const {
        if (perform_shift) {
            if (_use_optimized_shift) apply_mask_only(arr);
            else FFTW::ifftshift<T_Real>(arr);
        }

        Traits::execute_dft(_backward_plan, reinterpret_cast<FFTWComplexType*>(arr.get_data()), 
                            reinterpret_cast<FFTWComplexType*>(arr.get_data()));

        if (perform_shift && _use_optimized_shift) {
            // OPTIMIZATION: Use pre-computed flag instead of floating-point comparison
            if (_bwd_is_unity_norm) {
                apply_mask_only(arr);
            } else {
                apply_fused_mask_and_norm(arr, TransformDir::KspaceToImage); 
            }
        } else {
            if (perform_shift) FFTW::fftshift<T_Real>(arr);
            if (!_bwd_is_unity_norm) arr *= _bwd_norm_factor;
        }
    }
};


// =====================================================================================
// Public API Functions (Wrapper functions) for One-Off FFTs
// =====================================================================================

// 1D FFT fallback handler
template<typename T_Real>
void fft1(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          TransformDir dir, 
          int64_t axis = -1,
          bool perform_shift = true,
          Normalization norm = g_default_normalization) {

    using Traits = FFTWPrecisionTraits<std::complex<T_Real>>;
    using FFTWComplexType = typename Traits::FFTWComplexType;
    using FFTWPlan = typename Traits::PlanType;

    if (input.size() == 0) return;

    uint64_t ndim = input.ndim();
    if (axis < 0) axis = static_cast<int64_t>(ndim) - 1; 
    if (axis >= static_cast<int64_t>(ndim)) THROW_INVALID_ARGUMENT("FFTW::fft1: axis out of range.");

    uint64_t dim_size = input.dimensions(axis);

    bool has_singleton_non_fft = false;
    for (uint64_t d = 0; d < ndim; ++d) {
        if (d != static_cast<uint64_t>(axis) && input.dimensions(d) == 1) {
            has_singleton_non_fft = true;
            break;
        }
    }
    
    bool can_use_mask = (dim_size % 2 == 0);
    bool is_in_place = (&input == &output);
    bool need_copy_back = (!is_in_place) || (has_singleton_non_fft && !output.is_contiguous());
    
    GPIArray::Array<std::complex<T_Real>> temporary_array;
    Array<std::complex<T_Real>>* working_array_ptr;
    
    if (!is_in_place) {
        temporary_array = input.copy();
        working_array_ptr = &temporary_array;
    } else if (has_singleton_non_fft && !output.is_contiguous()) {
        temporary_array = output.copy();
        working_array_ptr = &temporary_array;
    } else {
        working_array_ptr = &output;
    }
    
    GPIArray::Array<std::complex<T_Real>>& working_array = *working_array_ptr;
    uint64_t stride = working_array.strides()[axis];
    
    std::complex<T_Real>* data = working_array.get_data();
    uint64_t total_size = working_array.size();

    if (perform_shift) {
        if (can_use_mask) apply_alternating_sign_mask_axis<T_Real>(working_array, axis);
        else ifftshift_axis<T_Real>(working_array, axis);
    }

    std::lock_guard<std::mutex> lock(g_fftw_plan_mutex); 

    int n_int = static_cast<int>(dim_size);
    if (axis == static_cast<int64_t>(ndim) - 1 && working_array.is_contiguous()) {
        int howmany = static_cast<int>(total_size / dim_size);
        FFTWPlan plan = Traits::plan_dft_(1, &n_int, howmany,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, 1, n_int,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, 1, n_int,
                                         static_cast<int>(dir), FFTW_ESTIMATE | FFTW_UNALIGNED);
        Traits::execute(plan);
        Traits::destroy_plan(plan);
    } 
    else {
        std::vector<uint64_t> other_axes;
        other_axes.reserve(ndim - 1);
        for(uint64_t d=0; d<ndim; ++d) if(d != static_cast<uint64_t>(axis)) other_axes.push_back(d);
        
        uint64_t num_others = 1;
        for(auto a : other_axes) num_others *= working_array.dimensions(a);

        FFTWPlan plan = Traits::plan_dft_(1, &n_int, 1,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, static_cast<int>(stride), 0,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, static_cast<int>(stride), 0,
                                         static_cast<int>(dir), FFTW_ESTIMATE | FFTW_UNALIGNED);

        // OPTIMIZATION: Pre-compute strides for offset calculation to avoid redundant divisions
        std::vector<uint64_t> axis_strides;
        axis_strides.reserve(other_axes.size());
        for(auto a : other_axes) axis_strides.push_back(working_array.strides()[a]);
        
        std::vector<uint64_t> axis_dims;
        axis_dims.reserve(other_axes.size());
        for(auto a : other_axes) axis_dims.push_back(working_array.dimensions(a));

        for (uint64_t i = 0; i < num_others; ++i) {
            uint64_t offset = 0;
            uint64_t temp = i;
            // Unroll common case of up to 3 dimensions for better performance
            for (size_t d = 0; d < other_axes.size(); ++d) {
                offset += (temp % axis_dims[d]) * axis_strides[d];
                temp /= axis_dims[d];
            }
            Traits::execute_dft(plan, reinterpret_cast<FFTWComplexType*>(data + offset), 
                                reinterpret_cast<FFTWComplexType*>(data + offset));
        }
        Traits::destroy_plan(plan);
    }

    if (perform_shift) {
        if (can_use_mask) apply_alternating_sign_mask_axis<T_Real>(working_array, axis); 
        else fftshift_axis<T_Real>(working_array, axis);
    }

    // OPTIMIZATION: Apply normalization factor with SIMD vectorization and restrict pointers
    T_Real factor = get_normalization_factor<T_Real>(dim_size, dir, norm);
    if (std::abs(factor - 1.0) > 1e-9) {  // Only apply if not unity
        std::complex<T_Real>* __restrict ndata = data;
        #pragma omp simd
        for (uint64_t i = 0; i < total_size; ++i) {
            ndata[i] *= factor;
        }
    }
    
    if (need_copy_back) {
        std::copy(working_array.get_data(), working_array.get_data() + working_array.size(), output.get_data());
    }
}


// --- THE MASTER FFTN WRAPPER ---
/**
 * @brief Performs 1D, 2D, 3D, or N-Dimensional FFT dynamically based on the requested axes.
 * Wraps the FFTPlan class logic for zero-friction one-off execution.
 */
template<typename T_Real>
void fftn(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          TransformDir dir,
          std::vector<uint64_t> axes = {}, // Defaults to all dimensions if empty
          bool perform_shift = true,
          Normalization norm = g_default_normalization) {

    if (input.ndim() != output.ndim() || input.size() != output.size()) {
        THROW_INVALID_ARGUMENT("FFTW::fftn: Input and output arrays must have matching dimensions and sizes.");
    }
    if (input.size() == 0) return;

    // If no axes specified, populate with ALL dimensions
    if (axes.empty()) {
        for(uint64_t i = 0; i < input.ndim(); ++i) axes.push_back(i);
    }

    std::sort(axes.begin(), axes.end());

    // Fallback logic for arbitrary 1D axes (handled perfectly by the custom looping in fft1)
    if (axes.size() == 1 && axes[0] != input.ndim() - 1) {
        fft1(input, output, dir, axes[0], perform_shift, norm);
        return;
    }

    // Validate that multi-axis targets are contiguous innermost dimensions
    bool is_innermost = true;
    if (axes.size() > input.ndim()) is_innermost = false;
    else {
        uint64_t start_axis = input.ndim() - axes.size();
        for (size_t i = 0; i < axes.size(); ++i) {
            if (axes[i] != start_axis + i) {
                is_innermost = false;
                break;  // Early exit on first mismatch
            }
        }
    }

    if (!is_innermost) {
        THROW_INVALID_ARGUMENT("FFTW::fftn: Multi-axis transforms must specify contiguous innermost axes (e.g. {1,2,3} for 3D). For arbitrary 1D transforms, specify a single axis.");
    }

    // Extract the full array shape - only allocate if needed
    std::vector<uint64_t> shape;
    shape.reserve(input.ndim());
    for(uint64_t i = 0; i < input.ndim(); ++i) shape.push_back(input.dimensions(i));

    // Instantiate a one-off FFTPlan using FFTW_ESTIMATE (zero planning overhead)
    FFTPlan<T_Real> temp_plan(shape, FFTW_ESTIMATE, axes, norm);

    bool is_in_place = (&input == &output);
    
    if (is_in_place) {
        if (dir == TransformDir::ImageToKspace) temp_plan.ImageToKspace(output, perform_shift);
        else temp_plan.KspaceToImage(output, perform_shift);
    } else {
        // Fast copy - std::copy is highly optimized and inlined by modern compilers
        std::copy(input.get_data(), input.get_data() + input.size(), output.get_data());
        if (dir == TransformDir::ImageToKspace) temp_plan.ImageToKspace(output, perform_shift);
        else temp_plan.KspaceToImage(output, perform_shift);
    }
}


// --- Deprecated Direct APIs ---
// Maintained for direct innermost slicing convenience, though fftn dynamically covers these.
template<typename T_Real>
void fft2(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          TransformDir dir, 
          bool perform_shift = true,
          Normalization norm = g_default_normalization) {
    
    if (input.ndim() < 2) THROW_INVALID_ARGUMENT("FFTW::fft2: Input array must be at least 2-dimensional.");
    
    std::vector<uint64_t> axes = {input.ndim() - 2, input.ndim() - 1};
    fftn(input, output, dir, axes, perform_shift, norm);
}

template<typename T_Real>
void fft3(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          TransformDir dir, 
          bool perform_shift = true,
          Normalization norm = g_default_normalization) {
    
    if (input.ndim() != 3) THROW_INVALID_ARGUMENT("FFTW::fft3: Input array must be exactly 3-dimensional.");
    fftn(input, output, dir, {0, 1, 2}, perform_shift, norm);
}


// =====================================================================================
// Wisdom & General Array Operations
// =====================================================================================

template <typename T_Real>
static bool save_wisdom(const std::string& filename) {
    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>,
                  "Wisdom saving only supports double or float precision.");
    FILE* fp = fopen(filename.c_str(), "w");
    if (!fp) {
        std::cerr << "Error: Could not open wisdom file for writing: " << filename << std::endl;
        return false;
    }
    if (std::is_same_v<T_Real, double>) {
        fftw_export_wisdom_to_file(fp);
    } else { 
        fftwf_export_wisdom_to_file(fp);
    }
    fclose(fp);
    return true;
}

template <typename T_Real>
static bool load_wisdom(const std::string& filename) {
    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>,
                  "Wisdom loading only supports double or float precision.");
    FILE* fp = fopen(filename.c_str(), "r");
    if (!fp) {
        std::cerr << "Warning: Could not open wisdom file for reading (file might not exist): " << filename << std::endl;
        return false;
    }
    bool success;
    if (std::is_same_v<T_Real, double>) {
        success = (fftw_import_wisdom_from_file(fp) != 0);
    } else { 
        success = (fftwf_import_wisdom_from_file(fp) != 0);
    }
    fclose(fp);
    if (!success) {
        std::cerr << "Warning: Failed to import FFTW wisdom from file: " << filename << std::endl;
    }
    return success;
}

template<typename T_Real> 
GPIArray::Array<std::complex<T_Real>> scale_mul(const GPIArray::Array<std::complex<T_Real>>& input_array, T_Real factor) {
    GPIArray::Array<std::complex<T_Real>> result = input_array.copy(); 
    for (uint64_t i = 0; i < result.size(); ++i) {
        result.get_data()[i] *= factor; 
    }
    return result;
}

template<typename T_Real> 
GPIArray::Array<std::complex<T_Real>> scale_div(const GPIArray::Array<std::complex<T_Real>>& input_array, T_Real factor) {
    GPIArray::Array<std::complex<T_Real>> result = input_array.copy(); 
    if (factor == static_cast<T_Real>(0)) {
        THROW_INVALID_ARGUMENT("Scale: Division by zero factor.");
    }
    for (uint64_t i = 0; i < result.size(); ++i) {
        result.get_data()[i] /= factor; 
    }
    return result;
}

template<typename T_Real>
Array<T_Real> dct(const Array<T_Real>& input) {
    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>, "DCT only supports float or double.");
    if (input.ndim() != 2) THROW_INVALID_ARGUMENT("DCT requires a 2D input array.");
    if (!input.is_contiguous()) THROW_INVALID_ARGUMENT("DCT input array must be contiguous.");

    using Traits = FFTWRealPrecisionTraits<T_Real>;
    Array<T_Real> output = input.empty_like();
    T_Real* in_ptr = input.get_data();
    T_Real* out_ptr = output.get_data();

    std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);
    
    typename Traits::PlanType plan = Traits::plan_r2r_2d(
        input.size(0), input.size(1),
        in_ptr, out_ptr,
        FFTW_REDFT10, FFTW_REDFT10,
        FFTW_ESTIMATE
    );

    if (!plan) THROW_RUNTIME_ERROR("FFTW: Failed to create DCT plan.");
    
    Traits::execute(plan);
    Traits::destroy_plan(plan);
    
    return output;
}

template<typename T_Real>
Array<T_Real> idct(const Array<T_Real>& input) {
    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>, "IDCT only supports float or double.");
    if (input.ndim() != 2) THROW_INVALID_ARGUMENT("IDCT requires a 2D input array.");
    if (!input.is_contiguous()) THROW_INVALID_ARGUMENT("IDCT input array must be contiguous.");

    using Traits = FFTWRealPrecisionTraits<T_Real>;
    Array<T_Real> output = input.empty_like();
    T_Real* in_ptr = input.get_data();
    T_Real* out_ptr = output.get_data();
    
    std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);

    typename Traits::PlanType plan = Traits::plan_r2r_2d(
        input.size(0), input.size(1),
        in_ptr, out_ptr,
        FFTW_REDFT01, FFTW_REDFT01,
        FFTW_ESTIMATE
    );

    if (!plan) THROW_RUNTIME_ERROR("FFTW: Failed to create IDCT plan.");
    
    Traits::execute(plan);
    Traits::destroy_plan(plan);

    T_Real normalization_factor = 1.0 / (4.0 * static_cast<T_Real>(input.size(0)) * static_cast<T_Real>(input.size(1)));
    output *= normalization_factor;
    
    return output;
}

} // namespace FFTW
} // namespace GPIArray

#endif // GPIArray_FFTW_HPP