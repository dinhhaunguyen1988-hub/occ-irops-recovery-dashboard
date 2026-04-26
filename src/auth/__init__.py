"""Authentication + role-based access control for the dashboard.

Sprint 5 ships with a YAML-file-backed implementation
(``streamlit-authenticator``) for the pilot phase. The module wraps it
behind a small interface so a future SSO / OIDC migration only changes
this file, not the rest of the app.

Roles
-----
- ``dm``      Duty manager: full access (run analysis, edit settings,
              view audit log, download exports).
- ``viewer``  Read-only: can see analysis results but cannot edit
              settings or trigger admin actions.

Auth bypass for local dev / CI
------------------------------
Setting the environment variable ``OCC_AUTH_DISABLED=1`` makes
:func:`require_login` return a hard-coded ``"localdev"`` user with role
``dm``. Production deployments must leave this unset.
"""

from src.auth.users import (
    AuthBypassedUser,
    AuthenticatedUser,
    Role,
    is_auth_disabled,
    load_users_config,
    require_login,
    role_can_edit_settings,
    role_can_view_audit,
)

__all__ = [
    "AuthBypassedUser",
    "AuthenticatedUser",
    "Role",
    "is_auth_disabled",
    "load_users_config",
    "require_login",
    "role_can_edit_settings",
    "role_can_view_audit",
]
