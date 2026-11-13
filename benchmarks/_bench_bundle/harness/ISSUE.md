# Task fix-percentile-boundary

percentile() returns wrong values at the upper boundary: percentile([1,2,3,4], 50) gives 3 instead of 2.5 and percentile([5,7], 100) interpolates out of range. The interpolation index must be scaled over (len-1), not len.

## Verification tests

- Fail-to-pass: tests/test_core.py::test_median, tests/test_core.py::test_max_is_hundred_percentile
- Pass-to-pass: tests/test_core.py::test_min_is_zero_percentile
