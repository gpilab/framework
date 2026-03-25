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
#include "gpi/include/Voxel/FFT_WRAPPER.hpp"
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
// Test 16: Sum of Array Elements (Running Pointer Arithmetic)
// ============================================================================
/**
 * Test aggregation function optimized with running pointer arithmetic
 * Works with contiguous, non-contiguous, and broadcasted arrays
 */
Complex test_sum_array(const Array_c& arr) {
    return sum(arr);
}

// ============================================================================
// Test 17: Product of Array Elements
// ============================================================================
/**
 * Test product aggregation
 * Optimized with running pointer arithmetic
 */
Complex test_prod_array(const Array_c& arr) {
    return prod(arr);
}

// ============================================================================
// Test 18: Count True Elements in Boolean Array
// ============================================================================
/**
 * Test count function for boolean arrays
 * Returns uint64_t count of true elements
 */
uint64_t test_count_true(const Array_b& arr) {
    return count(arr);
}

// ============================================================================
// Test 19: Minimum Value in Array (Complex by Magnitude)
// ============================================================================
/**
 * Test min aggregation
 * For complex: finds minimum magnitude
 * Optimized with running pointer arithmetic
 */
Complex test_min_array(const Array_c& arr) {
    return min(arr);
}

// ============================================================================
// Test 20: Maximum Value in Array (Complex by Magnitude)
// ============================================================================
/**
 * Test max aggregation
 * For complex: finds maximum magnitude
 * Optimized with running pointer arithmetic
 */
Complex test_max_array(const Array_c& arr) {
    return max(arr);
}

// ============================================================================
// Test 21: Standard Deviation of Array
// ============================================================================
/**
 * Test stdev aggregation
 * Computes standard deviation across all elements
 * Optimized with running pointer arithmetic
 */
double test_stdev_array(const Array_d& arr) {
    return stdev(arr);
}

// ============================================================================
// Test 22: L1 Norm (Sum of Absolute Values)
// ============================================================================
/**
 * Test L1 norm for complex arrays
 * l1norm() = sum(|element|) for all elements
 * Optimized with running pointer arithmetic
 */
double test_l1norm_array(const Array_c& arr) {
    return l1norm(arr);
}

// ============================================================================
// Test 23: L2 Norm (Euclidean)
// ============================================================================
/**
 * Test L2 norm for complex arrays
 * l2norm() = sqrt(sum(|element|^2))
 * Optimized with running pointer arithmetic
 */
double test_l2norm_array(const Array_c& arr) {
    return l2norm(arr);
}

// ============================================================================
// Test 24: L-Infinity Norm (Max Absolute Value)
// ============================================================================
/**
 * Test L-infinity norm
 * linfnorm() = max(|element|) for all elements
 * Optimized with running pointer arithmetic
 */
double test_linfnorm_array(const Array_c& arr) {
    return linfnorm(arr);
}

// ============================================================================
// Test 25: Lp Norm for Complex Arrays
// ============================================================================
/**
 * Test Lp norm for arbitrary p value
 * lpnorm(p) = (sum(|element|^p))^(1/p)
 * Optimized with running pointer arithmetic
 */
double test_lpnorm_array(const Array_c& arr, double p) {
    return lpnorm(arr, p);
}

// ============================================================================
// Test 26: Dot Product (Complex Arrays)
// ============================================================================
/**
 * Test dot product of two complex arrays
 * dot(a,b) = sum(conj(a[i]) * b[i])
 * Optimized with dual offset running pointer arithmetic
 */
Complex test_dot_complex(const Array_c& a, const Array_c& b) {
    return dot(a, b);
}

// ============================================================================
// Test 27: Outer Product of 1D Vectors
// ============================================================================
/**
 * Test outer product of two 1D vectors
 * Returns 2D array where result[i,j] = a[i] * b[j]
 * Optimized with direct stride-based indexing (no heap allocations)
 */
Array_c test_outer_product(const Array_c& a, const Array_c& b) {
    return outer_product(a, b);
}

// ============================================================================
// Test 28: In-Place Addition (Scalar)
// ============================================================================
/**
 * Test in-place addition with scalar
 * a += scalar applied to all elements
 */
void test_inplace_add_scalar(Array_d& a, double scalar) {
    a += scalar;
}

// ============================================================================
// Test 32: In-Place Subtraction (Scalar)
// ============================================================================
/**
 * Test in-place subtraction with scalar
 * a -= scalar
 */
void test_inplace_sub_scalar(Array_d& a, double scalar) {
    a -= scalar;
}

// ============================================================================
// Test 33: In-Place Multiplication (Scalar)
// ============================================================================
/**
 * Test in-place multiplication with scalar
 * a *= scalar
 */
void test_inplace_mul_scalar(Array_d& a, double scalar) {
    a *= scalar;
}

// ============================================================================
// Test 34: In-Place Division (Scalar)
// ============================================================================
/**
 * Test in-place division with scalar
 * a /= scalar with div-by-zero check
 */
void test_inplace_div_scalar(Array_d& a, double scalar) {
    a /= scalar;
}

// ============================================================================
// Test 35: In-Place Subtraction (Array)
// ============================================================================
/**
 * Test in-place subtraction with broadcasting
 * a -= b with proper broadcasting
 */
void test_inplace_sub_array(Array_c& a, const Array_c& b) {
    a -= b;
}

// ============================================================================
// Test 36: In-Place Division (Array)
// ============================================================================
/**
 * Test in-place division with broadcasting
 * a /= b with zero-check and proper broadcasting
 */
void test_inplace_div_array(Array_d& a, const Array_d& b) {
    a /= b;
}

// ============================================================================
// Test 37: Non-Contiguous Array Sum (Tests Stride Handling)
// ============================================================================
/**
 * Test sum on non-contiguous (strided) array
 * Verifies running pointer arithmetic works correctly
 */
Complex test_sum_strided(const Array_c& arr) {
    // Simulate strided access by getting slice
    return sum(arr);
}

// ============================================================================
// Test 38: L2 Norm on Broadcasted Array
// ============================================================================
/**
 * Test L2 norm on zero-copy broadcasted array
 * Verifies zero-stride handling in aggregation
 */
double test_l2norm_broadcasted(const Array_c& arr) {
    return l2norm(arr);
}

// ============================================================================
// Test 39: Dot Product with Complex Conjugate
// ============================================================================
/**
 * Test dot product computation direction
 * Verifies conjugate-multiply-accumulate is correct
 */
Complex test_dot_verification(const Array_c& a, const Array_c& b) {
    return dot(a, b);
}

// ============================================================================
// Test 40: Min/Max with Different Data Types
// ============================================================================
/**
 * Test min/max with real double arrays
 * Verifies aggregation works for real types
 */
double test_min_double(const Array_d& arr) {
    return min(arr);
}

// ============================================================================
// Test 41: Min/Max with Different Data Types (Max)
// ============================================================================
/**
 * Test max with real double arrays
 */
double test_max_double(const Array_d& arr) {
    return max(arr);
}

// ============================================================================
// Test 42: Product with Broadcasting
// ============================================================================
/**
 * Test prod aggregation on broadcasted array
 * Should handle zero-strides correctly
 */
double test_prod_broadcasted(const Array_d& arr) {
    return prod(arr);
}

// ============================================================================
// Test 43: Count with Complex Boolean Array
// ============================================================================
/**
 * Test counting true elements in boolean array
 * Created from comparison operations
 */
uint64_t test_count_comparison(const Array_c& a, const Array_c& b) {
    Array_b result = a > b;
    return count(result);
}

// ============================================================================
// Test 44: Chained Aggregations
// ============================================================================
/**
 * Test multiple aggregations in sequence
 * Verifies state consistency after operations
 */
double test_chained_aggregations(const Array_d& arr) {
    double sum_val = sum(arr);
    double min_val = min(arr);
    double max_val = max(arr);
    return sum_val + min_val + max_val;
}

// ============================================================================
// Test 45: Outer Product Shape Verification
// ============================================================================
/**
 * Test that outer product returns correct shape
 * Should be (n,) x (m,) → (n, m)
 */
std::vector<uint64_t> test_outer_product_shape(const Array_c& a, const Array_c& b) {
    Array_c result = outer_product(a, b);
    return result.dimensions_vector();
}

// ============================================================================
// Test 46: Lp Norm with p=1 (Should Match L1 Norm)
// ============================================================================
/**
 * Test that lpnorm(1) equals l1norm
 */
double test_lp_norm_p1(const Array_c& arr) {
    return lpnorm(arr, 1.0);
}

// ============================================================================
// Test 47: Lp Norm with p=2 (Should Match L2 Norm)
// ============================================================================
/**
 * Test that lpnorm(2) equals l2norm
 */
double test_lp_norm_p2(const Array_c& arr) {
    return lpnorm(arr, 2.0);
}

// ============================================================================
// Test 48: Lp Norm with Large Array
// ============================================================================
/**
 * Test lpnorm on large multi-dimensional arrays
 * Verifies numerical stability and optimization
 */
double test_lp_norm_large(const Array_d& arr, double p) {
    return lpnorm(arr, p);
}

// ============================================================================
// Test 49: Stdev with Complex Array
// ============================================================================
/**
 * Test standard deviation on complex array
 * Uses magnitude for complex values
 */
double test_stdev_complex(const Array_c& arr) {
    return stdev(arr);
}

// ============================================================================
// Test 50: FFT Forward Transform (1D)
// ============================================================================
/**
 * Test 1D FFT forward transform
 * Verifies PocketFFT integration
 */
Array_c test_fft1_forward(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 51: FFT Inverse Transform (1D)
// ============================================================================
/**
 * Test 1D FFT inverse transform
 * Verifies backward transform
 */
Array_c test_fft1_inverse(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::KspaceToImage, -1, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 52: FFT 2D Forward Transform
// ============================================================================
/**
 * Test 2D FFT forward transform
 * Verifies multi-dimensional FFT
 */
Array_c test_fft2_forward(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft2(input, output, Voxel::FFT::ImageToKspace, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 53: FFT 2D Inverse Transform
// ============================================================================
/**
 * Test 2D FFT inverse transform
 */
Array_c test_fft2_inverse(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft2(input, output, Voxel::FFT::KspaceToImage, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 54: FFT with Shift
// ============================================================================
/**
 * Test FFT with automatic fftshift
 * Verifies quadrant shifting
 */
Array_c test_fft1_with_shift(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, true, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 55: FFT Orthonormal Normalization
// ============================================================================
/**
 * Test FFT with orthonormal normalization
 * Both forward and inverse scale by 1/sqrt(N)
 */
Array_c test_fft1_ortho(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, false, Voxel::FFT::NORM_ORTHO);
    return output;
}

// ============================================================================
// Test 56: FFT Round-Trip (Forward + Inverse) - 1D
// ============================================================================
/**
 * Test FFT forward then inverse to verify Parseval's theorem
 * fft(ifft(x)) should equal x (within numerical precision)
 */
Array_c test_fft1_roundtrip(const Array_c& input) {
    Array_c temp = input.empty_like();
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, temp, Voxel::FFT::ImageToKspace, false, Voxel::FFT::NORM_BACKWARD);
    Voxel::FFT::fft1(temp, output, Voxel::FFT::KspaceToImage, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 57: FFT 3D Forward Transform
// ============================================================================
/**
 * Test 3D FFT forward transform
 * Verifies 3D multi-dimensional FFT support
 */
Array_c test_fft3_forward(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft3(input, output, Voxel::FFT::ImageToKspace, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 58: FFT 3D Inverse Transform
// ============================================================================
/**
 * Test 3D FFT inverse transform
 */
Array_c test_fft3_inverse(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft3(input, output, Voxel::FFT::KspaceToImage, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 59: FFT 1D with Shift (Frequency Domain Centering)
// ============================================================================
/**
 * Test 1D FFT with automatic fftshift (perform_shift=true)
 * Verifies DC component and low frequencies are centered
 */
Array_c test_fft1_forward_shifted(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, true, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 60: FFT 2D with Shift
// ============================================================================
/**
 * Test 2D FFT with automatic fftshift
 */
Array_c test_fft2_forward_shifted(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft2(input, output, Voxel::FFT::ImageToKspace, true, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 61: FFT 1D - NORM_NONE (No Normalization)
// ============================================================================
/**
 * Test FFT with no normalization
 * Standard numpy.fft default behavior
 */
Array_c test_fft1_norm_none(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, false, Voxel::FFT::NORM_NONE);
    return output;
}

// ============================================================================
// Test 62: IFFT 1D - NORM_NONE (No Normalization)
// ============================================================================
/**
 * Test inverse FFT with no normalization
 */
Array_c test_ifft1_norm_none(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::KspaceToImage, -1, false, Voxel::FFT::NORM_NONE);
    return output;
}

// ============================================================================
// Test 63: FFT 1D - NORM_ORTHO (Orthonormal)
// ============================================================================
/**
 * Test FFT with orthonormal normalization
 * Both forward and inverse scale by 1/sqrt(N)
 */
Array_c test_fft1_norm_ortho(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, false, Voxel::FFT::NORM_ORTHO);
    return output;
}

// ============================================================================
// Test 64: IFFT 1D - NORM_ORTHO (Orthonormal)
// ============================================================================
/**
 * Test inverse FFT with orthonormal normalization
 */
Array_c test_ifft1_norm_ortho(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::KspaceToImage, -1, false, Voxel::FFT::NORM_ORTHO);
    return output;
}

// ============================================================================
// Test 65: FFT on Impulse (Delta Function)
// ============================================================================
/**
 * FFT of impulse should give constant spectrum
 * input: [1, 0, 0, ..., 0] → FFT should give [1, 1, 1, ..., 1] (with backward norm)
 */
Array_c test_fft1_impulse(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 66: FFT on Constant (DC)
// ============================================================================
/**
 * FFT of constant should concentrate at DC component
 * input: [c, c, c, ..., c] → FFT[0] = N*c, rest ≈ 0
 */
Array_c test_fft1_constant(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 67: FFT on Sine Wave
// ============================================================================
/**
 * FFT of sine should show peaks at corresponding frequencies
 */
Array_c test_fft1_sine(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 68: FFT on Cosine Wave
// ============================================================================
/**
 * FFT of cosine should show peaks at corresponding frequencies
 */
Array_c test_fft1_cosine(const Array_c& input) {
    Array_c output = input.empty_like();
    Voxel::FFT::fft1(input, output, Voxel::FFT::ImageToKspace, -1, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 69: FFT 2D Round-Trip (Forward + Inverse)
// ============================================================================
/**
 * Test 2D FFT forward then inverse
 */
Array_c test_fft2_roundtrip(const Array_c& input) {
    Array_c temp = input.empty_like();
    Array_c output = input.empty_like();
    Voxel::FFT::fft2(input, temp, Voxel::FFT::ImageToKspace, false, Voxel::FFT::NORM_BACKWARD);
    Voxel::FFT::fft2(temp, output, Voxel::FFT::KspaceToImage, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}

// ============================================================================
// Test 70: FFT 3D Round-Trip (Forward + Inverse)
// ============================================================================
/**
 * Test 3D FFT forward then inverse
 */
Array_c test_fft3_roundtrip(const Array_c& input) {
    Array_c temp = input.empty_like();
    Array_c output = input.empty_like();
    Voxel::FFT::fft3(input, temp, Voxel::FFT::ImageToKspace, false, Voxel::FFT::NORM_BACKWARD);
    Voxel::FFT::fft3(temp, output, Voxel::FFT::KspaceToImage, false, Voxel::FFT::NORM_BACKWARD);
    return output;
}



// ============================================================================
// ============================================================================
// PYBIND11 Module Definition
// ============================================================================
PYBIND11_MODULE(test, m) {
    m.doc() = "Voxel Array Tests - Broadcasting, Aggregations, and Optimizations";

    // Broadcasting Tests (Original 15)
    m.def("test_broadcast_add", 
          &test_broadcast_add,
          "Add two arrays with automatic broadcasting.\n"
          "Example: (3,1,5) + (1,4,5) → (3,4,5)");

    m.def("test_broadcast_mul", 
          &test_broadcast_mul,
          "Multiply two arrays element-wise with broadcasting.\n"
          "Example: (5,1) * (1,3) → (5,3)");

    m.def("test_broadcast_sub", 
          &test_broadcast_sub,
          "Subtract arrays with broadcasting.\n"
          "Example: (4,3,1) - (1,1,2) → (4,3,2)");

    m.def("test_broadcast_div", 
          &test_broadcast_div,
          "Divide arrays element-wise with broadcasting.\n"
          "Example: (2,1,3) / (1,4,1) → (2,4,3)");

    m.def("test_broadcast_add_inplace", 
          &test_broadcast_add_inplace,
          "Add array B to A in-place with broadcasting.\n"
          "Modifies A to match broadcasted shape.");

    m.def("test_broadcast_mul_inplace", 
          &test_broadcast_mul_inplace,
          "Multiply A by B element-wise in-place with broadcasting.\n"
          "Modifies A to match broadcasted shape.");

    m.def("test_broadcast_eq", 
          &test_broadcast_eq,
          "Compare two arrays for equality with broadcasting.\n"
          "Returns Array<bool> with broadcasted shape.");

    m.def("test_broadcast_lt", 
          &test_broadcast_lt,
          "Compare two complex arrays by magnitude with broadcasting.\n"
          "For complex: |A| < |B|");

    m.def("test_broadcast_gt", 
          &test_broadcast_gt,
          "Compare two complex arrays by magnitude with broadcasting.\n"
          "For complex: |A| > |B|");

    m.def("test_is_broadcastable", 
          &test_is_broadcastable,
          "Check if array can broadcast to target shape without throwing.\n"
          "Returns True if broadcastable, False otherwise.");

    m.def("test_broadcast_chain", 
          &test_broadcast_chain,
          "Complex operation: (A * B) + C with multiple broadcasting steps.\n"
          "Demonstrates chaining multiple broadcasted operations.");

    m.def("test_broadcast_scalar_mul", 
          &test_broadcast_scalar_mul,
          "Multiply array by scalar (applies to all elements).\n"
          "Scalar broadcasting is automatic for any shape.");

    m.def("test_broadcast_scalar_lt", 
          &test_broadcast_scalar_lt,
          "Compare array elements against scalar threshold.\n"
          "Returns Array<bool> with same shape as input array.");

    m.def("test_get_broadcast_shape", 
          &test_get_broadcast_shape,
          "Compute output shape resulting from broadcasting two arrays.\n"
          "Returns vector<uint64_t> describing broadcasted dimensions.");

    m.def("test_broadcast_scalar_to_nd", 
          &test_broadcast_scalar_to_nd,
          "Broadcast a scalar array (0D or 1D) to target shape.\n"
          "Zero-copy operation using stride manipulation.");

    // Aggregation Tests (New: Tests 16-26)
    m.def("test_sum_array",
          &test_sum_array,
          "Sum all elements in array.\n"
          "Optimized with running pointer arithmetic.\n"
          "Handles contiguous, non-contiguous, and broadcasted arrays.");

    m.def("test_prod_array",
          &test_prod_array,
          "Product of all elements in array.\n"
          "Optimized with running pointer arithmetic.");

    m.def("test_count_true",
          &test_count_true,
          "Count true elements in boolean array.\n"
          "Returns uint64_t count.");

    m.def("test_min_array",
          &test_min_array,
          "Find minimum value in array.\n"
          "For complex: by magnitude.\n"
          "Optimized with running pointer arithmetic.");

    m.def("test_max_array",
          &test_max_array,
          "Find maximum value in array.\n"
          "For complex: by magnitude.\n"
          "Optimized with running pointer arithmetic.");

    m.def("test_stdev_array",
          &test_stdev_array,
          "Standard deviation of array elements.\n"
          "Optimized with running pointer arithmetic.");

    m.def("test_l1norm_array",
          &test_l1norm_array,
          "L1 norm: sum of absolute values.\n"
          "Optimized with running pointer arithmetic.");

    m.def("test_l2norm_array",
          &test_l2norm_array,
          "L2 norm (Euclidean): sqrt(sum(|x|^2)).\n"
          "Optimized with running pointer arithmetic.");

    m.def("test_linfnorm_array",
          &test_linfnorm_array,
          "L-infinity norm: max(|x|).\n"
          "Optimized with running pointer arithmetic.");

    m.def("test_lpnorm_array",
          &test_lpnorm_array,
          "Lp norm for arbitrary p: (sum(|x|^p))^(1/p).\n"
          "Optimized with running pointer arithmetic.",
          py::arg("arr"), py::arg("p"));

    // Dot Product and Outer Product (Tests 26-27)
    m.def("test_dot_complex",
          &test_dot_complex,
          "Complex dot product: sum(conj(a[i]) * b[i]).\n"
          "Optimized with dual offset running pointer arithmetic.");

    m.def("test_outer_product",
          &test_outer_product,
          "Outer product of two 1D vectors: (n,) x (m,) → (n,m).\n"
          "Optimized with direct stride-based indexing (zero heap allocations).");

    // In-Place Scalar Operations (Tests 28-31)
    m.def("test_inplace_add_scalar",
          &test_inplace_add_scalar,
          "In-place addition with scalar: a += scalar.\n"
          "Optimized with running pointer arithmetic.",
          py::arg("a"), py::arg("scalar"));

    m.def("test_inplace_sub_scalar",
          &test_inplace_sub_scalar,
          "In-place subtraction with scalar: a -= scalar.\n"
          "Optimized with running pointer arithmetic.",
          py::arg("a"), py::arg("scalar"));

    m.def("test_inplace_mul_scalar",
          &test_inplace_mul_scalar,
          "In-place multiplication with scalar: a *= scalar.\n"
          "Optimized with running pointer arithmetic.",
          py::arg("a"), py::arg("scalar"));

    m.def("test_inplace_div_scalar",
          &test_inplace_div_scalar,
          "In-place division with scalar: a /= scalar.\n"
          "Validated against zero before operation.",
          py::arg("a"), py::arg("scalar"));

    // In-Place Array Operations (Tests 35-36)
    m.def("test_inplace_sub_array",
          &test_inplace_sub_array,
          "In-place subtraction with broadcasting: a -= b.\n"
          "Optimized with dual running pointer arithmetic.");

    m.def("test_inplace_div_array",
          &test_inplace_div_array,
          "In-place division with broadcasting: a /= b.\n"
          "Zero-check and proper broadcasting.");

    // Advanced Tests (Tests 37-50)
    m.def("test_sum_strided",
          &test_sum_strided,
          "Sum of non-contiguous (strided) array.\n"
          "Verifies running pointer arithmetic handles strides.");

    m.def("test_l2norm_broadcasted",
          &test_l2norm_broadcasted,
          "L2 norm of broadcasted (zero-copy) array.\n"
          "Verifies zero-stride handling in aggregation.");

    m.def("test_dot_verification",
          &test_dot_verification,
          "Dot product with conjugate verification.\n"
          "Tests correctness of dual offset tracking.");

    m.def("test_min_double",
          &test_min_double,
          "Minimum of real double array.\n"
          "Tests aggregation with non-complex types.");

    m.def("test_max_double",
          &test_max_double,
          "Maximum of real double array.\n"
          "Tests aggregation with non-complex types.");

    m.def("test_prod_broadcasted",
          &test_prod_broadcasted,
          "Product of broadcasted array.\n"
          "Verifies zero-stride handling in multiplication.");

    m.def("test_count_comparison",
          &test_count_comparison,
          "Count true elements from comparison operation.\n"
          "Tests chaining comparison with count aggregation.");

    m.def("test_chained_aggregations",
          &test_chained_aggregations,
          "Multiple aggregations in sequence.\n"
          "Verifies state consistency after operations.");

    m.def("test_outer_product_shape",
          &test_outer_product_shape,
          "Verify outer product returns correct shape.\n"
          "Should be (n,) x (m,) → (n,m).");

    m.def("test_lp_norm_p1",
          &test_lp_norm_p1,
          "Lp norm with p=1 (should match L1 norm).\n"
          "Tests correctness of parametric norm function.");

    m.def("test_lp_norm_p2",
          &test_lp_norm_p2,
          "Lp norm with p=2 (should match L2 norm).\n"
          "Tests correctness of parametric norm function.");

    m.def("test_lp_norm_large",
          &test_lp_norm_large,
          "Lp norm on large multi-dimensional arrays.\n"
          "Verifies numerical stability and optimization.",
          py::arg("arr"), py::arg("p"));

    m.def("test_stdev_complex",
          &test_stdev_complex,
          "Standard deviation on complex array.\n"
          "Tests magnitude-based statistics for complex types.");

    // FFT Tests (Tests 50-55) - PocketFFT Integration
    m.def("test_fft1_forward",
          &test_fft1_forward,
          "1D FFT forward transform (ImageToKspace).\n"
          "Tests single-dimension FFT from PocketFFT backend.",
          py::arg("input"));

    m.def("test_fft1_inverse",
          &test_fft1_inverse,
          "1D FFT inverse transform (KspaceToImage).\n"
          "Tests inverse transform correctness.");

    m.def("test_fft2_forward",
          &test_fft2_forward,
          "2D FFT forward transform.\n"
          "Tests multi-dimensional FFT support.",
          py::arg("input"));

    m.def("test_fft2_inverse",
          &test_fft2_inverse,
          "2D FFT inverse transform.\n"
          "Tests 2D inverse transform.",
          py::arg("input"));

    m.def("test_fft1_with_shift",
          &test_fft1_with_shift,
          "1D FFT with automatic fftshift.\n"
          "Tests quadrant shifting in FFT output.",
          py::arg("input"));

    m.def("test_fft1_ortho",
          &test_fft1_ortho,
          "1D FFT with orthonormal normalization (NORM_ORTHO).\n"
          "Both forward and inverse scale by 1/sqrt(N).",
          py::arg("input"));

    // Extended FFT Tests (Tests 56-70) - Comprehensive PocketFFT Validation
    m.def("test_fft1_roundtrip",
          &test_fft1_roundtrip,
          "1D FFT round-trip test (forward + inverse).\n"
          "Verifies Parseval's theorem: fft(ifft(x)) ≈ x.",
          py::arg("input"));

    m.def("test_fft3_forward",
          &test_fft3_forward,
          "3D FFT forward transform.\n"
          "Tests 3D multi-dimensional FFT support.",
          py::arg("input"));

    m.def("test_fft3_inverse",
          &test_fft3_inverse,
          "3D FFT inverse transform.\n"
          "Tests 3D inverse transform.",
          py::arg("input"));

    m.def("test_fft1_forward_shifted",
          &test_fft1_forward_shifted,
          "1D FFT forward with fftshift (perform_shift=true).\n"
          "Tests frequency domain centering.",
          py::arg("input"));

    m.def("test_fft2_forward_shifted",
          &test_fft2_forward_shifted,
          "2D FFT forward with fftshift.\n"
          "Tests 2D frequency domain centering.",
          py::arg("input"));

    m.def("test_fft1_norm_none",
          &test_fft1_norm_none,
          "1D FFT with NORM_NONE (no normalization).\n"
          "Standard numpy.fft behavior without scaling.",
          py::arg("input"));

    m.def("test_ifft1_norm_none",
          &test_ifft1_norm_none,
          "1D inverse FFT with NORM_NONE.\n"
          "Standard numpy.ifft behavior without scaling.",
          py::arg("input"));

    m.def("test_fft1_norm_ortho",
          &test_fft1_norm_ortho,
          "1D FFT with NORM_ORTHO (orthonormal).\n"
          "Both forward and inverse scale by 1/sqrt(N).",
          py::arg("input"));

    m.def("test_ifft1_norm_ortho",
          &test_ifft1_norm_ortho,
          "1D inverse FFT with NORM_ORTHO.\n"
          "Orthonormal scaling for inverse transform.",
          py::arg("input"));

    m.def("test_fft1_impulse",
          &test_fft1_impulse,
          "FFT of impulse signal (delta function).\n"
          "Should give constant spectrum: [1, 1, 1, ...].",
          py::arg("input"));

    m.def("test_fft1_constant",
          &test_fft1_constant,
          "FFT of constant signal.\n"
          "Should concentrate at DC component.",
          py::arg("input"));

    m.def("test_fft1_sine",
          &test_fft1_sine,
          "FFT of sine wave.\n"
          "Should show peaks at corresponding frequencies.",
          py::arg("input"));

    m.def("test_fft1_cosine",
          &test_fft1_cosine,
          "FFT of cosine wave.\n"
          "Should show peaks at corresponding frequencies.",
          py::arg("input"));

    m.def("test_fft2_roundtrip",
          &test_fft2_roundtrip,
          "2D FFT round-trip test.\n"
          "Verifies Parseval's theorem in 2D.",
          py::arg("input"));

    m.def("test_fft3_roundtrip",
          &test_fft3_roundtrip,
          "3D FFT round-trip test.\n"
          "Verifies Parseval's theorem in 3D.",
          py::arg("input"));
}
