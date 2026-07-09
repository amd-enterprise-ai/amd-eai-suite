# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Shared team-member credential resolution for E2E tests.

Both API tests (token exchange) and UI tests (raw username/password for
browser login) need the same team-member identity. The convention is:

* If E2E_TEAM_MEMBER_USERNAME / E2E_TEAM_MEMBER_PASSWORD are set, use them.
* Otherwise derive from the admin account by replacing the local part with
  ``teammember`` and reusing the admin password (common in dev/test envs).

Not every target environment provisions a team-member account in Keycloak.
``is_provisioned`` performs one cheap password-grant against Keycloak so
RBAC suites can skip cleanly with a clear reason instead of failing in
suite setup.

This library is intentionally framework-agnostic Python so it can be reused
by both Robot Framework wrappers (APICredentials, UICredentials) and any
future direct caller. Keep all team-member derivation logic here -- the
wrappers should only adapt the API to Robot's keyword conventions.
"""

import importlib.util
import logging
import os
import sys
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


def _load_kubeconfig_auth():
    """Import KubeconfigAuth from the same directory regardless of pythonpath setup."""
    kca_path = Path(__file__).resolve().parent / "KubeconfigAuth.py"
    if not kca_path.exists():
        raise ImportError(f"KubeconfigAuth not found at expected path: {kca_path}")
    spec = importlib.util.spec_from_file_location("KubeconfigAuth", kca_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create module spec from {kca_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("KubeconfigAuth", module)
    spec.loader.exec_module(module)
    return module.KubeconfigAuth


KubeconfigAuth = _load_kubeconfig_auth()


class TeamMemberNotProvisioned(Exception):
    """Raised when the team-member account does not exist on the target environment.

    Carries a human-readable reason suitable for a Robot Framework Skip message.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class TeamMemberCredentials:
    """Single source of truth for team-member credential resolution.

    Used by both APICredentials (API token exchange) and UICredentials
    (browser login). Encapsulates derivation rules and provisioning
    detection so RBAC suites can skip cleanly when the team member
    user is absent from Keycloak.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    # Keycloak error codes that mean "the team-member account is not usable",
    # not "the network is broken". Anything else propagates so suite setup
    # fails loudly rather than silently skipping on transient infra issues.
    _NOT_PROVISIONED_ERRORS = frozenset({"invalid_grant"})

    def __init__(self):
        self._auth = KubeconfigAuth()
        self._cached: dict[str, str] | None = None
        self._provisioned: bool | None = None
        self._not_provisioned_reason: str | None = None

    # --- Admin credential access (delegates to KubeconfigAuth) ---

    def _get_admin_credentials(self) -> dict[str, str]:
        creds = self._auth._get_credentials_from_env()
        if not creds:
            try:
                creds = self._auth._get_credentials_from_kubeconfig()
            except Exception as exc:
                # In passthrough mode the kubeconfig exec plugin carries no password,
                # so RBAC suites can't derive a team member — skip cleanly. In any
                # other mode a kubeconfig error is a genuine misconfiguration (missing
                # file, wrong context, parse error); re-raise so setup fails loudly.
                if os.environ.get("USER_PASSTHROUGH_ENABLED", "").lower() == "true":
                    raise TeamMemberNotProvisioned(
                        f"Cannot derive team member credentials in passthrough mode: {exc}. "
                        "Set E2E_TEAM_MEMBER_USERNAME and E2E_TEAM_MEMBER_PASSWORD to enable "
                        "RBAC tests in this environment."
                    ) from exc
                raise
        return creds

    # --- Team member credential resolution ---

    def get_credentials(self) -> dict[str, str]:
        """Return the full team-member credential bundle.

        Includes Keycloak endpoint and client info so callers can perform
        token exchange. Cached for the lifetime of the instance.
        """
        if self._cached is None:
            admin_creds = self._get_admin_credentials()
            username = self._resolve_username(admin_creds)
            password = os.environ.get("E2E_TEAM_MEMBER_PASSWORD") or admin_creds["password"]
            self._cached = {
                "token_url": admin_creds["token_url"],
                "client_id": admin_creds["client_id"],
                "client_secret": admin_creds.get("client_secret", ""),
                "username": username,
                "password": password,
            }
        return self._cached

    @staticmethod
    def _resolve_username(admin_creds: dict[str, str]) -> str:
        env_username = os.environ.get("E2E_TEAM_MEMBER_USERNAME")
        if env_username:
            return env_username
        admin_username = admin_creds["username"]
        domain = admin_username.split("@")[1] if "@" in admin_username else ""
        if not domain:
            raise ValueError(
                "Cannot derive team member username: admin username has no domain. "
                "Set E2E_TEAM_MEMBER_USERNAME environment variable."
            )
        return f"teammember@{domain}"

    def get_username(self) -> str:
        return self.get_credentials()["username"]

    def get_password(self) -> str:
        return self.get_credentials()["password"]

    # --- Provisioning detection ---

    def is_provisioned(self) -> bool:
        """Check whether the team-member account exists in the target Keycloak.

        Performs one password-grant and caches the result. Returns False only
        for authentication errors (account missing, password wrong, account
        disabled) -- network and configuration errors propagate so they are
        not silently treated as "skip the suite".
        """
        if self._provisioned is None:
            try:
                self._fetch_token()
                self._provisioned = True
            except TeamMemberNotProvisioned as exc:
                self._provisioned = False
                self._not_provisioned_reason = exc.reason
        return self._provisioned

    def not_provisioned_reason(self) -> str:
        """Return a human-readable reason for skipping when not provisioned.

        Falls back to a generic message if ``is_provisioned`` has not been
        called or returned True.
        """
        return self._not_provisioned_reason or (
            f"Team member account '{self.get_username()}' is not provisioned in this environment"
        )

    def get_api_token(self) -> str:
        """Get a fresh API access token for the team-member user.

        Returns a fresh token each time (no caching) to ensure group
        claims are current. Raises a generic Exception with detail on
        non-auth failures, and TeamMemberNotProvisioned on auth failures
        so callers can distinguish "account missing" from "Keycloak down".
        """
        return self._fetch_token()

    # --- Internal ---

    def _fetch_token(self) -> str:
        creds = self.get_credentials()
        payload = {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "grant_type": "password",
            "username": creds["username"],
            "password": creds["password"],
            "scope": "openid profile email",
        }
        response = requests.post(
            creds["token_url"],
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
            verify=False,
        )

        if response.status_code == 200:
            access_token = response.json().get("access_token")
            if not access_token:
                raise Exception("No access_token in team member Keycloak response")
            return access_token

        error_code, error_description = self._parse_keycloak_error(response)

        if error_code in self._NOT_PROVISIONED_ERRORS:
            reason = (
                f"Team member account '{creds['username']}' not usable on this environment "
                f"(Keycloak: {error_code} -- {error_description})"
            )
            logger.info(reason)
            raise TeamMemberNotProvisioned(reason)

        raise Exception(
            f"Team member token request failed with status {response.status_code}: "
            f"{error_code or 'unknown_error'} -- {error_description or response.text}"
        )

    @staticmethod
    def _parse_keycloak_error(response: requests.Response) -> tuple[str | None, str | None]:
        try:
            data = response.json()
            return data.get("error"), data.get("error_description")
        except Exception:
            return None, response.text

    # --- Robot Framework convenience keywords ---
    # Exposed so a .robot file can import this library directly via:
    #   Library    TeamMemberCredentials.py
    # without needing the per-app wrappers when only the skip check is needed.

    def team_member_is_provisioned(self) -> bool:
        return self.is_provisioned()

    def team_member_skip_reason(self) -> str:
        return self.not_provisioned_reason()
