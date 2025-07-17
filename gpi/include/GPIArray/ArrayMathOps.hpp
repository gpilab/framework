// ArrayMathOps.hpp - Math operator overloads for Array<T>
#pragma once

#include <type_traits>
#include <stdexcept>
#include <vector>
#include <complex>
#include <cmath>
#include <numeric>     // For std::accumulate
#include <algorithm>   // For std::min_element, std::max_element, std::clamp, std::abs
#include <functional>  // For std::function
#include "Array.hpp" // Ensure Array.hpp is included if this file defines free functions for it
#include "ArrayException.hpp" // For THROW_INVALID_ARGUMENT, THROW_RUNTIME_ERROR

namespace GPIArray {

// Custom type trait for std::complex (C++17 compatible, replaces C++20 std::is_complex_v)
template <typename T>
struct is_complex : std::false_type {};

template <typename T>
struct is_complex<std::complex<T>> : std::true_type {};

template <typename T>
constexpr bool is_complex_v = is_complex<T>::value;

// Helper to iterate N-dimensionally and apply a function (Unary Array operation)
// T_OUT: Type of the output array (result)
// T_IN: Type of the input array (arr1)
template<typename T_OUT, typename T_IN, typename Func>
void apply_elementwise(Array<T_OUT>& result, const Array<T_IN>& arr1, Func func) {
    if (result.size() == 0) return;

    // The result.is_contiguous() and arr1.is_contiguous() calls will now correctly use their respective types.
    if (result.is_contiguous() && arr1.is_contiguous()) {
        T_OUT* res_data = result.get_data();
        const T_IN* arr1_data = arr1.get_data();
        for (uint64_t i = 0; i < result.size(); ++i) {
            res_data[i] = func(arr1_data[i]);
        }
    } else {
        std::vector<uint64_t> current_indices(result.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == result.ndim()) {
                result.get_item(current_indices) = func(arr1.get_item(current_indices));
                return;
            }
            for (uint64_t i = 0; i < result.dimensions(dim); ++i) { // Use result dimensions for iteration
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (result.ndim() == 0) result() = func(arr1());
        else recurse(0);
    }
}

// Helper to iterate N-dimensionally and apply a function (Binary Array operation)
// T_OUT: Type of the output array (result)
// T_IN1: Type of the first input array (arr1)
// T_IN2: Type of the second input array (arr2)
template<typename T_OUT, typename T_IN1, typename T_IN2, typename Func>
void apply_elementwise(Array<T_OUT>& result, const Array<T_IN1>& arr1, const Array<T_IN2>& arr2, Func func) {
    if (result.size() == 0) return;

    if (result.is_contiguous() && arr1.is_contiguous() && arr2.is_contiguous()) {
        T_OUT* res_data = result.get_data();
        const T_IN1* arr1_data = arr1.get_data();
        const T_IN2* arr2_data = arr2.get_data();
        for (uint64_t i = 0; i < result.size(); ++i) {
            res_data[i] = func(arr1_data[i], arr2_data[i]);
        }
    } else {
        std::vector<uint64_t> current_indices(result.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == result.ndim()) {
                result.get_item(current_indices) = func(arr1.get_item(current_indices), arr2.get_item(current_indices));
                return;
            }
            for (uint64_t i = 0; i < result.dimensions(dim); ++i) { // Use result dimensions for iteration
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (result.ndim() == 0) result() = func(arr1(), arr2());
        else recurse(0);
    }
}

// Helper to iterate N-dimensionally and apply a function (Array-Scalar operation)
// T_OUT: Type of the output array (result)
// T_IN: Type of the input array (arr1)
// Scalar: Type of the scalar value
template<typename T_OUT, typename T_IN, typename Scalar, typename Func>
void apply_elementwise(Array<T_OUT>& result, const Array<T_IN>& arr1, const Scalar& scalar_val, Func func) {
    if (result.size() == 0) return;

    if (result.is_contiguous() && arr1.is_contiguous()) {
        T_OUT* res_data = result.get_data();
        const T_IN* arr1_data = arr1.get_data();
        for (uint64_t i = 0; i < result.size(); ++i) {
            // Pass T_IN type from array, and Scalar type for the scalar value to func
            res_data[i] = func(arr1_data[i], scalar_val);
        }
    } else {
        std::vector<uint64_t> current_indices(result.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == result.ndim()) {
                // Pass T_IN type from array, and Scalar type for the scalar value to func
                result.get_item(current_indices) = func(arr1.get_item(current_indices), scalar_val);
                return;
            }
            for (uint64_t i = 0; i < result.dimensions(dim); ++i) { // Use result dimensions for iteration
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (result.ndim() == 0) result() = func(arr1(), scalar_val);
        else recurse(0);
    }
}

// --- Shape Validation Helper ---
template<typename T1, typename T2>
void validate_shapes(const Array<T1>& lhs, const Array<T2>& rhs, const std::string& op_name) {
    if (lhs.ndim() != rhs.ndim()) {
        THROW_INVALID_ARGUMENT("Dimension mismatch in " + op_name + " (lhs.ndim() = " + std::to_string(lhs.ndim()) + ", rhs.ndim() = " + std::to_string(rhs.ndim()) + ")");
    }
    if (lhs.size() == 0 && rhs.size() == 0) { // Both empty, considered compatible
        return;
    }
    if (lhs.size() != rhs.size()) { // Sizes must match for element-wise ops, after checking ndim
        THROW_INVALID_ARGUMENT("Size mismatch in " + op_name + " (lhs.size() = " + std::to_string(lhs.size()) + ", rhs.size() = " + std::to_string(rhs.size()) + ")");
    }
    // Deep dimension check
    for (uint64_t i = 0; i < lhs.ndim(); ++i) {
        if (lhs.dimensions(i) != rhs.dimensions(i)) {
            THROW_INVALID_ARGUMENT("Dimension mismatch at axis " + std::to_string(i) + " in " + op_name + " (lhs.dim(" + std::to_string(i) + ") = " + std::to_string(lhs.dimensions(i)) + ", rhs.dim(" + std::to_string(i) + ") = " + std::to_string(rhs.dimensions(i)) + ")");
        }
    }
}


// --- Array<T> op Array<T> ---

template<typename T>
Array<T> operator+(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, "+");
    Array<T> result(lhs.dimensions_vector());
    apply_elementwise<T, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a + b; });
    return result;
}

template<typename T>
Array<T> operator-(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, "-");
    Array<T> result(lhs.dimensions_vector());
    apply_elementwise<T, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a - b; });
    return result;
}

template<typename T>
Array<T> operator*(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, "*");
    Array<T> result(lhs.dimensions_vector());
    apply_elementwise<T, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a * b; });
    return result;
}

template<typename T>
Array<T> operator/(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, "/");
    Array<T> result(lhs.dimensions_vector());
    apply_elementwise<T, T, T>(result, lhs, rhs, [](const T& a, const T& b) {
        if constexpr (std::is_floating_point_v<T> || std::is_integral_v<T>) {
            if (b == static_cast<T>(0)) {
                THROW_RUNTIME_ERROR("Division by zero in Array / Array operation.");
            }
        } else if constexpr (is_complex_v<T>) {
            if (std::abs(b) < std::numeric_limits<typename T::value_type>::epsilon()) {
                THROW_RUNTIME_ERROR("Division by near-zero complex number in Array / Array operation.");
            }
        }
        return a / b;
    });
    return result;
}

// --- Array<T> op scalar ---

template<typename T, typename Scalar,
         typename R = std::common_type_t<T, Scalar>> // Result type can be promoted
Array<R> operator+(const Array<T>& lhs, const Scalar& val) {
    Array<R> result(lhs.dimensions_vector());
    // Explicitly pass R, T, Scalar for apply_elementwise
    apply_elementwise<R, T, Scalar>(result, lhs, val, [](const T& a, const Scalar& b_scalar){ return static_cast<R>(a) + static_cast<R>(b_scalar); });
    return result;
}

template<typename T, typename Scalar,
         typename R = std::common_type_t<T, Scalar>>
Array<R> operator-(const Array<T>& lhs, const Scalar& val) {
    Array<R> result(lhs.dimensions_vector());
    apply_elementwise<R, T, Scalar>(result, lhs, val, [](const T& a, const Scalar& b_scalar){ return static_cast<R>(a) - static_cast<R>(b_scalar); });
    return result;
}

template<typename T, typename Scalar,
         typename R = std::common_type_t<T, Scalar>>
Array<R> operator*(const Array<T>& lhs, const Scalar& val) {
    Array<R> result(lhs.dimensions_vector());
    apply_elementwise<R, T, Scalar>(result, lhs, val, [](const T& a, const Scalar& b_scalar){ return static_cast<R>(a) * static_cast<R>(b_scalar); });
    return result;
}

template<typename T, typename Scalar,
         typename R = std::common_type_t<T, Scalar>>
Array<R> operator/(const Array<T>& lhs, const Scalar& val) {
    Array<R> result(lhs.dimensions_vector());
    // Check for division by zero on the scalar value
    if constexpr (std::is_floating_point_v<Scalar> || std::is_integral_v<Scalar>) {
        if (val == static_cast<Scalar>(0)) {
            THROW_RUNTIME_ERROR("Division by zero scalar in Array / scalar operation.");
        }
    } else if constexpr (is_complex_v<Scalar>) {
        if (std::abs(val) < std::numeric_limits<typename Scalar::value_type>::epsilon()) {
            THROW_RUNTIME_ERROR("Division by near-zero complex scalar in Array / scalar operation.");
        }
    }
    apply_elementwise<R, T, Scalar>(result, lhs, val, [](const T& a, const Scalar& b_scalar){ return static_cast<R>(a) / static_cast<R>(b_scalar); });
    return result;
}

// --- scalar op Array<T> (with type promotion) ---

template<typename Scalar, typename T,
         typename R = std::common_type_t<Scalar, T>>
Array<R> operator+(const Scalar& val, const Array<T>& rhs) {
    Array<R> result(rhs.dimensions_vector());
    // Note: The order of arguments in the lambda matches the logical operation (scalar + element)
    apply_elementwise<R, T, Scalar>(result, rhs, val, [](const T& b, const Scalar& a_scalar){ return static_cast<R>(a_scalar) + static_cast<R>(b); });
    return result;
}

template<typename Scalar, typename T,
         typename R = std::common_type_t<Scalar, T>>
Array<R> operator-(const Scalar& val, const Array<T>& rhs) {
    Array<R> result(rhs.dimensions_vector());
    apply_elementwise<R, T, Scalar>(result, rhs, val, [](const T& b, const Scalar& a_scalar){ return static_cast<R>(a_scalar) - static_cast<R>(b); });
    return result;
}

template<typename Scalar, typename T,
         typename R = std::common_type_t<Scalar, T>>
Array<R> operator*(const Scalar& val, const Array<T>& rhs) {
    Array<R> result(rhs.dimensions_vector());
    apply_elementwise<R, T, Scalar>(result, rhs, val, [](const T& b, const Scalar& a_scalar){ return static_cast<R>(a_scalar) * static_cast<R>(b); });
    return result;
}

template<typename Scalar, typename T,
         typename R = std::common_type_t<Scalar, T>>
Array<R> operator/(const Scalar& val, const Array<T>& rhs) {
    Array<R> result(rhs.dimensions_vector());
    apply_elementwise<R, T, Scalar>(result, rhs, val, [](const T& b, const Scalar& a_scalar) {
        // Check for division by zero on array elements
        if constexpr (std::is_floating_point_v<T> || std::is_integral_v<T>) {
            if (b == static_cast<T>(0)) {
                THROW_RUNTIME_ERROR("Division by zero in scalar / Array operation.");
            }
        } else if constexpr (is_complex_v<T>) {
            if (std::abs(b) < std::numeric_limits<typename T::value_type>::epsilon()) {
                THROW_RUNTIME_ERROR("Division by near-zero complex number in scalar / Array operation.");
            }
        }
        return static_cast<R>(a_scalar) / static_cast<R>(b);
    });
    return result;
}

// --- Boolean operators for Array<T> (result is Array<bool>) ---

template<typename T>
Array<bool> operator==(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, "==");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a == b; });
    return result;
}

template<typename T>
Array<bool> operator!=(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, "!=");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a != b; });
    return result;
}

// Comparison operator for Array<T> vs. Scalar (returns Array<bool>)
template<typename T, typename Scalar>
Array<bool> operator==(const Array<T>& arr, const Scalar& val) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& a, const Scalar& b_scalar){ return a == static_cast<T>(b_scalar); });
    return result;
}

template<typename T, typename Scalar>
Array<bool> operator!=(const Array<T>& arr, const Scalar& val) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& a, const Scalar& b_scalar){ return a != static_cast<T>(b_scalar); });
    return result;
}


// --- Comparison operators (<, <=, >, >=) ---

template<typename T>
Array<bool> operator<(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, "<");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a < b; });
    return result;
}

// Specialization for std::complex<T> comparison based on magnitude
template<typename T>
Array<bool> operator<(const Array<std::complex<T>>& lhs, const Array<std::complex<T>>& rhs) {
    validate_shapes(lhs, rhs, "complex <");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, std::complex<T>, std::complex<T>>(result, lhs, rhs, [](const std::complex<T>& a, const std::complex<T>& b){ return std::abs(a) < std::abs(b); });
    return result;
}

template<typename T>
Array<bool> operator<=(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, "<=");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a <= b; });
    return result;
}

// Specialization for std::complex<T> comparison based on magnitude
template<typename T>
Array<bool> operator<=(const Array<std::complex<T>>& lhs, const Array<std::complex<T>>& rhs) {
    validate_shapes(lhs, rhs, "complex <=");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, std::complex<T>, std::complex<T>>(result, lhs, rhs, [](const std::complex<T>& a, const std::complex<T>& b){ return std::abs(a) <= std::abs(b); });
    return result;
}


template<typename T>
Array<bool> operator>(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, ">");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a > b; });
    return result;
}

// Specialization for std::complex<T> comparison based on magnitude
template<typename T>
Array<bool> operator>(const Array<std::complex<T>>& lhs, const Array<std::complex<T>>& rhs) {
    validate_shapes(lhs, rhs, "complex >");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, std::complex<T>, std::complex<T>>(result, lhs, rhs, [](const std::complex<T>& a, const std::complex<T>& b){ return std::abs(a) > std::abs(b); });
    return result;
}

template<typename T>
Array<bool> operator>=(const Array<T>& lhs, const Array<T>& rhs) {
    validate_shapes(lhs, rhs, ">=");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, T, T>(result, lhs, rhs, [](const T& a, const T& b){ return a >= b; });
    return result;
}

// Specialization for std::complex<T> comparison based on magnitude
template<typename T>
Array<bool> operator>=(const Array<std::complex<T>>& lhs, const Array<std::complex<T>>& rhs) {
    validate_shapes(lhs, rhs, "complex >=");
    Array<bool> result(lhs.dimensions_vector());
    apply_elementwise<bool, std::complex<T>, std::complex<T>>(result, lhs, rhs, [](const std::complex<T>& a, const std::complex<T>& b){ return std::abs(a) >= std::abs(b); });
    return result;
}

// Comparison operator for Array<T> vs. Scalar
template<typename T, typename Scalar>
Array<bool> operator<(const Array<T>& arr, const Scalar& val) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& a, const Scalar& b_scalar){ return a < static_cast<T>(b_scalar); });
    return result;
}

template<typename T, typename Scalar>
Array<bool> operator<=(const Array<T>& arr, const Scalar& val) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& a, const Scalar& b_scalar){ return a <= static_cast<T>(b_scalar); });
    return result;
}

template<typename T, typename Scalar>
Array<bool> operator>(const Array<T>& arr, const Scalar& val) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& a, const Scalar& b_scalar){ return a > static_cast<T>(b_scalar); });
    return result;
}

template<typename T, typename Scalar>
Array<bool> operator>=(const Array<T>& arr, const Scalar& val) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& a, const Scalar& b_scalar){ return a >= static_cast<T>(b_scalar); });
    return result;
}

// Scalar vs. Array Comparison Operators
template<typename Scalar, typename T>
Array<bool> operator<(const Scalar& val, const Array<T>& arr) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& b, const Scalar& a_scalar){ return static_cast<T>(a_scalar) < b; });
    return result;
}

template<typename Scalar, typename T>
Array<bool> operator<=(const Scalar& val, const Array<T>& arr) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& b, const Scalar& a_scalar){ return static_cast<T>(a_scalar) <= b; });
    return result;
}

template<typename Scalar, typename T>
Array<bool> operator>(const Scalar& val, const Array<T>& arr) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& b, const Scalar& a_scalar){ return static_cast<T>(a_scalar) > b; });
    return result;
}

template<typename Scalar, typename T>
Array<bool> operator>=(const Scalar& val, const Array<T>& arr) {
    Array<bool> result(arr.dimensions_vector());
    apply_elementwise<bool, T, Scalar>(result, arr, val, [](const T& b, const Scalar& a_scalar){ return static_cast<T>(a_scalar) >= b; });
    return result;
}


// --- Unary math functions ---

template<typename T>
Array<T> abs(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::abs(val); });
    return result;
}

// Specialization for std::complex<T> → real-valued magnitude
template<typename T>
Array<T> abs(const Array<std::complex<T>>& arr) {
    Array<T> out(arr.dimensions_vector()); // Result is real type
    apply_elementwise<T, std::complex<T>>(out, arr, [](const std::complex<T>& val){ return std::abs(val); });
    return out;
}

template<typename T>
Array<std::complex<T>> conj(const Array<std::complex<T>>& input) {
    Array<std::complex<T>> result(input.dimensions_vector());
    apply_elementwise<std::complex<T>, std::complex<T>>(result, input, [](const std::complex<T>& val){ return std::conj(val); });
    return result;
}

template<typename T>
Array<T> real(const Array<std::complex<T>>& input) {
    Array<T> result(input.dimensions_vector()); // Result is real type
    apply_elementwise<T, std::complex<T>>(result, input, [](const std::complex<T>& val){ return std::real(val); });
    return result;
}

template<typename T>
Array<T> imag(const Array<std::complex<T>>& input) {
    Array<T> result(input.dimensions_vector()); // Result is real type
    apply_elementwise<T, std::complex<T>>(result, input, [](const std::complex<T>& val){ return std::imag(val); });
    return result;
}

template<typename T>
Array<T> angle(const Array<std::complex<T>>& input) {
    Array<T> result(input.dimensions_vector()); // Result is real type
    apply_elementwise<T, std::complex<T>>(result, input, [](const std::complex<T>& val){ return std::arg(val); });
    return result;
}

// --- Trigonometric functions ---

template<typename T>
Array<T> sin(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::sin(val); });
    return result;
}

template<typename T>
Array<T> cos(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::cos(val); });
    return result;
}

template<typename T>
Array<T> tan(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::tan(val); });
    return result;
}

// --- Inverse trig functions ---

template<typename T>
Array<T> asin(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::asin(val); });
    return result;
}

template<typename T>
Array<T> acos(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::acos(val); });
    return result;
}

template<typename T>
Array<T> atan(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::atan(val); });
    return result;
}

// --- Hyperbolic trig functions ---

template<typename T>
Array<T> sinh(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::sinh(val); });
    return result;
}

template<typename T>
Array<T> cosh(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::cosh(val); });
    return result;
}

template<typename T>
Array<T> tanh(const Array<T>& input) {
    Array<T> result(input.dimensions_vector());
    apply_elementwise<T, T>(result, input, [](const T& val){ return std::tanh(val); });
    return result;
}

// ------------------------- Aggregation & Math Utilities ---------------------

template<typename T>
T sum(const Array<T>& arr) {
    if (arr.size() == 0) return T(0); // Handle empty array case
    // If contiguous, use std::accumulate directly on raw data for performance
    if (arr.is_contiguous()) {
        return std::accumulate(arr.get_data(), arr.get_data() + arr.size(), T(0));
    } else {
        // Fallback for non-contiguous: N-dimensional iteration
        T total_sum = T(0);
        std::vector<uint64_t> current_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == arr.ndim()) {
                total_sum += arr.get_item(current_indices);
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (arr.ndim() == 0) total_sum += arr();
        else recurse(0);
        return total_sum;
    }
}

// Non-template overload for Array<bool>
inline uint64_t sum(const Array<bool>& arr) {
    uint64_t count = 0;
    // For bool, direct iteration is always efficient enough
    const bool* arr_data = arr.get_data();
    const uint64_t s = arr.size();
    for (uint64_t i = 0; i < s; ++i) {
        if (arr_data[i]) { // Counts 'true' values (1s)
            count++;
        }
    }
    return count;
}


template<typename T>
double mean(const Array<T>& arr) {
    if (arr.size() == 0) THROW_INVALID_ARGUMENT("mean: input array cannot be empty."); // Handle division by zero
    return static_cast<double>(sum(arr)) / static_cast<double>(arr.size());
}

template<typename T>
T prod(const Array<T>& arr) {
    if (arr.size() == 0) return T(1); // Handle empty array case (product of no elements is 1)
    // If contiguous, use std::accumulate directly on raw data for performance
    if (arr.is_contiguous()) {
        return std::accumulate(arr.get_data(), arr.get_data() + arr.size(), T(1), std::multiplies<T>());
    } else {
        // Fallback for non-contiguous: N-dimensional iteration
        T total_prod = T(1);
        std::vector<uint64_t> current_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == arr.ndim()) {
                total_prod *= arr.get_item(current_indices);
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (arr.ndim() == 0) total_prod *= arr();
        else recurse(0);
        return total_prod;
    }
}

template<typename T>
double stdev(const Array<T>& arr) {
    double m = mean(arr);
    double accum = 0.0;
    if (arr.size() == 0) return 0.0; // Standard deviation for empty array

    if (arr.is_contiguous()) { // Fast path for contiguous arrays
        const T* arr_data = arr.get_data();
        const uint64_t s = arr.size();
        for (uint64_t i = 0; i < s; ++i) {
            accum += std::pow(static_cast<double>(std::norm(arr_data[i])) - m, 2);
        }
    } else {
        std::vector<uint64_t> current_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == arr.ndim()) {
                accum += std::pow(static_cast<double>(std::norm(arr.get_item(current_indices))) - m, 2);
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (arr.ndim() == 0) accum += std::pow(static_cast<double>(std::norm(arr())) - m, 2);
        else recurse(0);
    }
    if (arr.size() <= 1) return 0.0; // Handle single element or empty arrays
    return std::sqrt(accum / static_cast<double>(arr.size() - 1));
}

// ------------------------- Elementwise Math Functions -----------------------

template<typename T>
Array<T> floor(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::floor(val); });
    return out;
}

template<typename T>
Array<T> ceil(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::ceil(val); });
    return out;
}

template<typename T>
Array<T> exp(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::exp(val); });
    return out;
}

template<typename T>
Array<T> log(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::log(val); });
    return out;
}

template<typename T>
Array<T> log2(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::log2(val); });
    return out;
}

template<typename T>
Array<T> log10(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::log10(val); });
    return out;
}

template<typename T>
Array<T> sqrt(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::sqrt(val); });
    return out;
}

template<typename T>
Array<T> cbrt(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::cbrt(val); });
    return out;
}

template<typename T>
Array<T> round(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::round(val); });
    return out;
}

template<typename T>
Array<T> trunc(const Array<T>& arr) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [](const T& val){ return std::trunc(val); });
    return out;
}

template<typename T>
Array<T> pow(const Array<T>& base, const Array<T>& expn) {
    validate_shapes(base, expn, "pow");
    Array<T> out(base.dimensions_vector());
    apply_elementwise<T, T, T>(out, base, expn, [](const T& b, const T& e){ return std::pow(b, e); });
    return out;
}

// ------------------------- Min/Max/Clamp -----------------------

template<typename T>
T min(const Array<T>& arr) {
    if (arr.size() == 0) THROW_INVALID_ARGUMENT("min: input array cannot be empty.");
    if (arr.is_contiguous()) {
        return *std::min_element(arr.get_data(), arr.get_data() + arr.size());
    } else {
        T current_min = arr.get_item(std::vector<uint64_t>(arr.ndim(), 0)); // Initialize with value at (0,0,...)

        std::vector<uint64_t> global_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> full_scan_min =
            [&](uint64_t d) {
            if (d == arr.ndim()) {
                current_min = std::min(current_min, arr.get_item(global_indices));
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(d); ++i) {
                global_indices[d] = i;
                full_scan_min(d + 1);
            }
        };
        // Handle 0D case
        if (arr.ndim() == 0) return arr();
        
        full_scan_min(0);
        return current_min;
    }
}

template<typename T>
T max(const Array<T>& arr) {
    if (arr.size() == 0) THROW_INVALID_ARGUMENT("max: input array cannot be empty.");
    if (arr.is_contiguous()) {
        return *std::max_element(arr.get_data(), arr.get_data() + arr.size());
    } else {
        T current_max = arr.get_item(std::vector<uint64_t>(arr.ndim(), 0)); // Initialize with value at (0,0,...)
        std::vector<uint64_t> global_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> full_scan_max =
            [&](uint64_t d) {
            if (d == arr.ndim()) {
                current_max = std::max(current_max, arr.get_item(global_indices));
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(d); ++i) {
                global_indices[d] = i;
                full_scan_max(d + 1);
            }
        };
        // Handle 0D case
        if (arr.ndim() == 0) return arr();

        full_scan_max(0);
        return current_max;
    }
}

template<typename T>
Array<T> clamp(const Array<T>& arr, T lo, T hi) {
    Array<T> out(arr.dimensions_vector());
    apply_elementwise<T, T>(out, arr, [&](const T& val){ return std::clamp(val, lo, hi); });
    return out;
}

// ------------------------- Dot Product ---------------------

template<typename T>
Array<T> outer_product(const Array<T>& lhs, const Array<T>& rhs) {
    if (lhs.ndim() != 1 || rhs.ndim() != 1) {
        THROW_INVALID_ARGUMENT("outer_product: input arrays must be 1D.");
    }

    std::vector<uint64_t> result_dims = {lhs.size(), rhs.size()};
    Array<T> result(result_dims); // Result is always contiguous here

    // Iterate directly on underlying data as both are 1D and result is contiguous.
    // The indexing (i * rhs.size() + j) inherently handles contiguity for the result.
    const uint64_t lhs_s = lhs.size();
    const uint64_t rhs_s = rhs.size();

    // Check for non-contiguous inputs for efficiency
    if (lhs.is_contiguous() && rhs.is_contiguous()) {
        const T* lhs_data = lhs.get_data();
        const T* rhs_data = rhs.get_data();
        T* result_data = result.get_data();
        for (uint64_t i = 0; i < lhs_s; ++i) {
            for (uint64_t j = 0; j < rhs_s; ++j) {
                result_data[i * rhs_s + j] = lhs_data[i] * rhs_data[j];
            }
        }
    } else {
        // Fallback for non-contiguous inputs using get_item
        for (uint64_t i = 0; i < lhs_s; ++i) {
            for (uint64_t j = 0; j < rhs_s; ++j) {
                std::vector<uint64_t> lhs_indices = {i};
                std::vector<uint64_t> rhs_indices = {j};
                std::vector<uint64_t> result_indices = {i, j};
                result.get_item(result_indices) = lhs.get_item(lhs_indices) * rhs.get_item(rhs_indices);
            }
        }
    }
    return result;
}

template<typename T>
T dot(const Array<T>& a, const Array<T>& b) {
    if (a.size() != b.size()) {
        THROW_INVALID_ARGUMENT("dot: arrays must be of the same size.");
    }
    if (a.size() == 0) return T(0); // Dot product of empty vectors is 0

    T result = T(0);
    if (a.is_contiguous() && b.is_contiguous()) { // Fast path for contiguous arrays
        const T* a_data = a.get_data();
        const T* b_data = b.get_data();
        const uint64_t s = a.size();
        for (uint64_t i = 0; i < s; ++i) {
            result += a_data[i] * b_data[i];
        }
    } else {
        std::vector<uint64_t> current_indices(a.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == a.ndim()) {
                result += a.get_item(current_indices) * b.get_item(current_indices);
                return;
            }
            for (uint64_t i = 0; i < a.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (a.ndim() == 0) result += a() * b();
        else recurse(0);
    }
    return result;
}

template<typename T>
std::complex<T> dot(const Array<std::complex<T>>& a, const Array<std::complex<T>>& b) {
    if (a.size() != b.size()) {
        THROW_INVALID_ARGUMENT("dot: arrays must be of the same size.");
    }
    if (a.size() == 0) return std::complex<T>(0); // Dot product of empty vectors is 0

    std::complex<T> result = 0;
    if (a.is_contiguous() && b.is_contiguous()) { // Fast path for contiguous arrays
        const std::complex<T>* a_data = a.get_data();
        const std::complex<T>* b_data = b.get_data();
        const uint64_t s = a.size();
        for (uint64_t i = 0; i < s; ++i) {
            result += std::conj(a_data[i]) * b_data[i];
        }
    } else {
        std::vector<uint64_t> current_indices(a.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == a.ndim()) {
                result += std::conj(a.get_item(current_indices)) * b.get_item(current_indices);
                return;
            }
            for (uint64_t i = 0; i < a.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (a.ndim() == 0) result += std::conj(a()) * b();
        else recurse(0);
    }
    return result;
}

// ------------------------- Norms -----------------------

template<typename T>
double l1norm(const Array<T>& arr) {
    double result = 0.0;
    if (arr.size() == 0) return 0.0; // L1 norm of an empty vector is 0

    if (arr.is_contiguous()) { // Fast path for contiguous arrays
        const T* arr_data = arr.get_data();
        const uint64_t s = arr.size();
        for (uint64_t i = 0; i < s; ++i) {
            result += std::abs(static_cast<double>(arr_data[i]));
        }
    } else {
        std::vector<uint64_t> current_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == arr.ndim()) {
                result += std::abs(static_cast<double>(arr.get_item(current_indices)));
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (arr.ndim() == 0) result += std::abs(static_cast<double>(arr()));
        else recurse(0);
    }
    return result;
}

template<typename T>
double l2norm(const Array<T>& arr) {
    double sum_sq = 0.0;
    if (arr.size() == 0) return 0.0; // L2 norm of an empty vector is 0

    if (arr.is_contiguous()) { // Fast path for contiguous arrays
        const T* arr_data = arr.get_data();
        const uint64_t s = arr.size();
        for (uint64_t i = 0; i < s; ++i) {
            sum_sq += std::norm(arr_data[i]);
        }
    } else {
        std::vector<uint64_t> current_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == arr.ndim()) {
                sum_sq += std::norm(arr.get_item(current_indices));
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (arr.ndim() == 0) sum_sq += std::norm(arr());
        else recurse(0);
    }
    return std::sqrt(sum_sq);
}

template<typename T>
double linfnorm(const Array<T>& arr) {
    double max_val = 0.0;
    if (arr.size() == 0) return 0.0; // L-infinity norm of an empty vector is 0

    if (arr.is_contiguous()) { // Fast path for contiguous arrays
        const T* arr_data = arr.get_data();
        const uint64_t s = arr.size();
        for (uint64_t i = 0; i < s; ++i) {
            max_val = std::max(max_val, std::abs(static_cast<double>(arr_data[i])));
        }
    } else {
        std::vector<uint64_t> current_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == arr.ndim()) {
                max_val = std::max(max_val, std::abs(static_cast<double>(arr.get_item(current_indices))));
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (arr.ndim() == 0) max_val = std::max(max_val, std::abs(static_cast<double>(arr())));
        else recurse(0);
    }
    return max_val;
}

template<typename T>
double lpnorm(const Array<T>& arr, double p) {
    if (p < 1.0)
        THROW_INVALID_ARGUMENT("lpnorm: p must be >= 1.0");
    if (arr.size() == 0) return 0.0; // Lp norm of an empty vector is 0

    double sum_powers = 0.0;
    if (arr.is_contiguous()) { // Fast path for contiguous arrays
        const T* arr_data = arr.get_data();
        const uint64_t s = arr.size();
        for (uint64_t i = 0; i < s; ++i) {
            sum_powers += std::pow(std::abs(static_cast<double>(arr_data[i])), p);
        }
    } else {
        std::vector<uint64_t> current_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == arr.ndim()) {
                sum_powers += std::pow(std::abs(static_cast<double>(arr.get_item(current_indices))), p);
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (arr.ndim() == 0) sum_powers += std::pow(std::abs(static_cast<double>(arr())), p);
        else recurse(0);
    }
    return std::pow(sum_powers, 1.0 / p);
}

template<typename T>
double lpnorm(const Array<std::complex<T>>& arr, double p) {
    if (p < 1.0)
        THROW_INVALID_ARGUMENT("lpnorm: p must be >= 1.0");
    if (arr.size() == 0) return 0.0; // Lp norm of an empty vector is 0

    double sum_powers = 0.0;
    if (arr.is_contiguous()) { // Fast path for contiguous arrays
        const std::complex<T>* arr_data = arr.get_data();
        const uint64_t s = arr.size();
        for (uint64_t i = 0; i < s; ++i) {
            sum_powers += std::pow(std::abs(arr_data[i]), p);
        }
    } else {
        std::vector<uint64_t> current_indices(arr.ndim(), 0);
        std::function<void(uint64_t)> recurse =
            [&](uint64_t dim) {
            if (dim == arr.ndim()) {
                sum_powers += std::pow(std::abs(arr.get_item(current_indices)), p);
                return;
            }
            for (uint64_t i = 0; i < arr.dimensions(dim); ++i) {
                current_indices[dim] = i;
                recurse(dim + 1);
            }
        };
        if (arr.ndim() == 0) sum_powers += std::pow(std::abs(arr()), p);
        else recurse(0);
    }
    return std::pow(sum_powers, 1.0 / p);
}

template<typename T>
std::complex<T> norm(const Array<std::complex<T>>& arr) {
    return dot(arr, arr);
}

} // namespace GPIArray