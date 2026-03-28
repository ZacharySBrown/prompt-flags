"""Custom Jinja2 filters for prompt text processing.

Provides filters useful for prompt engineering, such as whitespace
management and text formatting.
"""

import re


def strip_empty_lines(text: str) -> str:
    """Remove all empty lines from text.

    Args:
        text: The input text.

    Returns:
        Text with empty lines removed.
    """
    lines = text.split("\n")
    return "\n".join(line for line in lines if line.strip())


def indent_block(text: str, spaces: int = 2) -> str:
    """Indent all non-empty lines of text by a given number of spaces.

    Args:
        text: The input text.
        spaces: Number of spaces to indent. Defaults to 2.

    Returns:
        Text with non-empty lines indented.
    """
    if not text:
        return text
    prefix = " " * spaces
    lines = text.split("\n")
    return "\n".join((prefix + line) if line.strip() else line for line in lines)


def collapse_blank_lines(text: str) -> str:
    """Collapse runs of multiple blank lines into single blank lines.

    Args:
        text: The input text.

    Returns:
        Text with consecutive blank lines collapsed to one.
    """
    return re.sub(r"\n{3,}", "\n\n", text)
