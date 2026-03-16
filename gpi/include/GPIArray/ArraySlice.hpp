
/**
 * @file ArraySlice.hpp
 * @brief Defines the GPIArray::Slice struct for advanced slicing operations on multi-dimensional arrays.
 *
 * This header provides the GPIArray::Slice struct, which encapsulates slicing semantics for array indexing.
 * Features:
 *   - Represents a slice with start, stop, and step.
 *   - Supports full-dimension selection (Slice::all()), center selection (Slice::center()), and single-index selection.
 *   - Supports flexible end-relative indexing: S(5, end), S(0, end-20, -1), S()
 *   - Provides convenient constructors for common slicing patterns with validation.
 *   - Query methods for safe type checking: is_all(), is_center(), is_single_index().
 *   - Equality comparison for slice objects.
 *   - Overloads the stream insertion operator for human-readable output.
 *   - Internal constants for representing "all", "center", and "end" slices.
 *
 * Validation:
 *   - Step must be non-zero (throws std::invalid_argument if violated).
 *   - For positive steps, start must be < stop unless slice is "all" or "center".
 *   - Invalid slice constructions are caught early with clear error messages.
 *
 * Example Usage:
 *   - S() - full slice (all elements)
 *   - S(5) - single element at index 5
 *   - S(0, 10) - elements 0 to 9
 *   - S(5, end) - elements from 5 to end of dimension
 *   - S(0, end-20) - elements 0 to (size-20)
 *   - S(0, end-20, -1) - reverse slice with offset (requires end-aware resolution)
 *   - S::all() - explicit all-elements marker
 *   - S::center() - center element
 *   - S::end - constant representing end of dimension
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

// Forward declaration for end-relative indexing
struct EndMarker;

// Dedicated Slice class
struct Slice {
    long long start;
    long long stop;
    long long step;

    // Internal markers for special slice types
    static constexpr long long ALL_MARKER = std::numeric_limits<long long>::max();
    static constexpr long long CENTER_MARKER = std::numeric_limits<long long>::min();
    static constexpr long long END_MARKER = std::numeric_limits<long long>::max() - 1;
    static constexpr long long END_REL_MARKER = std::numeric_limits<long long>::max() - 2;

    // Keep old names for backward compatibility
    static constexpr long long ALL_REPRESENTATION = ALL_MARKER;
    static constexpr long long CENTER_REPRESENTATION = CENTER_MARKER;

    // Helper class for end-relative indexing
    struct EndOffset {
        long long offset;  // 0 means end, -20 means end-20, etc.
        explicit EndOffset(long long off = 0) : offset(off) {}
        
        /**
         * @brief Support end-20 syntax: end - 20
         */
        EndOffset operator-(long long val) const {
            return EndOffset(offset - val);
        }
        
        /**
         * @brief Support end+10 syntax: end + 10
         */
        EndOffset operator+(long long val) const {
            return EndOffset(offset + val);
        }
    };

    // Static instance for S(5, end) syntax
    static EndOffset end;

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

    /**
     * @brief Constructor for Slice(start, end) with EndOffset.
     * Marks stop as END marker to be resolved at runtime.
     * Example: S(5, end) or S(0, end)
     */
    Slice(long long start_val, const EndOffset& end_val)
        : start(start_val), stop(END_MARKER + end_val.offset), step(1) {}

    /**
     * @brief Constructor for Slice(start, end, step) with EndOffset.
     * Marks stop as END marker with offset to be resolved at runtime.
     * Example: S(0, end-20, -1) or S(5, end, 2)
     */
    Slice(long long start_val, const EndOffset& end_val, long long step_val)
        : start(start_val), stop(END_MARKER + end_val.offset), step(step_val) {}

    /**
     * @brief Check if this slice uses end-relative indexing.
     */
    bool uses_end_marker() const noexcept {
        return stop > END_MARKER - 100 && stop < END_MARKER + 1;
    }

    /**
     * @brief Get the offset from end (0 means end, -20 means end-20, etc).
     */
    long long get_end_offset() const noexcept {
        if (uses_end_marker()) {
            return stop - END_MARKER;
        }
        return 0;
    }

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
     * Note: Validation for end-relative slices is deferred to runtime when dimension size is known.
     */
    void validate() const {
        // Allow special markers without validation
        if (is_all() || is_center()) return;

        // Allow end markers - validation happens at runtime
        if (uses_end_marker()) return;

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

// Static initialization for Slice::end
inline Slice::EndOffset Slice::end(0);

// Overload the stream insertion operator for Slice objects
inline std::ostream& operator<<(std::ostream& os, const Slice& s) {
    if (s.is_all()) {
        os << ":";
    } else if (s.is_center()) {
        os << "center";
    } else if (s.is_single_index()) {
        os << s.start;
    } else if (s.uses_end_marker()) {
        // Display end-relative slices
        os << s.start << ":";
        long long offset = s.get_end_offset();
        if (offset == 0) {
            os << "end";
        } else if (offset < 0) {
            os << "end" << offset;  // Shows as "end-20" for offset=-20
        } else {
            os << "end+" << offset;
        }
        if (s.step != 1) {
            os << ":" << s.step;
        }
    } else {
        os << s.start << ":" << s.stop;
        if (s.step != 1) {
            os << ":" << s.step;
        }
    }
    return os;
}

} // namespace GPIArray