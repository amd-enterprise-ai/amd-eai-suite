# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Robot Framework library for Keycloak authentication.

Supports authentication via three modes (auto-detected):

1. **Environment variables (legacy CI path)**: E2E_USERNAME, E2E_PASSWORD,
   KEYCLOAK_* config — password grant against the pre-staged e2e-user.

2. **User passthrough**: USER_PASSTHROUGH_ENABLED=true plus OIDC_ISSUER_URL,
   OIDC_CLIENT_ID, OIDC_USERNAME, and an offline refresh_token file path at
   SILODEV_OIDC_REFRESH_TOKEN_FILE. Acquires tokens via refresh-token grant so
   no password ever lands in the pod. Used by silodev remote runs that
   authenticate as the human invoking the test.

3. **Kubeconfig file (local)**: Extracts OIDC configuration from
   ~/.kube/config — password grant against the credentials baked into the
   user's exec credential.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import jwt
import requests
import urllib3
import yaml
from loguru import logger

# Suppress InsecureRequestWarning when making requests with verify=False.
# All dev/test clusters use self-signed certificates; this Python library cannot
# read Robot Framework variables, so SSL verification is always disabled here.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KubeconfigAuth:
    """Library for handling Keycloak authentication from environment or kubeconfig."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self):
        """Initialize the authentication library."""
        # Short-term cache to avoid hammering Keycloak with requests
        # but short enough that session refresh always gets fresh tokens
        self.auth_token = None
        self.token_timestamp = None
        self.token_ttl = 30  # 30 seconds - short cache to batch requests without risking expiration
        self.kubeconfig_path = Path.home() / ".kube" / "config"
        self._oidc_config = None

    def _get_credentials_from_env(self) -> dict[str, str] | None:
        """Try to get authentication credentials from environment variables."""
        required_vars = [
            "E2E_USERNAME",
            "E2E_PASSWORD",
            "KEYCLOAK_SERVER_URL",
            "KEYCLOAK_REALM",
            "KEYCLOAK_CLIENT_ID",
            "KEYCLOAK_CLIENT_SECRET",
        ]

        if all(os.environ.get(var) for var in required_vars):
            server_url = os.environ["KEYCLOAK_SERVER_URL"]
            realm = os.environ["KEYCLOAK_REALM"]

            logger.info(f"Using credentials from environment for user: {os.environ['E2E_USERNAME']}")
            return {
                "token_url": f"{server_url}/realms/{realm}/protocol/openid-connect/token",
                "client_id": os.environ["KEYCLOAK_CLIENT_ID"],
                "client_secret": os.environ["KEYCLOAK_CLIENT_SECRET"],
                "username": os.environ["E2E_USERNAME"],
                "password": os.environ["E2E_PASSWORD"],
            }

        return None

    def _get_credentials_from_passthrough(self) -> dict[str, str] | None:
        """Return refresh-token-grant credentials when running in passthrough mode.

        silodev mounts an offline refresh_token as a file (per-job Secret) and
        exports the OIDC config via env vars. We pull a fresh access_token on
        demand using that refresh_token — no password needed in the pod.
        """
        if os.environ.get("USER_PASSTHROUGH_ENABLED", "").lower() != "true":
            return None

        issuer = os.environ.get("OIDC_ISSUER_URL")
        client_id = os.environ.get("OIDC_CLIENT_ID")
        username = os.environ.get("OIDC_USERNAME")
        # Default to the path silodev mounts the per-job refresh-token Secret at,
        # so passthrough works even when the env var wasn't explicitly exported.
        rt_file = os.environ.get("SILODEV_OIDC_REFRESH_TOKEN_FILE", "/silodev-oidc/refresh_token")
        if not issuer or not client_id or not username or not rt_file:
            return None

        rt_path = Path(rt_file)
        if not rt_path.is_file():
            logger.warning(f"USER_PASSTHROUGH_ENABLED but refresh_token file not found: {rt_path}")
            return None
        try:
            refresh_token = rt_path.read_text().strip()
        except OSError as e:
            logger.warning(f"Failed to read refresh_token file {rt_path}: {e}")
            return None
        if not refresh_token:
            logger.warning(f"refresh_token file {rt_path} is empty")
            return None

        logger.info(f"Using user-passthrough credentials for: {username}")
        return {
            "token_url": f"{issuer.rstrip('/')}/protocol/openid-connect/token",
            "client_id": client_id,
            "client_secret": os.environ.get("OIDC_CLIENT_SECRET", ""),
            "username": username,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

    def _get_credentials_from_kubeconfig(self) -> dict[str, str]:
        """Extract OIDC credentials from kubeconfig file."""
        if not self.kubeconfig_path.exists():
            raise Exception(
                f"Kubeconfig file not found: {self.kubeconfig_path}. "
                f"This test requires kubectl to be configured with a valid context."
            )

        try:
            with open(self.kubeconfig_path) as f:
                config = yaml.safe_load(f)
                if not config:
                    raise Exception("Empty kubeconfig file")
        except yaml.YAMLError as e:
            raise Exception(f"Failed to parse kubeconfig: {e}")
        except Exception as e:
            raise Exception(f"Error reading kubeconfig: {e}")

        # Get current context
        current_context = config.get("current-context")
        if not current_context:
            raise Exception("No current kubectl context set. Please run 'kubectl config current-context' to verify.")

        logger.info(f"Using kubectl context: {current_context}")

        # Find the user configuration for current context
        contexts = config.get("contexts", [])
        user_name = None
        for context in contexts:
            if context.get("name") == current_context:
                user_name = context.get("context", {}).get("user")
                break

        if not user_name:
            raise Exception(f"No user defined for kubectl context: {current_context}")

        # Extract OIDC configuration from user
        users = config.get("users", [])
        for user in users:
            if user.get("name") == user_name:
                user_config = user.get("user", {})
                exec_config = user_config.get("exec", {})

                if exec_config.get("command") != "kubectl":
                    raise Exception(
                        f"Kubectl context '{current_context}' does not use OIDC authentication. "
                        f"Found command: {exec_config.get('command')}"
                    )

                args = exec_config.get("args", [])
                creds: dict[str, str | None] = {
                    "issuer_url": None,
                    "client_id": None,
                    "client_secret": None,
                    "username": None,
                    "password": None,
                }

                for arg in args:
                    if isinstance(arg, str):
                        if arg.startswith("--oidc-issuer-url="):
                            creds["issuer_url"] = arg.split("=", 1)[1]
                        elif arg.startswith("--oidc-client-id="):
                            creds["client_id"] = arg.split("=", 1)[1]
                        elif arg.startswith("--oidc-client-secret="):
                            creds["client_secret"] = arg.split("=", 1)[1]
                        elif arg.startswith("--username="):
                            creds["username"] = arg.split("=", 1)[1]
                        elif arg.startswith("--password="):
                            creds["password"] = arg.split("=", 1)[1]

                # Validate required fields
                if not creds["issuer_url"]:
                    raise Exception(f"No OIDC issuer URL found in kubectl config for user: {user_name}")
                if not creds["client_id"]:
                    raise Exception(f"No OIDC client ID found in kubectl config for user: {user_name}")
                if not creds["username"] or not creds["password"]:
                    raise Exception(f"No username/password found in kubectl config for user: {user_name}")

                issuer_url = creds["issuer_url"].rstrip("/")
                logger.info(f"Using kubeconfig credentials for user: {creds['username']}")

                return {
                    "token_url": f"{issuer_url}/protocol/openid-connect/token",
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"] or "",
                    "username": creds["username"],
                    "password": creds["password"],
                }

        raise Exception(f"User '{user_name}' not found in kubectl config")

    def _get_fresh_token(self) -> str:
        """Get a fresh token from Keycloak using password or refresh-token grant."""
        # Passthrough mode wins when active (offline refresh_token from silodev)
        creds = self._get_credentials_from_passthrough()

        # Otherwise, env vars (in-cluster CI path)
        if not creds:
            creds = self._get_credentials_from_env()

        # Fall back to kubeconfig (local dev)
        if not creds:
            creds = self._get_credentials_from_kubeconfig()

        # Build token request payload based on grant type.
        if creds.get("grant_type") == "refresh_token":
            payload = {
                "client_id": creds["client_id"],
                "grant_type": "refresh_token",
                "refresh_token": creds["refresh_token"],
            }
        else:
            payload = {
                "client_id": creds["client_id"],
                "grant_type": "password",
                "username": creds["username"],
                "password": creds["password"],
                "scope": "openid profile email",
            }
        # Public OIDC clients reject an empty client_secret (invalid_client); only
        # include it when one is configured.
        if creds.get("client_secret"):
            payload["client_secret"] = creds["client_secret"]

        try:
            logger.debug(f"Requesting token from: {creds['token_url']}")
            response = requests.post(
                creds["token_url"],
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
                verify=False,
            )

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                if access_token:
                    logger.info("Successfully retrieved token from Keycloak")
                    return access_token
                else:
                    raise Exception("No access token in Keycloak response")
            else:
                error_msg = f"Token request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
                except json.JSONDecodeError:
                    error_msg += f": {response.text}"
                raise Exception(error_msg)

        except requests.ConnectionError as e:
            raise Exception(f"Failed to connect to Keycloak at {creds['token_url']}: {e}")
        except requests.RequestException as e:
            raise Exception(f"Network error during token request: {e}")
        except Exception as e:
            if "Token request failed" in str(e) or "Failed to connect" in str(e):
                raise
            raise Exception(f"Unexpected error during token request: {e}")

    def get_authorization_token(self) -> str:
        """
        Get an authorization token with short-term caching.

        Uses a 30-second cache to avoid excessive Keycloak requests while
        ensuring session refresh (every 240s) always gets reasonably fresh tokens.
        This prevents rate-limiting from Keycloak.

        Returns:
            A valid JWT access token string.
        """
        current_time = datetime.now()

        # Check if we have a valid cached token
        if self.auth_token and self.token_timestamp:
            time_diff = (current_time - self.token_timestamp).total_seconds()
            if time_diff < self.token_ttl:
                logger.debug(f"Using cached token (age: {int(time_diff)}s)")
                return self.auth_token

        # Token doesn't exist or cache expired, get a new one
        logger.debug("Fetching fresh token from Keycloak")
        token = self._get_fresh_token()

        # Cache the token and timestamp
        self.auth_token = token
        self.token_timestamp = current_time

        return token

    def clear_token_cache(self):
        """
        Clear the cached token to force a refresh on next request.

        This is useful when user permissions have changed (e.g., after being
        added to a project) and a fresh token with updated claims is needed.
        """
        logger.info("Clearing cached token")
        self.auth_token = None
        self.token_timestamp = None

    def get_jwt_email_from_token(self, token):
        """
        Extract email from a JWT token.

        Args:
            token: JWT token string

        Returns:
            Email address from the token claims.
        """
        try:
            # Decode without verification (for testing purposes)
            claimset = jwt.decode(token, options={"verify_signature": False})
            email = claimset.get("email")
            if not email:
                raise Exception("No email found in JWT token")
            logger.debug(f"JWT token email: {email}")
            return email
        except Exception as e:
            logger.error(f"Failed to extract email from JWT token: {e}")
            raise Exception(f"Failed to extract email from JWT token: {e}")

    def validate_kubectl_config(self):
        """
        Validate that authentication credentials are properly configured.

        Tries each supported credential source in order: user passthrough,
        environment variables, then kubeconfig. Returns True for the first
        source that produces valid credentials.

        Raises:
            Exception: If configuration is invalid or missing required settings.
        """
        try:
            # User passthrough (silodev --user-passthrough)
            creds = self._get_credentials_from_passthrough()
            if creds:
                logger.info("User-passthrough credentials validated successfully")
                return True

            # Environment variables (legacy in-cluster path)
            creds = self._get_credentials_from_env()
            if creds:
                logger.info("Environment variable credentials validated successfully")
                return True

            # Fall back to kubeconfig (local dev)
            creds = self._get_credentials_from_kubeconfig()
            logger.info("Kubeconfig credentials validated successfully")
            return True
        except Exception as e:
            logger.error(f"Authentication configuration validation failed: {e}")
            raise
