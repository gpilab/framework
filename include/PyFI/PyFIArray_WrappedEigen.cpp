#ifndef _PYFIARRAY_WRAPPEDEIGEN_CPP_GUARD
#define _PYFIARRAY_WRAPPEDEIGEN_CPP_GUARD

#include <Eigen/Core>
#include <Eigen/LU>

namespace PyFI
{
namespace EigenWrapper
{

template<class T>
void PseudoInverse(Array<T> &A)
{
    std::vector<uint64_t> dims = A.dimensions_vector();
    int n_rows = dims[0];
    int n_cols = dims[1];
    Eigen::Map<Eigen::Matrix<T, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> > A_(A.data(), n_rows, n_cols);
    cout << A_ << endl;
}

}// Eigen namespace 
}// PYFI namespace



#endif // GUARD
