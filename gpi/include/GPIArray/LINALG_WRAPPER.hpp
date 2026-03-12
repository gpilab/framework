/**
 * @file LINALG_WRAPPER.hpp
 * @brief Eigen-based Linear Algebra wrapper for GPIArray::Array.
 *
 * This header provides the GPIArray::LinAlg namespace, which implements efficient 
 * matrix operations (SVD, PCA, MatMul, Linear Solvers) by mapping GPIArray memory 
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

#ifndef GPIArray_LINALG_WRAPPER_HPP
#define GPIArray_LINALG_WRAPPER_HPP

#include "Array.hpp"
#include "ArrayMacros.hpp"

// Suppress Eigen warnings about infinity with ARM NEON optimizations
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wnan-infinity-disabled"
#include <Eigen/Dense>
#include <Eigen/SVD>
#include <Eigen/Cholesky>
#include <Eigen/QR>
#pragma clang diagnostic pop

#include <complex>
#include <type_traits>
#include <algorithm>

namespace GPIArray {
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

// Expose them directly to the FFTW namespace for clean syntax
constexpr SVDComputeType SingularValuesOnly = SVDComputeType::SingularValuesOnly;
constexpr SVDComputeType Thin = SVDComputeType::Thin;
constexpr SVDComputeType Full = SVDComputeType::Full;


// =====================================================================================
// Singular Value Decomposition (SVD)
// =====================================================================================

/**
 * @brief Computes the Singular Value Decomposition A = U * S * V^H.
 * * Maps raw GPIArray memory to Eigen matrices (Row-Major) and computes the SVD 
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
    if (!A.is_contiguous() || !U.is_contiguous() || !S.is_contiguous() || !Vh.is_contiguous()) {
        THROW_RUNTIME_ERROR("LinAlg::svd requires all input and output arrays to be contiguous in memory.");
    }

    uint64_t rows = A.dimensions(0);
    uint64_t cols = A.dimensions(1);
    uint64_t diag_size = std::min(rows, cols);

    if (S.size() != diag_size) {
        THROW_INVALID_ARGUMENT("SVD: Singular values array 'S' must have size min(rows, cols).");
    }

    int eigen_options = 0;
    if (compute_type == SVDComputeType::Thin) {
        if (U.dimensions(0) != rows || U.dimensions(1) != diag_size) 
            THROW_INVALID_ARGUMENT("SVD (Thin): 'U' array must be shaped (rows, min(rows, cols)).");
        if (Vh.dimensions(0) != diag_size || Vh.dimensions(1) != cols) 
            THROW_INVALID_ARGUMENT("SVD (Thin): 'Vh' array must be shaped (min(rows, cols), cols).");
        
        eigen_options = Eigen::ComputeThinU | Eigen::ComputeThinV;
    } 
    else if (compute_type == SVDComputeType::Full) {
        if (U.dimensions(0) != rows || U.dimensions(1) != rows) 
            THROW_INVALID_ARGUMENT("SVD (Full): 'U' array must be shaped (rows, rows).");
        if (Vh.dimensions(0) != cols || Vh.dimensions(1) != cols) 
            THROW_INVALID_ARGUMENT("SVD (Full): 'Vh' array must be shaped (cols, cols).");
        
        eigen_options = Eigen::ComputeFullU | Eigen::ComputeFullV;
    }

    // Define Eigen Mapping Types (forcing Row-Major)
    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using EigenVector = Eigen::Matrix<RealType_t<Scalar>, Eigen::Dynamic, 1>;
    using ConstEigenMap = Eigen::Map<const EigenMatrix>;
    using EigenMap = Eigen::Map<EigenMatrix>;
    using EigenVecMap = Eigen::Map<EigenVector>;

    ConstEigenMap matA(A.get_data(), rows, cols);
    Eigen::BDCSVD<EigenMatrix> svd_solver(matA, eigen_options);

    EigenVecMap mapS(S.get_data(), diag_size);
    mapS = svd_solver.singularValues();

    if (compute_type != SVDComputeType::SingularValuesOnly) {
        EigenMap mapU(U.get_data(), U.dimensions(0), U.dimensions(1));
        mapU = svd_solver.matrixU();

        EigenMap mapVh(Vh.get_data(), Vh.dimensions(0), Vh.dimensions(1));
        mapVh = svd_solver.matrixV().adjoint(); // Native adjoint for MRI math compatibility
    }
}

// =====================================================================================
// Principal Component Analysis (PCA)
// =====================================================================================

/**
 * @brief Computes PCA by mean-centering the data and computing the SVD.
 * Useful for Coil Compression and Temporal Subspace Estimation.
 * * @param data (Samples/Voxels) x (Features/Coils)
 * @param principal_components Output shape (min(Samples, Features), Features)
 * @param variances Output shape min(Samples, Features)
 */
template<typename Scalar>
void pca(const Array<Scalar>& data, 
         Array<Scalar>& principal_components, 
         Array<RealType_t<Scalar>>& variances) 
{
    if (data.ndim() != 2) THROW_INVALID_ARGUMENT("PCA requires 2D data (Samples x Features).");
    if (!data.is_contiguous() || !principal_components.is_contiguous() || !variances.is_contiguous()) {
        THROW_RUNTIME_ERROR("PCA requires all arrays to be contiguous in memory.");
    }

    uint64_t rows = data.dimensions(0); // Samples
    uint64_t cols = data.dimensions(1); // Features
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

    ConstEigenMap mapData(data.get_data(), rows, cols);
    
    // Mean-center the features (subtract mean from each column)
    EigenMatrix centered = mapData.rowwise() - mapData.colwise().mean();

    // Compute SVD on the centered data
    Eigen::BDCSVD<EigenMatrix> svd_solver(centered, Eigen::ComputeThinV);

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
    if (!A.is_contiguous() || !B.is_contiguous() || !C.is_contiguous()) {
        THROW_RUNTIME_ERROR("Matmul requires contiguous memory for all arrays.");
    }

    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using ConstMap = Eigen::Map<const EigenMatrix>;
    using Map = Eigen::Map<EigenMatrix>;

    ConstMap mapA(A.get_data(), A.dimensions(0), A.dimensions(1));
    ConstMap mapB(B.get_data(), B.dimensions(0), B.dimensions(1));
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
    
    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using ConstMap = Eigen::Map<const EigenMatrix>;
    using Map = Eigen::Map<EigenMatrix>;

    ConstMap mapA(A.get_data(), A.dimensions(0), A.dimensions(1));
    ConstMap mapB(b.get_data(), b.dimensions(0), b.dimensions(1));
    Map mapX(x.get_data(), x.dimensions(0), x.dimensions(1));

    mapX = mapA.llt().solve(mapB);
}

/**
 * @brief Solves Ax = b using Householder QR Decomposition.
 * Used for generic Non-Square Least Squares fitting. Slower than Cholesky but numerically stable.
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

    using EigenMatrix = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using ConstMap = Eigen::Map<const EigenMatrix>;
    using Map = Eigen::Map<EigenMatrix>;

    ConstMap mapA(A.get_data(), A.dimensions(0), A.dimensions(1));
    ConstMap mapB(b.get_data(), b.dimensions(0), b.dimensions(1));
    Map mapX(x.get_data(), x.dimensions(0), x.dimensions(1));

    mapX = mapA.householderQr().solve(mapB);
}

} // namespace LinAlg
} // namespace GPIArray

#endif // GPIArray_LINALG_WRAPPER_HPP