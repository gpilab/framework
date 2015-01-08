#ifndef _PYFIARRAY_WRAPPEDEIGEN_CPP_GUARD
#define _PYFIARRAY_WRAPPEDEIGEN_CPP_GUARD

#include <Eigen/Core>
#include <Eigen/LU>
#include <Eigen/Dense>

namespace PyFI
{
namespace EigenWrapper
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
    int n_rows = dims[0];
    int n_cols = dims[1];
    Eigen::Map<mtype> Matrix_(Matrix.data(), n_rows, n_cols);
    Eigen::JacobiSVD<mtype> svd(Matrix_, Eigen::ComputeThinU | Eigen::ComputeThinV);
    mtype MatrixInverse_ = svd.solve(mtype::Identity(n_rows,n_rows));
    // cout << MatrixInverse_ << endl;
}

}// Eigen namespace 
}// PYFI namespace



#endif // GUARD
