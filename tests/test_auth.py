"""Tests for the auth module (yaml-loading, role helpers, bypass)."""

from __future__ import annotations

import os
from textwrap import dedent

import pytest

from src.auth import (
    AuthBypassedUser,
    is_auth_disabled,
    load_users_config,
    require_login,
    role_can_edit_settings,
    role_can_view_audit,
)


@pytest.fixture
def clear_env(monkeypatch):
    monkeypatch.delenv("OCC_AUTH_DISABLED", raising=False)
    yield


def test_role_can_edit_settings_only_for_dm() -> None:
    assert role_can_edit_settings("dm")
    assert not role_can_edit_settings("viewer")


def test_role_can_view_audit_only_for_dm() -> None:
    assert role_can_view_audit("dm")
    assert not role_can_view_audit("viewer")


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "YES"])
def test_is_auth_disabled_truthy_values(monkeypatch, val) -> None:
    monkeypatch.setenv("OCC_AUTH_DISABLED", val)
    assert is_auth_disabled()


@pytest.mark.parametrize("val", ["", "0", "false", "no"])
def test_is_auth_disabled_falsy_values(monkeypatch, val) -> None:
    monkeypatch.setenv("OCC_AUTH_DISABLED", val)
    assert not is_auth_disabled()


def test_is_auth_disabled_unset_is_false(monkeypatch) -> None:
    monkeypatch.delenv("OCC_AUTH_DISABLED", raising=False)
    assert not is_auth_disabled()


def test_require_login_returns_bypass_user_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OCC_AUTH_DISABLED", "1")
    user = require_login(users_path="/nonexistent/users.yaml")
    assert isinstance(user, AuthBypassedUser)
    assert user.role == "dm"


def test_load_users_config_round_trips(tmp_path, clear_env) -> None:
    yaml_text = dedent(
        """
        cookie:
          name: occ_irops_auth
          key: abc123
          expiry_days: 1
        credentials:
          usernames:
            dm1:
              name: DM One
              password: $2b$12$hashplaceholder
              role: dm
        """
    ).strip()
    p = tmp_path / "users.yaml"
    p.write_text(yaml_text)
    cfg = load_users_config(p)
    assert cfg["cookie"]["name"] == "occ_irops_auth"
    assert cfg["credentials"]["usernames"]["dm1"]["role"] == "dm"


def test_load_users_config_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_users_config(tmp_path / "no_such.yaml")


def test_load_users_config_rejects_invalid_role(tmp_path) -> None:
    yaml_text = dedent(
        """
        cookie: {name: x, key: y, expiry_days: 1}
        credentials:
          usernames:
            user1:
              name: User One
              password: hash
              role: superuser
        """
    ).strip()
    p = tmp_path / "users.yaml"
    p.write_text(yaml_text)
    with pytest.raises(ValueError, match="invalid role"):
        load_users_config(p)


def test_load_users_config_rejects_missing_password(tmp_path) -> None:
    yaml_text = dedent(
        """
        cookie: {name: x, key: y, expiry_days: 1}
        credentials:
          usernames:
            user1:
              name: User One
              role: dm
        """
    ).strip()
    p = tmp_path / "users.yaml"
    p.write_text(yaml_text)
    with pytest.raises(ValueError, match="missing 'password'"):
        load_users_config(p)


def test_load_users_config_rejects_empty_credentials(tmp_path) -> None:
    yaml_text = dedent(
        """
        cookie: {name: x, key: y, expiry_days: 1}
        credentials:
          usernames: {}
        """
    ).strip()
    p = tmp_path / "users.yaml"
    p.write_text(yaml_text)
    with pytest.raises(ValueError, match="at least one user"):
        load_users_config(p)


def test_clear_env_fixture_used():
    """Sanity check that the fixture can be referenced (no real assertion)."""
    # Side-effect test ensures monkeypatch teardown leaves env clean for parallel
    # test runs.
    assert os.environ.get("OCC_AUTH_DISABLED") in (None, "")
