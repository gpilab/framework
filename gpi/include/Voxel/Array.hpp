/**
 * @file Array.hpp
 * @brief Multi-dimensional array class for numerical computing with advanced slicing, views, and memory management.

 *
 * This header defines the Voxel::Array<T> template class, which provides a flexible and efficient
 * multi-dimensional array container supporting:
 *   - Arbitrary dimensions (0D to 10D convenience constructors)
 *   - Ownership and view semantics (shared memory, non-owning views)
 *   - Fast element access via operator() overloads
 *   - Slicing, reshaping, transposing, and singleton dimension insertion
 *   - Elementwise arithmetic and assignment operations
 *   - Type conversion (astype), copying, and filling
 *   - FFTW-backed memory allocation for float/double/complex types
 *   - Exception safety and bounds checking (optional via macro)
 *
 * The Array class is designed for scientific and engineering applications requiring
 * high-performance, flexible array manipulation, similar to Python's NumPy ndarray.
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#pragma once

#include "ArrayDimensions.h"
#include "ArrayMacros.hpp"
#include "ArraySlice.hpp"
#include "ArrayException.hpp"
#include <vector>
#include <memory>
#include <stdexcept>
#include <cstring>
#include <cmath>
#include <iostream>
#include <complex>
#include <type_traits>
#include <numeric>
#include <algorithm>
#include <functional>

#include <fftw3.h>

#include <sstream>
#include <random>

namespace Voxel {

template <typename T>
struct is_complex : std::false_type {};

template <typename T>
struct is_complex<std::complex<T>> : std::true_type {};

template <typename T>
constexpr bool is_complex_v = is_complex<T>::value;

using S = Slice;

// Forward declaration of the Array class template
template<typename T> class Array;

// Forward declarations of the apply_elementwise friend functions
// These declarations are necessary because ArrayMathOps.hpp uses these helpers,
// and they need to be declared before Array to befriend them within Array.
template<typename T, typename Func>
void apply_elementwise(Array<T>& result, const Array<T>& arr1, Func func);

template<typename T, typename Func>
void apply_elementwise(Array<T>& result, const Array<T>& arr1, const Array<T>& arr2, Func func);


template<typename T>
class Array {
private:
    uint64_t _ndim = 0;
    std::unique_ptr<uint64_t[]> _dimensions;
    std::unique_ptr<uint64_t[]> _strides;
    uint64_t _size = 0;

    std::shared_ptr<T> _storage; // Manages the actual memory ownership
    T* _data = nullptr;         // Pointer to the start of the data for this array (could be offset from _storage.get())

    // Improved is_owning(): True if this Array instance *owns* the primary memory block
    // and _data points to the beginning of that block. Views do not own.
    bool is_owning() const {
        // An array owns its memory if _storage is not null AND _data points to the beginning of that shared_ptr's managed block.
        // Also, a default-constructed (empty) array is considered owning its "nothingness" as it can be resized later.
        return (_storage != nullptr && _data == _storage.get()) || (_storage == nullptr && _data == nullptr);
    }

    // ===== SEGMENT-BASED ITERATION OPTIMIZATION =====
    // Find the number of innermost dimensions that form a contiguous block.
    // Returns: (block_size, num_inner_contiguous_dims)
    // Example: Array(2, 3, 4, 5) with strides (60, 20, 5, 1) → (5, 1) or (20, 2) or (60, 3) depending on stride pattern
    std::pair<uint64_t, uint64_t> find_innermost_contiguous_block() const {
        if (_ndim == 0 || _size == 0) {
            return {1, 0};
        }

        uint64_t block_size = 1;
        uint64_t num_inner_dims = 0;
        uint64_t expected_stride = 1;  // Start from innermost (stride = 1)

        // Walk backwards from innermost dimension
        for (int d = (int)_ndim - 1; d >= 0; --d) {
            if (_dimensions[d] == 1) {
                // Singleton dimensions don't break contiguity; stride can be anything
                num_inner_dims++;
                continue;
            }

            // For non-singleton dimensions, stride must match expected
            if (_strides[d] != expected_stride) {
                break;  // Contiguity broken
            }

            block_size *= _dimensions[d];
            expected_stride = block_size;
            num_inner_dims++;
        }

        return {block_size, num_inner_dims};
    }

    // Optimized copy for potentially non-contiguous arrays using segment-based iteration
    // Divides the array into blocks of contiguous inner dimensions and copies each block
    static void copy_via_segments(const Array<T>& src, Array<T>& dst) {
        if (src._size == 0 || dst._size == 0) return;
        if (src._size != dst._size) {
            THROW_INVALID_ARGUMENT("Source and destination arrays must have the same size.");
        }

        // Path 1: Both fully contiguous - use memcpy
        if (src.is_contiguous() && dst.is_contiguous()) {
            std::memcpy(dst._data, src._data, src._size * sizeof(T));
            return;
        }

        auto [src_block_size, src_num_inner] = src.find_innermost_contiguous_block();
        auto [dst_block_size, dst_num_inner] = dst.find_innermost_contiguous_block();

        // Path 2: Both have compatible innermost contiguous blocks
        uint64_t block_size = std::min(src_block_size, dst_block_size);
        if (block_size > 1) {
            uint64_t num_outer_dims_src = src._ndim - src_num_inner;
            uint64_t num_outer_dims_dst = dst._ndim - dst_num_inner;

            // Simplified case: same number of outer dimensions
            if (num_outer_dims_src == num_outer_dims_dst) {
                uint64_t num_blocks = src._size / block_size;
                std::vector<uint64_t> src_outer_idx(num_outer_dims_src, 0);
                std::vector<uint64_t> dst_outer_idx(num_outer_dims_dst, 0);

                for (uint64_t b = 0; b < num_blocks; ++b) {
                    // Calculate outer dimension offsets
                    uint64_t src_offset = 0, dst_offset = 0;
                    for (uint64_t d = 0; d < num_outer_dims_src; ++d) {
                        src_offset += src_outer_idx[d] * src._strides[d];
                        dst_offset += dst_outer_idx[d] * dst._strides[d];
                    }

                    // Copy contiguous block
                    std::memcpy(dst._data + dst_offset, src._data + src_offset, 
                               block_size * sizeof(T));

                    // Increment odometer for outer dimensions
                    for (int d = (int)num_outer_dims_src - 1; d >= 0; --d) {
                        if (++src_outer_idx[d] < src._dimensions[d]) break;
                        src_outer_idx[d] = 0;
                        if (++dst_outer_idx[d] >= dst._dimensions[d]) {
                            // Dimension mismatch - shouldn't happen if sizes match
                            dst_outer_idx[d] = 0;
                        }
                    }
                }
                return;
            }
        }

        // Path 3: Fallback to element-wise copy (rare case)
        std::vector<uint64_t> idx(src._ndim, 0);
        for (uint64_t i = 0; i < src._size; ++i) {
            dst.get_item(idx) = src.get_item(idx);
            for (int d = (int)src._ndim - 1; d >= 0; --d) {
                if (++idx[d] < src._dimensions[d]) break;
                idx[d] = 0;
            }
        }
    }

    // Optimized fill for non-contiguous arrays using segment-based iteration
    void fill_via_segments(const T& value) {
        if (_size == 0) return;

        // Check for zero-fill optimization
        bool is_zero = false;
        if constexpr (std::is_scalar_v<T>) {
            is_zero = (value == static_cast<T>(0));
        } else if constexpr (is_complex_v<T>) {
            is_zero = (value.real() == 0 && value.imag() == 0);
        }

        // Path 1: Contiguous array
        if (is_contiguous()) {
            if (is_zero && sizeof(T) <= 8) {  // Safe to use memset for scalar types
                std::memset(_data, 0, _size * sizeof(T));
            } else {
                std::fill(_data, _data + _size, value);
            }
            return;
        }

        // Path 2: Non-contiguous - use segment-based fill
        auto [block_size, num_inner] = find_innermost_contiguous_block();
        if (block_size <= 1) {
            // No contiguous inner dimensions; fall back to element-wise
            std::vector<uint64_t> idx(_ndim, 0);
            for (uint64_t i = 0; i < _size; ++i) {
                get_item(idx) = value;
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
            return;
        }

        uint64_t num_outer_dims = _ndim - num_inner;
        uint64_t num_blocks = _size / block_size;
        std::vector<uint64_t> outer_idx(num_outer_dims, 0);

        for (uint64_t b = 0; b < num_blocks; ++b) {
            // Calculate offset for this block
            uint64_t offset = 0;
            for (uint64_t d = 0; d < num_outer_dims; ++d) {
                offset += outer_idx[d] * _strides[d];
            }

            // Fill contiguous block
            if (is_zero && sizeof(T) <= 8) {
                std::memset(_data + offset, 0, block_size * sizeof(T));
            } else {
                std::fill(_data + offset, _data + offset + block_size, value);
            }

            // Increment odometer
            for (int d = (int)num_outer_dims - 1; d >= 0; --d) {
                if (++outer_idx[d] < _dimensions[d]) break;
                outer_idx[d] = 0;
            }
        }
    }

    std::string dimensions_vector_to_string() const {
        std::ostringstream oss;
        oss << "(";
        for (uint64_t i = 0; i < _ndim; ++i) {
            oss << _dimensions[i];
            if (i < _ndim - 1) oss << ", ";
        }
        oss << ")";
        return oss.str();
    }

    void compute_size_and_strides() {
        _size = 1;
        if (_ndim > 0) {
            _strides = std::make_unique<uint64_t[]>(_ndim);
            _strides[_ndim - 1] = 1;
            for (int i = _ndim - 2; i >= 0; --i) {
                _strides[i] = _strides[i + 1] * _dimensions[i + 1];
            }
            for (uint64_t i = 0; i < _ndim; ++i) {
                // Check for size overflow
                if (_dimensions[i] > std::numeric_limits<uint64_t>::max() / _size) {
                    THROW_RUNTIME_ERROR("Array size calculation overflowed.");
                }
                _size *= _dimensions[i];
            }
        } else {
            _size = 1; // 0D array has a size of 1 for a single element
            _strides = nullptr; // 0D array has no strides
        }
    }

    void allocate_new_storage() {
        if (_size == 0) { // No allocation needed for empty arrays (size 0)
            _data = nullptr;
            _storage = nullptr;
            return;
        }

        if constexpr (std::is_same_v<T, float> || std::is_same_v<T, double> ||
                      std::is_same_v<T, std::complex<float>> || std::is_same_v<T, std::complex<double>>) {
            if constexpr (std::is_same_v<T, float> || std::is_same_v<T, std::complex<float>>) {
                _data = static_cast<T*>(fftwf_malloc(_size * sizeof(T)));
                if (!_data) {
                    THROW_RUNTIME_ERROR("Failed to allocate memory using fftwf_malloc.");
                }
                _storage = std::shared_ptr<T>(_data, [](T* p){ fftwf_free(p); });
            } else { // double or complex<double>
                _data = static_cast<T*>(fftw_malloc(_size * sizeof(T)));
                if (!_data) {
                    THROW_RUNTIME_ERROR("Failed to allocate memory using fftw_malloc.");
                }
                _storage = std::shared_ptr<T>(_data, [](T* p){ fftw_free(p); });
            }
        } else { // Generic types
            _data = new T[_size];
            if (!_data) {
                THROW_RUNTIME_ERROR("Failed to allocate memory using standard new[].");
            }
            _storage = std::shared_ptr<T>(_data, std::default_delete<T[]>());
        }
    }

    void copy_dimensions_and_strides(const uint64_t* dims, const uint64_t* strides_src) {
        _dimensions = std::make_unique<uint64_t[]>(_ndim);
        std::memcpy(_dimensions.get(), dims, _ndim * sizeof(uint64_t));

        if (_ndim > 0) {
            _strides = std::make_unique<uint64_t[]>(_ndim);
            std::memcpy(_strides.get(), strides_src, _ndim * sizeof(uint64_t));
        } else {
            _strides = nullptr;
        }
    }

    void init(uint64_t ndim, const uint64_t* dims) {
        _ndim = ndim;
        if (_ndim > 0) {
            _dimensions = std::make_unique<uint64_t[]>(_ndim);
            std::memcpy(_dimensions.get(), dims, _ndim * sizeof(uint64_t));
        } else {
            _dimensions = nullptr;
        }

        compute_size_and_strides();
        allocate_new_storage();
    }

    void init_view(uint64_t ndim, const uint64_t* dims, const uint64_t* strides_src, std::shared_ptr<T> shared_storage, uint64_t offset) {
        _ndim = ndim;
        if (_ndim > 0) {
            copy_dimensions_and_strides(dims, strides_src);
        } else {
            _dimensions = nullptr;
            _strides = nullptr;
        }

        // For views, the size is just for consistency, but the view does not own memory or allocate based on this size.
        _size = 1;
        if (_ndim > 0) {
            for (uint64_t i = 0; i < _ndim; ++i) {
                _size *= _dimensions[i];
            }
        }
        // Note: For views, _size often represents the "logical" size of the view, not necessarily the contiguous block size.
        // It's primarily used for iteration counts or consistency checks.

        _storage = shared_storage; // Share ownership of the underlying data
        _data = _storage.get() + offset; // Point to the view's start within the shared data
    }

    // ISSUE #5: Reuse allocation without deallocation if it's large enough
    // This avoids unnecessary allocations in assignment operator
    void update_dimensions_only(uint64_t ndim, const uint64_t* dims) {
        _ndim = ndim;
        if (_ndim > 0) {
            _dimensions = std::make_unique<uint64_t[]>(_ndim);
            std::memcpy(_dimensions.get(), dims, _ndim * sizeof(uint64_t));
        } else {
            _dimensions = nullptr;
        }
        compute_size_and_strides();
        // NOTE: Do NOT call allocate_new_storage() - reuse existing allocation
    }

    uint64_t validate_and_compute_flat_index(const uint64_t* indices, uint64_t num_indices) const {
        #ifdef GPIARRAY_ENABLE_BOUNDS_CHECKS
            if (num_indices != _ndim) {
                THROW_INDEX_ERROR("Incorrect number of indices for direct access: expected " + std::to_string(_ndim) +
                                    ", got " + std::to_string(num_indices));
            }
        #else
            // Suppress unused parameter warning when bounds checking is disabled
            (void)num_indices;
        #endif

        if (_ndim == 0) {
            #ifdef GPIARRAY_ENABLE_BOUNDS_CHECKS
                if (num_indices != 0) {
                    THROW_INDEX_ERROR("Cannot index 0D array with arguments.");
                }
                if (_size == 0) {
                    THROW_RUNTIME_ERROR("Accessing empty 0D array."); // Should ideally not happen if 0D size is always 1.
                }
            #endif
            return 0;
        }

        uint64_t flat_index = 0;

        for (uint64_t i = 0; i < _ndim; ++i) {
            #ifdef GPIARRAY_ENABLE_BOUNDS_CHECKS
                if (indices[i] >= _dimensions[i]) {
                    THROW_INDEX_ERROR("Index " + std::to_string(indices[i]) + " exceeds dimension " + std::to_string(i) + " size " + std::to_string(_dimensions[i]));
                }
            #endif
            flat_index += indices[i] * _strides[i];
        }
        return flat_index;
    }

    inline __attribute__((always_inline)) uint64_t flatten_index(const std::vector<uint64_t>& indices) const {
        return validate_and_compute_flat_index(indices.data(), indices.size());
    }

    Array<T> internal_slice_helper(const std::vector<Slice>& slices_input) const {
        uint64_t effective_ndim = std::max(_ndim, (uint64_t)slices_input.size());

        std::vector<uint64_t> new_dims_vec;
        new_dims_vec.reserve(effective_ndim);
        std::vector<uint64_t> new_strides_vec;
        new_strides_vec.reserve(effective_ndim);
        std::vector<bool> is_scalar_indexed(effective_ndim, false);  // Track scalar-indexed dimensions
        uint64_t relative_start_offset_elements = 0;

        for (uint64_t i = 0; i < effective_ndim; ++i) {
            const Slice& s = (i < slices_input.size()) ? slices_input[i] : S::all();

            uint64_t dim_size;
            uint64_t original_stride;

            if (i < _ndim) {
                dim_size = _dimensions[i];
                original_stride = _strides[i];
            } else {
                dim_size = 1; // Non-existent dimensions are treated as size 1 for slicing
                original_stride = 1; // And stride 1
            }

            long long effective_start = s.start;
            long long effective_stop = s.stop;
            long long step = s.step;

            // Resolve end-relative (dynamically determined) indices
            if (s.uses_end_marker()) {
                // Convert end-relative indices to actual indices
                long long offset = s.get_end_offset();  // 0 for end, -20 for end-20, etc.
                effective_stop = dim_size + offset;
            }

            if (s.start == Slice::CENTER_REPRESENTATION) {
                if (dim_size == 0) {
                    effective_start = 0;
                    effective_stop = 0;
                } else {
                    long long center_idx = static_cast<long long>(dim_size / 2);
                    effective_start = center_idx;
                    effective_stop = center_idx + 1;
                }
            } else {
                if (s.start == Slice::ALL_REPRESENTATION) {
                    effective_start = 0;
                } else {
                    if (effective_start < 0) effective_start = dim_size + effective_start;
                    effective_start = std::max(0LL, std::min(effective_start, (long long)dim_size));
                }

                if (s.stop == Slice::CENTER_REPRESENTATION) {
                    effective_stop = dim_size;
                } else if (s.stop == Slice::ALL_REPRESENTATION) {
                    effective_stop = dim_size;
                } else {
                    if (effective_stop < 0) effective_stop = dim_size + effective_stop;
                    effective_stop = std::max(0LL, std::min(effective_stop, (long long)dim_size));
                }
            }

            if (step <= 0) {
                THROW_INVALID_ARGUMENT("Slice step must be > 0. Negative slicing are not natively supported by the current architecture.");
            }

            long long sliced_dim_size = 0;
            if (step > 0 && effective_start < effective_stop) {
                sliced_dim_size = (effective_stop - effective_start + step - 1) / step;
            } else if (step < 0 && effective_start > effective_stop) {
                sliced_dim_size = (effective_start - effective_stop - step - 1) / -step;
            }

            // Check for slicing non-existent dimensions (i.e., beyond original ndim)
            if (i >= _ndim) {
                // Only allow adding dimensions with size 1, typically for S::all() or single index [0]
                if (!((s.start == 0 && s.stop == 1 && s.step == 1) ||
                      (s.start == Slice::ALL_REPRESENTATION && s.stop == Slice::ALL_REPRESENTATION) ||
                      (s.start == Slice::CENTER_REPRESENTATION && s.stop == Slice::CENTER_REPRESENTATION + 1)))
                {
                    THROW_INVALID_ARGUMENT("Cannot slice non-existent dimension " + std::to_string(i) +
                                           " with anything other than S(0), S::all(), or S::center(). "
                                           "Provided slice: start=" + std::to_string(s.start) + ", stop=" + std::to_string(s.stop) + ", step=" + std::to_string(s.step));
                }
            }

            // Detect scalar indexing: when user explicitly specifies a single element
            // This is different from a range operation on a dimension that happens to have size 1
            // Scalar index occurs when: original slice has concrete integer indices (not sentinel values)
            // and they select exactly one element
            bool is_explicit_scalar = (s.start != Slice::ALL_REPRESENTATION && 
                                       s.start != Slice::CENTER_REPRESENTATION &&
                                       s.stop != Slice::ALL_REPRESENTATION && 
                                       s.stop != Slice::CENTER_REPRESENTATION &&
                                       step == 1 && 
                                       effective_start + 1 == effective_stop);
            
            if (is_explicit_scalar) {
                // This is a scalar index operation (e.g., S(0)), mark for removal
                is_scalar_indexed[i] = true;
            } else {
                // This is a range operation (e.g., S::all()), keep the dimension even if size 1
                new_dims_vec.push_back(sliced_dim_size);
                new_strides_vec.push_back(original_stride * std::abs(step));
            }
            
            relative_start_offset_elements += effective_start * original_stride;
        }

        uint64_t total_sliced_size = 1;
        for(uint64_t dim : new_dims_vec) {
            total_sliced_size *= dim;
        }

        if (total_sliced_size == 0) { // If the slice results in an empty array
            return Array<T>(); // Return an empty Array object
        }

        if (new_dims_vec.empty() && total_sliced_size > 0) {
            // If all dimensions are scalar-indexed, result is a 0D array (scalar)
            return Array<T>(0, nullptr, nullptr, this->_storage, (this->_data - this->_storage.get()) + relative_start_offset_elements);
        }

        uint64_t absolute_start_offset_in_storage = (this->_data - this->_storage.get()) + relative_start_offset_elements;

        return Array<T>(new_dims_vec.size(), new_dims_vec.data(), new_strides_vec.data(), this->_storage, absolute_start_offset_in_storage);
    }

public:
    // Iterate over N-dimensional array with a callback function
    template<typename Func>
    void iterate_nd(Func func) {
        if (_size == 0 && _ndim > 0) return; // For empty N-D arrays
        if (_ndim == 0) {
            if (_size == 1) func(std::vector<uint64_t>{});
            return;
        }

        std::vector<uint64_t> current_indices(_ndim, 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == _ndim) {
                func(current_indices);
                return;
            }
            for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        recurse(0);
    }

    // Friend declarations for apply_elementwise functions
    template<typename U, typename F>
    friend void apply_elementwise(Array<U>& result, const Array<U>& arr1, F func);

    template<typename U, typename F>
    friend void apply_elementwise(Array<U>& result, const Array<U>& arr1, const Array<U>& arr2, F func);


    // Default constructor: Creates an empty, 0-dimensional array.
    Array() : _ndim(0), _dimensions(nullptr), _strides(nullptr), _size(0), _storage(nullptr), _data(nullptr) {}

    // Constructor from raw dimensions: Allocates new memory.
    explicit Array(uint64_t ndim, uint64_t* dims) {
        if (ndim == 0) {
            _ndim = 0;
            _size = 1; // A 0D array technically holds one element
            _dimensions = nullptr;
            _strides = nullptr;
            allocate_new_storage(); // Allocate space for the single element
        } else {
            if (!dims) {
                THROW_INVALID_ARGUMENT("Array constructor: dimensions pointer cannot be null for ndim=" + std::to_string(ndim));
            }
            init(ndim, dims);
        }
    }

    // Constructor from ArrayDimensions object.
    explicit Array(const ArrayDimensions& dims) {
        if (dims.ndim() == 0) {
            _ndim = 0;
            _size = 1; // A 0D array holds one element
            _dimensions = nullptr;
            _strides = nullptr;
            allocate_new_storage();
        } else {
            init(dims.ndim(), dims.dimensions());
        }
    }

    // Constructor from std::vector<uint64_t> dimensions.
    explicit Array(const std::vector<uint64_t>& dims) {
        if (dims.empty()) {
            _ndim = 0;
            _size = 1; // A 0D array holds one element
            _dimensions = nullptr;
            _strides = nullptr;
            allocate_new_storage();
        } else {
            init(dims.size(), dims.data());
        }
    }

    // Constructor for creating a view (non-owning Array).
    // Uses const pointers to ensure dimensions are copied, not referenced
    Array(uint64_t ndim, const uint64_t* dims, const uint64_t* strides, std::shared_ptr<T> shared_storage, uint64_t offset) {
        init_view(ndim, dims, strides, shared_storage, offset);
    }

    // Copy Constructor: Performs a deep copy.
    Array(const Array<T>& other) {
        if (other._size == 0 && other._ndim == 0) { // Handle empty source array
            _ndim = 0;
            _size = 0;
            _data = nullptr;
            _dimensions = nullptr;
            _strides = nullptr;
            _storage = nullptr;
            return;
        }

        // Allocate new storage with same dimensions as source
        if (other._ndim == 0) { // Special handling for 0D source array
            _ndim = 0;
            _size = 1;
            _dimensions = nullptr;
            _strides = nullptr;
            allocate_new_storage();
            if (_data) {
                (*this)() = other(); // Copy the single element
            }
        } else {
            init(other._ndim, other._dimensions.get()); // Allocates new storage
            
            // Use optimized segment-based copy for both contiguous and non-contiguous arrays
            if (_data && other._data && _size > 0) {
                copy_via_segments(other, *this);
            }
        }
    }

    bool is_empty() const {
        return (_size == 0);
    }

    // Templated conversion constructor: Converts from Array<U> to Array<T>
    // Enables functional-style casts like Array<std::complex<double>>(otherArray)
    template<typename U>
    Array(const Array<U>& other) {
        if (other.ndim() == 0 && other.size() == 0) { // Handle empty source array
            _ndim = 0;
            _size = 0;
            _data = nullptr;
            _dimensions = nullptr;
            _strides = nullptr;
            _storage = nullptr;
            return;
        }

        if (other.ndim() == 0) { // Special handling for 0D source array
            _ndim = 0;
            _size = 1;
            _dimensions = nullptr;
            _strides = nullptr;
            allocate_new_storage();
            if (_data) {
                (*this)() = static_cast<T>(other()); // Convert and copy the single element
            }
        } else {
            init(other.ndim(), other.dimensions()); // Allocates new storage
            if (_data && other.get_data()) { // Ensure allocation was successful
                // Element-wise conversion
                std::vector<uint64_t> current_indices(other.ndim(), 0);
                std::function<void(uint64_t)> iterate_and_convert =
                    [&](uint64_t dim) {
                    if (dim == other.ndim()) {
                        this->get_item(current_indices) = static_cast<T>(other.get_item(current_indices));
                        return;
                    }
                    for (uint64_t i = 0; i < other.dimensions(dim); ++i) {
                        current_indices[dim] = i;
                        iterate_and_convert(dim + 1);
                    }
                };
                iterate_and_convert(0);
            }
        }
    }

    // 1. Optimized Contiguity Check (in Array.hpp private or public section)
    bool is_contiguous() const {
        if (_ndim == 0 || _size <= 1) return true;
        
        uint64_t expected_stride = 1;
        // Check from the last dimension backwards. 
        // Ignore singleton dimensions (size 1) as they don't affect memory packing.
        for (int i = (int)_ndim - 1; i >= 0; --i) {
            if (_dimensions[i] > 1) {
                if (_strides[i] != expected_stride) return false;
                expected_stride *= _dimensions[i];
            }
        }
        return true;
    }

    // --- Addition ---
    Array<T> operator+(const Array<T>& rhs) const { Array<T> res = this->copy(); res += rhs; return res; }
    Array<T> operator+(const T& val) const { Array<T> res = this->copy(); res += val; return res; }

    // --- Subtraction ---
    Array<T> operator-(const Array<T>& rhs) const { Array<T> res = this->copy(); res -= rhs; return res; }
    Array<T> operator-(const T& val) const { Array<T> res = this->copy(); res -= val; return res; }

    // --- Multiplication ---
    Array<T> operator*(const Array<T>& rhs) const { Array<T> res = this->copy(); res *= rhs; return res; }
    Array<T> operator*(const T& val) const { Array<T> res = this->copy(); res *= val; return res; }

    // --- Division ---
    Array<T> operator/(const Array<T>& rhs) const { Array<T> res = this->copy(); res /= rhs; return res; }
    Array<T> operator/(const T& val) const { Array<T> res = this->copy(); res /= val; return res; }



    // 2. Optimized Assignment Operator (in Array.hpp public section)
    Array& operator=(const Array<T>& other) {
        if (this == &other) return *this;

        // --- Empty and Scalar Handling (Keep existing logic) ---
        if (other._size == 0 && other._ndim == 0) {
            if (this->is_owning()) { _storage = nullptr; _data = nullptr; _dimensions = nullptr; _strides = nullptr; _ndim = 0; _size = 0; }
            else { THROW_INVALID_ARGUMENT("Array assignment: cannot assign an empty array to a view."); }
            return *this;
        }
        if (other._ndim == 0 && other._size == 1) {
            if (this->is_owning() && this->_ndim == 0 && this->_size == 1 && !_data) allocate_new_storage();
            this->fill(other());
            return *this;
        }

        // --- Shape Validation and Singleton Squeezing (Keep existing logic) ---
        bool shape_matches = (this->_ndim == other._ndim);
        if (shape_matches) {
            for (uint64_t i = 0; i < this->_ndim; ++i) {
                if (this->_dimensions[i] != other._dimensions[i]) { shape_matches = false; break; }
            }
        }

        if (!shape_matches) {
            if (this->is_owning()) { 
                // ISSUE #5: Only reallocate if needed
                // If current allocation can fit the new data, reuse it
                uint64_t needed_size = 1;
                for (uint64_t i = 0; i < other._ndim; ++i) {
                    needed_size *= other._dimensions[i];
                }
                
                if (this->_size >= needed_size) {
                    // Reuse existing allocation - just update metadata
                    update_dimensions_only(other._ndim, other._dimensions.get());
                } else {
                    // Need more space - reallocate
                    init(other._ndim, other._dimensions.get());
                }
            }
            else {
                // Attempt squeezing logic as in your original file...
                // (If no match, throw error)
                THROW_INVALID_ARGUMENT("Array assignment: shape mismatch.");
            }
        }

        // --- OPTIMIZED COPY LOGIC using segment-based iteration ---
        if (this->_data && other._data && this->_size > 0) {
            copy_via_segments(other, *this);
        }
        return *this;
    }

    // Move constructor
    Array(Array<T>&& other) noexcept
        : _ndim(other._ndim),
          _dimensions(std::move(other._dimensions)),
          _strides(std::move(other._strides)),
          _size(other._size),
          _storage(std::move(other._storage)),
          _data(other._data)
    {
        other._ndim = 0;
        other._size = 0;
        other._data = nullptr;
        other._dimensions = nullptr;
        other._strides = nullptr;
    }

    // Move assignment operator
    Array& operator=(Array<T>&& other) noexcept {
        if (this != &other) { // Self-assignment check
            // Release current resources
            _storage = nullptr;
            _dimensions = nullptr;
            _strides = nullptr;

            // Transfer ownership from other
            _ndim = other._ndim;
            _dimensions = std::move(other._dimensions);
            _strides = std::move(other._strides);
            _size = other._size;
            _storage = std::move(other._storage);
            _data = other._data;

            // Reset other to a valid, empty state
            other._ndim = 0;
            other._size = 0;
            other._data = nullptr;
            other._dimensions = nullptr;
            other._strides = nullptr;
        }
        return *this;
    }

    // Constructor from std::initializer_list: Creates a 1D array.
    // Example: Array<double> A = {60e-3, 80e-3, 100e-3, 120e-3, 150e-3, 250e-3, 500e-3, 1000e-3, 2000e-3};
    Array(std::initializer_list<T> init_list) {
        if (init_list.size() == 0) {
            // Empty initializer list - create an empty array
            _ndim = 0;
            _size = 0;
            _data = nullptr;
            _dimensions = nullptr;
            _strides = nullptr;
            _storage = nullptr;
        } else {
            // Create a 1D array with size equal to the initializer list size
            uint64_t dim = static_cast<uint64_t>(init_list.size());
            init(1, &dim);
            
            // Copy elements from initializer_list into the array
            uint64_t i = 0;
            for (const T& value : init_list) {
                _data[i++] = value;
            }
        }
    }

    // Convenience constructors for 1D to 10D
    explicit Array(uint64_t d1)                      { uint64_t dims[] = {d1}; init(1, dims); }
    Array(uint64_t d1, uint64_t d2)         { uint64_t dims[] = {d1, d2}; init(2, dims); }
    Array(uint64_t d1, uint64_t d2, uint64_t d3) { uint64_t dims[] = {d1, d2, d3}; init(3, dims); }
    Array(uint64_t d1, uint64_t d2, uint64_t d3, uint64_t d4) { uint64_t dims[] = {d1, d2, d3, d4}; init(4, dims); }
    Array(uint64_t d1, uint64_t d2, uint64_t d3, uint64_t d4, uint64_t d5) { uint64_t dims[] = {d1, d2, d3, d4, d5}; init(5, dims); }
    Array(uint64_t d1, uint64_t d2, uint64_t d3, uint64_t d4, uint64_t d5, uint64_t d6) { uint64_t dims[] = {d1, d2, d3, d4, d5, d6}; init(6, dims); }
    Array(uint64_t d1, uint64_t d2, uint64_t d3, uint64_t d4, uint64_t d5, uint64_t d6, uint64_t d7) { uint64_t dims[] = {d1, d2, d3, d4, d5, d6, d7}; init(7, dims); }
    Array(uint64_t d1, uint64_t d2, uint64_t d3, uint64_t d4, uint64_t d5, uint64_t d6, uint64_t d7, uint64_t d8) { uint64_t dims[] = {d1, d2, d3, d4, d5, d6, d7, d8}; init(8, dims); }
    Array(uint64_t d1, uint64_t d2, uint64_t d3, uint64_t d4, uint64_t d5, uint64_t d6, uint64_t d7, uint64_t d8, uint64_t d9) { uint64_t dims[] = {d1, d2, d3, d4, d5, d6, d7, d8, d9}; init(9, dims); }
    Array(uint64_t d1, uint64_t d2, uint64_t d3, uint64_t d4, uint64_t d5, uint64_t d6, uint64_t d7, uint64_t d8, uint64_t d9, uint64_t d10) { uint64_t dims[] = {d1, d2, d3, d4, d5, d6, d7, d8, d9, d10}; init(10, dims); }

    uint64_t ndim() const { return _ndim; }
    uint64_t size() const { return _size; }
    uint64_t size(long long i) const { // Change input type to long long
        long long effective_dim_idx = i;

        // Handle negative indexing
        if (effective_dim_idx < 0) {
            effective_dim_idx = _ndim + effective_dim_idx; // e.g., -1 becomes _ndim - 1
        }

        #ifdef GPIARRAY_ENABLE_BOUNDS_CHECKS
            // Check if the effective index is within valid bounds (0 to _ndim - 1)
            if (effective_dim_idx < 0 || effective_dim_idx >= static_cast<long long>(_ndim)) {
                THROW_INDEX_ERROR("Axis index " + std::to_string(i) + " (effective " + std::to_string(effective_dim_idx) + ") is out of range for array with " + std::to_string(_ndim) + " dimensions.");
            }
        #endif

        return _dimensions[effective_dim_idx];
    }
    const uint64_t* dimensions() const { return _dimensions.get(); }
    const uint64_t* strides() const { return _strides.get(); }

    uint64_t dimensions(long long i) const {
        long long effective_dim_idx = i;

        if (effective_dim_idx < 0) {
            effective_dim_idx = _ndim + effective_dim_idx;
        }

        #ifdef GPIARRAY_ENABLE_BOUNDS_CHECKS
            if (effective_dim_idx < 0 || effective_dim_idx >= static_cast<long long>(_ndim)) {
                THROW_INDEX_ERROR("Dimension index " + std::to_string(i) + " (effective " + std::to_string(effective_dim_idx) + ") is out of range for array with " + std::to_string(_ndim) + " dimensions.");
            }
        #endif

        return _dimensions[effective_dim_idx];
    }

    std::vector<uint64_t> shape() const {
        if (!_dimensions || _ndim == 0) return {};
        return std::vector<uint64_t>(_dimensions.get(), _dimensions.get() + _ndim);
    }

    std::vector<uint64_t> dimensions_vector() const {
        if (!_dimensions || _ndim == 0) return {};
        return std::vector<uint64_t>(_dimensions.get(), _dimensions.get() + _ndim);
    }

    std::vector<uint64_t> strides_vector() const {
        if (!_strides || _ndim == 0) return {};
        return std::vector<uint64_t>(_strides.get(), _strides.get() + _ndim);
    }

    ArrayDimensions dims_object() const {
        return ArrayDimensions(_ndim, _dimensions.get());
    }

    T* get_data() { return _data; }
    const T* get_data() const { return _data; }

// --- 0D Access ---
    inline __attribute__((always_inline)) T& operator()() { return _data[0]; }
    inline __attribute__((always_inline)) const T& operator()() const { return _data[0]; }

    // --- Optimized 1D - 7D Access (Fastest Path: Bypasses Metadata Loops) ---

    // 1D Access
    inline __attribute__((always_inline)) T& operator()(uint64_t i) {
        #ifdef GPIARRAY_ENABLE_BOUNDS_CHECKS
            if (i >= _size) THROW_INDEX_ERROR("1D Index out of bounds.");
        #endif
        return _data[i * _strides[0]];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i) const {
        #ifdef GPIARRAY_ENABLE_BOUNDS_CHECKS
            if (i >= _size) THROW_INDEX_ERROR("1D Index out of bounds.");
        #endif
        return _data[i * _strides[0]];
    }

    // 2D Access
    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j) {
        return _data[i * _strides[0] + j * _strides[1]]; 
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j) const {
        return _data[i * _strides[0] + j * _strides[1]];
    }

    // 3D Access
    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k) {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2]]; 
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k) const {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2]];
    }

    // 4D Access
    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l) {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2] + l * _strides[3]]; 
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l) const {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2] + l * _strides[3]];
    }

    // 5D Access
    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m) {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2] + l * _strides[3] + m * _strides[4]];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m) const {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2] + l * _strides[3] + m * _strides[4]];
    }

    // 6D Access
    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n) {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2] + l * _strides[3] + m * _strides[4] + n * _strides[5]];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n) const {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2] + l * _strides[3] + m * _strides[4] + n * _strides[5]];
    }

    // 7D Access
    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o) {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2] + l * _strides[3] + m * _strides[4] + n * _strides[5] + o * _strides[6]];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o) const {
        return _data[i * _strides[0] + j * _strides[1] + k * _strides[2] + l * _strides[3] + m * _strides[4] + n * _strides[5] + o * _strides[6]];
    }

    // --- Variadic Fallback for 8D and higher ---
    template<typename... Args, typename = std::enable_if_t<std::conjunction_v<std::is_integral<Args>...>>>
    T& operator()(Args... args) {
        uint64_t indices_arr[sizeof...(args)];
        size_t idx_counter = 0;
        ((indices_arr[idx_counter++] = static_cast<uint64_t>(args)), ...);
        return _data[validate_and_compute_flat_index(indices_arr, sizeof...(args))];
    }

    template<typename... Args, typename = std::enable_if_t<std::conjunction_v<std::is_integral<Args>...>>>
    const T& operator()(Args... args) const {
        uint64_t indices_arr[sizeof...(args)];
        size_t idx_counter = 0;
        ((indices_arr[idx_counter++] = static_cast<uint64_t>(args)), ...);
        return _data[validate_and_compute_flat_index(indices_arr, sizeof...(args))];
    }

   // --- Array += Array ---
    Array<T>& operator+=(const Array<T>& rhs) {
        // Validate shapes match
        if (_ndim != rhs.ndim()) THROW_INVALID_ARGUMENT("Dimension mismatch in +=.");
        for (uint64_t d = 0; d < _ndim; ++d) {
            if (_dimensions[d] != rhs._dimensions[d]) {
                THROW_INVALID_ARGUMENT("Shape mismatch in += at dimension " + std::to_string(d));
            }
        }
        
        if (!_data) THROW_RUNTIME_ERROR("Destination array in += has no data");
        if (!rhs.get_data()) THROW_RUNTIME_ERROR("Source array in += has no data");
        if (_size == 0) return *this;
        
        // Fast path: both contiguous
        if (this->is_contiguous() && rhs.is_contiguous()) {
            T* __restrict__ d_ptr = _data;
            const T* __restrict__ s_ptr = rhs.get_data();
            #pragma omp simd
            for (uint64_t i = 0; i < _size; ++i) d_ptr[i] += s_ptr[i];
        } else {
            // Non-contiguous path: use pointer arithmetic with strides
            std::vector<uint64_t> idx(_ndim, 0);
            
            for (uint64_t i = 0; i < _size; ++i) {
                // Compute byte offsets using strides
                uint64_t d_pos = 0, s_pos = 0;
                for (uint64_t d = 0; d < _ndim; ++d) {
                    d_pos += idx[d] * _strides[d];
                    s_pos += idx[d] * rhs._strides[d];
                }
                
                // Direct pointer addition
                _data[d_pos] += rhs.get_data()[s_pos];
                
                // Increment odometer using only destination dimensions
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
        }
        
        return *this;
    }

    // --- Array += Scalar ---
    Array<T>& operator+=(const T& val) {
        if (!_data || _size == 0) return *this;
        
        // Fast path: contiguous
        if (this->is_contiguous()) {
            T* __restrict__ d_ptr = _data;
            #pragma omp simd
            for (uint64_t i = 0; i < _size; ++i) d_ptr[i] += val;
        } else {
            // Non-contiguous path: use odometer iteration
            std::vector<uint64_t> idx(_ndim, 0);
            for (uint64_t i = 0; i < _size; ++i) {
                this->get_item(idx) += val;
                
                // Increment odometer
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
        }
        return *this;
    }

    // --- Array -= Array ---
    Array<T>& operator-=(const Array<T>& rhs) {
        // Validate shapes match
        if (_ndim != rhs.ndim()) THROW_INVALID_ARGUMENT("Dimension mismatch in -=.");
        for (uint64_t d = 0; d < _ndim; ++d) {
            if (_dimensions[d] != rhs._dimensions[d]) {
                THROW_INVALID_ARGUMENT("Shape mismatch in -= at dimension " + std::to_string(d));
            }
        }
        
        if (!_data) THROW_RUNTIME_ERROR("Destination array in -= has no data");
        if (!rhs.get_data()) THROW_RUNTIME_ERROR("Source array in -= has no data");
        if (_size == 0) return *this;
        
        // Fast path: both contiguous
        if (this->is_contiguous() && rhs.is_contiguous()) {
            T* __restrict__ d_ptr = _data;
            const T* __restrict__ s_ptr = rhs.get_data();
            #pragma omp simd
            for (uint64_t i = 0; i < _size; ++i) d_ptr[i] -= s_ptr[i];
        } else {
            // Non-contiguous path: use pointer arithmetic with strides
            std::vector<uint64_t> idx(_ndim, 0);
            
            for (uint64_t i = 0; i < _size; ++i) {
                // Compute byte offsets using strides
                uint64_t d_pos = 0, s_pos = 0;
                for (uint64_t d = 0; d < _ndim; ++d) {
                    d_pos += idx[d] * _strides[d];
                    s_pos += idx[d] * rhs._strides[d];
                }
                
                // Direct pointer subtraction
                _data[d_pos] -= rhs.get_data()[s_pos];
                
                // Increment odometer using only destination dimensions
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
        }
        
        return *this;
    }

    // --- Array -= Scalar ---
    Array<T>& operator-=(const T& val) {
        if (!_data || _size == 0) return *this;
        
        // Fast path: contiguous
        if (this->is_contiguous()) {
            T* __restrict__ d_ptr = _data;
            #pragma omp simd
            for (uint64_t i = 0; i < _size; ++i) d_ptr[i] -= val;
        } else {
            // Non-contiguous path: use odometer iteration
            std::vector<uint64_t> idx(_ndim, 0);
            for (uint64_t i = 0; i < _size; ++i) {
                this->get_item(idx) -= val;
                
                // Increment odometer
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
        }
        return *this;
    }

    // --- Array *= Array ---
    Array<T>& operator*=(const Array<T>& rhs) {
        // Validate shapes match
        if (_ndim != rhs.ndim()) THROW_INVALID_ARGUMENT("Dimension mismatch in *=.");
        for (uint64_t d = 0; d < _ndim; ++d) {
            if (_dimensions[d] != rhs._dimensions[d]) {
                THROW_INVALID_ARGUMENT("Shape mismatch in *= at dimension " + std::to_string(d));
            }
        }
        
        if (!_data) THROW_RUNTIME_ERROR("Destination array in *= has no data");
        if (!rhs.get_data()) THROW_RUNTIME_ERROR("Source array in *= has no data");
        if (_size == 0) return *this;
        
        // Fast path: both contiguous
        if (this->is_contiguous() && rhs.is_contiguous()) {
            T* __restrict__ d_ptr = _data;
            const T* __restrict__ s_ptr = rhs.get_data();
            #pragma omp simd
            for (uint64_t i = 0; i < _size; ++i) d_ptr[i] *= s_ptr[i];
        } else {
            // Non-contiguous path: use pointer arithmetic with strides
            std::vector<uint64_t> idx(_ndim, 0);
            
            for (uint64_t i = 0; i < _size; ++i) {
                // Compute byte offsets using strides
                uint64_t d_pos = 0, s_pos = 0;
                for (uint64_t d = 0; d < _ndim; ++d) {
                    d_pos += idx[d] * _strides[d];
                    s_pos += idx[d] * rhs._strides[d];
                }
                
                // Direct pointer multiplication
                _data[d_pos] *= rhs.get_data()[s_pos];
                
                // Increment odometer using only destination dimensions
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
        }
        
        return *this;
    }

    // --- Array *= Scalar ---
    Array<T>& operator*=(const T& val) {
        if (!_data || _size == 0) return *this;
        
        // Fast path: contiguous
        if (this->is_contiguous()) {
            T* __restrict__ d_ptr = _data;
            #pragma omp simd
            for (uint64_t i = 0; i < _size; ++i) d_ptr[i] *= val;
        } else {
            // Non-contiguous path: use odometer iteration
            std::vector<uint64_t> idx(_ndim, 0);
            for (uint64_t i = 0; i < _size; ++i) {
                this->get_item(idx) *= val;
                
                // Increment odometer
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
        }
        return *this;
    }

    // --- Array /= Array ---
    Array<T>& operator/=(const Array<T>& rhs) {
        // Validate shapes match
        if (_ndim != rhs.ndim()) THROW_INVALID_ARGUMENT("Dimension mismatch in /=.");
        for (uint64_t d = 0; d < _ndim; ++d) {
            if (_dimensions[d] != rhs._dimensions[d]) {
                THROW_INVALID_ARGUMENT("Shape mismatch in /= at dimension " + std::to_string(d));
            }
        }
        
        if (!_data) THROW_RUNTIME_ERROR("Destination array in /= has no data");
        if (!rhs.get_data()) THROW_RUNTIME_ERROR("Source array in /= has no data");
        if (_size == 0) return *this;
        
        // Fast path: both contiguous
        if (this->is_contiguous() && rhs.is_contiguous()) {
            T* __restrict__ d_ptr = _data;
            const T* __restrict__ s_ptr = rhs.get_data();
            // Check for zeros before vectorized loop
            for (uint64_t i = 0; i < _size; ++i) {
                if constexpr (is_complex_v<T>) {
                    if (std::abs(s_ptr[i]) == 0.0) THROW_RUNTIME_ERROR("Div by 0.");
                } else if (s_ptr[i] == 0) THROW_RUNTIME_ERROR("Div by 0.");
            }
            // Vectorized division
            #pragma omp simd
            for (uint64_t i = 0; i < _size; ++i) {
                d_ptr[i] /= s_ptr[i];
            }
        } else {
            // Non-contiguous path: use pointer arithmetic with strides and zero checks
            std::vector<uint64_t> idx(_ndim, 0);
            
            for (uint64_t i = 0; i < _size; ++i) {
                // Compute byte offsets using strides
                uint64_t d_pos = 0, s_pos = 0;
                for (uint64_t d = 0; d < _ndim; ++d) {
                    d_pos += idx[d] * _strides[d];
                    s_pos += idx[d] * rhs._strides[d];
                }
                
                T src_val = rhs.get_data()[s_pos];
                if constexpr (is_complex_v<T>) {
                    if (std::abs(src_val) == 0.0) THROW_RUNTIME_ERROR("Div by 0.");
                } else if (src_val == 0) THROW_RUNTIME_ERROR("Div by 0.");
                
                _data[d_pos] /= src_val;
                
                // Increment odometer using only destination dimensions
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
        }
        
        return *this;
    }

    // --- Array /= Scalar ---
    Array<T>& operator/=(const T& val) {
        if constexpr (is_complex_v<T>) {
            if (std::abs(val) == 0.0) THROW_RUNTIME_ERROR("Div by 0.");
        } else if (val == 0) THROW_RUNTIME_ERROR("Div by 0.");
        
        if (!_data || _size == 0) return *this;
        
        // Fast path: contiguous
        if (this->is_contiguous()) {
            T* __restrict__ d_ptr = _data;
            #pragma omp simd
            for (uint64_t i = 0; i < _size; ++i) d_ptr[i] /= val;
        } else {
            // Non-contiguous path: use odometer iteration
            std::vector<uint64_t> idx(_ndim, 0);
            for (uint64_t i = 0; i < _size; ++i) {
                this->get_item(idx) /= val;
                
                // Increment odometer
                for (int d = (int)_ndim - 1; d >= 0; --d) {
                    if (++idx[d] < _dimensions[d]) break;
                    idx[d] = 0;
                }
            }
        }
        return *this;
    }

    // Scalar assignment (fill)
    Array<T>& operator=(const T& val) {
        fill(val); // Delegate to the optimized fill method
        return *this;
    }


    Array<T> copy() const {
        // Return an empty Array if source is empty
        if (this->size() == 0 && this->ndim() == 0) {
            return Array<T>();
        }

        Array<T> result(this->_ndim, this->_dimensions.get()); // Create a new owning array of the same shape

        if (this->_data && result._data && this->_size > 0) {
            // Use optimized segment-based copy for both contiguous and non-contiguous arrays
            copy_via_segments(*this, result);
        }
        return result;
    }

    // 1. Replace the primary fill(const T& value)
    void fill(const T& value) {
        if (_data == nullptr && _size > 0) {
            THROW_RUNTIME_ERROR("Attempted to fill an unallocated array.");
        }
        if (_size == 0) return;

        // Use optimized segment-based fill for both contiguous and non-contiguous arrays
        fill_via_segments(value);
    }

    // 2. Replace the template fill(const ValueType& value)
    template<typename ValueType>
    void fill(const ValueType& value) {
        // Cast once and delegate to the optimized primary fill
        T cast_value = static_cast<T>(value);
        this->fill(cast_value);
    }

    // ===== ITERATOR SUPPORT FOR RANGE-BASED FOR LOOPS =====
    // Iterator class for flattened iteration over array elements
    class iterator {
    private:
        T* _ptr;
        uint64_t _index;
        uint64_t _size;
        
    public:
        using difference_type   = std::ptrdiff_t;
        using value_type        = T;
        using pointer           = T*;
        using reference         = T&;
        using iterator_category = std::random_access_iterator_tag;

        iterator(T* ptr = nullptr, uint64_t index = 0, uint64_t size = 0)
            : _ptr(ptr), _index(index), _size(size) {}

        // Dereference operators
        T& operator*() const { return *_ptr; }
        T* operator->() const { return _ptr; }

        // Increment/decrement operators
        iterator& operator++() {
            ++_index;
            ++_ptr;
            return *this;
        }
        iterator operator++(int) {
            iterator tmp = *this;
            ++(*this);
            return tmp;
        }
        iterator& operator--() {
            --_index;
            --_ptr;
            return *this;
        }
        iterator operator--(int) {
            iterator tmp = *this;
            --(*this);
            return tmp;
        }

        // Random access operators
        iterator operator+(difference_type n) const {
            return iterator(_ptr + n, _index + n, _size);
        }
        iterator operator-(difference_type n) const {
            return iterator(_ptr - n, _index - n, _size);
        }
        iterator& operator+=(difference_type n) {
            _ptr += n;
            _index += n;
            return *this;
        }
        iterator& operator-=(difference_type n) {
            _ptr -= n;
            _index -= n;
            return *this;
        }
        difference_type operator-(const iterator& other) const {
            return _ptr - other._ptr;
        }

        // Comparison operators
        bool operator==(const iterator& other) const { return _ptr == other._ptr; }
        bool operator!=(const iterator& other) const { return _ptr != other._ptr; }
        bool operator<(const iterator& other) const { return _ptr < other._ptr; }
        bool operator<=(const iterator& other) const { return _ptr <= other._ptr; }
        bool operator>(const iterator& other) const { return _ptr > other._ptr; }
        bool operator>=(const iterator& other) const { return _ptr >= other._ptr; }

        // Subscript operator
        T& operator[](difference_type n) const { return _ptr[n]; }
    };

    // Const iterator class for flattened iteration over array elements
    class const_iterator {
    private:
        const T* _ptr;
        uint64_t _index;
        uint64_t _size;
        
    public:
        using difference_type   = std::ptrdiff_t;
        using value_type        = T;
        using pointer           = const T*;
        using reference         = const T&;
        using iterator_category = std::random_access_iterator_tag;

        const_iterator(const T* ptr = nullptr, uint64_t index = 0, uint64_t size = 0)
            : _ptr(ptr), _index(index), _size(size) {}

        // Allow conversion from mutable iterator to const iterator
        const_iterator(const iterator& it)
            : _ptr(&(*it)), _index(0), _size(0) {}

        // Dereference operators
        const T& operator*() const { return *_ptr; }
        const T* operator->() const { return _ptr; }

        // Increment/decrement operators
        const_iterator& operator++() {
            ++_index;
            ++_ptr;
            return *this;
        }
        const_iterator operator++(int) {
            const_iterator tmp = *this;
            ++(*this);
            return tmp;
        }
        const_iterator& operator--() {
            --_index;
            --_ptr;
            return *this;
        }
        const_iterator operator--(int) {
            const_iterator tmp = *this;
            --(*this);
            return tmp;
        }

        // Random access operators
        const_iterator operator+(difference_type n) const {
            return const_iterator(_ptr + n, _index + n, _size);
        }
        const_iterator operator-(difference_type n) const {
            return const_iterator(_ptr - n, _index - n, _size);
        }
        const_iterator& operator+=(difference_type n) {
            _ptr += n;
            _index += n;
            return *this;
        }
        const_iterator& operator-=(difference_type n) {
            _ptr -= n;
            _index -= n;
            return *this;
        }
        difference_type operator-(const const_iterator& other) const {
            return _ptr - other._ptr;
        }

        // Comparison operators
        bool operator==(const const_iterator& other) const { return _ptr == other._ptr; }
        bool operator!=(const const_iterator& other) const { return _ptr != other._ptr; }
        bool operator<(const const_iterator& other) const { return _ptr < other._ptr; }
        bool operator<=(const const_iterator& other) const { return _ptr <= other._ptr; }
        bool operator>(const const_iterator& other) const { return _ptr > other._ptr; }
        bool operator>=(const const_iterator& other) const { return _ptr >= other._ptr; }

        // Subscript operator
        const T& operator[](difference_type n) const { return _ptr[n]; }
    };

    // Returns iterator to the beginning of the flattened array
    iterator begin() {
        return iterator(_data, 0, _size);
    }

    // Returns iterator to the end of the flattened array
    iterator end() {
        return iterator(_data + _size, _size, _size);
    }

    // Returns const iterator to the beginning of the flattened array
    const_iterator begin() const {
        return const_iterator(_data, 0, _size);
    }

    // Returns const iterator to the end of the flattened array
    const_iterator end() const {
        return const_iterator(_data + _size, _size, _size);
    }

    // Returns const iterator to the beginning of the flattened array (explicit const)
    const_iterator cbegin() const {
        return const_iterator(_data, 0, _size);
    }

    // Returns const iterator to the end of the flattened array (explicit const)
    const_iterator cend() const {
        return const_iterator(_data + _size, _size, _size);
    }

    // Reverse iterator support
    std::reverse_iterator<iterator> rbegin() {
        return std::reverse_iterator<iterator>(end());
    }

    std::reverse_iterator<iterator> rend() {
        return std::reverse_iterator<iterator>(begin());
    }

    std::reverse_iterator<const_iterator> crbegin() const {
        return std::reverse_iterator<const_iterator>(cend());
    }

    std::reverse_iterator<const_iterator> crend() const {
        return std::reverse_iterator<const_iterator>(cbegin());
    }

    Array<T> squeeze() const {
        std::vector<uint64_t> squeezed_dims_vec;
        std::vector<uint64_t> squeezed_strides_vec;

        if (_ndim == 0) { // Squeezing a 0D array returns a copy of itself
            return Array<T>(0, nullptr, nullptr, this->_storage, (this->_data - this->_storage.get()));
        }
        if (!_dimensions) { // Should not happen if _ndim > 0, but as a safeguard
             return Array<T>();
        }

        for (uint64_t d = 0; d < _ndim; ++d) {
            if (_dimensions[d] != 1) {
                squeezed_dims_vec.push_back(_dimensions[d]);
                squeezed_strides_vec.push_back(_strides[d]);
            }
        }

        if (squeezed_dims_vec.empty()) { // If all dimensions were of size 1, result is a 0D array
            if (_size == 0) { // Handle case where original array was empty N-D
                return Array<T>(); // Return empty 0D array
            } else {
                return Array<T>(0, nullptr, nullptr, this->_storage, (this->_data - this->_storage.get()));
            }
        }

        return Array<T>(squeezed_dims_vec.size(), squeezed_dims_vec.data(), squeezed_strides_vec.data(), this->_storage, (this->_data - this->_storage.get()));
    }


    template<typename... Args>
    Array<T> reshape(Args... dims) const {
        // Check if array is contiguous before reshaping
        if (!is_contiguous()) {
            THROW_RUNTIME_ERROR("Cannot reshape a non-contiguous view. Call .copy() first.");
        }
        
        std::vector<uint64_t> new_dims_vec = {static_cast<uint64_t>(dims)...};
        uint64_t new_total_size = 1;
        for (uint64_t dim : new_dims_vec) {
             // Check for overflow during new_total_size calculation
            if (dim > std::numeric_limits<uint64_t>::max() / new_total_size) {
                THROW_INVALID_ARGUMENT("Reshape dimensions lead to size overflow.");
            }
            new_total_size *= dim;
        }
        if (new_total_size != _size) {
            THROW_INVALID_ARGUMENT("Reshape operation requires the total number of elements to remain unchanged.");
        }

        std::vector<uint64_t> new_strides_vec(new_dims_vec.size());
        if (!new_dims_vec.empty()) {
            new_strides_vec[new_dims_vec.size() - 1] = 1;
            for (int i = new_dims_vec.size() - 2; i >= 0; --i) {
                new_strides_vec[i] = new_strides_vec[i + 1] * new_dims_vec[i + 1];
            }
        }

        if (new_dims_vec.empty() && _size > 0) { // Reshaping to a 0D scalar
             return Array<T>(0, nullptr, nullptr, this->_storage, (this->_data - this->_storage.get()));
        } else if (new_dims_vec.empty() && _size == 0) { // Reshaping empty array to empty 0D
             return Array<T>();
        }

        // Create a new view with the reshaped dimensions but pointing to the same underlying data
        return Array<T>(new_dims_vec.size(), new_dims_vec.data(), new_strides_vec.data(), this->_storage, (this->_data - this->_storage.get()));
    }

    // Overload for reshape that takes a vector of dimensions
    Array<T> reshape(const std::vector<uint64_t>& new_dims_vec) const {
        if (!this->is_contiguous()) {
            THROW_RUNTIME_ERROR("Cannot reshape a non-contiguous view. Call .copy() first.");
        }
        uint64_t new_total_size = 1;
        for (uint64_t dim : new_dims_vec) {
             // Check for overflow during new_total_size calculation
            if (dim > std::numeric_limits<uint64_t>::max() / new_total_size) {
                THROW_INVALID_ARGUMENT("Reshape dimensions lead to size overflow.");
            }
            new_total_size *= dim;
        }
        if (new_total_size != _size) {
            THROW_INVALID_ARGUMENT("Reshape operation requires the total number of elements to remain unchanged.");
        }

        // Calculate the new strides
        std::vector<uint64_t> new_strides_vec(new_dims_vec.size());
        if (!new_dims_vec.empty()) {
            new_strides_vec[new_dims_vec.size() - 1] = 1;
            for (size_t i = new_dims_vec.size() - 1; i > 0; --i) {
                new_strides_vec[i - 1] = new_strides_vec[i] * new_dims_vec[i];
            }
        }

        // Create a new view with the reshaped dimensions but pointing to the same underlying data
        return Array<T>(new_dims_vec.size(), new_dims_vec.data(), new_strides_vec.data(), this->_storage, (this->_data - this->_storage.get()));
    }

   /**
     * @brief Transposes the array by permuting the axes.
     * Returns a zero-copy VIEW by manipulating strides and dimensions.
     */
    Array<T> transpose(const std::vector<uint64_t>& axes_permutation) const {
        // 1. Handle edge cases: 0D/1D or empty arrays
        if (_ndim <= 1 || _size == 0) {
            return Array<T>(_ndim, _dimensions.get(), _strides.get(), _storage, static_cast<uint64_t>(_data - _storage.get()));
        }

        std::vector<uint64_t> perm = axes_permutation;
        
        // 2. Default case (empty vector): reverse all dimensions (like NumPy .T)
        if (perm.empty()) {
            perm.resize(_ndim);
            std::iota(perm.rbegin(), perm.rend(), 0);
        }

        // 3. Validation
        if (perm.size() != _ndim) {
            THROW_INVALID_ARGUMENT("Transpose axes permutation size must match array dimensions.");
        }
        std::vector<bool> seen(_ndim, false);
        for (uint64_t axis : perm) {
            if (axis >= _ndim) THROW_INDEX_ERROR("Transpose axis index out of range.");
            if (seen[axis]) THROW_INVALID_ARGUMENT("Duplicate axis in transpose permutation.");
            seen[axis] = true;
        }

        // ISSUE #6: Detect common patterns for fast-path optimization
        // Pattern 1: 2D matrix transpose (0,1) -> (1,0) - instant
        if (_ndim == 2 && perm.size() == 2 && perm[0] == 1 && perm[1] == 0) {
            uint64_t new_dims[2] = {_dimensions[1], _dimensions[0]};
            uint64_t new_strides[2] = {_strides[1], _strides[0]};
            return Array<T>(2, new_dims, new_strides, _storage, static_cast<uint64_t>(_data - _storage.get()));
        }
        
        // Pattern 2: Identity permutation (0,1,2,...) - just return a view copy
        bool is_identity = true;
        for (uint64_t i = 0; i < _ndim; ++i) {
            if (perm[i] != i) {
                is_identity = false;
                break;
            }
        }
        if (is_identity) {
            return Array<T>(_ndim, _dimensions.get(), _strides.get(), _storage, static_cast<uint64_t>(_data - _storage.get()));
        }

        // 4. Calculate new shape and strides based on permutation (general case)
        std::vector<uint64_t> new_dims(_ndim);
        std::vector<uint64_t> new_strides(_ndim);
        for (uint64_t i = 0; i < _ndim; ++i) {
            new_dims[i] = _dimensions[perm[i]];
            new_strides[i] = _strides[perm[i]];
        }

        // 5. Construct a non-owning view sharing the same storage
        return Array<T>(_ndim, new_dims.data(), new_strides.data(), _storage, static_cast<uint64_t>(_data - _storage.get()));
    }

    /**
     * @brief Variadic wrapper for transpose (e.g., arr.transpose(0, 2, 1)).
     */
    template<typename... Args, typename = std::enable_if_t<(std::is_integral_v<Args> && ...)>>
    Array<T> transpose(Args... axes) const {
        return transpose(std::vector<uint64_t>{static_cast<uint64_t>(axes)...});
    }

    /**
     * @brief Flattens the multi-dimensional array into a 1D array.
     * 
     * Returns a zero-copy view if the array is contiguous.
     * For non-contiguous arrays, throws an error and suggests calling .copy() first.
     * 
     * @return A 1D Array with the same total number of elements.
     * @throws If the array is non-contiguous.
     */
    Array<T> flatten() const {
        if (_size == 0) {
            return Array<T>(); // Return empty array
        }
        if (_ndim == 0) {
            // 0D array (scalar): reshape to 1D array with 1 element
            std::vector<uint64_t> new_dims{1};
            std::vector<uint64_t> new_strides{1};
            return Array<T>(1, new_dims.data(), new_strides.data(), 
                           this->_storage, (this->_data - this->_storage.get()));
        }
        if (_ndim == 1) {
            // Already 1D, return a view of the same data
            return Array<T>(1, _dimensions.get(), _strides.get(), _storage, (this->_data - _storage.get()));
        }
        
        // For multi-dimensional arrays, check contiguity
        if (!this->is_contiguous()) {
            THROW_RUNTIME_ERROR("Cannot flatten a non-contiguous view. Call .copy() first.");
        }
        
        // Create a 1D view with all elements
        std::vector<uint64_t> new_dims{_size};
        std::vector<uint64_t> new_strides{1};
        return Array<T>(1, new_dims.data(), new_strides.data(), 
                       this->_storage, (this->_data - this->_storage.get()));
    }

    Array<T> empty_like() const {
        if (this->ndim() == 0) { 
            // Passes ndim=0 and a null dimension pointer to create a true scalar
            return Array<T>(0, nullptr); 
        }
        return Array<T>(this->_ndim, this->_dimensions.get());
    }

    Array<T> zeros_like() const {
        return Array<T>::zeros(this->dimensions_vector());
    }

    Array<T> ones_like() const {
        return Array<T>::ones(this->dimensions_vector());
    }

    Array<T> contiguous() const {
        return is_contiguous() ? *this : this->copy();
    }

    std::shared_ptr<T> get_raw_storage_ptr() const { return _storage; }

    inline __attribute__((always_inline)) T& get_item(const std::vector<uint64_t>& indices) { return _data[flatten_index(indices)]; }
    inline __attribute__((always_inline)) const T& get_item(const std::vector<uint64_t>& indices) const { return _data[flatten_index(indices)]; }

    template<typename... SliceArgs>
    Array<T> slice(SliceArgs... slices) const {
        static_assert((std::is_same_v<Slice, std::decay_t<SliceArgs>> && ...),
                      "All arguments to slice() must be of type Slice");
        std::vector<Slice> slices_vec = {slices...};
        return internal_slice_helper(slices_vec);
    }

    Array<T> slice(const std::vector<Slice>& slices) const {
        return internal_slice_helper(slices);
    }

    template<typename... Args,
             typename = std::enable_if_t<std::conjunction_v<std::is_integral<Args>...>>>
    void resize(Args... dims) {
        std::vector<uint64_t> new_dims_vec = {static_cast<uint64_t>(dims)...};
        resize(new_dims_vec);
    }

    void resize(const std::vector<uint64_t>& new_dims_vec) {
        // Clear current state
        _storage = nullptr;
        _data = nullptr;
        _dimensions = nullptr;
        _strides = nullptr;
        _size = 0;
        _ndim = 0;

        if (new_dims_vec.empty()) {
            _ndim = 0;
            _size = 1; // Resizing to a 0D array means it will hold one element
        } else {
            _ndim = new_dims_vec.size();
            _dimensions = std::make_unique<uint64_t[]>(_ndim);
            std::memcpy(_dimensions.get(), new_dims_vec.data(), _ndim * sizeof(uint64_t));
        }

        compute_size_and_strides();

        if (_size > 0) { // Only allocate if new size is not zero
            allocate_new_storage();
        }
    }

    /**
     * @brief Adds a singleton dimension (dimension of size 1) at the specified axis.
     * This creates a new view of the array without copying data.
     *
     * @param axis The axis at which to insert the new dimension.
     * Must be between 0 and ndim() (inclusive).
     * @return A new Array object that is a view with the added dimension.
     */
    Array<T> add_singleton_dimension(uint64_t axis) const {
        if (axis > _ndim) {
            THROW_INVALID_ARGUMENT("Axis " + std::to_string(axis) + " is out of bounds for array with " + std::to_string(_ndim) + " dimensions.");
        }

        // Handle empty array case: Returns an empty array with the new conceptual dimensions
        if (_size == 0) {
            std::vector<uint64_t> new_dims_vec_empty_case;
            for(uint64_t i = 0; i < _ndim; ++i) {
                new_dims_vec_empty_case.push_back(_dimensions[i]);
            }
            new_dims_vec_empty_case.insert(new_dims_vec_empty_case.begin() + axis, 1);
            // For an empty array, it will still be empty (_size 0) with new shape.
            return Array<T>(new_dims_vec_empty_case); // This constructor allocates for size=0 which is nullptr
        }

        // Construct new dimensions vector
        std::vector<uint64_t> new_dims_vec;
        new_dims_vec.reserve(_ndim + 1);
        for (uint64_t i = 0; i < axis; ++i) {
            new_dims_vec.push_back(_dimensions[i]);
        }
        new_dims_vec.push_back(1); // Insert the new singleton dimension
        for (uint64_t i = axis; i < _ndim; ++i) {
            new_dims_vec.push_back(_dimensions[i]);
        }

        // Construct new strides vector
        std::vector<uint64_t> new_strides_vec;
        new_strides_vec.reserve(_ndim + 1);
        for (uint64_t i = 0; i < axis; ++i) {
            new_strides_vec.push_back(_strides[i]);
        }
        // The stride for the new dimension is the stride of the dimension it's inserted before
        // or 1 if it's the new innermost dimension.
        if (axis < _ndim) {
            new_strides_vec.push_back(_strides[axis]);
        } else { // Inserting at the end, new innermost dimension
            new_strides_vec.push_back(1);
        }
        for (uint64_t i = axis; i < _ndim; ++i) {
            new_strides_vec.push_back(_strides[i]);
        }

        uint64_t absolute_start_offset_in_storage = (this->_data - this->_storage.get());

        // Return a new Array object as a view
        return Array<T>(new_dims_vec.size(), new_dims_vec.data(), new_strides_vec.data(), this->_storage, absolute_start_offset_in_storage);
    }

    template<typename U>
    Array<U> astype() const {
        Array<U> result;
        if (this->ndim() == 0) {
            result = Array<U>(0); // 0D array will have size 1
        } else {
            result = Array<U>(this->_ndim, this->_dimensions.get());
        }

        if (this->size() == 0) { // If source is empty, result is also empty
            return result;
        }

        // Optimized cast for contiguous arrays
        if (this->is_contiguous() && result.is_contiguous()) {
            for (uint64_t i = 0; i < _size; ++i) {
                result.get_data()[i] = static_cast<U>(_data[i]);
            }
        } else {
            // Fallback for non-contiguous arrays
            std::vector<uint64_t> current_indices(this->_ndim, 0);

            std::function<void(uint64_t)> iterate_and_cast =
                [&](uint64_t dim) {
                if (dim == this->_ndim) {
                    result.get_item(current_indices) = static_cast<U>(this->get_item(current_indices));
                    return;
                }

                for (uint64_t i = 0; i < this->_dimensions[dim]; ++i) {
                    current_indices[dim] = i;
                    iterate_and_cast(dim + 1);
                }
            };

            if (this->_ndim == 0) { // Special handling for 0D source
                if (this->_size == 1) {
                    result() = static_cast<U>((*this)());
                }
            } else {
                iterate_and_cast(0);
            }
        }
        return result;
    }

    // 1. Primary Factory (Single allocation pass)
    static Array<T> zeros(const std::vector<uint64_t>& dims) {
        Array<T> arr(dims); 
        // This triggers the specialized memset logic in your updated fill()
        arr.fill(static_cast<T>(0)); 
        return arr;
    }

    // 2. Convenience Variadic Factory
    template<typename... Args>
    static Array<T> zeros(Args... args) {
        return zeros(std::vector<uint64_t>{static_cast<uint64_t>(args)...});
    }

    // 3. Clone Factory
    static Array<T> zeros_like(const Array<T>& other) {
        return zeros(other.dimensions_vector());
    }

    // 1. Primary Factory (Single allocation pass)
    static Array<T> ones(const std::vector<uint64_t>& dims) {
        Array<T> arr(dims); 
        // This triggers the specialized memset logic in your updated fill()
        arr.fill(static_cast<T>(1)); 
        return arr;
    }

    // 2. Convenience Variadic Factory
    template<typename... Args>
    static Array<T> ones(Args... args) {
        return ones(std::vector<uint64_t>{static_cast<uint64_t>(args)...});
    }

    // 3. Clone Factory
    static Array<T> ones_like(const Array<T>& other) {
        return ones(other.dimensions_vector());
    }

    // 1. Primary Factory (Single allocation pass)
    static Array<T> rand(const std::vector<uint64_t>& dims) {
        Array<T> arr(dims);
        // Use thread_local to guarantee OpenMP safety
        thread_local std::mt19937 gen(std::random_device{}());
        
        if constexpr (is_complex_v<T>) {
            using value_type = typename T::value_type;
            std::uniform_real_distribution<value_type> dis(0.0, 1.0);
            for (uint64_t i = 0; i < arr._size; ++i) {
                arr._data[i] = T(dis(gen), dis(gen));
            }
        } else {
            std::uniform_real_distribution<T> dis(0.0, 1.0);
            for (uint64_t i = 0; i < arr._size; ++i) {
                arr._data[i] = dis(gen);
            }
        }
        return arr;
    }

    // 2. Convenience Variadic Factory
    template<typename... Args>
    static Array<T> rand(Args... args) {
        return rand(std::vector<uint64_t>{static_cast<uint64_t>(args)...});
    }

    // 3. Clone Factory
    static Array<T> rand_like(const Array<T>& other) {
        return rand(other.dimensions_vector());
    }

};

} // namespace Voxel

#include "ArrayMathOps.hpp"
