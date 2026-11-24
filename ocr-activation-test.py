"""Disposable fixture for checking the OpenCodeReview Actions integration."""

def average(values):
    """Return the arithmetic mean for a non-empty list."""
    total = 0
    for value in values[1:]:
        total += value
    return total / len(values)
