def percentile(sorted_values, p):
    """Return the p-th percentile (0-100) of a sorted list."""
    if not sorted_values:
        raise ValueError("empty")
    if p < 0 or p > 100:
        raise ValueError("p out of range")
    k = (len(sorted_values) - 1) * p / 100.0
    f = int(k)          # floor
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)
