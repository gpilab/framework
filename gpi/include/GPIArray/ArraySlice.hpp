// Slice.hpp - Dedicated Slice class for multidimensional array slicing
#pragma once

#include <limits>
#include <iostream> // Included for operator<<, consistent with original file

namespace GPIArray {

// Dedicated Slice class
struct Slice {
    long long start;
    long long stop;
    long long step; // Still kept internally but always 1 for user-facing constructors

    // Private helper constants for internal use by Slice constructors/static methods.
    static constexpr long long ALL_REPRESENTATION = std::numeric_limits<long long>::max();
    static constexpr long long CENTER_REPRESENTATION = std::numeric_limits<long long>::min();

    // Constructors
    // Default constructor (e.g., S()) for a full slice
    Slice() : start(ALL_REPRESENTATION), stop(ALL_REPRESENTATION), step(1) {}

    // Constructor for Slice(start, stop)
    Slice(long long start_val, long long stop_val)
        : start(start_val), stop(stop_val), step(1) {}

    // Constructor for Slice(single_index) - acts like arr[5:6]
    Slice(long long single_index) : start(single_index), stop(single_index + 1), step(1) {}

    // Public static member functions to get pre-defined Slice objects.
    // This avoids the "incomplete type" issue because the function body (which constructs the Slice)
    // is only evaluated when the function is called, at which point 'Slice' is a complete type.
    static Slice all() { return Slice(ALL_REPRESENTATION, ALL_REPRESENTATION); }
    static Slice center() { return Slice(CENTER_REPRESENTATION, CENTER_REPRESENTATION + 1); }
};

// Overload the stream insertion operator for Slice objects
inline std::ostream& operator<<(std::ostream& os, const Slice& s) {
    if (s.start == Slice::ALL_REPRESENTATION) {
        os << "all";
    } else if (s.start == Slice::CENTER_REPRESENTATION) {
        os << "center";
    } else {
        os << s.start;
    }

    // Only print stop if it's not a single index slice (i.e., s.start + 1)
    // and not Slice::all (as 'all' implies the entire dimension)
    if (s.stop != s.start + 1 || s.start == Slice::ALL_REPRESENTATION) {
        os << ":";
        if (s.stop == Slice::ALL_REPRESENTATION) {
            os << "all";
        } else if (s.stop == Slice::CENTER_REPRESENTATION) {
            // This case indicates a potential issue if Slice::center is passed as a stop value directly
            os << "center_stop_issue";
        } else {
            os << s.stop;
        }
    }
    // Step is currently always 1, so no need to print unless that changes.
    return os;
}

} // namespace GPIArray