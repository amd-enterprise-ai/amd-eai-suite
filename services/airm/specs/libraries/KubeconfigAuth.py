# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Robot Framework library for Keycloak authentication using kubectl config.

This library extracts OIDC configuration from the kubectl configuration file
(~/.kube/config) and uses it to authenticate with Keycloak, retrieving fresh
tokens automatically without needing environment variables.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import jwt
import requests
import yaml
from loguru import logger


class KubeconfigAuth:
    """Library for handling Keycloak authentication using kubectl config."""

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
        self._keycloak_client = None

    def _load_kubeconfig(self) -> dict[str, Any]:
        """Load and parse the kubeconfig file."""
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
                return config
        except yaml.YAMLError as e:
            raise Exception(f"Failed to parse kubeconfig: {e}")
        except Exception as e:
            raise Exception(f"Error reading kubeconfig: {e}")

    def _get_oidc_config(self) -> dict[str, str | None]:
        """Extract OIDC configuration from current kubectl context."""
        if self._oidc_config:
            return self._oidc_config

        config = self._load_kubeconfig()

        # Get current context
        current_context = config.get("current-context")
        if not current_context:
            raise Exception("No current kubectl context set. Please run 'kubectl config current-context' to verify.")

        logger.info(f"Using kubectl context: {current_context}")

        # Find the context configuration
        contexts = config.get("contexts", [])
        user_name = None
        for context in contexts:
            if context.get("name") == current_context:
                user_name = context.get("context", {}).get("user")
                break

        if not user_name:
            raise Exception(f"No user defined for kubectl context: {current_context}")

        # Find the user configuration
        users = config.get("users", [])
        for user in users:
            if user.get("name") == user_name:
                user_config = user.get("user", {})
                exec_config = user_config.get("exec", {})

                # Check if this is an OIDC configuration
                if exec_config.get("command") != "kubectl":
                    raise Exception(
                        f"Kubectl context '{current_context}' does not use OIDC authentication. "
                        f"Found command: {exec_config.get('command')}"
                    )

                args = exec_config.get("args", [])

                # Parse OIDC arguments
                oidc_config: dict[str, str | None] = {
                    "issuer_url": None,
                    "client_id": None,
                    "client_secret": None,
                    "username": None,
                    "password": None,
                    "grant_type": None,
                }

                for arg in args:
                    if isinstance(arg, str):
                        if arg.startswith("--oidc-issuer-url="):
                            oidc_config["issuer_url"] = arg.split("=", 1)[1]
                        elif arg.startswith("--oidc-client-id="):
                            oidc_config["client_id"] = arg.split("=", 1)[1]
                        elif arg.startswith("--oidc-client-secret="):
                            oidc_config["client_secret"] = arg.split("=", 1)[1]
                        elif arg.startswith("--username="):
                            oidc_config["username"] = arg.split("=", 1)[1]
                        elif arg.startswith("--password="):
                            oidc_config["password"] = arg.split("=", 1)[1]
                        elif arg.startswith("--grant-type="):
                            oidc_config["grant_type"] = arg.split("=", 1)[1]

                # Validate configuration
                if not oidc_config["issuer_url"]:
                    raise Exception(f"No OIDC issuer URL found in kubectl config for user: {user_name}")
                if not oidc_config["client_id"]:
                    raise Exception(f"No OIDC client ID found in kubectl config for user: {user_name}")

                # Determine grant type
                if not oidc_config["grant_type"]:
                    if oidc_config["username"] and oidc_config["password"]:
                        oidc_config["grant_type"] = "password"
                    elif oidc_config["client_secret"]:
                        oidc_config["grant_type"] = "client_credentials"
                    else:
                        raise Exception("Cannot determine grant type from kubectl config")

                logger.info(
                    f"OIDC config extracted - issuer: {oidc_config['issuer_url']}, "
                    f"client_id: {oidc_config['client_id']}, "
                    f"grant_type: {oidc_config['grant_type']}"
                )

                self._oidc_config = oidc_config
                return oidc_config

        raise Exception(f"User '{user_name}' not found in kubectl config")

    def _get_fresh_token(self) -> str:
        """Get a fresh token from Keycloak using kubectl config credentials."""
        oidc_config = self._get_oidc_config()

        # Construct token endpoint
        issuer_url_value = oidc_config["issuer_url"]
        assert issuer_url_value is not None, "issuer_url should have been validated in _get_oidc_config"
        issuer_url = issuer_url_value.rstrip("/")
        token_endpoint = f"{issuer_url}/protocol/openid-connect/token"

        # Prepare request based on grant type
        if oidc_config["grant_type"] == "password":
            if not oidc_config["username"] or not oidc_config["password"]:
                raise Exception("Username and password required for password grant")

            data = {
                "client_id": oidc_config["client_id"],
                "grant_type": "password",
                "username": oidc_config["username"],
                "password": oidc_config["password"],
                "scope": "openid profile email organization",
            }

            if oidc_config["client_secret"]:
                data["client_secret"] = oidc_config["client_secret"]

            logger.info(f"Authenticating as user: {oidc_config['username']}")

        elif oidc_config["grant_type"] == "client_credentials":
            if not oidc_config["client_secret"]:
                raise Exception("Client secret required for client credentials grant")

            data = {
                "client_id": oidc_config["client_id"],
                "client_secret": oidc_config["client_secret"],
                "grant_type": "client_credentials",
                "scope": "openid profile email organization",
            }

            logger.info(f"Authenticating with client credentials: {oidc_config['client_id']}")
        else:
            raise Exception(f"Unsupported grant type: {oidc_config['grant_type']}")

        # Make token request
        try:
            logger.debug(f"Requesting token from: {token_endpoint}")
            response = requests.post(
                token_endpoint, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                if access_token:
                    logger.info("Successfully retrieved fresh token from Keycloak")
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

        except requests.RequestException as e:
            raise Exception(f"Network error during token request: {e}")
        except Exception as e:
            if "Token request failed" in str(e):
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
        Validate that kubectl is properly configured for OIDC authentication.

        This method checks that:
        1. kubectl config exists
        2. A current context is set
        3. The context uses OIDC authentication
        4. Required OIDC parameters are present

        Raises:
            Exception: If kubectl config is invalid or missing required OIDC settings.
        """
        try:
            oidc_config = self._get_oidc_config()
            logger.info("Kubectl config validated successfully")
            return True
        except Exception as e:
            logger.error(f"Kubectl config validation failed: {e}")
            raise
