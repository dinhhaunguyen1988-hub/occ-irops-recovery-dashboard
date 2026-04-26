"""Lightweight i18n for the OCC IROPS Recovery Dashboard.

Translations live in YAML files under ``locales/`` (one file per
language, two-letter ISO code as the filename, e.g. ``vi.yaml``,
``en.yaml``). Each file is a flat key→string map; nested keys are
*not* supported on purpose to keep grep-ability of every UI string.

Usage::

    from src.i18n import set_locale, t
    set_locale("vi")
    st.title(t("app.title"))

If a key is missing from the active locale, the function returns the
key unchanged so the missing string is obvious in the UI rather than
raising at runtime — translation is a content concern, not a
functional one.
"""

from src.i18n.translator import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    available_locales,
    get_locale,
    set_locale,
    t,
)

__all__ = [
    "DEFAULT_LOCALE",
    "SUPPORTED_LOCALES",
    "available_locales",
    "get_locale",
    "set_locale",
    "t",
]
