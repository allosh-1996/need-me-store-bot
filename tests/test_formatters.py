import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bot.render.formatters import safe, bold, code


def test_safe_escapes_lt():
    assert safe("<") == "&lt;"


def test_safe_escapes_gt():
    assert safe(">") == "&gt;"


def test_safe_escapes_amp():
    assert safe("&") == "&amp;"


def test_safe_handles_none():
    assert safe(None) == ""


def test_safe_handles_number():
    assert safe(42) == "42"


def test_bold():
    assert bold("hello") == "<b>hello</b>"


def test_bold_escapes_input():
    assert bold("<x>") == "<b>&lt;x&gt;</b>"


def test_code():
    assert code("abc") == "<code>abc</code>"


def test_code_escapes_input():
    assert code("<b>") == "<code>&lt;b&gt;</code>"
