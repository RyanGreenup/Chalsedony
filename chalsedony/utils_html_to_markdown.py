from markdownify import markdownify as md


def html_to_markdown(html: str) -> str:
    # Convert HTML to markdown
    markdown_text = md(
        html,
        heading_style="ATX",  # Use `#` for headings
        code_language="guess",  # Try to detect code language
        strip=["style", "script"],  # Remove unwanted tags
        autolinks=True,  # Convert URLs to links
        default_title=True,  # Use title attribute for links
        escape_underscores=False,  # Don't escape underscores
        keep_inline_images_in=["img"],  # Keep image tags
        wrap_width=0,  # Don't wrap text
    )

    return str(markdown_text)
