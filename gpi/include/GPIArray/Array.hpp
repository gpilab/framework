/**
 * @file Array.hpp
 * @brief Multi-dimensional array class for numerical computing with advanced slicing, views, and memory management.

 *
 * This header defines the GPIArray::Array<T> template class, which provides a flexible and efficient
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
#ifndef GPIArray_ARRAY_HPP
#define GPIArray_ARRAY_HPP

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

namespace GPIArray {

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

    uint64_t flatten_index(const std::vector<uint64_t>& indices) const {
        return validate_and_compute_flat_index(indices.data(), indices.size());
    }

    Array<T> internal_slice_helper(const std::vector<Slice>& slices_input) const {
        uint64_t effective_ndim = std::max(_ndim, (uint64_t)slices_input.size());

        std::vector<uint64_t> new_dims_vec;
        new_dims_vec.reserve(effective_ndim);
        std::vector<uint64_t> new_strides_vec;
        new_strides_vec.reserve(effective_ndim);
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

            if (step == 0) THROW_INVALID_ARGUMENT("Slice step cannot be zero.");

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

            new_dims_vec.push_back(sliced_dim_size);
            new_strides_vec.push_back(original_stride * std::abs(step));
            relative_start_offset_elements += effective_start * original_stride;
        }

        std::vector<uint64_t> squeezed_dims_final;
        std::vector<uint64_t> squeezed_strides_final;

        uint64_t total_sliced_size = 1;
        for(uint64_t dim : new_dims_vec) {
            total_sliced_size *= dim;
        }

        if (total_sliced_size == 0) { // If the slice results in an empty array
            return Array<T>(); // Return an empty Array object
        }

        for (uint64_t d = 0; d < new_dims_vec.size(); ++d) {
            if (new_dims_vec[d] != 1) { // Squeeze out dimensions of size 1
                squeezed_dims_final.push_back(new_dims_vec[d]);
                squeezed_strides_final.push_back(new_strides_vec[d]);
            }
        }

        if (squeezed_dims_final.empty() && total_sliced_size > 0) {
            // If all dimensions are squeezed to 1, result is a 0D array (scalar)
            return Array<T>(0, nullptr, nullptr, this->_storage, (this->_data - this->_storage.get()) + relative_start_offset_elements);
        }

        uint64_t absolute_start_offset_in_storage = (this->_data - this->_storage.get()) + relative_start_offset_elements;

        return Array<T>(squeezed_dims_final.size(), squeezed_dims_final.data(), squeezed_strides_final.data(), this->_storage, absolute_start_offset_in_storage);
    }

    template<typename Func>
    void iterate_nd(Func func) {
        if (_size == 0 && _ndim > 0) return; // For empty N-D arrays
        if (_ndim == 0) {
            if (_size == 1) func(0); // For 0D scalar
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


public:
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
    Array(uint64_t ndim, uint64_t* dims, uint64_t* strides, std::shared_ptr<T> shared_storage, uint64_t offset) {
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

        // Optimized deep copy for contiguous arrays
        if (other.is_contiguous() && other._data != nullptr) {
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
                if (_data) { // Ensure allocation was successful
                    std::memcpy(_data, other._data, _size * sizeof(T));
                }
            }
        } else {
            // Fallback to element-wise copy for non-contiguous arrays or unallocated source
            if (other._ndim == 0) { // 0D non-contiguous (e.g. view of scalar)
                _ndim = 0;
                _size = 1;
                _dimensions = nullptr;
                _strides = nullptr;
                allocate_new_storage();
                if (_data) {
                    (*this)() = other();
                }
            } else {
                init(other._ndim, other._dimensions.get()); // Allocates new storage for copy
                if (_data && other._data) { // Only copy if both source and destination have data
                    std::vector<uint64_t> current_indices(other._ndim, 0);
                    std::function<void(uint64_t)> iterate_copy =
                        [&](uint64_t dim) {
                        if (dim == other._ndim) {
                            this->get_item(current_indices) = other.get_item(current_indices);
                            return;
                        }
                        for (uint64_t i = 0; i < other._dimensions[dim]; ++i) {
                            current_indices[dim] = i;
                            iterate_copy(dim + 1);
                        }
                    };
                    iterate_copy(0);
                }
            }
        }
    }

    bool is_empty() const {
        return (_size == 0);
    }

    bool is_contiguous() const {
        if (_ndim == 0) return true; // 0D arrays are trivially contiguous
        if (_size == 0) return true; // Empty arrays are trivially contiguous (no data to be non-contiguous)

        uint64_t expected_stride = 1;
        // Check from the last dimension backwards for row-major contiguity
        for (int i = _ndim - 1; i >= 0; --i) {
            if (_strides[i] != expected_stride) {
                return false;
            }
            // Portable overflow check (using std::numeric_limits instead of __builtin_mul_overflow)
            if (_dimensions[i] > std::numeric_limits<uint64_t>::max() / expected_stride) {
                 // If multiplication would overflow, it's not a standard contiguous layout that fits uint64_t
                 return false;
            }
            expected_stride *= _dimensions[i];
        }
        return true;
    }

    // Copy Assignment Operator: Handles reallocation for owning arrays, and maintains views.
    Array& operator=(const Array<T>& other) {
        if (this == &other) { // Self-assignment check
            return *this;
        }

        // --- Handle empty 'other' array ---
        if (other._size == 0 && other._ndim == 0) {
            if (this->is_owning()) {
                _storage = nullptr; _data = nullptr; _dimensions = nullptr; _strides = nullptr; _ndim = 0; _size = 0;
            } else {
                // If 'this' is a view, it cannot become empty; size mismatch
                THROW_INVALID_ARGUMENT("Array assignment: cannot assign an empty array to a view.");
            }
            return *this;
        }

        // --- Handle 'other' being a 0D scalar (size == 1, ndim == 0) ---
        if (other._ndim == 0 && other._size == 1) {
            if (this->is_owning() && this->_ndim == 0 && this->_size == 1 && !_data) {
                // If this is an unallocated 0D array, allocate it.
                allocate_new_storage();
            }
            // Scalar assignment (broadcasting) handles both owning and view cases correctly
            this->fill(other());
            return *this;
        }

        // --- Handle N-dimensional array assignment ---
        // At this point, 'other' is guaranteed to be an N-dimensional array (ndim > 0, size > 0).

        // Determine if target array's shape needs to change.
        bool shape_matches = (this->_ndim == other._ndim);
        if (shape_matches) {
            for (uint64_t i = 0; i < this->_ndim; ++i) {
                if (this->_dimensions[i] != other._dimensions[i]) {
                    shape_matches = false;
                    break;
                }
            }
        }

        // If shapes don't match, try to squeeze singletons from 'other' to match 'this'
        if (!shape_matches) {
            // Check if 'other' has singleton dimensions that when squeezed would match 'this'
            std::vector<uint64_t> other_squeezed_shape;
            uint64_t other_squeezed_ndim = 0;
            for (uint64_t d = 0; d < other._ndim; ++d) {
                if (other._dimensions[d] != 1) {
                    other_squeezed_shape.push_back(other._dimensions[d]);
                    other_squeezed_ndim++;
                }
            }
            
            // Check if squeezed shape matches this shape
            if (other_squeezed_ndim == this->_ndim) {
                bool squeezed_matches = true;
                for (uint64_t i = 0; i < this->_ndim; ++i) {
                    if (this->_dimensions[i] != other_squeezed_shape[i]) {
                        squeezed_matches = false;
                        break;
                    }
                }
                
                if (squeezed_matches) {
                    // Create a squeezed view of 'other' and assign from it
                    std::vector<uint64_t> other_squeezed_strides;
                    for (uint64_t d = 0; d < other._ndim; ++d) {
                        if (other._dimensions[d] != 1) {
                            other_squeezed_strides.push_back(other._strides[d]);
                        }
                    }
                    Array<T> other_squeezed(other_squeezed_ndim, other_squeezed_shape.data(), 
                                           other_squeezed_strides.data(), other._storage, 
                                           (other._data - other._storage.get()));
                    return *this = other_squeezed;  // Recursive call with matched shapes
                }
            }
        }

        if (!shape_matches) {
            if (this->is_owning()) {
                // If 'this' is an owning array and shapes don't match, reallocate to match 'other's shape.
                init(other._ndim, other._dimensions.get());
            } else {
                // If 'this' is a view and shapes don't match, it's an error. Views cannot change shape.
                THROW_INVALID_ARGUMENT("Array assignment: cannot assign array of shape " +
                                       other.dimensions_vector_to_string() + " to a view of shape " +
                                       this->dimensions_vector_to_string() + " (dimensions mismatch).");
            }
        }
        // If shapes match (either initially, or after re-allocation for owning array), proceed to copy elements.

        // Perform element-wise copy.
        if (this->_data && other._data && this->_size > 0) {
            // Optimization for contiguous arrays: use memcpy
            if (this->is_contiguous() && other.is_contiguous()) {
                std::memcpy(this->_data, other._data, this->_size * sizeof(T));
            } else {
                // Robust N-dimensional iteration for potentially non-contiguous source or destination.
                std::vector<uint64_t> current_indices(this->_ndim, 0);
                std::function<void(uint64_t)> iterate_copy =
                    [&](uint64_t dim) {
                    if (dim == this->_ndim) {
                        this->get_item(current_indices) = other.get_item(current_indices);
                        return;
                    }
                    for (uint64_t i = 0; i < this->_dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        iterate_copy(dim + 1);
                    }
                };
                iterate_copy(0);
            }
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
            if (effective_dim_idx < 0 || effective_dim_idx >= _ndim) {
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
            if (effective_dim_idx < 0 || effective_dim_idx >= _ndim) {
                THROW_INDEX_ERROR("Dimension index " + std::to_string(i) + " (effective " + std::to_string(effective_dim_idx) + ") is out of range for array with " + std::to_string(_ndim) + " dimensions.");
            }
        #endif

        return _dimensions[effective_dim_idx];
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

    T* get_data() const { return _data; }

    inline __attribute__((always_inline)) T& operator()(uint64_t i) {
        uint64_t indices[] = {i};
        return _data[validate_and_compute_flat_index(indices, 1)];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i) const {
        uint64_t indices[] = {i};
        return _data[validate_and_compute_flat_index(indices, 1)];
    }

    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j) {
        uint64_t indices[] = {i, j};
        return _data[validate_and_compute_flat_index(indices, 2)];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j) const {
        uint64_t indices[] = {i, j};
        return _data[validate_and_compute_flat_index(indices, 2)];
    }

    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k) {
        uint64_t indices[] = {i, j, k};
        return _data[validate_and_compute_flat_index(indices, 3)];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k) const {
        uint64_t indices[] = {i, j, k};
        return _data[validate_and_compute_flat_index(indices, 3)];
    }

    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l) {
        uint64_t indices[] = {i, j, k, l};
        return _data[validate_and_compute_flat_index(indices, 4)];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l) const {
        uint64_t indices[] = {i, j, k, l};
        return _data[validate_and_compute_flat_index(indices, 4)];
    }

    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m) {
        uint64_t indices[] = {i, j, k, l, m};
        return _data[validate_and_compute_flat_index(indices, 5)];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m) const {
        uint64_t indices[] = {i, j, k, l, m};
        return _data[validate_and_compute_flat_index(indices, 5)];
    }

    inline __attribute__((always_inline)) T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n) {
        uint64_t indices[] = {i, j, k, l, m, n};
        return _data[validate_and_compute_flat_index(indices, 6)];
    }
    inline __attribute__((always_inline)) const T& operator()(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n) const {
        uint64_t indices[] = {i, j, k, l, m, n};
        return _data[validate_and_compute_flat_index(indices, 6)];
    }
    template<typename... Args,
             typename = std::enable_if_t<std::conjunction_v<std::is_integral<Args>...>>>
    T& operator()(Args... args) {
        uint64_t indices_arr[sizeof...(args)];
        size_t idx_counter = 0;
        ((indices_arr[idx_counter++] = static_cast<uint64_t>(args)), ...);
        return _data[validate_and_compute_flat_index(indices_arr, sizeof...(args))];
    }

    template<typename... Args,
             typename = std::enable_if_t<std::conjunction_v<std::is_integral<Args>...>>>
    const T& operator()(Args... args) const {
        uint64_t indices_arr[sizeof...(args)];
        size_t idx_counter = 0;
        ((indices_arr[idx_counter++] = static_cast<uint64_t>(args)), ...);
        return _data[validate_and_compute_flat_index(indices_arr, sizeof...(args))];
    }
    T& operator()() {
        return _data[validate_and_compute_flat_index(nullptr, 0)];
    }
    const T& operator()() const {
        return _data[validate_and_compute_flat_index(nullptr, 0)];
    }


    Array<T>& operator+=(const Array<T>& rhs) {
        if (_ndim != rhs._ndim) THROW_INVALID_ARGUMENT("Dimension mismatch in += (Array vs Array)");
        for(uint64_t i = 0; i < _ndim; ++i) {
            if(_dimensions[i] != rhs._dimensions[i]) {
                THROW_INVALID_ARGUMENT("Dimension mismatch at axis " + std::to_string(i) + " in += (Array vs Array)");
            }
        }
        if (_data && rhs._data && _size > 0) {
            // Fast path for contiguous arrays
            if (this->is_contiguous() && rhs.is_contiguous()) {
                for (uint64_t i = 0; i < _size; ++i) {
                    _data[i] += rhs._data[i];
                }
            } else {
                std::vector<uint64_t> current_indices(_ndim);
                std::function<void(uint64_t)> recurse =
                    [&](uint64_t dim) {
                    if (dim == _ndim) {
                        get_item(current_indices) += rhs.get_item(current_indices);
                        return;
                    }
                    for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        recurse(dim + 1);
                    }
                };
                if (_ndim == 0) (*this)() += rhs();
                else recurse(0);
            }
        }
        return *this;
    }
    Array<T>& operator-=(const Array<T>& rhs) {
        if (_ndim != rhs._ndim) THROW_INVALID_ARGUMENT("Dimension mismatch in -= (Array vs Array)");
        for(uint64_t i = 0; i < _ndim; ++i) {
            if(_dimensions[i] != rhs._dimensions[i]) {
                THROW_INVALID_ARGUMENT("Dimension mismatch at axis " + std::to_string(i) + " in -= (Array vs Array)");
            }
        }
        if (_data && rhs._data && _size > 0) {
            // Fast path for contiguous arrays
            if (this->is_contiguous() && rhs.is_contiguous()) {
                for (uint64_t i = 0; i < _size; ++i) {
                    _data[i] -= rhs._data[i];
                }
            } else {
                std::vector<uint64_t> current_indices(_ndim);
                std::function<void(uint64_t)> recurse =
                    [&](uint64_t dim) {
                    if (dim == _ndim) {
                        get_item(current_indices) -= rhs.get_item(current_indices);
                        return;
                    }
                    for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        recurse(dim + 1);
                    }
                };
                if (_ndim == 0) (*this)() -= rhs();
                else recurse(0);
            }
        }
        return *this;
    }
    Array<T>& operator*=(const Array<T>& rhs) {
        if (_ndim != rhs._ndim) THROW_INVALID_ARGUMENT("Dimension mismatch in *= (Array vs Array)");
        for(uint64_t i = 0; i < _ndim; ++i) {
            if(_dimensions[i] != rhs._dimensions[i]) {
                THROW_INVALID_ARGUMENT("Dimension mismatch at axis " + std::to_string(i) + " in *= (Array vs Array)");
            }
        }
        if (_data && rhs._data && _size > 0) {
            // Fast path for contiguous arrays
            if (this->is_contiguous() && rhs.is_contiguous()) {
                for (uint64_t i = 0; i < _size; ++i) {
                    _data[i] *= rhs._data[i];
                }
            } else {
                std::vector<uint64_t> current_indices(_ndim);
                std::function<void(uint64_t)> recurse =
                    [&](uint64_t dim) {
                    if (dim == _ndim) {
                        get_item(current_indices) *= rhs.get_item(current_indices);
                        return;
                    }
                    for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        recurse(dim + 1);
                    }
                };
                if (_ndim == 0) (*this)() *= rhs();
                else recurse(0);
            }
        }
        return *this;
    }
    Array<T>& operator/=(const Array<T>& rhs) {
        if (_ndim != rhs._ndim) THROW_INVALID_ARGUMENT("Dimension mismatch in /= (Array vs Array)");
        for(uint64_t i = 0; i < _ndim; ++i) {
            if(_dimensions[i] != rhs._dimensions[i]) {
                THROW_INVALID_ARGUMENT("Dimension mismatch at axis " + std::to_string(i) + " in /= (Array vs Array)");
            }
        }
        if (_data && rhs._data && _size > 0) {
            // Fast path for contiguous arrays
            if (this->is_contiguous() && rhs.is_contiguous()) {
                for (uint64_t i = 0; i < _size; ++i) {
                    if constexpr (std::is_floating_point_v<T> || std::is_integral_v<T>) {
                        if (rhs._data[i] == static_cast<T>(0)) {
                            THROW_RUNTIME_ERROR("Division by zero in Array /= Array operation.");
                        }
                    } else if constexpr (std::is_same_v<T, std::complex<float>> || std::is_same_v<T, std::complex<double>>) {
                        if (std::abs(rhs._data[i]) < std::numeric_limits<typename T::value_type>::epsilon()) {
                             THROW_RUNTIME_ERROR("Division by near-zero complex number in Array /= Array operation.");
                        }
                    }
                    _data[i] /= rhs._data[i];
                }
            } else {
                std::vector<uint64_t> current_indices(_ndim);
                std::function<void(uint64_t)> recurse =
                    [&](uint64_t dim) {
                    if (dim == _ndim) {
                        if constexpr (std::is_floating_point_v<T> || std::is_integral_v<T>) {
                            if (rhs.get_item(current_indices) == static_cast<T>(0)) {
                                THROW_RUNTIME_ERROR("Division by zero in Array /= Array operation.");
                            }
                        } else if constexpr (std::is_same_v<T, std::complex<float>> || std::is_same_v<T, std::complex<double>>) {
                            if (std::abs(rhs.get_item(current_indices)) < std::numeric_limits<typename T::value_type>::epsilon()) {
                                 THROW_RUNTIME_ERROR("Division by near-zero complex number in Array /= Array operation.");
                            }
                        }
                        get_item(current_indices) /= rhs.get_item(current_indices);
                        return;
                    }
                    for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        recurse(dim + 1);
                    }
                };
                if (_ndim == 0) (*this)() /= rhs();
                else recurse(0);
            }
        }
        return *this;
    }

    Array<T>& operator+=(const T& val) {
        if (_data && _size > 0) {
            if (this->is_contiguous()) { // Fast path for contiguous arrays
                for (uint64_t i = 0; i < _size; ++i) {
                    _data[i] += val;
                }
            } else {
                std::vector<uint64_t> current_indices(_ndim);
                std::function<void(uint64_t)> recurse =
                    [&](uint64_t dim) {
                    if (dim == _ndim) {
                        get_item(current_indices) += val;
                        return;
                    }
                    for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        recurse(dim + 1);
                    }
                };
                if (_ndim == 0) (*this)() += val;
                else recurse(0);
            }
        }
        return *this;
    }
    Array<T>& operator-=(const T& val) {
        if (_data && _size > 0) {
            if (this->is_contiguous()) { // Fast path for contiguous arrays
                for (uint64_t i = 0; i < _size; ++i) {
                    _data[i] -= val;
                }
            } else {
                std::vector<uint64_t> current_indices(_ndim);
                std::function<void(uint64_t)> recurse =
                    [&](uint64_t dim) {
                    if (dim == _ndim) {
                        get_item(current_indices) -= val;
                        return;
                    }
                    for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        recurse(dim + 1);
                    }
                };
                if (_ndim == 0) (*this)() -= val;
                else recurse(0);
            }
        }
        return *this;
    }
    Array<T>& operator*=(const T& val) {
        if (_data && _size > 0) {
            if (this->is_contiguous()) { // Fast path for contiguous arrays
                for (uint64_t i = 0; i < _size; ++i) {
                    _data[i] *= val;
                }
            } else {
                std::vector<uint64_t> current_indices(_ndim);
                std::function<void(uint64_t)> recurse =
                    [&](uint64_t dim) {
                    if (dim == _ndim) {
                        get_item(current_indices) *= val;
                        return;
                    }
                    for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        recurse(dim + 1);
                    }
                };
                if (_ndim == 0) (*this)() *= val;
                else recurse(0);
            }
        }
        return *this;
    }
    Array<T>& operator/=(const T& val) {
        if constexpr (std::is_floating_point_v<T> || std::is_integral_v<T>) {
            if (val == static_cast<T>(0)) {
                THROW_RUNTIME_ERROR("Division by zero scalar in Array /= scalar operation.");
            }
        } else if constexpr (std::is_same_v<T, std::complex<float>> || std::is_same_v<T, std::complex<double>>) {
            if (std::abs(val) < std::numeric_limits<typename T::value_type>::epsilon()) {
                 THROW_RUNTIME_ERROR("Division by near-zero complex scalar in Array /= scalar operation.");
            }
        }
        if (_data && _size > 0) {
            if (this->is_contiguous()) { // Fast path for contiguous arrays
                for (uint64_t i = 0; i < _size; ++i) {
                    _data[i] /= val;
                }
            } else {
                std::vector<uint64_t> current_indices(_ndim);
                std::function<void(uint64_t)> recurse =
                    [&](uint64_t dim) {
                    if (dim == _ndim) {
                        get_item(current_indices) /= val;
                        return;
                    }
                    for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        recurse(dim + 1);
                    }
                };
                if (_ndim == 0) (*this)() /= val;
                else recurse(0);
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

        if (this->_data && result._data) { // Ensure both have valid data pointers
            // Optimized copy for contiguous arrays
            if (this->is_contiguous()) {
                std::memcpy(result._data, this->_data, this->_size * sizeof(T));
            } else {
                // Fallback to N-dimensional iteration for non-contiguous arrays
                std::vector<uint64_t> current_indices(this->_ndim, 0);
                std::function<void(uint64_t)> iterate_copy =
                    [&](uint64_t dim) {
                    if (dim == this->_ndim) {
                        result.get_item(current_indices) = this->get_item(current_indices);
                        return;
                    }
                    for (uint64_t i = 0; i < this->_dimensions[dim]; ++i) {
                        current_indices[dim] = i;
                        iterate_copy(dim + 1);
                    }
                };
                iterate_copy(0);
            }
        }
        return result;
    }

    // 1. Replace the primary fill(const T& value)
    void fill(const T& value) {
        if (_data == nullptr && _size > 0) {
            THROW_RUNTIME_ERROR("Attempted to fill an unallocated array.");
        }
        if (_size == 0) return;

        if (is_contiguous()) {
            // Check for zero-fill optimization
            bool is_zero = false;
            if constexpr (std::is_scalar_v<T>) {
                is_zero = (value == static_cast<T>(0));
            } else if constexpr (is_complex_v<T>) { // Uses your is_complex_v trait
                is_zero = (value.real() == 0 && value.imag() == 0);
            }

            if (is_zero) {
                // The high-speed fix for your 1.5s Step 2 bottleneck
                std::memset(_data, 0, _size * sizeof(T));
                return;
            }
            std::fill(_data, _data + _size, value);
        } else {
            // Fallback for non-contiguous views (e.g., slices)
            std::vector<uint64_t> current_indices(_ndim);
            std::function<void(uint64_t)> recurse = [&](uint64_t dim) {
                if (dim == _ndim) {
                    get_item(current_indices) = value;
                    return;
                }
                for (uint64_t i = 0; i < _dimensions[dim]; ++i) {
                    current_indices[dim] = i;
                    recurse(dim + 1);
                }
            };
            if (_ndim == 0) (*this)() = value;
            else recurse(0);
        }
    }

    // 2. Replace the template fill(const ValueType& value)
    template<typename ValueType>
    void fill(const ValueType& value) {
        // Cast once and delegate to the optimized primary fill
        T cast_value = static_cast<T>(value);
        this->fill(cast_value);
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
        return Array<T>(new_dims_vec.size(), const_cast<uint64_t*>(new_dims_vec.data()), new_strides_vec.data(), this->_storage, (this->_data - this->_storage.get()));
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
        return Array<T>(new_dims_vec.size(), const_cast<uint64_t*>(new_dims_vec.data()), new_strides_vec.data(), this->_storage, (this->_data - this->_storage.get()));
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

        // 4. Calculate new shape and strides based on permutation
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

    Array<T> empty_like() const {
        if (this->ndim() == 0) { // Return empty 0D if source is 0D
            return Array<T>(0);
        }
        // Returns a new owning array with the same shape but uninitialized data
        return Array<T>(this->_ndim, this->_dimensions.get());
    }

    std::shared_ptr<T> get_raw_storage_ptr() const { return _storage; }

    T& get_item(const std::vector<uint64_t>& indices) { return _data[flatten_index(indices)]; }
    const T& get_item(const std::vector<uint64_t>& indices) const { return _data[flatten_index(indices)]; }

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

};

} // namespace GPIArray

#include "ArrayMathOps.hpp"

#endif // GPIArray_ARRAY_HPP