
/**
 * @file ArraySlice.hpp
 * @brief Defines the GPIArray::Slice struct for advanced slicing operations on multi-dimensional arrays.
 *
 * This header provides the GPIArray::Slice struct, which encapsulates slicing semantics for array indexing.
 * Features:
 *   - Represents a slice with start, stop, and step.
 *   - Supports full-dimension selection (Slice::all()), center selection (Slice::center()), and single-index selection.
 *   - Provides convenient constructors for common slicing patterns with validation.
 *   - Query methods for safe type checking: is_all(), is_center(), is_single_index().
 *   - Equality comparison for slice objects.
 *   - Overloads the stream insertion operator for human-readable output.
 *   - Internal constants for representing "all" and "center" slices.
 *
 * Validation:
 *   - Step must be non-zero (throws std::invalid_argument if violated).
 *   - For positive steps, start must be < stop unless slice is "all" or "center".
 *   - Invalid slice constructions are caught early with clear error messages.
 *
 * The Slice struct is intended for use with GPIArray containers to enable expressive and efficient slicing,
 * similar to Python's slice notation in NumPy.
 * @author Guru Krishnamoorthy
 * @date 2025 July
 */
#pragma once

#include <limits>
#include <iostream> // Included for operator<<, consistent with original file

namespace GPIArray {

// Dedicated Slice class
struct Slice {
    long long start;
    long long stop;
    long long step;

    // Internal markers for special slice types
    static constexpr long long ALL_MARKER = std::numeric_limits<long long>::max();
    static constexpr long long CENTER_MARKER = std::numeric_limits<long long>::min();

    // Keep old names for backward compatibility
    static constexpr long long ALL_REPRESENTATION = ALL_MARKER;
    static constexpr long long CENTER_REPRESENTATION = CENTER_MARKER;

    // Constructors with validation
    /**
     * @brief Default constructor - represents a full slice (all elements).
     */
    Slice() : start(ALL_MARKER), stop(ALL_MARKER), step(1) {}

    /**
     * @brief Constructor for Slice(start, stop) with unit step.
     * @throws std::invalid_argument if start >= stop (for positive step).
     */
    Slice(long long start_val, long long stop_val) : start(start_val), stop(stop_val), step(1) {
        validate();
    }

    /**
     * @brief Constructor for Slice(start, stop, step) with explicit step.
     * @throws std::invalid_argument if step == 0 or bounds are invalid.
     */
    Slice(long long start_val, long long stop_val, long long step_val)
        : start(start_val), stop(stop_val), step(step_val) {
        validate();
    }

    /**
     * @brief Constructor for single-element slice (acts like arr[index] which is arr[index:index+1]).
     */
    explicit Slice(long long single_index) : start(single_index), stop(single_index + 1), step(1) {}

    // Query methods for safe type checking
    /**
     * @brief Check if this slice represents "all elements" (full dimension).
     */
    bool is_all() const noexcept {
        return start == ALL_MARKER && stop == ALL_MARKER;
    }

    /**
     * @brief Check if this slice represents "center element".
     */
    bool is_center() const noexcept {
        return start == CENTER_MARKER && stop == CENTER_MARKER + 1;
    }

    /**
     * @brief Check if this is a single-index slice (represents one element).
     */
    bool is_single_index() const noexcept {
        return !is_all() && !is_center() && (stop == start + 1) && step == 1;
    }

    /**
     * @brief Check if this is a valid "all" or "center" special slice.
     */
    bool is_special() const noexcept {
        return is_all() || is_center();
    }

    /**
     * @brief Equality comparison for slice objects.
     */
    bool operator==(const Slice& other) const noexcept {
        return start == other.start && stop == other.stop && step == other.step;
    }

    /**
     * @brief Inequality comparison for slice objects.
     */
    bool operator!=(const Slice& other) const noexcept {
        return !(*this == other);
    }

 private:
    /**
     * @brief Validate slice parameters. Throws on invalid configuration.
     */
    void validate() const {
        // Allow special markers without validation
        if (is_all() || is_center()) return;

        // Step must be non-zero
        if (step == 0) {
            throw std::invalid_argument("Slice step cannot be zero");
        }

        // For positive step, start must be < stop
        if (step > 0 && start >= stop) {
            throw std::invalid_argument("Slice: For positive step, start (" +
                std::to_string(start) + ") must be less than stop (" +
                std::to_string(stop) + ")");
        }

        // For negative step, start must be > stop
        if (step < 0 && start <= stop) {
            throw std::invalid_argument("Slice: For negative step, start (" +
                std::to_string(start) + ") must be greater than stop (" +
                std::to_string(stop) + ")");
        }
    }

public:
    // Public static member functions to get pre-defined Slice objects
    /**
     * @brief Create a slice representing all elements in this dimension.
     */
    static Slice all() { return Slice(ALL_MARKER, ALL_MARKER); }

    /**
     * @brief Create a slice representing the center element of this dimension.
     */
    static Slice center() {
        Slice s;
        s.start = CENTER_MARKER;
        s.stop = CENTER_MARKER + 1;
        return s;
    }
};

// Overload the stream insertion operator for Slice objects
inline std::ostream& operator<<(std::ostream& os, const Slice& s) {
    if (s.is_all()) {
        os << ":";
    } else if (s.is_center()) {
        os << "center";
    } else if (s.is_single_index()) {
        os << s.start;
    } else {
        os << s.start << ":" << s.stop;
        if (s.step != 1) {
            os << ":" << s.step;
        }
    }
    return os;
}

} // namespace GPIArray