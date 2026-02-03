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
              unsigned int plan_flags = FFTW_ESTIMATE) { // Added plan_flags for individual calls

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
    if (dir == FFTW_BACKWARD) {
        double N_total = 1.0;
        // N_total is the product of dimensions involved in ONE transform (product of n_dims_vec).
        for (uint64_t dim_size : n_dims_vec) {
            N_total *= dim_size;
        }

        std::complex<T_Real>* output_raw_data = output.get_data();
        T_Real normalization_value = static_cast<T_Real>(N_total);
        for (uint64_t i = 0; i < output.size(); ++i) { // Iterate over total size
            output_raw_data[i] /= normalization_value;
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
    uint64_t stride = input.strides()[axis];
    bool use_opt_shift = (dim_size % 2 == 0); // Optimization for even sizes

    bool is_in_place = (&input == &output);
    if (!is_in_place) output = input.copy();
    
    std::complex<T_Real>* data = output.get_data();
    uint64_t total_size = output.size();

    // OPTIMIZED SHIFT: Sign-flip logic along the specific axis
    auto apply_1d_mask = [&](GPIArray::Array<std::complex<T_Real>>& arr) {
        std::complex<T_Real>* arr_ptr = arr.get_data(); // Use the passed array's data
        uint64_t total_size = arr.size();
        #pragma omp parallel for
        for (uint64_t i = 0; i < total_size; ++i) {
            // Efficiently flip sign based on index along target axis
            if (((i / stride) % dim_size) % 2 != 0) {
                arr_ptr[i] *= static_cast<T_Real>(-1.0);
            }
        }
    };

    if (use_opt_shift) apply_1d_mask(output);
    else roll_axis_in_place(output, axis, dim_size / 2); // Fallback for odd sizes

    std::lock_guard<std::mutex> lock(g_fftw_plan_mutex); // Thread safety

    int n_int = static_cast<int>(dim_size);
    // Path 1: Innermost contiguous axis allows for one batch plan
    if (axis == static_cast<int64_t>(ndim) - 1 && output.is_contiguous()) {
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
        for(auto a : other_axes) num_others *= input.dimensions(a);

        FFTWPlan plan = Traits::plan_dft_(1, &n_int, 1,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, static_cast<int>(stride), 0,
                                         reinterpret_cast<FFTWComplexType*>(data), NULL, static_cast<int>(stride), 0,
                                         dir, FFTW_ESTIMATE | FFTW_UNALIGNED);

        for (uint64_t i = 0; i < num_others; ++i) {
            uint64_t offset = 0;
            uint64_t temp = i;
            for (int j = static_cast<int>(other_axes.size()) - 1; j >= 0; --j) {
                uint64_t a = other_axes[j];
                offset += (temp % input.dimensions(a)) * input.strides()[a];
                temp /= input.dimensions(a);
            }
            Traits::execute_dft(plan, reinterpret_cast<FFTWComplexType*>(data + offset), 
                                reinterpret_cast<FFTWComplexType*>(data + offset));
        }
        Traits::destroy_plan(plan);
    }

    if (use_opt_shift) apply_1d_mask(output);
    else roll_axis_in_place(output, axis, (dim_size + 1) / 2);

    if (dir == FFTW_BACKWARD) {
        T_Real norm = static_cast<T_Real>(dim_size);
        #pragma omp parallel for
        for (uint64_t i = 0; i < total_size; ++i) data[i] /= norm;
    }
}


// 2D FFT: fft2(input, output, direction) - Now uses fftw_plan_dft_2d
template<typename T_Real>
void fft2(const GPIArray::Array<std::complex<T_Real>>& input,
          GPIArray::Array<std::complex<T_Real>>& output,
          int dir) {
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

    // Normalization for inverse FFTW_BACKWARD transform
    if (dir == FFTW_BACKWARD) {
        double N_total = static_cast<double>(working_arr.dimensions(0)) * static_cast<double>(working_arr.dimensions(1));
        std::complex<T_Real>* output_raw_data = working_arr.get_data();
        T_Real normalization_value = static_cast<T_Real>(N_total);
        for (uint64_t i = 0; i < working_arr.size(); ++i) {
            output_raw_data[i] /= normalization_value;
        }
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
          int dir) {
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

    // Normalization for inverse FFTW_BACKWARD transform
    if (dir == FFTW_BACKWARD) {
        double N_total = static_cast<double>(working_arr.dimensions(0)) *
                         static_cast<double>(working_arr.dimensions(1)) *
                         static_cast<double>(working_arr.dimensions(2));
        std::complex<T_Real>* output_raw_data = working_arr.get_data();
        T_Real normalization_value = static_cast<T_Real>(N_total);
        for (uint64_t i = 0; i < working_arr.size(); ++i) {
            output_raw_data[i] /= normalization_value;
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

// New class to manage FFTW plans for specific dimensions
template<typename T_Real>
class FFTPlanManager {
public:
    using ComplexT = std::complex<T_Real>;
    using Traits = FFTWPrecisionTraits<ComplexT>;
    using FFTWComplexType = typename Traits::FFTWComplexType;
    using FFTWPlan = typename Traits::PlanType;

private:
    std::vector<int> _dims_int;
    FFTWPlan _forward_plan = nullptr;
    FFTWPlan _backward_plan = nullptr;
    unsigned int _plan_flags; // Store the planning flags
    std::vector<T_Real> _alternating_mask; 
    bool _use_optimized_shift = false;

    // Helper to check if all dimensions are even
    bool check_all_dims_even() const {
        for (int dim : _dims_int) {
            if (dim % 2 != 0) return false;
        }
        return true;
    }

    /**
     * @brief Generates the 1D alternating sign sequence (-1)^(sum of indices) for the entire contiguous buffer.
     * This runs only once in the constructor if all dimensions are even.
     */
    void generate_alternating_mask() {
        if (!_use_optimized_shift) return; 

        uint64_t total_size = 1;
        for (int dim : _dims_int) total_size *= dim;

        _alternating_mask.resize(total_size);
        
        // Calculate strides assuming a perfectly contiguous row-major layout
        std::vector<uint64_t> contrived_strides(_dims_int.size());
        if (!_dims_int.empty()) {
            contrived_strides[_dims_int.size() - 1] = 1;
            for (int i = _dims_int.size() - 2; i >= 0; --i) {
                contrived_strides[i] = contrived_strides[i + 1] * _dims_int[i + 1];
            }
        }

        std::vector<uint64_t> current_coords(_dims_int.size(), 0);

        std::function<void(uint64_t)> recurse = 
            [&](uint64_t dim) {
            
            if (dim == _dims_int.size()) {
                // Calculate the flat index and total parity
                uint64_t flat_idx = 0;
                uint64_t parity_sum = 0;
                for(uint64_t d = 0; d < _dims_int.size(); ++d) {
                    flat_idx += current_coords[d] * contrived_strides[d];
                    parity_sum += current_coords[d];
                }
                
                // Sign is +1 if parity_sum is even, -1 if odd
                T_Real sign = (parity_sum % 2 == 0) ? static_cast<T_Real>(1.0) : static_cast<T_Real>(-1.0);
                
                _alternating_mask[flat_idx] = sign;
                return;
            }

            for (int i = 0; i < _dims_int[dim]; ++i) {
                current_coords[dim] = i;
                recurse(dim + 1);
            }
        };

        if (total_size > 0) recurse(0);
    }

    /**
     * @brief Applies the pre-computed sign mask to the contiguous array data (O(N) operation).
     */
    void apply_mask_in_place(GPIArray::Array<ComplexT>& in_out_array) const {
        std::complex<T_Real>* data = in_out_array.get_data();
        uint64_t size = in_out_array.size();
        
        for (uint64_t i = 0; i < size; ++i) {
            data[i] *= _alternating_mask[i]; // Multiply by the pre-computed sign factor
        }
    }

public:
    // Constructor: Creates FFTW plans for a given matrix size
    FFTPlanManager(const std::vector<uint64_t>& dims, unsigned int plan_flags = FFTW_ESTIMATE)
        : _plan_flags(plan_flags) {
        
        if (dims.empty()) {
            THROW_INVALID_ARGUMENT("FFTPlanManager: Dimensions cannot be empty for plan creation.");
        }

        _dims_int.reserve(dims.size());
        for (uint64_t d : dims) {
            _dims_int.push_back(static_cast<int>(d));
        }

        // 1. Check for optimized shift condition and generate mask
        _use_optimized_shift = check_all_dims_even();
        generate_alternating_mask(); 

        // Calculate total size for dummy buffer allocation
        int rank = static_cast<int>(_dims_int.size());
        int howmany = 1; // Planning for a single transform
        int idist = 1; 
        for(int d_size : _dims_int) idist *= d_size;
        int odist = idist;


        // Allocate a single dummy buffer for in-place planning
        FFTWComplexType* dummy_data;
        if constexpr (std::is_same_v<T_Real, float>) {
            dummy_data = static_cast<FFTWComplexType*>(fftwf_malloc(idist * sizeof(ComplexT)));
        } else { // double
            dummy_data = static_cast<FFTWComplexType*>(fftw_malloc(idist * sizeof(ComplexT)));
        }

        if (!dummy_data) {
            THROW_RUNTIME_ERROR("FFTPlanManager: Failed to allocate dummy memory for plan creation.");
        }

        // Thread-safe plan creation
        std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);

        // Create forward plan (in-place planning: in and out pointers are the same)
        _forward_plan = Traits::plan_dft_(
            rank, _dims_int.data(), howmany,
            dummy_data, NULL, 1, idist, // in pointer
            dummy_data, NULL, 1, odist, // out pointer
            FFTW_FORWARD, _plan_flags | FFTW_UNALIGNED
        );

        // Create backward plan (in-place planning: in and out pointers are the same)
        _backward_plan = Traits::plan_dft_(
            rank, _dims_int.data(), howmany,
            dummy_data, NULL, 1, idist, // in pointer
            dummy_data, NULL, 1, odist, // out pointer
            FFTW_BACKWARD, _plan_flags | FFTW_UNALIGNED
        );

        // Free dummy buffer
        if constexpr (std::is_same_v<T_Real, float>) {
            fftwf_free(dummy_data);
        } else {
            fftw_free(dummy_data);
        }

        if (!_forward_plan || !_backward_plan) {
            // Clean up any partially created plans
            if (_forward_plan) Traits::destroy_plan(_forward_plan);
            if (_backward_plan) Traits::destroy_plan(_backward_plan);
            THROW_RUNTIME_ERROR("FFTPlanManager: Failed to create one or both FFTW plans.");
        }
    }

    // Destructor: Destroys the FFTW plans
    ~FFTPlanManager() {
        std::lock_guard<std::mutex> lock(g_fftw_plan_mutex); // Protect destruction as well
        if (_forward_plan) {
            Traits::destroy_plan(_forward_plan);
            _forward_plan = nullptr;
        }
        if (_backward_plan) {
            Traits::destroy_plan(_backward_plan);
            _backward_plan = nullptr;
        }
    }

    // Disable copy constructor and copy assignment
    FFTPlanManager(const FFTPlanManager&) = delete;
    FFTPlanManager& operator=(const FFTPlanManager&) = delete;

    // Move constructor and move assignment
    FFTPlanManager(FFTPlanManager&& other) noexcept
        : _dims_int(std::move(other._dims_int)),
          _forward_plan(other._forward_plan),
          _backward_plan(other._backward_plan),
          _plan_flags(other._plan_flags) {
        other._forward_plan = nullptr;
        other._backward_plan = nullptr;
    }

    FFTPlanManager& operator=(FFTPlanManager&& other) noexcept {
        if (this != &other) {
            // Destroy existing plans first
            {
                std::lock_guard<std::mutex> lock(g_fftw_plan_mutex);
                if (_forward_plan) Traits::destroy_plan(_forward_plan);
                if (_backward_plan) Traits::destroy_plan(_backward_plan);
            }

            _dims_int = std::move(other._dims_int);
            _forward_plan = other._forward_plan;
            _backward_plan = other._backward_plan;
            _plan_flags = other._plan_flags;

            other._forward_plan = nullptr;
            other._backward_plan = nullptr;
        }
        return *this;
    }

    // Execute forward FFT with automatic shifting
    void execute_forward(GPIArray::Array<ComplexT>& in_out_array, bool perform_shift = true) const {
        if (!_forward_plan) {
            THROW_RUNTIME_ERROR("FFTPlanManager: Forward plan is not initialized.");
        }
        // Validate dimensions
        if (in_out_array.ndim() != _dims_int.size()) {
             THROW_INVALID_ARGUMENT("FFTPlanManager::execute_forward: Array dimension mismatch.");
        }
        for(uint64_t i = 0; i < in_out_array.ndim(); ++i) {
            if (in_out_array.dimensions(i) != static_cast<uint64_t>(_dims_int[i])) {
                THROW_INVALID_ARGUMENT("FFTPlanManager::execute_forward: Array shape mismatch with planned dimensions.");
            }
        }
        
        FFTWComplexType* data_ptr = reinterpret_cast<FFTWComplexType*>(in_out_array.get_data());
        
        if(perform_shift){
            if (_use_optimized_shift) {
                // OPTIMIZED SHIFT: Multiply by pre-computed mask (in-place)
                apply_mask_in_place(in_out_array);
            } else {
                // TRADITIONAL SHIFT: Roll elements (required for odd sizes)
                FFTW::ifftshift<T_Real>(in_out_array);
            }
        }

        // Execute the plan
        Traits::execute_dft(_forward_plan, data_ptr, data_ptr);
        
        if(perform_shift){
            if (_use_optimized_shift) {
                // OPTIMIZED SHIFT: Multiply by pre-computed mask again
                apply_mask_in_place(in_out_array);
            } else {
                // TRADITIONAL SHIFT: Roll elements back (required for odd sizes)
                FFTW::fftshift<T_Real>(in_out_array);
            }
        }
    }

    // Execute backward FFT with automatic shifting and normalization
    void execute_backward(GPIArray::Array<ComplexT>& in_out_array, bool perform_shift = true) const {
        if (!_backward_plan) {
            THROW_RUNTIME_ERROR("FFTPlanManager: Backward plan is not initialized.");
        }
        // Validate dimensions
        if (in_out_array.ndim() != _dims_int.size()) {
             THROW_INVALID_ARGUMENT("FFTPlanManager::execute_backward: Array dimension mismatch.");
        }
        for(uint64_t i = 0; i < in_out_array.ndim(); ++i) {
            if (in_out_array.dimensions(i) != static_cast<uint64_t>(_dims_int[i])) {
                THROW_INVALID_ARGUMENT("FFTPlanManager::execute_backward: Array shape mismatch with planned dimensions.");
            }
        }

        FFTWComplexType* data_ptr = reinterpret_cast<FFTWComplexType*>(in_out_array.get_data());

        if(perform_shift){
            if (_use_optimized_shift) {
                // OPTIMIZED SHIFT: Multiply by pre-computed mask
                apply_mask_in_place(in_out_array);
            } else {
                // TRADITIONAL SHIFT: Roll elements (required for odd sizes)
                FFTW::ifftshift<T_Real>(in_out_array);
            }
        }

        // Execute the plan
        Traits::execute_dft(_backward_plan, data_ptr, data_ptr);

        if(perform_shift){
            if (_use_optimized_shift) {
                // OPTIMIZED SHIFT: Multiply by pre-computed mask again
                apply_mask_in_place(in_out_array);
            } else {
                // TRADITIONAL SHIFT: Roll elements back
                FFTW::fftshift<T_Real>(in_out_array);
            }
        }

        // Apply normalization for inverse FFT
        double N_total = 1.0;
        for (int dim_size : _dims_int) {
            N_total *= dim_size;
        }
        T_Real normalization_value = static_cast<T_Real>(N_total);
        for (uint64_t i = 0; i < in_out_array.size(); ++i) { // Iterate over total size
            in_out_array.get_data()[i] /= normalization_value;
        }
    }
};


} // namespace FFTW
} // namespace GPIArray

#endif // GPIArray_FFTW_HPP