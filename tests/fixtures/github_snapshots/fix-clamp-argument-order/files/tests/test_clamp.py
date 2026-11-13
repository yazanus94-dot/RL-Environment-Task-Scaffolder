from numtools.clamp import clamp

def test_clamps_inside():
    assert clamp(5, 0, 10) == 5

def test_clamp_at_high():
    assert clamp(10, 0, 10) == 10
