# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Robot Framework library that exposes OIDC credentials for browser-based login.

Supports multiple user roles for RBAC testing. Admin credentials come from
kubeconfig, team member credentials from environment variables or defaults.
"""

import importlib.util
import os
import sys
from pathlib import Path

# KubeconfigAuth lives in the shared testing libraries, which is on the RF
# pythonpath but shadowed by the local libraries/ package. Import it directly.
_testing = Path(__file__).resolve().parents[5] / "testing"
_kca_path = _testing / "libraries" / "KubeconfigAuth.py"
if not _kca_path.exists():
    raise ImportError(f"KubeconfigAuth not found at expected path: {_kca_path}")
_spec = importlib.util.spec_from_file_location("KubeconfigAuth", _kca_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Failed to create module spec from {_kca_path}")
_module = importlib.util.module_from_spec(_spec)
sys.modules["KubeconfigAuth"] = _module
_spec.loader.exec_module(_module)
KubeconfigAuth = _module.KubeconfigAuth


class UICredentials:
    """Provides UI login credentials for multiple user roles.

    Admin credentials are extracted from kubeconfig OIDC configuration.
    Team member credentials use a convention-based default (same domain,
    'teammember' username, same password) or can be set via environment
    variables E2E_TEAM_MEMBER_USERNAME and E2E_TEAM_MEMBER_PASSWORD.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self):
        self._auth = KubeconfigAuth()

    def _get_credentials(self) -> dict[str, str]:
        """Get admin credentials from environment or kubeconfig.

        Uses KubeconfigAuth private methods directly because it has no public
        API for raw credential extraction (its public methods return RF variables).
        Coupled to KubeconfigAuth internals -- update if that class is refactored.
        """
        creds = self._auth._get_credentials_from_env()
        if not creds:
            creds = self._auth._get_credentials_from_kubeconfig()
        return creds

    def get_ui_username(self) -> str:
        """Get the admin OIDC username for browser login."""
        username = self._get_credentials().get("username")
        if not username:
            raise ValueError("No username found in credentials")
        return username

    def get_ui_password(self) -> str:
        """Get the admin OIDC password for browser login."""
        password = self._get_credentials().get("password")
        if not password:
            raise ValueError("No password found in credentials")
        return password

    def get_team_member_username(self) -> str:
        """Get the team member username for browser login.

        Uses E2E_TEAM_MEMBER_USERNAME env var if set, otherwise derives from
        admin username by replacing the local part with 'teammember'.
        """
        env_username = os.environ.get("E2E_TEAM_MEMBER_USERNAME")
        if env_username:
            return env_username

        admin_username = self.get_ui_username()
        domain = admin_username.split("@")[1] if "@" in admin_username else ""
        if not domain:
            raise ValueError(
                "Cannot derive team member username: admin username has no domain. "
                "Set E2E_TEAM_MEMBER_USERNAME environment variable."
            )
        return f"teammember@{domain}"

    def get_team_member_password(self) -> str:
        """Get the team member password for browser login.

        Uses E2E_TEAM_MEMBER_PASSWORD env var if set, otherwise uses the same
        password as the admin user (common in dev/test environments).
        """
        env_password = os.environ.get("E2E_TEAM_MEMBER_PASSWORD")
        if env_password:
            return env_password
        return self.get_ui_password()
