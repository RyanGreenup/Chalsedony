import pytest
from chalsedony.utils__ngram_filter import ngram_filter

def test_trigram_filter():
    """Test default trigram filtering"""
    input_lines = ["abc", "abcd", "ab", ""]
    result = ngram_filter(input_lines)
    assert result == ["abcd"]  # Only 'abcd' contains a trigram

def test_custom_ngram_length():
    """Test with custom n-gram length"""
    input_lines = ["abc", "abcd", "ab"]
    result = ngram_filter(input_lines, n=2)
    assert result == ["abc", "abcd"]  # Both contain bigrams

def test_empty_input():
    """Test with empty input list"""
    assert ngram_filter([]) == []

def test_no_valid_ngrams():
    """Test when no strings contain valid n-grams"""
    input_lines = ["a", "ab"]
    result = ngram_filter(input_lines, n=3)
    assert result == []
