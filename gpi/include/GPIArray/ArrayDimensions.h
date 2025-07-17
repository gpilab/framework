/**
 * @file ArrayDimensions.h
 * @brief Defines the GPIArray::ArrayDimensions class for representing multi-dimensional array shapes.
 *
 * This header provides the GPIArray::ArrayDimensions class, which encapsulates the dimensionality
 * and shape of multi-dimensional arrays. Key features include:
 *   - Construction from std::vector or up to 10 explicit dimension arguments (0D to 10D)
 *   - Efficient storage and access to dimension sizes
 *   - Exception-safe bounds checking for dimension queries
 *   - Comparison operators for shape equality
 *   - Conversion to std::vector for interoperability
 *   - Stream output for easy debugging and logging
 *
 * The ArrayDimensions class is intended for use in scientific and engineering applications
 * requiring flexible and robust handling of array shapes, and is designed to integrate
 * seamlessly with the GPIArray array container classes.
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#ifndef GPIArray_ARRAYDIMENSIONS_HPP
#define GPIArray_ARRAYDIMENSIONS_HPP

#include <vector>
#include <iostream>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <stdexcept>

namespace GPIArray {

class ArrayDimensions {
private:
    uint64_t _ndim;
    uint64_t *_dimensions;

    void array_from_dims(uint64_t ndim, const uint64_t *dimensions) {
        _ndim = ndim;
        if (ndim > 0) { // Only allocate if ndim > 0
            _dimensions = static_cast<uint64_t *>(malloc(ndim * sizeof(uint64_t)));
            if (!_dimensions)
                throw std::bad_alloc();
            std::memcpy(_dimensions, dimensions, ndim * sizeof(uint64_t));
        } else {
            _dimensions = nullptr; // For 0D, _dimensions is nullptr
        }
    }

public:
    ArrayDimensions(const std::vector<uint64_t> &dims) {
        array_from_dims(dims.size(), dims.data());
    }

    ArrayDimensions(uint64_t ndim, uint64_t *dimensions) {
        array_from_dims(ndim, dimensions);
    }

    // Explicit constructors
    explicit ArrayDimensions(uint64_t i) { // Make explicit
        uint64_t dims[1] = {i};
        array_from_dims(1, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j) {
        uint64_t dims[2] = {i, j};
        array_from_dims(2, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j, uint64_t k) {
        uint64_t dims[3] = {i, j, k};
        array_from_dims(3, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l) {
        uint64_t dims[4] = {i, j, k, l};
        array_from_dims(4, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m) {
        uint64_t dims[5] = {i, j, k, l, m};
        array_from_dims(5, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n) {
        uint64_t dims[6] = {i, j, k, l, m, n};
        array_from_dims(6, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o) {
        uint64_t dims[7] = {i, j, k, l, m, n, o};
        array_from_dims(7, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p) {
        uint64_t dims[8] = {i, j, k, l, m, n, o, p};
        array_from_dims(8, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q) {
        uint64_t dims[9] = {i, j, k, l, m, n, o, p, q};
        array_from_dims(9, dims);
    }

    ArrayDimensions(uint64_t i, uint64_t j, uint64_t k, uint64_t l, uint64_t m, uint64_t n, uint64_t o, uint64_t p, uint64_t q, uint64_t r) {
        uint64_t dims[10] = {i, j, k, l, m, n, o, p, q, r};
        array_from_dims(10, dims);
    }

    ~ArrayDimensions() {
        std::free(_dimensions);
    }

    uint64_t ndim() const { return _ndim; }

    const uint64_t* dimensions() const { return _dimensions; }

    uint64_t dimensions(uint64_t i) const {
        if (i >= _ndim)
            throw std::out_of_range("ArrayDimensions: dimension index out of range");
        return _dimensions[i];
    }

    std::vector<uint64_t> dimensions_vector() const {
        return std::vector<uint64_t>(_dimensions, _dimensions + _ndim);
    }

    bool operator==(const ArrayDimensions &rhs) const {
        if (_ndim != rhs._ndim) return false;
        for (uint64_t i = 0; i < _ndim; ++i)
            if (_dimensions[i] != rhs._dimensions[i]) return false;
        return true;
    }

    bool operator!=(const ArrayDimensions &rhs) const {
        return !(*this == rhs);
    }
};

inline std::ostream& operator<<(std::ostream &os, const ArrayDimensions &dims) {
    os << "ArrayDimensions " << dims.ndim() << "D (";
    for (uint64_t i = 0; i < dims.ndim(); ++i) {
        os << dims.dimensions()[i];
        if (i < dims.ndim() - 1) os << " x ";
    }
    os << ")";
    return os;
}

} // namespace GPIArray

#endif // GPIArray_ARRAYDIMENSIONS_HPP
