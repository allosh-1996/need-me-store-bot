from html import escape


def safe(text: object) -> str:
    return escape(str(text or ""))


def bold(text: object) -> str:
    return f"<b>{safe(text)}</b>"


def code(text: object) -> str:
    return f"<code>{safe(text)}</code>"
