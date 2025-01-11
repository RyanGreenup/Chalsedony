from typing import Set

def generate_ngrams(text: str, n: int = 2) -> Set[str]:
    """Generate n-grams from text.

    Args:
        text: Input text to generate n-grams from
        n: Length of each n-gram (default=2 for digrams)

    Returns:
        Set of n-grams
    """
    # Convert to lowercase and remove extra whitespace
    text = ' '.join(text.lower().split())

    # Generate n-grams including spaces
    ngrams = set()
    for i in range(len(text) - n + 1):
        ngrams.add(text[i:i + n])
    return ngrams

# AI: Use this function
def text_matches_filter(filter_text: str, target_text: str, n: int = 2, match_all: bool = True) -> bool:
    """Check if target text matches filter text using n-gram comparison.

    Args:
        filter_text: Text to filter by
        target_text: Text to check against filter
        n: Length of n-grams to use (default=2)
        match_all: If True, all filter n-grams must be present in target; if False, any filter n-gram can be present (default=False)
                   True is tentative, useful for strict filtering,
                   False is useful for fuzzy filtering (greedy)

    Returns:
        True if target text matches filter criteria
    """
    if target_text == "":
        return False
    if not filter_text or not target_text:
        return True

    if len(filter_text) < n or len(target_text) < n:
        n = min(len(filter_text), len(target_text))

    # Generate n-grams for both texts
    filter_ngrams = generate_ngrams(filter_text, n)
    target_ngrams = generate_ngrams(target_text, n)

    # Check if all or any filter n-grams are present in target
    return all(ng in target_ngrams for ng in filter_ngrams) if match_all else any(ng in target_ngrams for ng in filter_ngrams)



