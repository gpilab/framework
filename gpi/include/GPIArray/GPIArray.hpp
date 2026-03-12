/**
 * @file GPIArray.hpp
 * @brief Pybind11 integration for GPIArray::Array<T> with zero-copy NumPy interoperability.
 *
 * This header provides pybind11 type casters and Python bindings for the GPIArray::Array<T> template,
 * enabling seamless conversion between C++ multi-dimensional arrays and NumPy ndarrays.
 *
 * Features:
 *   - Automatic dtype mapping between C++ types and NumPy types (float, double, int, complex, etc.)
 *   - Zero-copy views: Python and C++ share memory, with correct lifetime management via shared_ptr and capsules
 *   - Column-major (Fortran-style) and row-major (C-style) layout translation between C++ and Python
 *   - Full support for advanced slicing, indexing, and assignment from Python
 *   - Exposure of FFTW-based functions for fast Fourier transforms on arrays
 *   - Math operations (e.g., L2 norm) exposed to Python for supported types
 *   - Exception translation for robust error handling between C++ and Python
 *
 * The bindings are designed for scientific computing, providing high-performance interoperability
 * between C++ and Python, similar to NumPy's ndarray, but with additional features and memory control.
 *
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#ifndef GPIARRAY_HPP_INCLUDED
#define GPIARRAY_HPP_INCLUDED

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/complex.h> // Required for complex number support

#include "Array.hpp"
#include "FFTW_WRAPPER.hpp"
#include "NumpyReadWrite.hpp"
#include "Wavelet.hpp"
#include "LINALG_WRAPPER.hpp"


namespace py = pybind11;

// --- Helper to get NumPy dtype for a given C++ type ---
// Moved into an anonymous namespace to prevent redefinition across translation units
namespace gpi_array_detail {
template<typename T>
inline py::dtype get_numpy_dtype();

template<> inline py::dtype get_numpy_dtype<float>() { return py::dtype::of<float>(); }
template<> inline py::dtype get_numpy_dtype<double>() { return py::dtype::of<double>(); }
template<> inline py::dtype get_numpy_dtype<int>() { return py::dtype::of<int>(); }
template<> inline py::dtype get_numpy_dtype<int8_t>() { return py::dtype::of<int8_t>(); }
template<> inline py::dtype get_numpy_dtype<bool>() { return py::dtype::of<bool>(); }
template<> inline py::dtype get_numpy_dtype<long>() { return py::dtype::of<long>(); }
template<> inline py::dtype get_numpy_dtype<unsigned int>() { return py::dtype::of<unsigned int>(); }
template<> inline py::dtype get_numpy_dtype<unsigned long>() { return py::dtype::of<unsigned long>(); }
template<> inline py::dtype get_numpy_dtype<std::complex<float>>() { return py::dtype::of<std::complex<float>>(); }
template<> inline py::dtype get_numpy_dtype<std::complex<double>>() { return py::dtype::of<std::complex<double>>(); }
template<> inline py::dtype get_numpy_dtype<unsigned long long>() { return py::dtype::of<unsigned long long>(); }
// Add more specializations for other types you use in GPIArray::Array<T>
} // end namespace gpi_array_detail

// --- Type Caster for GPIArray::Array<T> ---
namespace pybind11 { namespace detail {

template <typename T>
struct type_caster<GPIArray::Array<T>> {
public:
    PYBIND11_TYPE_CASTER(GPIArray::Array<T>, _("GPIArray::Array[") + pybind11::detail::type_caster<T>::name + _("]"));

    bool load(py::handle src, bool convert) {
        // 1. Delegate the incredibly complex type-checking (float vs complex, 
        // exact dtype matching, endianness) to Pybind11's native array_t caster. 
        // This natively understands and honors the .noconvert() policy flawlessly.
        pybind11::detail::type_caster<py::array_t<T>> array_caster;
        if (!array_caster.load(src, convert)) {
            return false;
        }

        // 2. Extract the successfully validated array
        py::array_t<T> numpy_array = array_caster;
        
        // 3. Request read-only buffer safely (avoids throwing BufferError 
        // if the user passes read-only data from GPI nodes)
        py::buffer_info buf_info;
        try {
            buf_info = numpy_array.request();
        } catch (...) {
            return false;
        }

        if (!buf_info.ptr) return false;

        const int ndim = buf_info.ndim;
        const size_t itemsize = buf_info.itemsize;

        if (ndim < 0) return false;

        if (buf_info.size == 0 && ndim > 0) {
            value = GPIArray::Array<T>();  // Empty array
            return true;
        }

        // Use shape and strides directly without reversing for GPIArray
        std::vector<uint64_t> gpi_dims(ndim);
        std::vector<uint64_t> gpi_strides_elements(ndim);
        for (int i = 0; i < ndim; ++i) {
            gpi_dims[i] = static_cast<uint64_t>(buf_info.shape[i]);
            gpi_strides_elements[i] = static_cast<uint64_t>(buf_info.strides[i]) / itemsize;
        }

        // Create shared_ptr to keep NumPy array alive
        T* data_ptr = static_cast<T*>(buf_info.ptr);
        py::object numpy_owner = numpy_array; 

        std::shared_ptr<T> storage_ptr(data_ptr, [numpy_owner](T*) {
            // capture keeps NumPy array alive
        });

        // Construct view
        const uint64_t offset = 0;
        if (ndim == 0) {
            value = GPIArray::Array<T>(0, nullptr, nullptr, storage_ptr, offset);
        } else {
            value = GPIArray::Array<T>(ndim, gpi_dims.data(), gpi_strides_elements.data(), storage_ptr, offset);
        }

        return true;
    }

    // C++ -> Python: Convert a GPIArray::Array to a NumPy array view
    static py::handle cast(const GPIArray::Array<T>& src, py::return_value_policy, py::handle) {
        if (src.get_data() == nullptr && src.size() > 0) {
            PyErr_SetString(PyExc_RuntimeError, "GPIArray has valid dimensions but null data pointer.");
            return nullptr;
        }

        const uint64_t ndim = src.ndim();
        std::vector<py::ssize_t> numpy_shape(ndim);
        std::vector<py::ssize_t> numpy_strides_bytes(ndim);

        // Use shape and strides directly without reversing for GPIArray
        for (uint64_t i = 0; i < ndim; ++i) {
            numpy_shape[i] = static_cast<py::ssize_t>(src.dimensions()[i]);
            numpy_strides_bytes[i] = static_cast<py::ssize_t>(src.strides()[i]) * sizeof(T);
        }


        // Handle 0D and empty cases
        if (ndim == 0 && src.size() == 0) {
            numpy_shape = {0};
            numpy_strides_bytes = {};
        }

        // Create capsule to manage shared_ptr lifetime
        auto shared_ptr_copy = src.get_raw_storage_ptr();
        py::capsule owner_capsule(
            new std::shared_ptr<T>(shared_ptr_copy),
            "GPIArray_shared_ptr_owner",
            [](void *p) {
                delete static_cast<std::shared_ptr<T>*>(p);
            }
        );

        // Construct NumPy array
        py::array numpy_array_view;
        if (ndim == 0 && src.size() > 0) {
            // For a 0D scalar, NumPy expects shape () and no strides.
            // py::array(dtype, shape, data, owner)
            numpy_array_view = py::array(gpi_array_detail::get_numpy_dtype<T>(), {}, src.get_data(), owner_capsule);
        } else {
            numpy_array_view = py::array(gpi_array_detail::get_numpy_dtype<T>(), numpy_shape, numpy_strides_bytes, src.get_data(), owner_capsule);
        }

        return numpy_array_view.release();
    }
};

}} // namespace pybind11::detail

namespace GPIArray {
    // Elevate these to the main GPIArray namespace for global use
    using FFTW::ImageToKspace;
    using FFTW::KspaceToImage;
    using LinAlg::SingularValuesOnly;
    using LinAlg::Thin;
    using LinAlg::Full;
}

#endif // GPIARRAY_HPP_INCLUDED
