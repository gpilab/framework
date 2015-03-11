/*
 *   Copyright (C) 2014  Dignity Health
 *
 *   This program is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU Lesser General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU Lesser General Public License for more details.
 *
 *   You should have received a copy of the GNU Lesser General Public License
 *   along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *   NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
 *   AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
 *   SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
 *   PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
 *   USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
 *   LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
 *   MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
 *   SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.
 */

#ifndef _PYFIARRAY_WRAPPEDEIGEN_CPP_GUARD
#define _PYFIARRAY_WRAPPEDEIGEN_CPP_GUARD

#include <Eigen/Core>
#include <Eigen/Cholesky>
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
    int n_rows = dims[1];
    int n_cols = dims[0];
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
    Eigen::Map<mtype> B_(B.data(), m_, p);

    // m_ should == m

    // cout << "PyFIArray_WrappedEigen\t" << n << "\t" << p << endl;
    // Eigen::JacobiSVD<mtype> svd(A_, Eigen::ComputeThinU | Eigen::ComputeThinV);
    Eigen::HouseholderQR<mtype> qr(A_);
    // Eigen::LDLT<mtype> ldlt(A_);

    Eigen::Map<mtype> X_(X.data(), n, p);
    // X_ = svd.solve(B_);
    X_ = qr.solve(B_);
    // X_ = ldlt.solve(B_);
}

}// Eigen namespace 
}// PYFI namespace



#endif // GUARD
