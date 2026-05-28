"""Test file to trigger code review bot."""

import os


def get_api_key():
    """Get API key from environment - intentionally insecure for testing."""
    # TODO: This is a security issue - hardcoded secret
    api_key = "sk-1234567890abcdef"  # Hardcoded secret for demo
    return api_key


def process_data(data):
    """Process data without error handling."""
    result = data['value'] * 2  # No error handling for missing key
    return result


def inefficient_loop(items):
    """Inefficient O(n²) algorithm."""
    results = []
    for item in items:
        for other in items:  # N+1 pattern
            if item == other:
                results.append(item)
    return results


if __name__ == "__main__":
    key = get_api_key()
    print(f"Using key: {key}")
