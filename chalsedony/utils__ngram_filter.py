# Implement logic for an ngram filter, this will default to a trigram filter. AI!
def ngram_filter(lines: List[str], n: int = 3) -> List[str]:
    """
    Filter out lines that don't contain any n-grams from the input list of lines.
    """
