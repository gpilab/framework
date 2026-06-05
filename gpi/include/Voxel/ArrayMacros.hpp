
/**
 * @file ArrayMacros.hpp
 * @brief Macro definitions and exception handling utilities for Voxel.
 *
 * This header provides macro utilities and exception handling support for the Voxel library.
 * It includes common macros used throughout the array implementation and integrates
 * exception classes for robust error reporting.
 *
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#pragma once

#pragma once

// MSVC does not expose M_PI from <cmath> unless this is defined before the first math include
#ifndef _USE_MATH_DEFINES
    #define _USE_MATH_DEFINES
#endif
#include <cmath>

// Fallback for any compiler that still omits M_PI
#ifndef M_PI
    #define M_PI 3.14159265358979323846
#endif

#include "ArrayException.hpp"
#include <sstream>
#include <stdexcept>

#ifdef _MSC_VER
    #define VOXEL_ALWAYS_INLINE __forceinline
    #define VOXEL_RESTRICT __restrict
#else
    #define VOXEL_ALWAYS_INLINE inline __attribute__((always_inline))
    #define VOXEL_RESTRICT __restrict__
#endif

