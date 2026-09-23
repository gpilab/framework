/**
 * @file test_FFT_PYBIND11.cpp
 * @brief Pybind11 bridge for comprehensive benchmarking of PocketFFT vs FFTW.
 */

#include "Voxel/Voxel.hpp" 
#include "Voxel/FFTW_WRAPPER.hpp" // Ensure FFTW wrapper is included

namespace py = pybind11;
using namespace Voxel;

using ComplexArray = Array<std::complex<double>>;

PYBIND11_MODULE(test_FFT, m) {
    m.doc() = "Voxel FFT Comprehensive Benchmark Module (PocketFFT vs FFTW)";

    // =========================================================================
    // 1. POCKETFFT BINDINGS (Voxel::FFT)
    // =========================================================================
    py::enum_<Voxel::FFT::TransformDir>(m, "TransformDir")
        .value("Forward", Voxel::FFT::TransformDir::Forward)
        .value("Backward", Voxel::FFT::TransformDir::Backward)
        .value("ImageToKspace", Voxel::FFT::TransformDir::ImageToKspace)
        .value("KspaceToImage", Voxel::FFT::TransformDir::KspaceToImage)
        .export_values();

    py::class_<Voxel::FFT::FFTPlan<double>>(m, "FFTPlan")
        .def(py::init<const std::vector<uint64_t>&, const std::vector<uint64_t>&>(),
             py::arg("total_shape"), py::arg("transform_axes") = std::vector<uint64_t>{})
        .def("ImageToKspace", [](const Voxel::FFT::FFTPlan<double>& plan, ComplexArray& arr, bool shift) {
            plan.ImageToKspace(arr, shift);
        }, py::arg("arr"), py::arg("perform_shift") = true)
        .def("KspaceToImage", [](const Voxel::FFT::FFTPlan<double>& plan, ComplexArray& arr, bool shift) {
            plan.KspaceToImage(arr, shift);
        }, py::arg("arr"), py::arg("perform_shift") = true);

    m.def("fftn", [](const ComplexArray& input, Voxel::FFT::TransformDir dir, std::vector<uint64_t> axes, bool shift) {
        return Voxel::FFT::fftn<double>(input, dir, axes, shift, Voxel::FFT::NORM_BACKWARD);
    }, py::arg("input"), py::arg("dir"), py::arg("axes") = std::vector<uint64_t>{}, py::arg("perform_shift") = true);

    // =========================================================================
    // 2. FFTW BINDINGS (Voxel::FFTW)
    // =========================================================================
    py::enum_<Voxel::FFTW::TransformDir>(m, "FFTWTransformDir")
        .value("FFTW_Forward", Voxel::FFTW::TransformDir::Forward)
        .value("FFTW_Backward", Voxel::FFTW::TransformDir::Backward)
        .value("FFTW_ImageToKspace", Voxel::FFTW::TransformDir::ImageToKspace)
        .value("FFTW_KspaceToImage", Voxel::FFTW::TransformDir::KspaceToImage)
        .export_values();

    py::class_<Voxel::FFTW::FFTPlan<double>>(m, "FFTWPlan")
        // FIX: Use a lambda to map the 2-argument Python call to the 3-argument C++ constructor
        .def(py::init([](const std::vector<uint64_t>& total_shape, const std::vector<uint64_t>& transform_axes) {
            return new Voxel::FFTW::FFTPlan<double>(total_shape, FFTW_MEASURE, transform_axes);
        }), py::arg("total_shape"), py::arg("transform_axes") = std::vector<uint64_t>{})
        .def("ImageToKspace", [](const Voxel::FFTW::FFTPlan<double>& plan, ComplexArray& arr, bool shift) {
            plan.ImageToKspace(arr, shift);
        }, py::arg("arr"), py::arg("perform_shift") = true)
        .def("KspaceToImage", [](const Voxel::FFTW::FFTPlan<double>& plan, ComplexArray& arr, bool shift) {
            plan.KspaceToImage(arr, shift);
        }, py::arg("arr"), py::arg("perform_shift") = true);

    m.def("fftw_fftn", [](const ComplexArray& input, Voxel::FFTW::TransformDir dir, std::vector<uint64_t> axes, bool shift) {
        // 1. Allocate the output array to match the input shape
        ComplexArray output(input.shape()); 
        
        // 2. Call the void-returning fftn function
        Voxel::FFTW::fftn<double>(input, output, dir, axes, shift, Voxel::FFTW::NORM_BACKWARD);
        
        // 3. Return the populated array to Python
        return output;
    }, py::arg("input"), py::arg("dir"), py::arg("axes") = std::vector<uint64_t>{}, py::arg("perform_shift") = true);
}