from shape_stats.core import percentile

def test_median():
    assert percentile([1, 2, 3, 4], 50) == 2.5

def test_min_is_zero_percentile():
    assert percentile([5, 7], 0) == 5

def test_max_is_hundred_percentile():
    assert percentile([5, 7], 100) == 7
