# pyrefly: ignore [missing-import]
from telegram.helpers import escape_html

def markdown_to_html(text: str) -> str:
    """Very simple conversion from a subset of Markdown to HTML for Telegram messages.
    It escapes HTML characters and replaces common markdown patterns:
    - **bold** -> <b>bold</b>
    - *italic* -> <i>italic</i>
    - `code` -> <code>code</code>
    - __underline__ -> <u>underline</u>
    This is not a full markdown parser but sufficient for the project's messages.
    """
    # Escape HTML first
    escaped = escape_html(text)
    # Replace markdown patterns. Order matters to avoid double replacement.
    escaped = escaped.replace('**', '<b>').replace('**', '</b>', 1)  # simplistic; will be refined below
    # Better approach: use a simple state machine for pairs
    # For brevity, handle **bold**, *italic*, `code`, __underline__ via regex
    import re
    # Bold
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped)
    # Italic (single *)
    escaped = re.sub(r'\*(.+?)\*', r'<i>\1</i>', escaped)
    # Inline code
    escaped = re.sub(r'`(.+?)`', r'<code>\1</code>', escaped)
    # Underline (double underscore)
    escaped = re.sub(r'__(.+?)__', r'<u>\1</u>', escaped)
    return escaped
