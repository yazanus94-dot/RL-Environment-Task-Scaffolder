def clamp(value, low, high):
    """Clamp value into [low, high]."""
    return max(min(value, low), high)
