/**
 * @file LINALG_WRAPPER.hpp
 * @brief Eigen-based Linear Algebra wrapper for Voxel::Array.
 *
 * This header provides the Voxel::LinAlg namespace, which implements efficient 
 * matrix operations (SVD, PCA, MatMul, Linear Solvers) by mapping Voxel memory 
 * directly into Eigen matrices. This ensures zero-copy overhead and maximizes 
 * cache locality.
 *
 * Features:
 * - Strongly-typed SVD computation flags (Thin vs Full)
 * - Zero-copy memory mapping via Eigen::Map with strict Row-Major alignment
 * - Principal Component Analysis (PCA) for Coil/Subspace Compression
 * - General Matrix Multiplication (GEMM)
 * - Direct Linear System Solvers (Cholesky for SPD matrices, QR for Least Squares)
 * - Strict bounds and contiguity checking to prevent silent memory corruption
 *
 * @author Guru Krishnamoorthy
 * @date 2026 March
 */

#pragma once

#include "Array.hpp"
#include "ArrayMacros.hpp"

#include <Eigen/Dense>
#include <Eigen/SVD>
#include <Eigen/Cholesky>
#include <Eigen/QR>
#ifdef __clang__
#pragma clang diagnostic pop
#endif

#include <complex>
#include <type_traits>
#include <algorithm>
#include <limits>
#include <tuple>

namespace Voxel {
namespace LinAlg {

// --- Type Traits ---
// Extracts the real precision type from complex types (used for singular values/variances)
template<typename T>
struct RealType { using type = T; };

template<typename T>
struct RealType<std::complex<T>> { using type = T; };

template<typename T>
using RealType_t = typename RealType<T>::type;

// Strongly-typed flags for SVD computation sizes
enum class SVDComputeType {
    SingularValuesOnly,
    Thin,   // Computes min(M,N) vectors
    Full    // Computes full M_x_M and N_x_N unitary matrices
};

// Expose them directly to the namespace for clean syntax
constexpr SVDComputeType SingularValuesOnly = SVDComputeType::SingularValuesOnly;
constexpr SVDComputeType Thin = SVDComputeType::Thin;
constexpr SVDComputeType Full = SVDComputeType::Full;


// =====================================================================================
// Singular Value Decomposition (SVD)
// =====================================================================================

/**
 * @brief Computes the Singular Value Decomposition A = U * S * V^H.
 * Maps raw Voxel memory to Eigen matrices (Row-Major) and computes the SVD 
 * using the highly optimized Divide-and-Conquer algorithm (BDCSVD). 
 * All output arrays must be pre-allocated and perfectly sized.
 */
template<typename Scalar>
void svd(const Array<Scalar>& A, 
         Array<Scalar>& U, 
         Array<RealType_t<Scalar>>& S, 
         Array<Scalar>& Vh, 
         SVDComputeType compute_type = SVDComputeType::Thin) 
{
    if (A.ndim() != 2) THROW_INVALID_ARGUMENT("SVD requires a 2D input array.");
    
    // CRITICAL FIX: Check for BLAS 32-bit integer overflow before proceeding
    uint64_t rows = A.dimensions(0);
    uint64_t cols = A.dimensions(1);
    if (rows > static_cast<uint64_t>(std::numeric_limits<int>::max()) ||
        cols > static_cast<uint64_t>(std::numeric_limits<int>::max())) {
        THROW_RUNTIME_ERROR("SVD: Array dimensions exceed 32-bit integer limit for standard BLAS. "
                           "Maximum dimension size: " + std::to_string(std::numeric_limits<int>::max()));
    }
    
    // Ensure input is contiguous (copy only if necessary)
    auto contiguous_A = A.contiguous();
    // Note: U, S, Vh are outputs and modified in-place, so they must already be contiguous
    if (!U.is_contiguous() || !S.is_contiguous() || !Vh.is_contiguous()) {
        THROW_RUNTIME_ERROR("LinAlg::svd output arrays (U, S, Vh) must be contiguous in memory.");
    }

    uint64_t diag_size = std::min(rows, cols);

    if (S.size() != diag_size) {
        THROW_INVALID_ARGUMENT("SVD: Singular values array 'S' must have size min(rows, cols).");
    }

    // Define Eigen Mapping Types (forcing Row-Major)
    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using EigenVector = Eigen::Matrix<RealType_t<Scalar>, Eigen::Dynamic, 1>;
    using ConstEigenMap = Eigen::Map<const EigenMatrix>;
    using EigenMap = Eigen::Map<EigenMatrix>;
    using EigenVecMap = Eigen::Map<EigenVector>;

    ConstEigenMap matA(contiguous_A.get_data(), rows, cols);
    EigenVecMap mapS(S.get_data(), diag_size);

    // Branch execution based on template types to satisfy modern Eigen compile-time requirements
    if (compute_type == SVDComputeType::Thin) {
        if (U.dimensions(0) != rows || U.dimensions(1) != diag_size) 
            THROW_INVALID_ARGUMENT("SVD (Thin): 'U' array must be shaped (rows, min(rows, cols)).");
        if (Vh.dimensions(0) != diag_size || Vh.dimensions(1) != cols) 
            THROW_INVALID_ARGUMENT("SVD (Thin): 'Vh' array must be shaped (min(rows, cols), cols).");

        Eigen::BDCSVD<EigenMatrix, Eigen::ComputeThinU | Eigen::ComputeThinV> svd_solver(matA);
        
        if (svd_solver.info() != Eigen::Success) THROW_RUNTIME_ERROR("SVD computation failed: BDCSVD did not converge.");
        
        mapS = svd_solver.singularValues();
        
        EigenMap mapU(U.get_data(), U.dimensions(0), U.dimensions(1));
        mapU = svd_solver.matrixU();

        EigenMap mapVh(Vh.get_data(), Vh.dimensions(0), Vh.dimensions(1));
        mapVh = svd_solver.matrixV().adjoint(); // Native adjoint for MRI math compatibility

    } 
    else if (compute_type == SVDComputeType::Full) {
        if (U.dimensions(0) != rows || U.dimensions(1) != rows) 
            THROW_INVALID_ARGUMENT("SVD (Full): 'U' array must be shaped (rows, rows).");
        if (Vh.dimensions(0) != cols || Vh.dimensions(1) != cols) 
            THROW_INVALID_ARGUMENT("SVD (Full): 'Vh' array must be shaped (cols, cols).");
        
        Eigen::BDCSVD<EigenMatrix, Eigen::ComputeFullU | Eigen::ComputeFullV> svd_solver(matA);
        
        if (svd_solver.info() != Eigen::Success) THROW_RUNTIME_ERROR("SVD computation failed: BDCSVD did not converge.");

        mapS = svd_solver.singularValues();
        
        EigenMap mapU(U.get_data(), U.dimensions(0), U.dimensions(1));
        mapU = svd_solver.matrixU();

        EigenMap mapVh(Vh.get_data(), Vh.dimensions(0), Vh.dimensions(1));
        mapVh = svd_solver.matrixV().adjoint();

    } 
    else { // SingularValuesOnly
        Eigen::BDCSVD<EigenMatrix> svd_solver(matA);
        
        if (svd_solver.info() != Eigen::Success) THROW_RUNTIME_ERROR("SVD computation failed: BDCSVD did not converge.");
        
        mapS = svd_solver.singularValues();
    }
}

// =====================================================================================
// Principal Component Analysis (PCA)
// =====================================================================================

/**
 * @brief Computes PCA by mean-centering the data and computing the SVD.
 * Useful for Coil Compression and Temporal Subspace Estimation.
 * @param data (Samples/Voxels) x (Features/Coils)
 * @param principal_components Output shape (min(Samples, Features), Features)
 * @param variances Output shape min(Samples, Features)
 */
template<typename Scalar>
void pca(const Array<Scalar>& data, 
         Array<Scalar>& principal_components, 
         Array<RealType_t<Scalar>>& variances) 
{
    if (data.ndim() != 2) THROW_INVALID_ARGUMENT("PCA requires 2D data (Samples x Features).");
    
    // CRITICAL FIX: Check for BLAS 32-bit integer overflow before proceeding
    uint64_t rows = data.dimensions(0);
    uint64_t cols = data.dimensions(1);
    if (rows > static_cast<uint64_t>(std::numeric_limits<int>::max()) ||
        cols > static_cast<uint64_t>(std::numeric_limits<int>::max())) {
        THROW_RUNTIME_ERROR("PCA: Array dimensions exceed 32-bit integer limit for standard BLAS. "
                           "Maximum dimension size: " + std::to_string(std::numeric_limits<int>::max()));
    }
    
    // Ensure input is contiguous (copy only if necessary)
    auto contiguous_data = data.contiguous();
    // Note: principal_components and variances are outputs, so they must already be contiguous
    if (!principal_components.is_contiguous() || !variances.is_contiguous()) {
        THROW_RUNTIME_ERROR("PCA output arrays (principal_components, variances) must be contiguous in memory.");
    }

    uint64_t diag_size = std::min(rows, cols);

    if (variances.size() != diag_size) 
        THROW_INVALID_ARGUMENT("PCA: Variances array must have size min(Samples, Features).");
    if (principal_components.dimensions(0) != diag_size || principal_components.dimensions(1) != cols) 
        THROW_INVALID_ARGUMENT("PCA: Principal components array must be shaped (min(Samples, Features), Features).");

    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using EigenVector = Eigen::Matrix<RealType_t<Scalar>, Eigen::Dynamic, 1>;
    using ConstEigenMap = Eigen::Map<const EigenMatrix>;
    using EigenMap = Eigen::Map<EigenMatrix>;
    using EigenVecMap = Eigen::Map<EigenVector>;

    ConstEigenMap mapData(contiguous_data.get_data(), rows, cols);
    
    // Mean-center the features (subtract mean from each column)
    EigenMatrix centered = mapData.rowwise() - mapData.colwise().mean();

    // Compute SVD on the centered data using compile-time template parameter
    Eigen::BDCSVD<EigenMatrix, Eigen::ComputeThinV> svd_solver(centered);

    if (svd_solver.info() != Eigen::Success) {
        THROW_RUNTIME_ERROR("PCA computation failed: SVD did not converge.");
    }

    // Compute variances: singular_values^2 / (N - 1)
    EigenVecMap mapVar(variances.get_data(), diag_size);
    RealType_t<Scalar> n_minus_1 = static_cast<RealType_t<Scalar>>(rows > 1 ? rows - 1 : 1);
    mapVar = svd_solver.singularValues().array().square() / n_minus_1;

    EigenMap mapPC(principal_components.get_data(), diag_size, cols);
    mapPC = svd_solver.matrixV().adjoint(); 
}


// =====================================================================================
// General Matrix Multiplication (GEMM)
// =====================================================================================

/**
 * @brief Zero-allocation Matrix Multiplication: C = A * B.
 * Applies .noalias() to ensure Eigen writes directly to C without temporary buffers.
 */
template<typename Scalar>
void matmul(const Array<Scalar>& A, const Array<Scalar>& B, Array<Scalar>& C) {
    if (A.ndim() != 2 || B.ndim() != 2 || C.ndim() != 2) {
        THROW_INVALID_ARGUMENT("Matmul requires 2D input arrays.");
    }
    if (A.dimensions(1) != B.dimensions(0)) {
        THROW_INVALID_ARGUMENT("Matmul dimension mismatch: A cols must equal B rows.");
    }
    if (C.dimensions(0) != A.dimensions(0) || C.dimensions(1) != B.dimensions(1)) {
        THROW_INVALID_ARGUMENT("Matmul: Output array C is incorrectly shaped.");
    }
    
    // CRITICAL FIX: Check for BLAS 32-bit integer overflow before proceeding
    uint64_t m = A.dimensions(0);
    uint64_t n = B.dimensions(1);
    uint64_t k = A.dimensions(1);
    if (m > static_cast<uint64_t>(std::numeric_limits<int>::max()) ||
        n > static_cast<uint64_t>(std::numeric_limits<int>::max()) ||
        k > static_cast<uint64_t>(std::numeric_limits<int>::max())) {
        THROW_RUNTIME_ERROR("Matmul: Array dimensions exceed 32-bit integer limit for standard BLAS. "
                           "Maximum dimension size: " + std::to_string(std::numeric_limits<int>::max()));
    }
    
    // Ensure inputs are contiguous (copy only if necessary)
    auto contiguous_A = A.contiguous();
    auto contiguous_B = B.contiguous();
    // Note: C is output and modified in-place, so it must already be contiguous
    if (!C.is_contiguous()) {
        THROW_RUNTIME_ERROR("Matmul output array C must be contiguous in memory.");
    }

    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using ConstMap = Eigen::Map<const EigenMatrix>;
    using Map = Eigen::Map<EigenMatrix>;

    ConstMap mapA(contiguous_A.get_data(), contiguous_A.dimensions(0), contiguous_A.dimensions(1));
    ConstMap mapB(contiguous_B.get_data(), contiguous_B.dimensions(0), contiguous_B.dimensions(1));
    Map mapC(C.get_data(), C.dimensions(0), C.dimensions(1));

    // Zero-allocation direct write
    mapC.noalias() = mapA * mapB; 
}


// =====================================================================================
// Linear System Solvers (Ax = b)
// =====================================================================================

/**
 * @brief Solves Ax = b using Cholesky Decomposition (LLT).
 * WARNING: Matrix A MUST be Square, Symmetric/Hermitian, and Positive-Definite (e.g. A^H A).
 * @throws Throws if A is not positive-definite or arrays are not contiguous.
 */
template<typename Scalar>
void solve_cholesky(const Array<Scalar>& A, const Array<Scalar>& b, Array<Scalar>& x) {
    if (A.ndim() != 2 || A.dimensions(0) != A.dimensions(1)) {
        THROW_INVALID_ARGUMENT("Cholesky solver requires a square matrix A.");
    }
    if (A.dimensions(1) != b.dimensions(0)) {
        THROW_INVALID_ARGUMENT("Solver dimension mismatch between A and b.");
    }
    if (x.dimensions(0) != A.dimensions(1) || x.dimensions(1) != b.dimensions(1)) {
        THROW_INVALID_ARGUMENT("Solver: Output array x is incorrectly shaped.");
    }
    
    // Ensure inputs are contiguous (copy only if necessary)
    auto contiguous_A = A.contiguous();
    auto contiguous_b = b.contiguous();
    // Note: x is output and modified in-place, so it must already be contiguous
    if (!x.is_contiguous()) {
        THROW_RUNTIME_ERROR("Cholesky solver output array x must be contiguous in memory.");
    }
    
    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using ConstMap = Eigen::Map<const EigenMatrix>;
    using Map = Eigen::Map<EigenMatrix>;

    ConstMap mapA(contiguous_A.get_data(), contiguous_A.dimensions(0), contiguous_A.dimensions(1));
    ConstMap mapB(contiguous_b.get_data(), contiguous_b.dimensions(0), contiguous_b.dimensions(1));
    Map mapX(x.get_data(), x.dimensions(0), x.dimensions(1));

    auto llt = mapA.llt();
    if (llt.info() != Eigen::Success) {
        THROW_RUNTIME_ERROR("Cholesky decomposition failed: Matrix A is not positive-definite. "
                           "Ensure A is symmetric/hermitian with all positive eigenvalues.");
    }
    mapX = llt.solve(mapB);
}

/**
 * @brief Solves Ax = b using Householder QR Decomposition.
 * Used for generic Non-Square Least Squares fitting. Slower than Cholesky but numerically stable.
 * @throws Throws if arrays not contiguous or system is rank-deficient.
 */
template<typename Scalar>
void solve_qr(const Array<Scalar>& A, const Array<Scalar>& b, Array<Scalar>& x) {
    if (A.ndim() != 2 || b.ndim() != 2 || x.ndim() != 2) {
        THROW_INVALID_ARGUMENT("QR solver requires 2D arrays.");
    }
    if (A.dimensions(0) != b.dimensions(0)) {
        THROW_INVALID_ARGUMENT("QR Solver: A rows must equal b rows.");
    }
    if (x.dimensions(0) != A.dimensions(1) || x.dimensions(1) != b.dimensions(1)) {
        THROW_INVALID_ARGUMENT("QR Solver: Output array x is incorrectly shaped.");
    }
    
    // Ensure inputs are contiguous (copy only if necessary)
    auto contiguous_A = A.contiguous();
    auto contiguous_b = b.contiguous();
    // Note: x is output and modified in-place, so it must already be contiguous
    if (!x.is_contiguous()) {
        THROW_RUNTIME_ERROR("QR solver output array x must be contiguous in memory.");
    }

    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using ConstMap = Eigen::Map<const EigenMatrix>;
    using Map = Eigen::Map<EigenMatrix>;
    using RealScalar = RealType_t<Scalar>;

    ConstMap mapA(contiguous_A.get_data(), contiguous_A.dimensions(0), contiguous_A.dimensions(1));
    ConstMap mapB(contiguous_b.get_data(), contiguous_b.dimensions(0), contiguous_b.dimensions(1));
    Map mapX(x.get_data(), x.dimensions(0), x.dimensions(1));

    auto qr = mapA.householderQr();
    // Check effective rank via diagonal elements of upper triangular matrix
    RealScalar max_diag = qr.matrixQR().topRows(contiguous_A.dimensions(1)).array().diagonal().abs().maxCoeff();
    RealScalar min_diag = qr.matrixQR().topRows(contiguous_A.dimensions(1)).array().diagonal().abs().minCoeff();
    RealScalar rank_tol = 1e-9 * max_diag * std::max(contiguous_A.dimensions(0), contiguous_A.dimensions(1));
    if (!qr.isInvertible() || min_diag < rank_tol) {
        THROW_RUNTIME_ERROR("QR solver: Matrix A is rank-deficient. The system may have infinite or no solutions.");
    }
    mapX = qr.solve(mapB);
}

// =====================================================================================
// Matrix Adjoint (Conjugate Transpose / Hermitian Transpose)
// =====================================================================================

/**
 * @brief Computes the Hermitian (Conjugate Transpose) of a matrix: A_hermitian = A^H.
 * For real matrices, this is simply the transpose.
 * For complex matrices, this computes the conjugate transpose.
 * * @param A Input matrix (rows x cols)
 * @param A_hermitian Output matrix (cols x rows), must be pre-allocated
 */
template<typename Scalar>
void hermitian(const Array<Scalar>& A, Array<Scalar>& A_hermitian) {

    if (A.ndim() != 2) {
        THROW_INVALID_ARGUMENT("Hermitian operation requires a 2D input array.");
    }
    if (A_hermitian.ndim() != 2) {
        THROW_INVALID_ARGUMENT("Hermitian operation requires a 2D output array.");
    }
    if (A_hermitian.dimensions(0) != A.dimensions(1) || A_hermitian.dimensions(1) != A.dimensions(0)) {
        THROW_INVALID_ARGUMENT("Hermitian: Output array must be transposed shape (cols x rows).");
    }

    // Ensure input is contiguous (copy only if necessary)
    auto contiguous_A = A.contiguous();
    // Note: A_hermitian is output and modified in-place, so it must already be contiguous
    if (!A_hermitian.is_contiguous()) {
        THROW_RUNTIME_ERROR("Hermitian output array must be contiguous in memory.");
    }

    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using ConstMap = Eigen::Map<const EigenMatrix>;
    using Map = Eigen::Map<EigenMatrix>;

    uint64_t rows = contiguous_A.dimensions(0);
    uint64_t cols = contiguous_A.dimensions(1);

    ConstMap mapA(contiguous_A.get_data(), rows, cols);
    Map mapH(A_hermitian.get_data(), cols, rows);

    // Compute conjugate transpose (adjoint)
    mapH = mapA.adjoint();
}

// =====================================================================================
// OVERLOADS WITH AUTOMATIC OUTPUT ALLOCATION
// =====================================================================================

/**
 * @brief SVD with automatic output allocation - returns tuple (U, S, Vh).
 */
template<typename Scalar>
std::tuple<Array<Scalar>, Array<RealType_t<Scalar>>, Array<Scalar>> svd(const Array<Scalar>& A, SVDComputeType compute_type = SVDComputeType::Thin) {
    if (A.ndim() != 2) THROW_INVALID_ARGUMENT("SVD requires a 2D input array.");
    
    uint64_t rows = A.dimensions(0);
    uint64_t cols = A.dimensions(1);
    uint64_t diag_size = std::min(rows, cols);

    Array<Scalar> U;
    Array<RealType_t<Scalar>> S(std::vector<uint64_t>{diag_size});
    Array<Scalar> Vh;

    if (compute_type == SVDComputeType::Thin) {
        U = Array<Scalar>(std::vector<uint64_t>{rows, diag_size});
        Vh = Array<Scalar>(std::vector<uint64_t>{diag_size, cols});
    } 
    else if (compute_type == SVDComputeType::Full) {
        U = Array<Scalar>(std::vector<uint64_t>{rows, rows});
        Vh = Array<Scalar>(std::vector<uint64_t>{cols, cols});
    }
    else { // SingularValuesOnly
        U = Array<Scalar>(std::vector<uint64_t>{0});
        Vh = Array<Scalar>(std::vector<uint64_t>{0});
    }

    // Call the existing implementation
    svd(A, U, S, Vh, compute_type);
    return std::tuple<Array<Scalar>, Array<RealType_t<Scalar>>, Array<Scalar>>(U, S, Vh);
}

/**
 * @brief PCA with automatic output allocation - returns tuple (principal_components, variances).
 */
template<typename Scalar>
std::tuple<Array<Scalar>, Array<RealType_t<Scalar>>> pca(const Array<Scalar>& data) {
    if (data.ndim() != 2) THROW_INVALID_ARGUMENT("PCA requires 2D data (Samples x Features).");
    
    uint64_t rows = data.dimensions(0); // Samples
    uint64_t cols = data.dimensions(1); // Features
    uint64_t diag_size = std::min(rows, cols);

    Array<RealType_t<Scalar>> variances(std::vector<uint64_t>{diag_size});
    Array<Scalar> principal_components(std::vector<uint64_t>{diag_size, cols});

    // Call the existing implementation
    pca(data, principal_components, variances);
    return std::tuple<Array<Scalar>, Array<RealType_t<Scalar>>>(principal_components, variances);
}

/**
 * @brief Matrix Multiplication with automatic output allocation - returns C = A * B.
 */
template<typename Scalar>
Array<Scalar> matmul(const Array<Scalar>& A, const Array<Scalar>& B) {
    if (A.ndim() != 2 || B.ndim() != 2) {
        THROW_INVALID_ARGUMENT("Matmul requires 2D input arrays.");
    }
    if (A.dimensions(1) != B.dimensions(0)) {
        THROW_INVALID_ARGUMENT("Matmul dimension mismatch: A cols must equal B rows.");
    }

    Array<Scalar> C(std::vector<uint64_t>{A.dimensions(0), B.dimensions(1)});
    matmul(A, B, C);
    return C;
}

/**
 * @brief Cholesky Solver with automatic output allocation - returns x solving Ax = b.
 */
template<typename Scalar>
Array<Scalar> solve_cholesky(const Array<Scalar>& A, const Array<Scalar>& b) {
    if (A.ndim() != 2 || A.dimensions(0) != A.dimensions(1)) {
        THROW_INVALID_ARGUMENT("Cholesky solver requires a square matrix A.");
    }
    if (A.dimensions(1) != b.dimensions(0)) {
        THROW_INVALID_ARGUMENT("Solver dimension mismatch between A and b.");
    }

    Array<Scalar> x(std::vector<uint64_t>{A.dimensions(1), b.dimensions(1)});
    solve_cholesky(A, b, x);
    return x;
}

/**
 * @brief QR Solver with automatic output allocation - returns x solving Ax = b.
 */
template<typename Scalar>
Array<Scalar> solve_qr(const Array<Scalar>& A, const Array<Scalar>& b) {
    if (A.ndim() != 2 || b.ndim() != 2) {
        THROW_INVALID_ARGUMENT("QR solver requires 2D arrays.");
    }
    if (A.dimensions(0) != b.dimensions(0)) {
        THROW_INVALID_ARGUMENT("QR Solver: A rows must equal b rows.");
    }

    Array<Scalar> x(std::vector<uint64_t>{A.dimensions(1), b.dimensions(1)});
    solve_qr(A, b, x);
    return x;
}

/**
 * @brief Hermitian (Conjugate Transpose) with automatic output allocation - returns A^H.
 */
template<typename Scalar>
Array<Scalar> hermitian(const Array<Scalar>& A) {
    if (A.ndim() != 2) {
        THROW_INVALID_ARGUMENT("Hermitian operation requires a 2D input array.");
    }

    Array<Scalar> A_hermitian(std::vector<uint64_t>{A.dimensions(1), A.dimensions(0)});
    hermitian(A, A_hermitian);
    return A_hermitian;
}

} // namespace LinAlg
} // namespace Voxel