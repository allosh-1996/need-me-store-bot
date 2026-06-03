import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bot.render.strings import STRINGS, t


def test_all_keys_have_ar_and_en():
    for key, langs in STRINGS.items():
        assert "ar" in langs, f"Missing 'ar' for key: {key}"
        assert "en" in langs, f"Missing 'en' for key: {key}"


def test_t_returns_correct_lang():
    assert "NexVault" in t("welcome", "ar")
    assert "NexVault" in t("welcome", "en")


def test_t_fallback_to_en():
    assert t("welcome", "fr") == t("welcome", "en")


def test_t_format():
    result = t("af_submitted", "ar", order_id=1, game_name="Test", levels="5,10", price_usd="4", balance="12.00")
    assert "#1" in result
