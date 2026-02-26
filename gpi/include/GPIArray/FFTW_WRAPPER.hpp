/**
 * @file FFTW_WRAPPER.hpp
 * @brief FFTW-based multi-dimensional FFT and DCT wrapper for GPIArray::Array.
 *
 * This header provides the GPIArray::FFTW namespace, which implements efficient multi-dimensional
 * Fast Fourier Transform (FFT), Inverse FFT, Discrete Cosine Transform (DCT), and related operations
 * for GPIArray::Array containers using the FFTW library.
 *
 * Features:
 *   - Type-safe FFTW integration for std::complex<float> and std::complex<double>
 *   - 1D, 2D, 3D, and N-dimensional FFTs (forward and backward) with automatic centering (fftshift/ifftshift)
 *   - In-place and out-of-place transforms with normalization for inverse FFT
 *   - DCT-II (forward) and DCT-III (inverse) for real-valued 2D arrays
 *   - Thread-safe FFTW plan creation/destruction via global mutex
 *   - Wisdom import/export for FFTW plan optimization
 *   - Elementwise scaling utilities for complex arrays
 *   - Roll/shift and quadrant shifting (fftshift/ifftshift) for multi-dimensional arrays
 *   - FFTPlanManager class for persistent FFTW plan management and repeated transforms
 *
 * Limitations:
 *   - Axis-specific FFTs are not fully implemented; only full-dimension transforms are supported with automatic centering.
 *   - Requires GPIArray::Array to provide contiguous memory and shape/stride access.
 *
 * Usage:
 *   - Use fft1, fft2, fft3, fftn for complex FFTs; dct/idct for real DCTs.
 *   - Use FFTPlanManager for repeated transforms on fixed-size arrays.
 *   - Save/load FFTW wisdom for faster plan creation.
 *
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */

#ifndef GPIArray_FFTW_HPP
#define GPIArray_FFTW_HPP

#include <fftw3.h> // Include the FFTW library header (provides FFTW_FORWARD, FFTW_BACKWARD macros)
#include "Array.hpp" // For GPIArray::Array
#include "ArrayMacros.hpp" // For THROW_INVALID_ARGUMENT
#include <complex>   // For std::complex
#include <vector>
#include <numeric>   // For std::accumulate
#include <type_traits> // For std::is_same_v
#include <algorithm> // For std::min, std::max, std::reverse, std::copy
#include <cstdio>    // For fopen, fclose (for wisdom)
#include <string>    // For std::string (for wisdom filename)
#include <mutex>     // Include for std::mutex and std::lock_guard
#include <iostream>  // For std::cerr (used in wisdom functions)
#include <cstring>   // For std::memcpy (used in roll_axis_in_place)


namespace GPIArray {

namespace FFTW { // Namespace for FFTW integration

enum Normalization {
    NORM_NONE,     // No scaling (Forward: 1, Backward: 1)
    NORM_BACKWARD, // Standard (Forward: 1, Backward: 1/N)
    NORM_ORTHO     // Orthonormal (Forward: 1/sqrt(N), Backward: 1/sqrt(N))
};

// Helper to calculate normalization factors
template<typename T>
T get_normalization_factor(uint64_t N, int dir, Normalization norm) {
    if (norm == NORM_NONE) return static_cast<T>(1.0);
    if (norm == NORM_BACKWARD) {
        return (dir == FFTW_BACKWARD) ? static_cast<T>(1.0 / N) : static_cast<T>(1.0);
    }
    if (norm == NORM_ORTHO) {
        return static_cast<T>(1.0 / std::sqrt(static_cast<double>(N)));
    }
    return static_cast<T>(1.0);
}

// We are not creating a new enum Direction. We directly use FFTW_FORWARD and FFTW_BACKWARD macros from fftw3.h.
// Direction parameters will be 'int'.


// NEW: Global mutex to protect FFTW plan creation and destruction.
// This ensures that only one thread is creating/destroying plans at a time,
// which is safer, especially when using planning flags like FFTW_ESTIMATE (which updates wisdom).
static std::mutex g_fftw_plan_mutex;


// --- Type Trait to select FFTW functions based on complex type ---
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

// --- Type Trait for REAL-to-REAL FFT functions (for DCT/IDCT) ---
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

// In FFTW_WRAPPER.hpp

template<typename T_Real>
void roll_axis_in_place(GPIArray::Array<std::complex<T_Real>>& arr, uint64_t axis, int64_t shift_amount) {
    if (arr.ndim() == 0 || arr.dimensions(axis) <= 1) {
        return; // No shifting needed for 0D arrays or dimensions of size 0 or 1
    }

    uint64_t dim_size = arr.dimensions(axis);
    // Normalize shift to be positive and within the dimension's bounds
    int64_t normalized_shift_amount = (shift_amount % dim_size + dim_size) % dim_size;
    if (normalized_shift_amount == 0) {
        return; // No actual shift if normalized amount is 0
    }

    std::complex<T_Real>* raw_data = arr.get_data();
    const uint64_t* strides = arr.strides();
    const uint64_t axis_stride = strides[axis]; // Stride along the axis being shifted

    // Calculate the total number of independent 1D lines to shift along the specified axis.
    uint64_t num_lines_to_shift = 1;
    for (uint64_t d_idx = 0; d_idx < arr.ndim(); ++d_idx) {
        if (d_idx != axis) {
            num_lines_to_shift *= arr.dimensions(d_idx);
        }
    }

    // Allocate temporary buffers only if needed (i.e., if axis_stride != 1)
    std::unique_ptr<std::complex<T_Real>[], std::function<void(std::complex<T_Real>*)>> temp_line_buffer_owner = nullptr;
    std::complex<T_Real>* temp_line_buffer = nullptr;

    if (axis_stride != 1) { // If the axis is not contiguous, we need a temporary buffer
        if constexpr (std::is_same_v<T_Real, float>) {
            temp_line_buffer = static_cast<std::complex<T_Real>*>(fftwf_malloc(dim_size * sizeof(std::complex<T_Real>)));
            temp_line_buffer_owner = std::unique_ptr<std::complex<T_Real>[], std::function<void(std::complex<T_Real>*)>>(
                reinterpret_cast<std::complex<T_Real>*>(temp_line_buffer), [](std::complex<T_Real>* p){ fftwf_free(p); });
        } else { // double
            temp_line_buffer = static_cast<std::complex<T_Real>*>(fftw_malloc(dim_size * sizeof(std::complex<T_Real>)));
            temp_line_buffer_owner = std::unique_ptr<std::complex<T_Real>[], std::function<void(std::complex<T_Real>*)>>(
                reinterpret_cast<std::complex<T_Real>*>(temp_line_buffer), [](std::complex<T_Real>* p){ fftw_free(p); });
        }
        if (!temp_line_buffer) {
            THROW_RUNTIME_ERROR("Failed to allocate temporary buffer for non-contiguous roll_axis_in_place.");
        }
    }

    // Precompute all base_flat_idx values to avoid repeated calculations in the loop
    std::vector<uint64_t> all_base_flat_indices(num_lines_to_shift); //
    std::vector<uint64_t> current_coords_builder(arr.ndim()); // Temporary for building coordinates

    for (uint64_t line_master_idx = 0; line_master_idx < num_lines_to_shift; ++line_master_idx) { //
        uint64_t temp_line_idx = line_master_idx; //
        uint64_t base_flat_idx_val = 0; //
        // Reconstruct the N-dimensional coordinates and compute the base_flat_idx for this line
        for (uint64_t d_idx = 0; d_idx < arr.ndim(); ++d_idx) { //
            if (d_idx == axis) { //
                // This dimension is being shifted, its coordinate is not fixed for a 'line'
                current_coords_builder[d_idx] = 0; //
            } else { //
                current_coords_builder[d_idx] = temp_line_idx % arr.dimensions(d_idx); //
                temp_line_idx /= arr.dimensions(d_idx); //
                base_flat_idx_val += current_coords_builder[d_idx] * strides[d_idx]; //
            }
        }
        all_base_flat_indices[line_master_idx] = base_flat_idx_val; //
    }

    // Iterate over each independent line and apply the shift.
    for (uint64_t line_master_idx = 0; line_master_idx < num_lines_to_shift; ++line_master_idx) { //
        // Retrieve precomputed base_flat_idx
        uint64_t base_flat_idx = all_base_flat_indices[line_master_idx]; //

        if (axis_stride == 1) { // Optimized path for contiguous axis
            std::complex<T_Real>* line_start_ptr = raw_data + base_flat_idx;
            std::rotate(line_start_ptr, line_start_ptr + normalized_shift_amount, line_start_ptr + dim_size);
        } else { // Original path for non-contiguous axis, using temporary buffer
            // 1. Extract the 1D line into `temp_line_buffer`.
            for (uint64_t i_line_elem = 0; i_line_elem < dim_size; ++i_line_elem) { //
                temp_line_buffer[i_line_elem] = raw_data[base_flat_idx + i_line_elem * axis_stride]; //
            }

            // 2. Perform the circular shift on `temp_line_buffer`.
            // Use std::rotate for the shift. This is generally more robust than manual memcpy for circular shifts.
            std::rotate(temp_line_buffer, temp_line_buffer + normalized_shift_amount, temp_line_buffer + dim_size);

            // 3. Put the shifted line back into the array from the `temp_line_buffer`.
            for (uint64_t i_line_elem = 0; i_line_elem < dim_size; ++i_line_elem) { //
                raw_data[base_flat_idx + i_line_elem * axis_stride] = temp_line_buffer[i_line_elem]; //
            }
        }
    }
    // `temp_line_buffer_owner` will automatically free `temp_line_buffer` when it goes out of scope.
}


// =====================================================================================
// Quadrant Shifting: fftshift and ifftshift (Optimized for efficiency)
// These functions perform in-place shifting by using a temporary copy for faster element reordering.
// =====================================================================================

template<typename T_Real>
void fftshift(GPIArray::Array<std::complex<T_Real>>& arr) {
    const uint64_t ndim = arr.ndim();
    if (arr.size() <= 1) return;

    // Apply roll along each dimension
    for (uint64_t d = 0; d < ndim; ++d) {
        // For fftshift, it's typically a left shift by floor(N/2).
        int64_t shift_amount = arr.dimensions(d) / 2; // Floor division
        roll_axis_in_place(arr, d, shift_amount); // roll_axis_in_place now performs a LEFT shift
    }
}

// ifftshift: In-place version. Inverse of fftshift.
template<typename T_Real>
void ifftshift(GPIArray::Array<std::complex<T_Real>>& arr) {
    const uint64_t ndim = arr.ndim();
    if (arr.size() <= 1) return;

    // Apply roll along each dimension
    for (uint64_t d = 0; d < ndim; ++d) {
        // For ifftshift, it's typically a left shift by ceil(N/2).
        int64_t shift_amount = (arr.dimensions(d) + 1) / 2; // Ceiling division
        roll_axis_in_place(arr, d, shift_amount); // roll_axis_in_place now performs a LEFT shift
    }
}

// fftshift on a single axis only - properly using roll without complex workarounds
template<typename T_Real>
void fftshift_axis(GPIArray::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size() <= 1 || arr.dimensions(axis) <= 1) return;
    int64_t shift_amount = arr.dimensions(axis) / 2; // Floor division
    roll_axis_in_place(arr, axis, shift_amount);
}

// ifftshift on a single axis only - properly using roll without complex workarounds
template<typename T_Real>
void ifftshift_axis(GPIArray::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size() <= 1 || arr.dimensions(axis) <= 1) return;
    int64_t shift_amount = (arr.dimensions(axis) + 1) / 2; // Ceiling division
    roll_axis_in_place(arr, axis, shift_amount);
}

// Apply alternating sign mask along a single axis (fast alternative to ifftshift/fftshift)
// Uses scalar multiplication by ±1 pattern, matching FFTPlanManager's approach
template<typename T_Real>
void apply_alternating_sign_mask_axis(GPIArray::Array<std::complex<T_Real>>& arr, uint64_t axis) {
    if (arr.size() <= 1 || arr.dimensions(axis) <= 1) return;
    
    uint64_t dim_size = arr.dimensions(axis);
    uint64_t stride = arr.strides()[axis];
    uint64_t total_size = arr.size();
    
    std::complex<T_Real>* data = arr.get_data();
    
    // Pre-compute the alternating mask for this axis
    std::vector<T_Real> mask(total_size);
    
    for (uint64_t i = 0; i < total_size; ++i) {
        // Compute index along the FFT axis
        uint64_t idx_along_axis = (i / stride) % dim_size;
        // Sign is +1 if index is even, -1 if odd
        mask[i] = (idx_along_axis % 2 == 0) ? static_cast<T_Real>(1.0) : static_cast<T_Real>(-1.0);
    }
    
    // Apply mask with scalar multiplication
    for (uint64_t i = 0; i < total_size; ++i) {
        data[i] *= mask[i];
    }
}



// =====================================================================================
// Core FFT Implementation: fft_impl (now only used by fftn for general N-D)
// Template for complex<double> or complex<float>. Direction parameter is 'int'.
// =====================================================================================
template<typename T_Real> // T_Real will be float or double
void fft_impl(const GPIArray::Array<std::complex<T_Real>>& input,
              GPIArray::Array<std::complex<T_Real>>& output,
              int dir, // Passed directly from FFTW_FORWARD/FFTW_BACKWARD macros
              const std::vector<uint64_t>& n_dims_vec, // Dimensions for the FFT of ONE transform
              uint64_t howmany_transforms, // NEW: Number of transforms to batch
              uint64_t input_dist,        // NEW: Input distance between transforms
              uint64_t output_dist,       // NEW: Output distance between transforms
              unsigned int plan_flags = FFTW_ESTIMATE,
              Normalization norm = NORM_ORTHO) { // Added plan_flags for individual calls

    // Compile-time check for supported complex types
    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>,
                  "FFTW operations only support std::complex<double> or std::complex<float>.");

    // Select the correct FFTW precision traits
    using Traits = FFTWPrecisionTraits<std::complex<T_Real>>;
    using FFTWComplexType = typename Traits::FFTWComplexType;
    using FFTWPlan = typename Traits::PlanType;

    // Validate input/output array compatibility
    if (input.ndim() != output.ndim() || input.size() != output.size()) {
        THROW_INVALID_ARGUMENT("FFTW: Input and output arrays must have matching dimensions and sizes.");
    }

    if (input.size() == 0) { // Handle empty arrays
        return;
    }

    // Convert dimensions to int array as required by FFTW
    std::vector<int> n_dims_int(n_dims_vec.begin(), n_dims_vec.end());

    // Get raw pointers to data from GPIArray::Array
    FFTWComplexType* in_ptr = reinterpret_cast<FFTWComplexType*>(input.get_data());
    FFTWComplexType* out_ptr = reinterpret_cast<FFTWComplexType*>(output.get_data());

    FFTWPlan plan_instance; // Declare plan_instance here

    // NEW: Lock to protect plan creation and destruction
    std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);

    // Create the plan
    plan_instance = Traits::plan_dft_( // This now points to fftw_plan_many_dft
        static_cast<int>(n_dims_int.size()), // rank
        n_dims_int.data(),                   // n (dimensions of one transform)
        static_cast<int>(howmany_transforms),// howmany (number of transforms to batch)
        in_ptr,                              // in
        NULL,                                // inembed (NULL for contiguous)
        1,                                   // istride (1 for contiguous data within one transform)
        static_cast<int>(input_dist),        // idist (distance between first elements of successive transforms)
        out_ptr,                             // out
        NULL,                                // onembed (NULL for contiguous)
        1,                                   // ostride (1 for contiguous data within one transform)
        static_cast<int>(output_dist),       // odist (distance between first elements of successive transforms in output)
        dir,                                 // sign
        plan_flags | FFTW_UNALIGNED          // flags (combine with FFTW_UNALIGNED for generic arrays)
    );

    if (!plan_instance) {
        THROW_RUNTIME_ERROR("FFTW::fft_impl: Failed to create FFTW plan.");
    }
    
    // Execute the plan
    Traits::execute(plan_instance);
    
    // Destroy the plan immediately after use
    Traits::destroy_plan(plan_instance);

    // Normalization:
    uint64_t N_one_transform = 1;
    for (uint64_t dim_size : n_dims_vec) N_one_transform *= dim_size;

    T_Real factor = get_normalization_factor<T_Real>(N_one_transform, dir, norm);
    
    if (std::abs(factor - 1.0) > 1e-9) {
        std::complex<T_Real>* data = output.get_data();
        for (uint64_t i = 0; i < output.size(); ++i) {
            data[i] *= factor;
        }
    }
}


// =====================================================================================
// Public API Functions (Wrapper functions) for FFT
// Templated for float or double complex types. Direction parameter is 'int'.
// These functions now handle their own plan creation/destruction.
// =====================================================================================

// N-Dimensional FFT along ALL axes: fftn(input, output, direction)
template<typename T_Real>
void fftn(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          int dir) {

    // Validate input/output array compatibility
    if (input.ndim() != output.ndim() || input.size() != output.size()) {
        THROW_INVALID_ARGUMENT("FFTW::fftn: Input and output arrays must have matching dimensions and sizes.");
    }
    if (input.size() == 0) {
        return; // Nothing to do for empty arrays
    }

    bool is_in_place = (&input == &output);
    GPIArray::Array<std::complex<T_Real>>* working_arr_ptr;
    GPIArray::Array<std::complex<T_Real>> temp_arr_storage;
    if (is_in_place) {
        working_arr_ptr = &output;
    } else {
        temp_arr_storage = input.copy();
        working_arr_ptr = &temp_arr_storage;
    }
    GPIArray::Array<std::complex<T_Real>>& working_arr = *working_arr_ptr;

    std::vector<uint64_t> n_dims(input.ndim());
    for (uint64_t i = 0; i < input.ndim(); ++i) {
        n_dims[i] = input.dimensions(i); // All dimensions are transformed
    }

    // For fftn (transforming all dimensions), howmany is 1, and dist is the total size.
    uint64_t howmany_transforms = 1;
    uint64_t dist = input.size(); // Total size of the array, as it's one big transform

    // Apply first shift to the data in the working array
    ifftshift<T_Real>(working_arr);

    // Perform the core FFTW transform using the new fft_impl signature
    // The fft_impl now takes non-const references so it can be used for in-place operations easily.
    fft_impl<T_Real>(working_arr, working_arr, dir, n_dims, howmany_transforms, dist, dist);

    // Apply second shift to the data in the working array
    fftshift<T_Real>(working_arr);

    // If it was an out-of-place transform, copy the final result from the temporary array to output.
    if (!is_in_place) {
        std::copy(working_arr.get_data(), working_arr.get_data() + working_arr.size(), output.get_data());
    }
}


// 1D FFT: fft1(input, output, direction) - Now uses fftw_plan_dft_1d
template<typename T_Real>
void fft1(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          int dir,
          int64_t axis = -1) {

    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>,
                  "FFTW operations only support std::complex<double> or std::complex<float>.");

    using Traits = FFTWPrecisionTraits<std::complex<T_Real>>;
    using FFTWComplexType = typename Traits::FFTWComplexType;
    using FFTWPlan = typename Traits::PlanType;

    if (input.size() == 0) return;

    uint64_t ndim = input.ndim();
    if (axis < 0) axis = static_cast<int64_t>(ndim) - 1; // Default to innermost
    if (axis >= static_cast<int64_t>(ndim)) THROW_INVALID_ARGUMENT("FFTW::fft1: axis out of range.");

    uint64_t dim_size = input.dimensions(axis);

    // Check if there are any singleton dimensions in non-FFT axes
    bool has_singleton_non_fft = false;
    for (uint64_t d = 0; d < ndim; ++d) {
        if (d != static_cast<uint64_t>(axis) && input.dimensions(d) == 1) {
            has_singleton_non_fft = true;
            break;
        }
    }
    
    // Check if we can use the fast alternating mask (only when FFT axis is even)
    bool can_use_mask = (dim_size % 2 == 0);

    // Always work on a contiguous array if output is not contiguous or if out-of-place
    bool is_in_place = (&input == &output);
    bool need_copy_back = (!is_in_place) || (has_singleton_non_fft && !output.is_contiguous());
    
    GPIArray::Array<std::complex<T_Real>> temporary_array;
    Array<std::complex<T_Real>>* working_array_ptr;
    
    if (!is_in_place) {
        // Out-of-place: create contiguous copy from input to work on
        temporary_array = input.copy();
        working_array_ptr = &temporary_array;
    } else if (has_singleton_non_fft && !output.is_contiguous()) {
        // In-place but non-contiguous: create contiguous copy from output
        temporary_array = output.copy();
        working_array_ptr = &temporary_array;
    } else {
        // In-place and contiguous (or no singletons): work directly on output
        working_array_ptr = &output;
    }
    
    // Work with the array (either output or temporary contiguous copy)
    GPIArray::Array<std::complex<T_Real>>& working_array = *working_array_ptr;
    
    // Work with the working array
    uint64_t stride = working_array.strides()[axis];
    
    std::complex<T_Real>* data = working_array.get_data();
    uint64_t total_size = working_array.size();

    // Apply centering before FFT: use fast mask for even dimensions, rolls for odd
    if (can_use_mask) {
        apply_alternating_sign_mask_axis<T_Real>(working_array, axis);
    } else {
        ifftshift_axis<T_Real>(working_array, axis);
    }

    std::lock_guard<std::mutex> lock(g_fftw_plan_mutex); // Thread safety

    int n_int = static_cast<int>(dim_size);
    // Path 1: Innermost contiguous axis allows for one batch plan
    if (axis == static_cast<int64_t>(ndim) - 1 && working_array.is_contiguous()) {
        int howmany = static_cast<int>(total_size / dim_size);
        FFTWPlan plan = Traits::plan_dft_(1, &n_int, howmany,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, 1, n_int,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, 1, n_int,
                                         dir, FFTW_ESTIMATE | FFTW_UNALIGNED);
        Traits::execute(plan);
        Traits::destroy_plan(plan);
    } 
    // Path 2: Loop for non-contiguous or mid-volume axes
    else {
        std::vector<uint64_t> other_axes;
        for(uint64_t d=0; d<ndim; ++d) if(d != static_cast<uint64_t>(axis)) other_axes.push_back(d);
        
        uint64_t num_others = 1;
        for(auto a : other_axes) num_others *= working_array.dimensions(a);

        FFTWPlan plan = Traits::plan_dft_(1, &n_int, 1,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, static_cast<int>(stride), 0,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, static_cast<int>(stride), 0,
                                         dir, FFTW_ESTIMATE | FFTW_UNALIGNED);

        for (uint64_t i = 0; i < num_others; ++i) {
            uint64_t offset = 0;
            uint64_t temp = i;
            for (int j = static_cast<int>(other_axes.size()) - 1; j >= 0; --j) {
                uint64_t a = other_axes[j];
                offset += (temp % working_array.dimensions(a)) * working_array.strides()[a];
                temp /= working_array.dimensions(a);
            }
            Traits::execute_dft(plan, reinterpret_cast<FFTWComplexType*>(data + offset), 
                                reinterpret_cast<FFTWComplexType*>(data + offset));
        }
        Traits::destroy_plan(plan);
    }

    // Apply de-centering after FFT: use fast mask for even dimensions (self-inverse), rolls for odd
    if (can_use_mask) {
        apply_alternating_sign_mask_axis<T_Real>(working_array, axis); // Self-inverse for even sizes
    } else {
        fftshift_axis<T_Real>(working_array, axis);
    }

    // Unitary scaling (only for backward/inverse transform)
    if (dir == FFTW_BACKWARD) {
        T_Real norm = 1.0 / static_cast<T_Real>(dim_size);
        for (uint64_t i = 0; i < total_size; ++i) data[i] *= norm;
    }
    
    // Copy back to output if we worked on a temporary array
    if (need_copy_back) {
        std::copy(working_array.get_data(), working_array.get_data() + working_array.size(), output.get_data());
    }
}


// 2D FFT: fft2(input, output, direction) - Now uses fftw_plan_dft_2d
template<typename T_Real>
void fft2(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          int dir,
          Normalization norm = NORM_ORTHO) {
    // Compile-time check for supported complex types
    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>,
                  "FFTW operations only support std::complex<double> or std::complex<float>.");

    // Select the correct FFTW precision traits
    using Traits = FFTWPrecisionTraits<std::complex<T_Real>>;
    using FFTWComplexType = typename Traits::FFTWComplexType;
    using FFTWPlan = typename Traits::PlanType; // Use the general plan type

    // Validate input/output array compatibility
    if (input.ndim() != output.ndim() || input.size() != output.size()) {
        THROW_INVALID_ARGUMENT("FFTW::fft2: Input and output arrays must have matching dimensions and sizes.");
    }

    // Ensure it's a 2D array
    if (input.ndim() != 2) {
        THROW_INVALID_ARGUMENT("FFTW::fft2: Input array must be 2-dimensional.");
    }
    if (input.size() == 0) {
        return; // Nothing to do for empty arrays
    }

    bool is_in_place = (&input == &output);
    GPIArray::Array<std::complex<T_Real>>* working_arr_ptr;
    GPIArray::Array<std::complex<T_Real>> temp_arr_storage;
    if (is_in_place) {
        working_arr_ptr = &output;
    } else {
        temp_arr_storage = input.copy();
        working_arr_ptr = &temp_arr_storage;
    }
    GPIArray::Array<std::complex<T_Real>>& working_arr = *working_arr_ptr;

    // Apply pre-FFT shift
    ifftshift<T_Real>(working_arr);

    // Get raw pointers to data from the working GPIArray::Array
    FFTWComplexType* actual_in_ptr = reinterpret_cast<FFTWComplexType*>(working_arr.get_data());
    FFTWComplexType* actual_out_ptr = reinterpret_cast<FFTWComplexType*>(working_arr.get_data());

    FFTWPlan plan; // Declare plan here

    // NEW: Lock to protect plan creation and destruction
    std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);

    // Create the specialized 2D plan
    plan = Traits::plan_dft_2d(
        static_cast<int>(working_arr.dimensions(0)), // n0
        static_cast<int>(working_arr.dimensions(1)), // n1
        actual_in_ptr, actual_out_ptr, // in, out
        dir, // sign
        FFTW_ESTIMATE // flags
    );

    if (!plan) { THROW_RUNTIME_ERROR("FFTW::fft2: Failed to create 2D FFTW plan."); }

    // Execute the plan
    Traits::execute(plan);
    Traits::destroy_plan(plan); // Destroy plan immediately after use

    // Apply post-FFT shift
    fftshift<T_Real>(working_arr);

    // Dynamic Normalization
    uint64_t N = working_arr.dimensions(0) * working_arr.dimensions(1);
    T_Real factor = get_normalization_factor<T_Real>(N, dir, norm);
    
    if (std::abs(factor - 1.0) > 1e-9) {
        std::complex<T_Real>* data = working_arr.get_data();
        for (uint64_t i = 0; i < working_arr.size(); ++i) data[i] *= factor;
    }

    if (!is_in_place) {
        std::copy(working_arr.get_data(), working_arr.get_data() + working_arr.size(), output.get_data());
    }

    // If it was an out-of-place transform, copy the final result from the temporary array to output.
    if (!is_in_place) {
        std::copy(working_arr.get_data(), working_arr.get_data() + working_arr.size(), output.get_data());
    }
}


// 3D FFT: fft3(input, output, direction) - Now uses fftw_plan_dft_3d
template<typename T_Real>
void fft3(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          int dir,
          Normalization norm = NORM_ORTHO) {
    // Compile-time check for supported complex types
    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>,
                  "FFTW operations only support std::complex<double> or std::complex<float>.");

    // Select the correct FFTW precision traits
    using Traits = FFTWPrecisionTraits<std::complex<T_Real>>;
    using FFTWComplexType = typename Traits::FFTWComplexType;
    using FFTWPlan = typename Traits::PlanType; // Use the general plan type

    // Validate input/output array compatibility
    if (input.ndim() != output.ndim() || input.size() != output.size()) {
        THROW_INVALID_ARGUMENT("FFTW::fft3: Input and output arrays must have matching dimensions and sizes.");
    }

    // Ensure it's a 3D array
    if (input.ndim() != 3) {
        THROW_INVALID_ARGUMENT("FFTW::fft3: Input array must be 3-dimensional.");
    }
    if (input.size() == 0) {
        return; // Nothing to do for empty arrays
    }

    bool is_in_place = (&input == &output);
    GPIArray::Array<std::complex<T_Real>>* working_arr_ptr;
    GPIArray::Array<std::complex<T_Real>> temp_arr_storage;
    if (is_in_place) {
        working_arr_ptr = &output;
    } else {
        temp_arr_storage = input.copy();
        working_arr_ptr = &temp_arr_storage;
    }
    GPIArray::Array<std::complex<T_Real>>& working_arr = *working_arr_ptr;

    // Apply pre-FFT shift
    ifftshift<T_Real>(working_arr);

    // Get raw pointers to data from the working GPIArray::Array
    FFTWComplexType* actual_in_ptr = reinterpret_cast<FFTWComplexType*>(working_arr.get_data());
    FFTWComplexType* actual_out_ptr = reinterpret_cast<FFTWComplexType*>(working_arr.get_data());

    FFTWPlan plan; // Declare plan here

    // NEW: Lock to protect plan creation and destruction
    std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);

    // Create the specialized 3D plan
    plan = Traits::plan_dft_3d(
        static_cast<int>(working_arr.dimensions(0)), // n0
        static_cast<int>(working_arr.dimensions(1)), // n1
        static_cast<int>(working_arr.dimensions(2)), // n2
        actual_in_ptr, actual_out_ptr, // in, out
        dir, // sign
        FFTW_ESTIMATE // flags
    );

    if (!plan) { THROW_RUNTIME_ERROR("FFTW::fft3: Failed to create 3D FFTW plan."); }

    // Execute the plan
    Traits::execute(plan);
    Traits::destroy_plan(plan); // Destroy plan immediately after use

    // Apply post-FFT shift
    fftshift<T_Real>(working_arr);

    // --- Dynamic Normalization Logic ---
    uint64_t N_total = static_cast<uint64_t>(working_arr.dimensions(0)) *
                       static_cast<uint64_t>(working_arr.dimensions(1)) *
                       static_cast<uint64_t>(working_arr.dimensions(2));
    
    T_Real factor = get_normalization_factor<T_Real>(N_total, dir, norm);
    
    // Apply scaling if factor is not 1.0
    if (std::abs(factor - static_cast<T_Real>(1.0)) > static_cast<T_Real>(1e-9)) {
        std::complex<T_Real>* data = working_arr.get_data();
        for (uint64_t i = 0; i < working_arr.size(); ++i) {
            data[i] *= factor;
        }
    }

    // If it was an out-of-place transform, copy the final result from the temporary array to output.
    if (!is_in_place) {
        std::copy(working_arr.get_data(), working_arr.get_data() + working_arr.size(), output.get_data());
    }
}

// FFT along specified axes (currently throws, needs advanced FFTW planning)
// --- CORRECTED LOGIC FOR AXES-SPECIFIC FFT ---
template<typename T_Real>
void fftn(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          const std::vector<uint64_t>& axes, // Axes to transform along
          int dir) {

    // If axes vector is empty, default to all axes, and use the existing fftn overload.
    if (axes.empty()) {
        fftn<T_Real>(input, output, dir); // This will handle shifting for all axes
        return;
    }

    // For specific axes, the shifting needs to be applied only to those axes.
    // This requires a more complex `fftshift` and `ifftshift` implementation that
    // can operate on specified axes, and `fft_impl` would also need to support
    // planning for specific axes.
    // Current `fftshift`/`ifftshift` operates on all dimensions.
    // If you need axis-specific shifting and FFTs, you'll need to implement those.
    THROW_INVALID_ARGUMENT("FFTW: FFT along specified axes is currently NOT fully implemented "
                           "with axis-specific shifting. Only fft1, fft2, fft3, and fftn (all axes) "
                           "provide automatic centering. For specific axes, you may need to apply "
                           "fftshift/ifftshift manually on those axes before/after the FFT if your "
                           "FFT implementation supports it.");
}


/**
 * @brief Saves the current FFTW wisdom to a file.
 * This function uses fftw_export_wisdom_to_file (or fftwf_export_wisdom_to_file for float).
 *
 * @param filename The path to the file where wisdom should be saved.
 * @return True if wisdom was successfully saved, false otherwise.
 */
template <typename T_Real>
static bool save_wisdom(const std::string& filename) {
    static_assert(std::is_same_v<T_Real, double> || std::is_same_v<T_Real, float>,
                  "Wisdom saving only supports double or float precision.");
    FILE* fp = fopen(filename.c_str(), "w");
    if (!fp) {
        std::cerr << "Error: Could not open wisdom file for writing: " << filename << std::endl;
        return false;
    }
    // Use the appropriate export function based on precision.
    if (std::is_same_v<T_Real, double>) {
        fftw_export_wisdom_to_file(fp);
    } else { // float
        fftwf_export_wisdom_to_file(fp);
    }
    fclose(fp);
    return true;
}

/**
 * @brief Loads FFTW wisdom from a file.
 * This function uses fftw_import_wisdom_from_file (or fftwf_import_wisdom_from_file for float).
 *
 * @param filename The path to the file from which wisdom should be loaded.
 * @return True if wisdom was successfully loaded, false otherwise.
 */
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
    } else { // float
        success = (fftwf_import_wisdom_from_file(fp) != 0);
    }
    fclose(fp);
    if (!success) {
        std::cerr << "Warning: Failed to import FFTW wisdom from file: " << filename << std::endl;
    }
    return success;
}


// =====================================================================================
// Scaling Functions (Element-wise multiplication and division by a scalar)
// =====================================================================================

// Element-wise scaling by a scalar (multiplication)
template<typename T_Real> // T_Real corresponds to the real part of the complex type (float or double)
GPIArray::Array<std::complex<T_Real>> scale_mul(const GPIArray::Array<std::complex<T_Real>>& input_array, T_Real factor) {
    GPIArray::Array<std::complex<T_Real>> result = input_array.copy(); // Operate on a copy
    for (uint64_t i = 0; i < result.size(); ++i) {
        result.get_data()[i] *= factor; // Uses std::complex<T>::operator*=
    }
    return result;
}

// Element-wise scaling by a scalar (division)
template<typename T_Real> // T_Real corresponds to the real part of the complex type (float or double)
GPIArray::Array<std::complex<T_Real>> scale_div(const GPIArray::Array<std::complex<T_Real>>& input_array, T_Real factor) {
    GPIArray::Array<std::complex<T_Real>> result = input_array.copy(); // Operate on a copy
    if (factor == static_cast<T_Real>(0)) {
        THROW_INVALID_ARGUMENT("Scale: Division by zero factor.");
    }
    for (uint64_t i = 0; i < result.size(); ++i) {
        result.get_data()[i] /= factor; // Uses std::complex<T>::operator/=
    }
    return result;
}

// --- DCT and IDCT implementations ---

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

/**
 * @brief Thread-safe FFTW Plan Manager for N-Dimensional batched transforms.
 * Configured for total shape first, with optional specific axes transform.
 */
/**
 * @brief Thread-safe FFTW Plan Manager for N-Dimensional batched transforms.
 * Configured for total shape first, with optional specific axes transform.
 */
template<typename T_Real>
class FFTPlanManager {
public:
    using ComplexT = std::complex<T_Real>;
    using Traits = FFTWPrecisionTraits<ComplexT>;
    using FFTWComplexType = typename Traits::FFTWComplexType;
    using FFTWPlan = typename Traits::PlanType;

private:
    std::vector<int> _fft_dims;      // Rank dimensions of the actual FFT
    FFTWPlan _forward_plan = nullptr;
    FFTWPlan _backward_plan = nullptr;
    unsigned int _plan_flags;
    int _howmany;
    int _dist;
    int _total_elements;
    std::vector<T_Real> _alternating_mask; 
    bool _use_optimized_shift = false;
    Normalization _norm_method;

    // Faster shift path: Check if all dimensions being transformed are even
    bool check_all_dims_even() const {
        for (int dim : _fft_dims) if (dim % 2 != 0) return false;
        return true;
    }

    void generate_alternating_mask() {
        if (!_use_optimized_shift) return; 
        uint64_t vol_size = 1;
        for (int dim : _fft_dims) vol_size *= dim;
        _alternating_mask.resize(vol_size);
        
        std::vector<uint64_t> contrived_strides(_fft_dims.size());
        if (!_fft_dims.empty()) {
            contrived_strides[_fft_dims.size() - 1] = 1;
            for (int i = (int)_fft_dims.size() - 2; i >= 0; --i) {
                contrived_strides[i] = contrived_strides[i + 1] * _fft_dims[i + 1];
            }
        }

        std::vector<uint64_t> current_coords(_fft_dims.size(), 0);
        std::function<void(uint64_t)> recurse = [&](uint64_t dim) {
            if (dim == _fft_dims.size()) {
                uint64_t flat_idx = 0;
                uint64_t parity_sum = 0;
                for(uint64_t d = 0; d < _fft_dims.size(); ++d) {
                    flat_idx += current_coords[d] * contrived_strides[d];
                    parity_sum += current_coords[d];
                }
                _alternating_mask[flat_idx] = (parity_sum % 2 == 0) ? 
                    static_cast<T_Real>(1.0) : static_cast<T_Real>(-1.0);
                return;
            }
            for (int i = 0; i < _fft_dims[dim]; ++i) {
                current_coords[dim] = i;
                recurse(dim + 1);
            }
        };
        if (vol_size > 0) recurse(0);
    }

    // Apply pre-computed sign mask to the whole contiguous buffer
    void apply_mask_in_place(GPIArray::Array<ComplexT>& in_out_array) const {
        ComplexT* data = in_out_array.get_data();
        uint64_t size = in_out_array.size();
        uint64_t mask_size = _alternating_mask.size();
        for (uint64_t i = 0; i < size; ++i) data[i] *= _alternating_mask[i % mask_size]; 
    }

    void apply_normalization(GPIArray::Array<ComplexT>& arr, int dir) const {
        uint64_t N = 1;
        for (int dim : _dims_int) N *= dim;
        T_Real factor = get_normalization_factor<T_Real>(N, dir, _norm_method);
        
        if (std::abs(factor - 1.0) > 1e-9) {
            ComplexT* data = arr.get_data();
            for (uint64_t i = 0; i < arr.size(); ++i) data[i] *= factor;
        }
    }

public:
    /**
     * @param total_array_shape The full shape of the container (e.g., {340, 340, 84}).
     * @param plan_flags FFTW planning flags (defaulting to FFTW_ESTIMATE).
     * @param transform_dims Optional: Axes to transform. If empty, performs full ND FFT.
     */
    FFTPlanManager(const std::vector<uint64_t>& total_array_shape, 
                   unsigned int plan_flags = FFTW_ESTIMATE,
                   const std::vector<uint64_t>& transform_dims = {},
                   Normalization norm = NORM_ORTHO)
        : _plan_flags(plan_flags), _norm_method(norm) {
        
        if (total_array_shape.empty()) THROW_INVALID_ARGUMENT("FFTPlanManager: total_array_shape cannot be empty.");

        // 1. Determine which dimensions to transform
        std::vector<uint64_t> target_dims = transform_dims.empty() ? total_array_shape : transform_dims;

        // 2. Validation: Ensure transform_dims match the innermost (last) axes for contiguity
        if (!transform_dims.empty()) {
            if (transform_dims.size() > total_array_shape.size()) {
                THROW_INVALID_ARGUMENT("FFTPlanManager: transform_dims rank exceeds total_array_shape ndim.");
            }
            size_t start_axis = total_array_shape.size() - transform_dims.size();
            for (size_t i = 0; i < transform_dims.size(); ++i) {
                if (transform_dims[i] != total_array_shape[start_axis + i]) {
                    THROW_INVALID_ARGUMENT("FFTPlanManager: transform_dims must match the innermost (last) axes.");
                }
            }
        }

        // 3. Configure FFTW Batch Parameters
        _dist = 1;
        for (uint64_t d : target_dims) {
            _fft_dims.push_back(static_cast<int>(d));
            _dist *= static_cast<int>(d);
        }

        _total_elements = 1;
        for (uint64_t d : total_array_shape) _total_elements *= d;
        _howmany = static_cast<int>(_total_elements / _dist);

        _use_optimized_shift = check_all_dims_even();
        generate_alternating_mask();

        // 4. Thread-Safe Planning using global mutex
        FFTWComplexType* dummy;
        size_t alloc_bytes = (size_t)_total_elements * sizeof(ComplexT);
        if constexpr (std::is_same_v<T_Real, float>) dummy = (FFTWComplexType*)fftwf_malloc(alloc_bytes);
        else dummy = (FFTWComplexType*)fftw_malloc(alloc_bytes);

        {
            std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);
            _forward_plan = Traits::plan_dft_((int)_fft_dims.size(), _fft_dims.data(), _howmany,
                dummy, NULL, 1, _dist, dummy, NULL, 1, _dist, 
                FFTW_FORWARD, _plan_flags | FFTW_UNALIGNED);

            _backward_plan = Traits::plan_dft_((int)_fft_dims.size(), _fft_dims.data(), _howmany,
                dummy, NULL, 1, _dist, dummy, NULL, 1, _dist, 
                FFTW_BACKWARD, _plan_flags | FFTW_UNALIGNED);
        }

        if constexpr (std::is_same_v<T_Real, float>) fftwf_free(dummy); else fftw_free(dummy);
        if (!_forward_plan || !_backward_plan) THROW_RUNTIME_ERROR("FFTPlanManager: Failed to create plans.");
    }

    ~FFTPlanManager() {
        std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);
        if (_forward_plan) Traits::destroy_plan(_forward_plan);
        if (_backward_plan) Traits::destroy_plan(_backward_plan);
    }

    void execute_forward(GPIArray::Array<ComplexT>& in_out_array, bool perform_shift = true) const {
        if (in_out_array.size() != static_cast<uint64_t>(_total_elements)) {
            THROW_INVALID_ARGUMENT("FFTPlanManager::execute_forward: Input array size does not match the planned dimensions.");
        }
        if(perform_shift){
            if (_use_optimized_shift) apply_mask_in_place(in_out_array);
            else FFTW::ifftshift<T_Real>(in_out_array);
        }
        Traits::execute_dft(_forward_plan, reinterpret_cast<FFTWComplexType*>(in_out_array.get_data()), 
                            reinterpret_cast<FFTWComplexType*>(in_out_array.get_data()));
        if(perform_shift){
            if (_use_optimized_shift) apply_mask_in_place(in_out_array);
            else FFTW::fftshift<T_Real>(in_out_array);
        }

        apply_normalization(in_out_array, FFTW_FORWARD);
    }

    void execute_backward(GPIArray::Array<ComplexT>& in_out_array, bool perform_shift = true) const {
        if (in_out_array.size() != static_cast<uint64_t>(_total_elements)) {
            THROW_INVALID_ARGUMENT("FFTPlanManager::execute_backward: Input array size does not match the planned dimensions.");
        }
        if(perform_shift){
            if (_use_optimized_shift) apply_mask_in_place(in_out_array);
            else FFTW::ifftshift<T_Real>(in_out_array);
        }
        Traits::execute_dft(_backward_plan, reinterpret_cast<FFTWComplexType*>(in_out_array.get_data()), 
                            reinterpret_cast<FFTWComplexType*>(in_out_array.get_data()));
        if(perform_shift){
            if (_use_optimized_shift) apply_mask_in_place(in_out_array);
            else FFTW::fftshift<T_Real>(in_out_array);
        }
        
        apply_normalization(in_out_array, FFTW_BACKWARD);
    }
};
} // namespace FFTW
} // namespace GPIArray

#endif // GPIArray_FFTW_HPP