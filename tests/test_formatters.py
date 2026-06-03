import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bot.render.formatters import safe, bold, code


def test_safe_escapes_html():
    assert safe("<b>test</b>") == "&lt;b&gt;test&lt;/b&gt;"


def test_safe_handles_none():
    assert safe(None) == ""


def test_bold():
    assert bold("hello") == "<b>hello</b>"


def test_code():
    assert code("abc") == "<code>abc</code>"
