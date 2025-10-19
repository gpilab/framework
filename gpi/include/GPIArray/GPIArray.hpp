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

    // Python -> C++: Convert a NumPy array to a GPIArray::Array view
    bool load(py::handle src, bool convert) {
        if (!convert) return false;

        py::array_t<T> array = py::array_t<T>::ensure(src);
        if (!array) return false;

        const auto buf_info = array.request();

        if (!buf_info.ptr) {
            PyErr_SetString(PyExc_ValueError, "NumPy array has null data pointer.");
            return false;
        }

        const int ndim = buf_info.ndim;
        const size_t itemsize = buf_info.itemsize;

        if (ndim < 0) {
            PyErr_SetString(PyExc_ValueError, "NumPy array has negative dimensions.");
            return false;
        }

        if (itemsize != sizeof(T)) {
            PyErr_SetString(PyExc_ValueError, "NumPy array dtype does not match expected C++ type.");
            return false;
        }

        if (buf_info.size == 0 && ndim > 0) {
            value = GPIArray::Array<T>();  // Empty array
            return true;
        }

        // Reverse shape and strides for GPIArray to appear column-major from Python
        std::vector<uint64_t> gpi_dims(ndim);
        std::vector<uint64_t> gpi_strides_elements(ndim);
        for (int i = 0; i < ndim; ++i) {
            const int rev_i = ndim - 1 - i; // Reverse index
            gpi_dims[i] = static_cast<uint64_t>(buf_info.shape[rev_i]);
            gpi_strides_elements[i] = static_cast<uint64_t>(buf_info.strides[rev_i]) / itemsize;
        }


        // Create shared_ptr to keep NumPy array alive
        T* data_ptr = static_cast<T*>(buf_info.ptr);
        py::object numpy_owner = py::reinterpret_borrow<py::object>(array);

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

        // Reverse dimensions and strides for NumPy to appear row-major from Python
        for (uint64_t i = 0; i < ndim; ++i) {
            const uint64_t rev_i = ndim - 1 - i; // Reverse index
            numpy_shape[i] = static_cast<py::ssize_t>(src.dimensions()[rev_i]);
            numpy_strides_bytes[i] = static_cast<py::ssize_t>(src.strides()[rev_i]) * sizeof(T);
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

#endif // GPIARRAY_HPP_INCLUDED
// // --- Pybind11 Module Definition ---
// PYBIND11_MODULE(gpi_array_module, m) {
//     m.doc() = "pybind11 plugin for GPIArray C++ library with zero-copy NumPy integration.";

//     // Expose the Array class
//     py::class_<GPIArray::Array<float>>(m, "ArrayF")
//         .def(py::init<>())
//         .def(py::init<uint64_t>())
//         .def(py::init<uint64_t, uint64_t>())
//         .def(py::init<uint64_t, uint64_t, uint64_t>())
//         .def(py::init<uint64_t, uint64_t, uint64_t, uint64_t>())
//         .def(py::init<const std::vector<uint64_t>&>())
//         .def("ndim", &GPIArray::Array<float>::ndim)
//         .def("size", py::overload_cast<>(&GPIArray::Array<float>::size, py::const_), "Total number of elements")
//         .def("size", py::overload_cast<uint64_t>(&GPIArray::Array<float>::size, py::const_), "Size of a specific dimension")
//         .def("dimensions", &GPIArray::Array<float>::dimensions_vector)
//         .def("strides", &GPIArray::Array<float>::strides_vector)
//         .def("get_data", &GPIArray::Array<float>::get_data, py::return_value_policy::reference_internal) // Returns raw pointer
//         .def("fill", py::overload_cast<const float&>(&GPIArray::Array<float>::fill), "Fill array with a scalar")
//         .def("fill", py::overload_cast<const int&>(&GPIArray::Array<float>::fill), "Fill array with an int scalar (casting)") // Expose overload for int
//         .def("copy", &GPIArray::Array<float>::copy, "Create a deep copy of the array")
//         .def("empty_like", &GPIArray::Array<float>::empty_like, "Create an uninitialized array with the same shape")
//         .def("squeeze", &GPIArray::Array<float>::squeeze, "Remove dimensions of size 1")
//         .def("reshape", &GPIArray::Array<float>::template reshape<py::args>, "Reshape array (variadic args)") // Use template for variadic args
//         .def("transpose", &GPIArray::Array<float>::template transpose<py::args>, "Transpose array (variadic args)")
//         .def("__getitem__", [](const GPIArray::Array<float>& a, py::handle idx) -> GPIArray::Array<float> {
//             // Handle various indexing types (single int, tuple of ints/slices)
//             if (py::isinstance<py::int_>(idx)) {
//                 // Single integer index for 1D access or first dimension
//                 return a.get_slice(GPIArray::S(py::cast<long long>(idx))); // Cast to long long for S constructor
//             } else if (py::isinstance<py::tuple>(idx)) {
//                 // Tuple of integers or slice objects
//                 std::vector<GPIArray::Slice> slices;
//                 for (py::handle item : py::cast<py::tuple>(idx)) {
//                     if (py::isinstance<py::int_>(item)) {
//                         slices.push_back(GPIArray::S(py::cast<long long>(item)));
//                     } else if (py::isinstance<py::slice>(item)) {
//                         py::slice s_py = py::cast<py::slice>(item);
//                         // Accessing start/stop/step as attributes directly
//                         long long start_ll = py::cast<long long>(s_py.attr("start"));
//                         long long stop_ll = py::cast<long long>(s_py.attr("stop"));
//                         long long step_ll = py::cast<long long>(s_py.attr("step"));

//                         // Map Python's None to ALL_REPRESENTATION as needed by GPIArray::Slice.
//                         // Python's slice(None, None, None) maps to start=None, stop=None, step=None.
//                         if (s_py.attr("start").is_none()) start_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("stop").is_none()) stop_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("step").is_none()) step_ll = 1; // Default step is 1 for Python None.

//                         slices.push_back(GPIArray::Slice(start_ll, stop_ll, step_ll));

//                     } else if (item.is_none()) { // Corresponds to Python `None` for adding new dimensions (treated as S::all() for slicing)
//                          slices.push_back(GPIArray::S::all());
//                     } else {
//                         throw py::type_error("Invalid index type for GPIArray::Array.__getitem__");
//                     }
//                 }
//                 return a.get_slice(slices);
//             }
//             throw py::type_error("Invalid index type for GPIArray::Array.__getitem__");
//         })
//         .def("__setitem__", [](GPIArray::Array<float>& a, py::handle idx, py::handle value_py) {
//             // Very basic setitem implementation. Needs significant expansion for full NumPy-like behavior.
//             // For now, only support scalar assignment.
//             if (py::isinstance<py::int_>(idx)) { // Set single element
//                 uint64_t i = py::cast<uint64_t>(idx);
//                 float val = py::cast<float>(value_py);
//                 a(i) = val;
//             } else if (py::isinstance<py::tuple>(idx)) { // Setting slices/multiple elements. Very complex.
//                 // This would require iterating through the slice and assigning values.
//                 // For a minimal working example, we'll only support scalar assignments to slices.
//                 std::vector<GPIArray::Slice> slices;
//                 for (py::handle item : py::cast<py::tuple>(idx)) {
//                      if (py::isinstance<py::int_>(item)) {
//                         slices.push_back(GPIArray::S(py::cast<long long>(item)));
//                     } else if (py::isinstance<py::slice>(item)) {
//                         py::slice s_py = py::cast<py::slice>(item);
//                         long long start_ll = py::cast<long long>(s_py.attr("start"));
//                         long long stop_ll = py::cast<long long>(s_py.attr("stop"));
//                         long long step_ll = py::cast<long long>(s_py.attr("step"));

//                         if (s_py.attr("start").is_none()) start_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("stop").is_none()) stop_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("step").is_none()) step_ll = 1;

//                         slices.push_back(GPIArray::Slice(start_ll, stop_ll, step_ll));
//                     } else if (item.is_none()) {
//                          slices.push_back(GPIArray::S::all());
//                     } else {
//                         throw py::type_error("Invalid index type for GPIArray::Array.__setitem__");
//                     }
//                 }
//                 GPIArray::Array<float> target_slice = a.get_slice(slices);
//                 if (py::isinstance<py::float_>(value_py) || py::isinstance<py::int_>(value_py)) {
//                     target_slice.fill(py::cast<float>(value_py));
//                 } else if (py::isinstance<GPIArray::Array<float>>(value_py)) {
//                     // Assignment of one array to a slice of another. Sizes must match.
//                     const GPIArray::Array<float>& rhs_arr = py::cast<const GPIArray::Array<float>&>(value_py);
//                     if (target_slice.size() != rhs_arr.size()) {
//                         throw py::value_error("Size mismatch when assigning Array to slice.");
//                     }
//                     // Iterate and assign element by element.
//                     // This is inefficient but safe for potentially non-contiguous slices.
//                      std::vector<uint64_t> current_indices(target_slice.ndim(), 0);
//                      std::function<void(uint64_t)> iterate_assign =
//                          [&](uint64_t dim) {
//                          if (dim == target_slice.ndim()) {
//                              target_slice.get_item(current_indices) = rhs_arr.get_item(current_indices);
//                              return;
//                          }
//                          for (uint64_t i = 0; i < target_slice.dimensions()[dim]; ++i) {
//                              current_indices[dim] = i;
//                              iterate_assign(dim + 1);
//                          }
//                      };
//                      if (target_slice.ndim() == 0) { // Scalar slice assignment
//                         target_slice() = rhs_arr();
//                      } else {
//                         iterate_assign(0);
//                      }
//                 }
//                 else {
//                     throw py::type_error("Invalid value type for GPIArray::Array.__setitem__");
//                 }
//             } else {
//                 throw py::type_error("Invalid index type for GPIArray::Array.__setitem__");
//             }
//         });

//     py::class_<GPIArray::Array<double>>(m, "ArrayD")
//         .def(py::init<>())
//         .def(py::init<uint64_t>())
//         .def(py::init<uint64_t, uint64_t>())
//         .def(py::init<uint64_t, uint64_t, uint64_t>())
//         .def(py::init<uint64_t, uint64_t, uint64_t, uint64_t>())
//         .def(py::init<const std::vector<uint64_t>&>())
//         .def("ndim", &GPIArray::Array<double>::ndim)
//         .def("size", py::overload_cast<>(&GPIArray::Array<double>::size, py::const_))
//         .def("size", py::overload_cast<uint64_t>(&GPIArray::Array<double>::size, py::const_))
//         .def("dimensions", &GPIArray::Array<double>::dimensions_vector)
//         .def("strides", &GPIArray::Array<double>::strides_vector)
//         .def("get_data", &GPIArray::Array<double>::get_data, py::return_value_policy::reference_internal)
//         .def("fill", py::overload_cast<const double&>(&GPIArray::Array<double>::fill), "Fill array with a scalar")
//         .def("fill", py::overload_cast<const int&>(&GPIArray::Array<double>::fill), "Fill array with an int scalar (casting)")
//         .def("copy", &GPIArray::Array<double>::copy)
//         .def("empty_like", &GPIArray::Array<double>::empty_like)
//         .def("squeeze", &GPIArray::Array<double>::squeeze)
//         .def("reshape", &GPIArray::Array<double>::template reshape<py::args>)
//         .def("transpose", &GPIArray::Array<double>::template transpose<py::args>)
//         .def("__getitem__", [](const GPIArray::Array<double>& a, py::handle idx) -> GPIArray::Array<double> {
//             if (py::isinstance<py::int_>(idx)) {
//                 return a.get_slice(GPIArray::S(py::cast<long long>(idx)));
//             } else if (py::isinstance<py::tuple>(idx)) {
//                 std::vector<GPIArray::Slice> slices;
//                 for (py::handle item : py::cast<py::tuple>(idx)) {
//                      if (py::isinstance<py::int_>(item)) {
//                         slices.push_back(GPIArray::S(py::cast<long long>(item)));
//                     } else if (py::isinstance<py::slice>(item)) {
//                         py::slice s_py = py::cast<py::slice>(item);
//                         long long start_ll = py::cast<long long>(s_py.attr("start"));
//                         long long stop_ll = py::cast<long long>(s_py.attr("stop"));
//                         long long step_ll = py::cast<long long>(s_py.attr("step"));

//                         if (s_py.attr("start").is_none()) start_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("stop").is_none()) stop_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("step").is_none()) step_ll = 1;

//                         slices.push_back(GPIArray::Slice(start_ll, stop_ll, step_ll));
//                     } else if (item.is_none()) {
//                          slices.push_back(GPIArray::S::all());
//                     } else {
//                         throw py::type_error("Invalid index type for GPIArray::Array.__getitem__");
//                     }
//                 }
//                 return a.get_slice(slices);
//             }
//             throw py::type_error("Invalid index type for GPIArray::Array.__getitem__");
//         })
//         .def("__setitem__", [](GPIArray::Array<double>& a, py::handle idx, py::handle value_py) {
//             if (py::isinstance<py::int_>(idx)) {
//                 uint64_t i = py::cast<uint64_t>(idx);
//                 double val = py::cast<double>(value_py);
//                 a(i) = val;
//             } else if (py::isinstance<py::tuple>(idx)) {
//                 std::vector<GPIArray::Slice> slices;
//                 for (py::handle item : py::cast<py::tuple>(idx)) {
//                      if (py::isinstance<py::int_>(item)) {
//                         slices.push_back(GPIArray::S(py::cast<long long>(item)));
//                     } else if (py::isinstance<py::slice>(item)) {
//                         py::slice s_py = py::cast<py::slice>(item);
//                         long long start_ll = py::cast<long long>(s_py.attr("start"));
//                         long long stop_ll = py::cast<long long>(s_py.attr("stop"));
//                         long long step_ll = py::cast<long long>(s_py.attr("step"));

//                         if (s_py.attr("start").is_none()) start_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("stop").is_none()) stop_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("step").is_none()) step_ll = 1;

//                         slices.push_back(GPIArray::Slice(start_ll, stop_ll, step_ll));
//                     } else if (item.is_none()) {
//                          slices.push_back(GPIArray::S::all());
//                     } else {
//                         throw py::type_error("Invalid index type for GPIArray::Array.__setitem__");
//                     }
//                 }
//                 GPIArray::Array<double> target_slice = a.get_slice(slices);
//                 if (py::isinstance<py::float_>(value_py) || py::isinstance<py::int_>(value_py)) {
//                     target_slice.fill(py::cast<double>(value_py));
//                 } else if (py::isinstance<GPIArray::Array<double>>(value_py)) {
//                      const GPIArray::Array<double>& rhs_arr = py::cast<const GPIArray::Array<double>&>(value_py);
//                      if (target_slice.size() != rhs_arr.size()) {
//                         throw py::value_error("Size mismatch when assigning Array to slice.");
//                     }
//                     std::vector<uint64_t> current_indices(target_slice.ndim(), 0);
//                      std::function<void(uint64_t)> iterate_assign =
//                          [&](uint64_t dim) {
//                          if (dim == target_slice.ndim()) {
//                              target_slice.get_item(current_indices) = rhs_arr.get_item(current_indices);
//                              return;
//                          }
//                          for (uint64_t i = 0; i < target_slice.dimensions()[dim]; ++i) {
//                              current_indices[dim] = i;
//                              iterate_assign(dim + 1);
//                          }
//                      };
//                      if (target_slice.ndim() == 0) {
//                         target_slice() = rhs_arr();
//                      } else {
//                         iterate_assign(0);
//                      }
//                 } else {
//                     throw py::type_error("Invalid value type for GPIArray::Array.__setitem__");
//                 }
//             } else {
//                 throw py::type_error("Invalid index type for GPIArray::Array.__setitem__");
//             }
//         });

//     py::class_<GPIArray::Array<std::complex<float>>>(m, "ArrayCF")
//         .def(py::init<>())
//         .def(py::init<uint64_t>())
//         .def(py::init<uint64_t, uint64_t>())
//         .def(py::init<uint64_t, uint64_t, uint64_t>())
//         .def(py::init<uint64_t, uint64_t, uint64_t, uint64_t>())
//         .def(py::init<const std::vector<uint64_t>&>())
//         .def("ndim", &GPIArray::Array<std::complex<float>>::ndim)
//         .def("size", py::overload_cast<>(&GPIArray::Array<std::complex<float>>::size, py::const_))
//         .def("size", py::overload_cast<uint64_t>(&GPIArray::Array<std::complex<float>>::size, py::const_))
//         .def("dimensions", &GPIArray::Array<std::complex<float>>::dimensions_vector)
//         .def("strides", &GPIArray::Array<std::complex<float>>::strides_vector)
//         .def("get_data", &GPIArray::Array<std::complex<float>>::get_data, py::return_value_policy::reference_internal)
//         .def("fill", py::overload_cast<const std::complex<float>&>(&GPIArray::Array<std::complex<float>>::fill), "Fill array with a complex scalar")
//         .def("fill", py::overload_cast<const float&>(&GPIArray::Array<std::complex<float>>::fill), "Fill array with a float scalar (casting)")
//         .def("fill", py::overload_cast<const int&>(&GPIArray::Array<std::complex<float>>::fill), "Fill array with an int scalar (casting)")
//         .def("copy", &GPIArray::Array<std::complex<float>>::copy)
//         .def("empty_like", &GPIArray::Array<std::complex<float>>::empty_like)
//         .def("squeeze", &GPIArray::Array<std::complex<float>>::squeeze)
//         .def("reshape", &GPIArray::Array<std::complex<float>>::template reshape<py::args>)
//         .def("transpose", &GPIArray::Array<std::complex<float>>::template transpose<py::args>)
//          .def("__getitem__", [](const GPIArray::Array<std::complex<float>>& a, py::handle idx) -> GPIArray::Array<std::complex<float>> {
//             if (py::isinstance<py::int_>(idx)) {
//                 return a.get_slice(GPIArray::S(py::cast<long long>(idx)));
//             } else if (py::isinstance<py::tuple>(idx)) {
//                 std::vector<GPIArray::Slice> slices;
//                 for (py::handle item : py::cast<py::tuple>(idx)) {
//                      if (py::isinstance<py::int_>(item)) {
//                         slices.push_back(GPIArray::S(py::cast<long long>(item)));
//                     } else if (py::isinstance<py::slice>(item)) {
//                         py::slice s_py = py::cast<py::slice>(item);
//                         long long start_ll = py::cast<long long>(s_py.attr("start"));
//                         long long stop_ll = py::cast<long long>(s_py.attr("stop"));
//                         long long step_ll = py::cast<long long>(s_py.attr("step"));

//                         if (s_py.attr("start").is_none()) start_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("stop").is_none()) stop_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("step").is_none()) step_ll = 1;

//                         slices.push_back(GPIArray::Slice(start_ll, stop_ll, step_ll));
//                     } else if (item.is_none()) {
//                          slices.push_back(GPIArray::S::all());
//                     } else {
//                         throw py::type_error("Invalid index type for GPIArray::Array.__getitem__");
//                     }
//                 }
//                 return a.get_slice(slices);
//             }
//             throw py::type_error("Invalid index type for GPIArray::Array.__getitem__");
//         })
//         .def("__setitem__", [](GPIArray::Array<std::complex<float>>& a, py::handle idx, py::handle value_py) {
//             if (py::isinstance<py::int_>(idx)) {
//                 uint64_t i = py::cast<uint64_t>(idx);
//                 std::complex<float> val = py::cast<std::complex<float>>(value_py);
//                 a(i) = val;
//             } else if (py::isinstance<py::tuple>(idx)) {
//                 std::vector<GPIArray::Slice> slices;
//                 for (py::handle item : py::cast<py::tuple>(idx)) {
//                      if (py::isinstance<py::int_>(item)) {
//                         slices.push_back(GPIArray::S(py::cast<long long>(item)));
//                     } else if (py::isinstance<py::slice>(item)) {
//                         py::slice s_py = py::cast<py::slice>(item);
//                         long long start_ll = py::cast<long long>(s_py.attr("start"));
//                         long long stop_ll = py::cast<long long>(s_py.attr("stop"));
//                         long long step_ll = py::cast<long long>(s_py.attr("step"));

//                         if (s_py.attr("start").is_none()) start_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("stop").is_none()) stop_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("step").is_none()) step_ll = 1;

//                         slices.push_back(GPIArray::Slice(start_ll, stop_ll, step_ll));
//                     } else if (item.is_none()) {
//                          slices.push_back(GPIArray::S::all());
//                     } else {
//                         throw py::type_error("Invalid index type for GPIArray::Array.__setitem__");
//                     }
//                 }
//                 GPIArray::Array<std::complex<float>> target_slice = a.get_slice(slices);
//                 if (py::isinstance<py::float_>(value_py) || py::isinstance<py::int_>(value_py) || py::isinstance<py::complex>(value_py)) {
//                     target_slice.fill(py::cast<std::complex<float>>(value_py));
//                 } else if (py::isinstance<GPIArray::Array<std::complex<float>>>(value_py)) {
//                      const GPIArray::Array<std::complex<float>>& rhs_arr = py::cast<const GPIArray::Array<std::complex<float>>&>(value_py);
//                      if (target_slice.size() != rhs_arr.size()) {
//                         throw py::value_error("Size mismatch when assigning Array to slice.");
//                     }
//                     std::vector<uint64_t> current_indices(target_slice.ndim(), 0);
//                      std::function<void(uint64_t)> iterate_assign =
//                          [&](uint64_t dim) {
//                          if (dim == target_slice.ndim()) {
//                              target_slice.get_item(current_indices) = rhs_arr.get_item(current_indices);
//                              return;
//                          }
//                          for (uint64_t i = 0; i < target_slice.dimensions()[dim]; ++i) {
//                              current_indices[dim] = i;
//                              iterate_assign(dim + 1);
//                          }
//                      };
//                      if (target_slice.ndim() == 0) {
//                         target_slice() = rhs_arr();
//                      } else {
//                         iterate_assign(0);
//                      }
//                 } else {
//                     throw py::type_error("Invalid value type for GPIArray::Array.__setitem__");
//                 }
//             } else {
//                 throw py::type_error("Invalid index type for GPIArray::Array.__setitem__");
//             }
//         });

//     py::class_<GPIArray::Array<std::complex<double>>>(m, "ArrayCD")
//         .def(py::init<>())
//         .def(py::init<uint64_t>())
//         .def(py::init<uint64_t, uint64_t>())
//         .def(py::init<uint64_t, uint64_t, uint64_t>())
//         .def(py::init<uint64_t, uint64_t, uint64_t, uint64_t>())
//         .def(py::init<const std::vector<uint64_t>&>())
//         .def("ndim", &GPIArray::Array<std::complex<double>>::ndim)
//         .def("size", py::overload_cast<>(&GPIArray::Array<std::complex<double>>::size, py::const_))
//         .def("size", py::overload_cast<uint64_t>(&GPIArray::Array<std::complex<double>>::size, py::const_))
//         .def("dimensions", &GPIArray::Array<std::complex<double>>::dimensions_vector)
//         .def("strides", &GPIArray::Array<std::complex<double>>::strides_vector)
//         .def("get_data", &GPIArray::Array<std::complex<double>>::get_data, py::return_value_policy::reference_internal)
//         .def("fill", py::overload_cast<const std::complex<double>&>(&GPIArray::Array<std::complex<double>>::fill), "Fill array with a complex scalar")
//         .def("fill", py::overload_cast<const double&>(&GPIArray::Array<std::complex<double>>::fill), "Fill array with a double scalar (casting)")
//         .def("fill", py::overload_cast<const int&>(&GPIArray::Array<std::complex<double>>::fill), "Fill array with an int scalar (casting)")
//         .def("copy", &GPIArray::Array<std::complex<double>>::copy)
//         .def("empty_like", &GPIArray::Array<std::complex<double>>::empty_like)
//         .def("squeeze", &GPIArray::Array<std::complex<double>>::squeeze)
//         .def("reshape", &GPIArray::Array<std::complex<double>>::template reshape<py::args>)
//         .def("transpose", &GPIArray::Array<std::complex<double>>::template transpose<py::args>)
//         .def("__getitem__", [](const GPIArray::Array<std::complex<double>>& a, py::handle idx) -> GPIArray::Array<std::complex<double>> {
//             if (py::isinstance<py::int_>(idx)) {
//                 return a.get_slice(GPIArray::S(py::cast<long long>(idx)));
//             } else if (py::isinstance<py::tuple>(idx)) {
//                 std::vector<GPIArray::Slice> slices;
//                 for (py::handle item : py::cast<py::tuple>(idx)) {
//                      if (py::isinstance<py::int_>(item)) {
//                         slices.push_back(GPIArray::S(py::cast<long long>(item)));
//                     } else if (py::isinstance<py::slice>(item)) {
//                         py::slice s_py = py::cast<py::slice>(item);
//                         long long start_ll = py::cast<long long>(s_py.attr("start"));
//                         long long stop_ll = py::cast<long long>(s_py.attr("stop"));
//                         long long step_ll = py::cast<long long>(s_py.attr("step"));

//                         if (s_py.attr("start").is_none()) start_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("stop").is_none()) stop_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("step").is_none()) step_ll = 1;

//                         slices.push_back(GPIArray::Slice(start_ll, stop_ll, step_ll));
//                     } else if (item.is_none()) {
//                          slices.push_back(GPIArray::S::all());
//                     } else {
//                         throw py::type_error("Invalid index type for GPIArray::Array.__getitem__");
//                     }
//                 }
//                 return a.get_slice(slices);
//             }
//             throw py::type_error("Invalid index type for GPIArray::Array.__getitem__");
//         })
//         .def("__setitem__", [](GPIArray::Array<std::complex<double>>& a, py::handle idx, py::handle value_py) {
//             if (py::isinstance<py::int_>(idx)) {
//                 uint64_t i = py::cast<uint64_t>(idx);
//                 std::complex<double> val = py::cast<std::complex<double>>(value_py);
//                 a(i) = val;
//             } else if (py::isinstance<py::tuple>(idx)) {
//                 std::vector<GPIArray::Slice> slices;
//                 for (py::handle item : py::cast<py::tuple>(idx)) {
//                      if (py::isinstance<py::int_>(item)) {
//                         slices.push_back(GPIArray::S(py::cast<long long>(item)));
//                     } else if (py::isinstance<py::slice>(item)) {
//                         py::slice s_py = py::cast<py::slice>(item);
//                         long long start_ll = py::cast<long long>(s_py.attr("start"));
//                         long long stop_ll = py::cast<long long>(s_py.attr("stop"));
//                         long long step_ll = py::cast<long long>(s_py.attr("step"));

//                         if (s_py.attr("start").is_none()) start_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("stop").is_none()) stop_ll = GPIArray::Slice::ALL_REPRESENTATION;
//                         if (s_py.attr("step").is_none()) step_ll = 1;

//                         slices.push_back(GPIArray::Slice(start_ll, stop_ll, step_ll));
//                     } else if (item.is_none()) {
//                          slices.push_back(GPIArray::S::all());
//                     } else {
//                         throw py::type_error("Invalid index type for GPIArray::Array.__setitem__");
//                     }
//                 }
//                 GPIArray::Array<std::complex<double>> target_slice = a.get_slice(slices);
//                 if (py::isinstance<py::float_>(value_py) || py::isinstance<py::int_>(value_py) || py::isinstance<py::complex>(value_py)) {
//                     target_slice.fill(py::cast<std::complex<double>>(value_py));
//                 } else if (py::isinstance<GPIArray::Array<std::complex<double>>>(value_py)) {
//                      const GPIArray::Array<std::complex<double>>& rhs_arr = py::cast<const GPIArray::Array<std::complex<double>>&>(value_py);
//                      if (target_slice.size() != rhs_arr.size()) {
//                         throw py::value_error("Size mismatch when assigning Array to slice.");
//                     }
//                     std::vector<uint64_t> current_indices(target_slice.ndim(), 0);
//                      std::function<void(uint64_t)> iterate_assign =
//                          [&](uint64_t dim) {
//                          if (dim == target_slice.ndim()) {
//                              target_slice.get_item(current_indices) = rhs_arr.get_item(current_indices);
//                              return;
//                          }
//                          for (uint64_t i = 0; i < target_slice.dimensions()[dim]; ++i) {
//                              current_indices[dim] = i;
//                              iterate_assign(dim + 1);
//                          }
//                      };
//                      if (target_slice.ndim() == 0) {
//                         target_slice() = rhs_arr();
//                      } else {
//                         iterate_assign(0);
//                      }
//                 } else {
//                     throw py::type_error("Invalid value type for GPIArray::Array.__setitem__");
//                 }
//             } else {
//                 throw py::type_error("Invalid index type for GPIArray::Array.__setitem__");
//             }
//         });

//     // Expose FFTW functions (example, ensure your FFTW.hpp includes them correctly)
//     m.def("fftn_float", &GPIArray::FFTW::fftn<float>, "N-dimensional FFT for float complex arrays (all axes)");
//     m.def("fftn_double", &GPIArray::FFTW::fftn<double>, "N-dimensional FFT for double complex arrays (all axes)");
//     m.def("fft1_float", &GPIArray::FFTW::fft1<float>, "1D FFT for float complex arrays");
//     m.def("fft1_double", &GPIArray::FFTW::fft1<double>, "1D FFT for double complex arrays");
//     m.def("fft2_float", &GPIArray::FFTW::fft2<float>, "2D FFT for float complex arrays");
//     m.def("fft2_double", &GPIArray::FFTW::fft2<double>, "2D FFT for double complex arrays");
//     m.def("fft3_float", &GPIArray::FFTW::fft3<float>, "3D FFT for float complex arrays");
//     m.def("fft3_double", &GPIArray::FFTW::fft3<double>, "3D FFT for double complex arrays");
    
//     // Expose FFTW constants
//     m.attr("FFTW_FORWARD") = FFTW_FORWARD;
//     m.attr("FFTW_BACKWARD") = FFTW_BACKWARD;

//     // Example of exposing a MathOp
//     m.def("l2norm_float", &GPIArray::l2norm<float>, "L2 Norm for float arrays");
//     m.def("l2norm_double", &GPIArray::l2norm<double>, "L2 Norm for double arrays");
//     m.def("l2norm_complex_float", &GPIArray::l2norm<std::complex<float>>, "L2 Norm for complex float arrays");
//     m.def("l2norm_complex_double", &GPIArray::l2norm<std::complex<double>>, "L2 Norm for complex double arrays");

//     // Add more Array and Math/FFTW exposures as needed for other types (int, long etc.)
// }
