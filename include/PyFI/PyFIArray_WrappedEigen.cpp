#ifndef _PYFIARRAY_WRAPPEDEIGEN_CPP_GUARD
#define _PYFIARRAY_WRAPPEDEIGEN_CPP_GUARD

#include <Eigen/Core>
#include <Eigen/QR>
#include <Eigen/Dense>

namespace PyFI
{
namespace PyFEigen
{

/*
 * PrintArrayAsEigenMat(Array<T> &A)
 *
 * Wraps a PyFI array in an Eigen Matrix and prints the contents. This is a
 * useful test for the Eigen wrapping method.
 *
 */
template<class T>
void PrintArrayAsEigenMat(Array<T> &A)
{
    std::vector<uint64_t> dims = A.dimensions_vector();
    int n_rows = dims[0];
    int n_cols = dims[1];
    Eigen::Map<Eigen::Matrix<T, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> > A_(A.data(), n_rows, n_cols);
    cout << A_ << endl;
}

template<class T>
void PseudoInverse(Array<T> &Matrix, Array<T> &InverseMatrix)
{
    typedef Eigen::Matrix<T, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> mtype;
    std::vector<uint64_t> dims = Matrix.dimensions_vector();
    int n_rows = dims[1];
    int n_cols = dims[0];
    Eigen::Map<mtype> Matrix_(Matrix.data(), n_rows, n_cols);
    // Eigen::JacobiSVD<mtype> svd(Matrix_, Eigen::ComputeThinU | Eigen::ComputeThinV);
    Eigen::HouseholderQR<mtype> qr(Matrix_);

    Eigen::Map<mtype> InverseMatrix_(InverseMatrix.data(), n_cols, n_rows);
    // InverseMatrix_ = svd.solve(mtype::Identity(n_rows,n_rows));
    InverseMatrix_ = qr.solve(mtype::Identity(n_rows,n_rows));
    // cout << MatrixInverse_ << endl;
}

template<class T>
void MLDivide(Array<T> &A, Array<T> &B, Array<T> &X)
{
    typedef Eigen::Matrix<T, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> mtype;

    std::vector<uint64_t> dims = A.dimensions_vector();
    int m = dims[1];
    int n = dims[0];
    Eigen::Map<mtype> A_(A.data(), m, n);

    dims = B.dimensions_vector();
    int m_ = dims[1];
    int p = dims[0];
    Eigen::Map<mtype> B_(B.data(), m, p);

    cout << n << "\t" << p << endl;
    Eigen::JacobiSVD<mtype> svd(A_, Eigen::ComputeThinU | Eigen::ComputeThinV);
    // Eigen::HouseholderQR<mtype> qr(A_);

    Eigen::Map<mtype> X_(X.data(), n, p);
    X_ = svd.solve(B_);
    // X_ = qr.solve(B_);
    // cout << MatrixInverse_ << endl;
}

}// Eigen namespace 
}// PYFI namespace



#endif // GUARD
