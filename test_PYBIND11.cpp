/**
 * @file test_PYBIND11.cpp
 * @brief Broadcasting functionality tests exposed to Python via Pybind11
 * @description Tests zero-copy broadcasting in Array operators:
 *   - Binary arithmetic with shape broadcasting
 *   - In-place operators with broadcasting
 *   - Comparison operators with broadcasting
 *   - Broadcasting shape validation
 */

#include "gpi/include/Voxel/Voxel.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <complex>

namespace py = pybind11;
using namespace Voxel;

using Complex = std::complex<double>;
using Array_c = Array<Complex>;
using Array_d = Array<double>;
using Array_b = Array<bool>;

// ============================================================================
// Test 1: Broadcasting Addition (Array + Array)
// ============================================================================
/**
 * Test shape: (3, 1, 5) + (1, 4, 5) → (3, 4, 5)
 * Demonstrates right-aligned broadcasting where dimensions of size 1 expand
 */
Array_c test_broadcast_add(const Array_c& A, const Array_c& B) {
    return A + B;
}

// ============================================================================
// Test 2: Broadcasting Multiplication (Array * Array)
// ============================================================================
/**
 * Test Element-wise multiplication with broadcasting
 * Shape: (5, 1) * (1, 3) → (5, 3)
 */
Array_c test_broadcast_mul(const Array_c& A, const Array_c& B) {
    return A * B;
}

// ============================================================================
// Test 3: Broadcasting Subtraction (Array - Array)
// ============================================================================
/**
 * Test Element-wise subtraction with broadcasting
 * Shape: (4, 3, 1) - (1, 1, 2) → (4, 3, 2)
 */
Array_c test_broadcast_sub(const Array_c& A, const Array_c& B) {
    return A - B;
}

// ============================================================================
// Test 4: Broadcasting Division (Array / Array)
// ============================================================================
/**
 * Test Element-wise division with broadcasting
 * Shape: (2, 1, 3) / (1, 4, 1) → (2, 4, 3)
 */
Array_c test_broadcast_div(const Array_c& A, const Array_c& B) {
    return A / B;
}

// ============================================================================
// Test 5: In-Place Broadcasting Addition (Array += Array)
// ============================================================================
/**
 * Test in-place addition with broadcasting
 * Modifies lhs shape to match after broadcasting
 */
void test_broadcast_add_inplace(Array_c& A, const Array_c& B) {
    A += B;
}

// ============================================================================
// Test 6: In-Place Broadcasting Multiplication (Array *= Array)
// ============================================================================
/**
 * Test in-place element-wise multiplication with broadcasting
 */
void test_broadcast_mul_inplace(Array_c& A, const Array_c& B) {
    A *= B;
}

// ============================================================================
// Test 7: Broadcasting Equality Comparison (Array == Array)
// ============================================================================
/**
 * Test broadcasting in equality comparisons
 * Returns Array<bool> with broadcasted shape
 */
Array_b test_broadcast_eq(const Array_c& A, const Array_c& B) {
    return A == B;
}

// ============================================================================
// Test 8: Broadcasting Less-Than Comparison (Array < Array)
// ============================================================================
/**
 * Test broadcasting in less-than comparison (by magnitude for complex)
 * Returns Array<bool> with broadcasted shape
 */
Array_b test_broadcast_lt(const Array_c& A, const Array_c& B) {
    return A < B;
}

// ============================================================================
// Test 9: Broadcasting Greater-Than Comparison (Array > Array)
// ============================================================================
/**
 * Test broadcasting in greater-than comparison
 * Returns Array<bool> with broadcasted shape
 */
Array_b test_broadcast_gt(const Array_c& A, const Array_c& B) {
    return A > B;
}

// ============================================================================
// Test 10: Test is_broadcastable_to Helper
// ============================================================================
/**
 * Check if an array shape can broadcast to target shape without throwing
 */
bool test_is_broadcastable(const Array_c& arr, const std::vector<uint64_t>& target_shape) {
    return arr.is_broadcastable_to(target_shape);
}

// ============================================================================
// Test 11: Broadcast Multiple Arrays and Combine Results
// ============================================================================
/**
 * Complex operation: (A * B) + C with multiple broadcasting steps
 * Demonstrates chaining multiple broadcasting operations
 */
Array_c test_broadcast_chain(const Array_c& A, const Array_c& B, const Array_c& C) {
    auto result = (A * B) + C;
    return result;
}

// ============================================================================
// Test 12: Scalar Broadcasting with Arrays
// ============================================================================
/**
 * Test broadcasting scalar across array
 * Should apply scalar to all elements regardless of shape
 */
Array_d test_broadcast_scalar_mul(const Array_d& A, double scalar) {
    return A * scalar;
}

// ============================================================================
// Test 13: Scalar Broadcasting in Comparison
// ============================================================================
/**
 * Test broadcasting scalar in comparison operations
 * Returns Array<bool> with same shape as array
 */
Array_b test_broadcast_scalar_lt(const Array_d& A, double scalar) {
    return A < scalar;
}

// ============================================================================
// Test 14: Get Result Shape After Broadcasting
// ============================================================================
/**
 * Helper to determine the output shape after broadcasting two arrays
 * Returns vector<uint64_t> describing the broadcasted shape
 */
std::vector<uint64_t> test_get_broadcast_shape(const Array_c& A, const Array_c& B) {
    // Manually compute what broadcast_to would produce
    const auto& shape_a = A.dimensions_vector();
    const auto& shape_b = B.dimensions_vector();
    
    int ndim_a = shape_a.size();
    int ndim_b = shape_b.size();
    int max_ndim = std::max(ndim_a, ndim_b);
    
    std::vector<uint64_t> result(max_ndim);
    for (int i = 1; i <= max_ndim; ++i) {
        uint64_t dim_a = (ndim_a - i >= 0) ? shape_a[ndim_a - i] : 1;
        uint64_t dim_b = (ndim_b - i >= 0) ? shape_b[ndim_b - i] : 1;
        result[max_ndim - i] = std::max(dim_a, dim_b);
    }
    return result;
}

// ============================================================================
// Test 15: Edge Case - Broadcasting to 0D Array
// ============================================================================
/**
 * Test broadcasting scalar array to full-dimensional array
 */
Array_c test_broadcast_scalar_to_nd(const Array_c& scalar_arr, const std::vector<uint64_t>& target_shape) {
    return scalar_arr.broadcast_to(target_shape);
}

// ============================================================================
// PYBIND11 Module Definition
// ============================================================================
PYBIND11_MODULE(test, m) {
    m.doc() = "Voxel Array Broadcasting Tests - Callable from Python";

    // Test 1: Broadcasting Addition
    m.def("test_broadcast_add", 
          &test_broadcast_add,
          "Add two arrays with automatic broadcasting.\n"
          "Example: (3,1,5) + (1,4,5) → (3,4,5)");

    // Test 2: Broadcasting Multiplication
    m.def("test_broadcast_mul", 
          &test_broadcast_mul,
          "Multiply two arrays element-wise with broadcasting.\n"
          "Example: (5,1) * (1,3) → (5,3)");

    // Test 3: Broadcasting Subtraction
    m.def("test_broadcast_sub", 
          &test_broadcast_sub,
          "Subtract arrays with broadcasting.\n"
          "Example: (4,3,1) - (1,1,2) → (4,3,2)");

    // Test 4: Broadcasting Division
    m.def("test_broadcast_div", 
          &test_broadcast_div,
          "Divide arrays element-wise with broadcasting.\n"
          "Example: (2,1,3) / (1,4,1) → (2,4,3)");

    // Test 5: In-Place Broadcasting Addition
    m.def("test_broadcast_add_inplace", 
          &test_broadcast_add_inplace,
          "Add array B to A in-place with broadcasting.\n"
          "Modifies A to match broadcasted shape.");

    // Test 6: In-Place Broadcasting Multiplication
    m.def("test_broadcast_mul_inplace", 
          &test_broadcast_mul_inplace,
          "Multiply A by B element-wise in-place with broadcasting.\n"
          "Modifies A to match broadcasted shape.");

    // Test 7: Broadcasting Equality
    m.def("test_broadcast_eq", 
          &test_broadcast_eq,
          "Compare two arrays for equality with broadcasting.\n"
          "Returns Array<bool> with broadcasted shape.");

    // Test 8: Broadcasting Less-Than
    m.def("test_broadcast_lt", 
          &test_broadcast_lt,
          "Compare two complex arrays by magnitude with broadcasting.\n"
          "For complex: |A| < |B|");

    // Test 9: Broadcasting Greater-Than
    m.def("test_broadcast_gt", 
          &test_broadcast_gt,
          "Compare two complex arrays by magnitude with broadcasting.\n"
          "For complex: |A| > |B|");

    // Test 10: Check Broadcastability
    m.def("test_is_broadcastable", 
          &test_is_broadcastable,
          "Check if array can broadcast to target shape without throwing.\n"
          "Returns True if broadcastable, False otherwise.");

    // Test 11: Chained Broadcasting
    m.def("test_broadcast_chain", 
          &test_broadcast_chain,
          "Complex operation: (A * B) + C with multiple broadcasting steps.\n"
          "Demonstrates chaining multiple broadcasted operations.");

    // Test 12: Scalar Broadcasting
    m.def("test_broadcast_scalar_mul", 
          &test_broadcast_scalar_mul,
          "Multiply array by scalar (applies to all elements).\n"
          "Scalar broadcasting is automatic for any shape.");

    // Test 13: Scalar Comparison
    m.def("test_broadcast_scalar_lt", 
          &test_broadcast_scalar_lt,
          "Compare array elements against scalar threshold.\n"
          "Returns Array<bool> with same shape as input array.");

    // Test 14: Get Broadcast Shape
    m.def("test_get_broadcast_shape", 
          &test_get_broadcast_shape,
          "Compute output shape resulting from broadcasting two arrays.\n"
          "Returns vector<uint64_t> describing broadcasted dimensions.");

    // Test 15: Broadcast Scalar to ND
    m.def("test_broadcast_scalar_to_nd", 
          &test_broadcast_scalar_to_nd,
          "Broadcast a scalar array (0D or 1D) to target shape.\n"
          "Zero-copy operation using stride manipulation.");
}
