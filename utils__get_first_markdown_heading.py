

# AI!
# Write a function to extract the first markdown heading from a string of markdown content. The function should return the heading text without the leading "#" characters. If no heading is found, the function should return None.
# Only look through the first n lines (default n to 20) of the content to find the heading. This is to prevent the function from taking too long to run on large files.
# 
def get_markdown_heading(content: str) -> str | None:
