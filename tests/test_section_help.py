"""SectionHelp widget + required help_* i18n keys."""

from studio.i18n import LANG_EN, LANG_ZH, I18n, _STRINGS
from studio.section_help import SectionHelpButton, section_title_row

REQUIRED_HELP_KEYS = (
    "help_missing",
    "help_button_a11y",
    "help_dialog_title",
    "help_runtime",
    "help_runtime_advanced",
    "help_page_match",
    "help_page_images",
    "help_case_basic",
    "help_case_post",
    "help_case_advanced",
    "help_steps",
    "help_macros",
    "help_pairs",
)


def test_help_keys_exist_both_langs():
    for lang in (LANG_EN, LANG_ZH):
        for key in REQUIRED_HELP_KEYS:
            assert key in _STRINGS[lang], f"missing {key} in {lang}"
            assert _STRINGS[lang][key].strip(), f"empty {key} in {lang}"


def test_section_help_button_tooltip():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    i18n = I18n(LANG_ZH)
    btn = SectionHelpButton(i18n.t, "help_runtime")
    tip = btn.toolTip()
    assert "截屏间隔" in tip or "最低相似度" in tip
    row, title, h = section_title_row(i18n.t, "params_group", "help_runtime")
    assert title.text()
    assert h.help_key == "help_runtime"


def test_help_texts_mention_neutral_labels():
    """Section help should use the same product labels as the form fields."""
    zh = _STRINGS[LANG_ZH]
    en = _STRINGS[LANG_EN]
    assert "最低相似度" in zh["help_runtime"] and "截屏间隔" in zh["help_runtime"]
    assert "相近容差" in zh["help_runtime_advanced"] and "领先要求" in zh["help_runtime_advanced"]
    assert "后续观察" in zh["help_case_post"] and "观察次数" in zh["help_case_post"]
    assert "易混淆" in zh["help_pairs"]
    assert "Min. similarity" in en["help_runtime"]
    assert "Required lead" in en["help_runtime_advanced"]
    assert "Follow-up" in en["help_case_post"] or "follow-up" in en["help_case_post"]
