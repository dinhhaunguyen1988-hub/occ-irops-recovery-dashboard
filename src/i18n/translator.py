"""Translation lookup with thread-local locale state."""

from __future__ import annotations

import threading
from functools import cache
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LOCALE = "vi"
SUPPORTED_LOCALES = ("vi", "en")
_LOCALES_DIR = Path("locales")

_state = threading.local()


def _locales_root() -> Path:
    """Resolve ``locales/`` relative to the repo root.

    Falls back to the directory next to the package import in case the
    process CWD is not the repo root (e.g. inside a Docker container).
    """
    candidates = [
        Path.cwd() / _LOCALES_DIR,
        Path(__file__).resolve().parents[2] / _LOCALES_DIR,
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


@cache
def _load_locale(locale: str) -> dict[str, Any]:
    path = _locales_root() / f"{locale}.yaml"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    # Coerce all keys to str so callers can't accidentally pass non-str.
    return {str(k): v for k, v in data.items()}


def available_locales() -> tuple[str, ...]:
    """Return the tuple of locales we ship a translation file for."""
    found = []
    for loc in SUPPORTED_LOCALES:
        if (_locales_root() / f"{loc}.yaml").is_file():
            found.append(loc)
    return tuple(found) or (DEFAULT_LOCALE,)


def set_locale(locale: str) -> None:
    """Set the active locale for the current thread."""
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(f"Unsupported locale {locale!r}. Supported: {SUPPORTED_LOCALES!r}")
    _state.locale = locale


def get_locale() -> str:
    """Return the active locale, defaulting to the package default."""
    return getattr(_state, "locale", DEFAULT_LOCALE)


def t(key: str, **kwargs: Any) -> str:
    """Translate ``key`` into the active locale.

    Falls back to the default locale, and finally to the key itself if
    nothing matches. Supports ``str.format``-style placeholders so
    callers can interpolate values without breaking translation.
    """
    locale = get_locale()
    primary = _load_locale(locale)
    if key in primary:
        template = str(primary[key])
    else:
        fallback = _load_locale(DEFAULT_LOCALE)
        template = str(fallback.get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template
    return template
