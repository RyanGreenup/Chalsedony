def get_markdown_heading(content: str, max_lines: int = 20) -> str | None:
    """Extract the first markdown heading from content.
    
    Args:
        content: Markdown content to search
        max_lines: Maximum number of lines to check (default 20)
        
    Returns:
        The heading text without leading # characters, or None if no heading found
    """
    lines = content.splitlines()
    for line in lines[:max_lines]:
        line = line.lstrip()
        if line.startswith("#"):
            # Remove all leading # characters and whitespace
            return line.lstrip("#").strip()
    return None
