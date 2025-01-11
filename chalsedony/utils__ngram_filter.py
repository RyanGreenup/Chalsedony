from typing import List

def ngram_filter(lines: List[str], n: int = 3) -> List[str]:
    """
    Filter out lines that don't contain any n-grams from the input list of lines.
    Returns only lines that contain at least one n-gram sequence.
    
    Args:
        lines: List of strings to filter
        n: Length of n-grams to check for (default=3 for trigrams)
        
    Returns:
        List of strings that contain at least one n-gram
    """
    def get_ngrams(text: str, n: int) -> set:
        """Generate set of n-grams from text"""
        return {text[i:i+n] for i in range(len(text) - n + 1)}
    
    # Filter lines that have at least one n-gram
    return [line for line in lines if len(get_ngrams(line, n)) > 0]
