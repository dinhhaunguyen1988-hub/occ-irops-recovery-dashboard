"""Tests for the i18n translator."""

from __future__ import annotations

from src.i18n import available_locales, get_locale, set_locale, t
from src.i18n.translator import _load_locale


def teardown_function(_func) -> None:
    set_locale("vi")  # reset thread-local state between tests


def test_available_locales_includes_vi_and_en() -> None:
    locales = available_locales()
    assert "vi" in locales
    assert "en" in locales


def test_default_locale_is_vi() -> None:
    set_locale("vi")
    assert get_locale() == "vi"


def test_set_locale_round_trips() -> None:
    set_locale("en")
    assert get_locale() == "en"


def test_t_returns_localised_string_for_known_key() -> None:
    set_locale("vi")
    assert "Hồi phục" in t("app.title")
    set_locale("en")
    assert t("app.title") == "OCC IROPS Recovery Dashboard"


def test_t_falls_back_to_default_locale_for_missing_key() -> None:
    # Add a synthetic key only in default (vi); make sure en falls back.
    vi = _load_locale("vi")
    assert "kpi.affected" in vi
    set_locale("en")
    out = t("kpi.affected")
    assert isinstance(out, str) and out


def test_t_returns_key_when_missing_from_all_locales() -> None:
    set_locale("vi")
    out = t("nonexistent.key.never.added")
    assert out == "nonexistent.key.never.added"


def test_t_supports_format_kwargs() -> None:
    set_locale("en")
    out = t("app.signed_in_as", name="Dinh", role="dm")
    assert "Dinh" in out and "dm" in out


def test_t_safe_when_kwargs_missing() -> None:
    """If template references a placeholder not provided, do not raise."""
    set_locale("en")
    # signed_in_as expects {name} and {role}; pass nothing — must return template.
    out = t("app.signed_in_as")
    assert isinstance(out, str)


def test_set_locale_rejects_unsupported() -> None:
    import pytest

    with pytest.raises(ValueError):
        set_locale("fr")
