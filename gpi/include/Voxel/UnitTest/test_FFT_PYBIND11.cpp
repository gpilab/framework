/**
 * @file test_FFT_PYBIND11.cpp
 * @brief Pybind11 bridge for comprehensive benchmarking of the Voxel::FFT module.
 */


#include "Voxel/Voxel.hpp" // Assumes Voxel.hpp includes Array.hpp, FFT_WRAPPER.hpp, and type casters

namespace py = pybind11;
using namespace Voxel;
using namespace Voxel::FFT;

using ComplexArray = Array<std::complex<double>>;

PYBIND11_MODULE(test_FFT, m) {
    m.doc() = "Voxel FFT Comprehensive Benchmark Module";

    // 1. Expose Enums
    py::enum_<TransformDir>(m, "TransformDir")
        .value("Forward", TransformDir::Forward)
        .value("Backward", TransformDir::Backward)
        .value("ImageToKspace", TransformDir::ImageToKspace)
        .value("KspaceToImage", TransformDir::KspaceToImage)
        .export_values();

    // 2. Expose FFTPlan
    py::class_<FFTPlan<double>>(m, "FFTPlan")
        .def(py::init<const std::vector<uint64_t>&, const std::vector<uint64_t>&>(),
             py::arg("total_shape"), py::arg("transform_axes") = std::vector<uint64_t>{})
        // In-place transforms
        .def("ImageToKspace", [](const FFTPlan<double>& plan, ComplexArray& arr, bool shift) {
            plan.ImageToKspace(arr, shift);
        }, py::arg("arr"), py::arg("perform_shift") = true)
        .def("KspaceToImage", [](const FFTPlan<double>& plan, ComplexArray& arr, bool shift) {
            plan.KspaceToImage(arr, shift);
        }, py::arg("arr"), py::arg("perform_shift") = true);

    // 3. Expose One-Off Allocating Functions
    m.def("fftn", [](const ComplexArray& input, TransformDir dir, std::vector<uint64_t> axes, bool shift) {
        return Voxel::FFT::fftn<double>(input, dir, axes, shift, NORM_BACKWARD);
    }, py::arg("input"), py::arg("dir"), py::arg("axes") = std::vector<uint64_t>{}, py::arg("perform_shift") = true);
}