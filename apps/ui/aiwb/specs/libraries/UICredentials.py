# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Robot Framework library that exposes OIDC credentials for browser-based login.

Delegates to KubeconfigAuth for credential extraction and exposes
username/password as separate keywords for use in Browser Library login flows.
"""

import importlib.util
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
    """Provides UI login credentials extracted from kubeconfig OIDC configuration."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self):
        self._auth = KubeconfigAuth()

    def _get_credentials(self) -> dict[str, str]:
        """Get credentials from environment or kubeconfig.

        Uses KubeconfigAuth private methods directly because it has no public
        API for raw credential extraction (its public methods return RF variables).
        Coupled to KubeconfigAuth internals — update if that class is refactored.
        """
        creds = self._auth._get_credentials_from_env()
        if not creds:
            creds = self._auth._get_credentials_from_kubeconfig()
        return creds

    def get_ui_username(self) -> str:
        """Get the OIDC username for browser login."""
        username = self._get_credentials().get("username")
        if not username:
            raise ValueError("No username found in credentials")
        return username

    def get_ui_password(self) -> str:
        """Get the OIDC password for browser login."""
        password = self._get_credentials().get("password")
        if not password:
            raise ValueError("No password found in credentials")
        return password
