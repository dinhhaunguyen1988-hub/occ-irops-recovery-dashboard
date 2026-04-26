"""YAML-file backed user/role lookup + Streamlit login helper.

Designed to be imported by ``app.py`` only. Importing this module does
not pull in ``streamlit_authenticator`` unless :func:`require_login` is
actually called — that keeps unit tests for the auth module free of
heavyweight UI dependencies.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

Role = Literal["dm", "viewer"]
DEFAULT_USERS_PATH = Path("config") / "users.yaml"


@dataclass(frozen=True)
class AuthenticatedUser:
    """A successfully-authenticated dashboard user."""

    username: str
    name: str
    role: Role


@dataclass(frozen=True)
class AuthBypassedUser:
    """Sentinel returned when ``OCC_AUTH_DISABLED=1`` is set."""

    username: str = "localdev"
    name: str = "Local Dev"
    role: Role = "dm"


def is_auth_disabled() -> bool:
    """Return True iff the auth bypass env var is set to a truthy value."""
    return os.environ.get("OCC_AUTH_DISABLED", "").strip().lower() in {"1", "true", "yes"}


def role_can_edit_settings(role: Role) -> bool:
    return role == "dm"


def role_can_view_audit(role: Role) -> bool:
    return role == "dm"


def load_users_config(path: str | Path = DEFAULT_USERS_PATH) -> dict[str, Any]:
    """Load and lightly validate the users YAML file.

    Expected structure (compatible with ``streamlit-authenticator``)::

        cookie:
          name: occ_irops_auth
          key: <random-secret>
          expiry_days: 1
        credentials:
          usernames:
            dm1:
              name: Dinh DM
              password: <bcrypt-hash>
              role: dm

    The ``role`` field is an *extension* of the streamlit-authenticator
    schema; the library passes it through unchanged because it lives
    inside ``credentials.usernames.<u>``.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"users.yaml not found at {p}. Copy config/users.example.yaml and edit."
        )
    with p.open() as f:
        cfg = yaml.safe_load(f) or {}
    creds = cfg.get("credentials", {}).get("usernames", {})
    if not isinstance(creds, dict) or not creds:
        raise ValueError("users.yaml must define at least one user under credentials.usernames")
    for u, info in creds.items():
        if not isinstance(info, dict):
            raise ValueError(f"users.yaml: user {u!r} must be a mapping")
        if "password" not in info:
            raise ValueError(f"users.yaml: user {u!r} missing 'password' (bcrypt hash)")
        if info.get("role") not in {"dm", "viewer"}:
            raise ValueError(f"users.yaml: user {u!r} has invalid role {info.get('role')!r}")
    return cfg


def require_login(
    users_path: str | Path = DEFAULT_USERS_PATH,
) -> AuthenticatedUser | AuthBypassedUser | None:
    """Render the Streamlit login form and return the authed user.

    Returns ``None`` while authentication is still pending so the
    caller can ``st.stop()``. When ``OCC_AUTH_DISABLED=1``, returns an
    :class:`AuthBypassedUser` immediately (no UI rendered).
    """
    if is_auth_disabled():
        return AuthBypassedUser()

    # Lazy import so unit tests can import the module without Streamlit
    # being available.
    import streamlit as st
    import streamlit_authenticator as stauth

    cfg = load_users_config(users_path)

    authenticator = stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        int(cfg["cookie"].get("expiry_days", 1)),
    )

    # streamlit-authenticator >=0.3 stores results in session_state and may
    # return either a tuple (older) or None (newer). Read defensively.
    result = authenticator.login(location="main", key="login_form")
    if isinstance(result, tuple) and len(result) >= 3:
        name, auth_status, username = result[:3]
    else:
        name = st.session_state.get("name")
        auth_status = st.session_state.get("authentication_status")
        username = st.session_state.get("username")

    if auth_status is False:
        st.error("Sai username hoặc password.")
        return None
    if auth_status is None or username is None:
        st.info("Vui lòng đăng nhập để sử dụng dashboard.")
        return None

    role = cfg["credentials"]["usernames"][username].get("role", "viewer")
    authenticator.logout(location="sidebar", key="logout_button")
    return AuthenticatedUser(username=username, name=name or username, role=role)
