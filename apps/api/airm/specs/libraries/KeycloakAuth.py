# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os
from datetime import datetime

import jwt
import requests
from jwt.exceptions import InvalidTokenError
from loguru import logger


def _decode_jwt_token(token: str) -> dict:
    """
    Decode a JWT token without verification (for testing/development).
    In production, you should verify the token properly.
    """
    try:
        # Decode without verification for simplicity
        # In production, you'd want to verify with the public key
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except InvalidTokenError as e:
        raise Exception(f"Invalid JWT token: {e}")


class KeycloakAuth:
    """Library for handling Keycloak authentication in Kubernetes environment."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self):
        self.auth_token = None
        self.token_timestamp = None
        self.token_ttl = 3600  # Token time-to-live in seconds (1 hour)

    def get_service_account_token(self, token_url=None):
        """Get a service account token from Keycloak using the CI client secret.

        Args:
            token_url: Full token URL. If not provided, will try to get from environment/ConfigMap.
        """
        # Get the token URL from parameter, environment, or ConfigMap
        if not token_url:
            token_url = self._get_token_url()

        logger.info(f"Getting new service account token from {token_url}")

        # Get the client secret from environment or secret mount
        client_secret = self._get_client_secret()

        # Prepare the request
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "client_id": "ci-service-account",
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }

        try:
            response = requests.post(token_url, headers=headers, data=payload)
            response.raise_for_status()

            token_data = response.json()
            return token_data["access_token"]
        except requests.ConnectionError as e:
            error_msg = f"Failed to connect to Keycloak at {token_url}. Make sure Keycloak is running and accessible."
            logger.error(error_msg)
            logger.error(f"Connection error details: {str(e)}")
            raise Exception(error_msg)
        except requests.HTTPError as e:
            error_msg = f"HTTP error when getting auth token from {token_url}"
            logger.error(error_msg)
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            raise Exception(f"{error_msg}: {str(e)}")
        except requests.RequestException as e:
            error_msg = f"Request error when getting auth token from {token_url}"
            logger.error(error_msg)
            logger.error(f"Request error details: {str(e)}")
            raise Exception(f"{error_msg}: {str(e)}")

    def _get_token_url(self):
        """Get the Keycloak token URL from environment variables."""
        # Get server URL and realm from environment variables
        server_url = os.environ.get("KEYCLOAK_SERVER_URL")
        realm = os.environ.get("KEYCLOAK_REALM")

        if not server_url or not realm:
            missing = []
            if not server_url:
                missing.append("KEYCLOAK_SERVER_URL")
            if not realm:
                missing.append("KEYCLOAK_REALM")
            raise Exception(f"Missing Keycloak configuration: {', '.join(missing)} environment variables not set")

        # Construct the token URL
        token_url = f"{server_url}/realms/{realm}/protocol/openid-connect/token"
        logger.info(f"Constructed Keycloak token URL: {token_url}")
        return token_url

    def _get_client_secret(self):
        """Get the client secret from the appropriate location."""
        # Check environment variable first
        client_secret = os.environ.get("CI_CLIENT_SECRET")
        if client_secret:
            return client_secret

        # Check for mounted secret in Kubernetes
        secret_path = "/etc/secrets/ci-client-secret"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, encoding="utf-8") as f:
                    return f.read().strip()
            except UnicodeDecodeError as e:
                raise Exception(
                    f"Failed to read CI_CLIENT_SECRET from {secret_path} due to encoding error. "
                    f"The secret file may be corrupted or incorrectly encoded: {e}"
                )

        raise Exception("CI_CLIENT_SECRET not found in environment variables or secrets mount")

    def get_authorization_token(self, token_url=None):
        """
        Robot Framework keyword to get an authorization token with caching.

        Args:
            token_url: Optional full token URL. If not provided, will get from environment/ConfigMap.

        Returns the token as a string.
        """
        current_time = datetime.now()

        # Check if we have a valid cached token
        if self.auth_token and self.token_timestamp:
            time_diff = (current_time - self.token_timestamp).total_seconds()
            # If token is still valid (less than TOKEN_TTL seconds old), return it
            if time_diff < self.token_ttl:
                logger.info("Using cached auth token")
                return self.auth_token

        # Token doesn't exist or is expired, get a new one
        logger.info("Getting new auth token from Keycloak")
        token = self.get_service_account_token(token_url)

        # Cache the token and timestamp
        self.auth_token = token
        self.token_timestamp = current_time
        logger.info("Using new auth token")

        return token

    def get_jwt_email_from_token(self, token):
        """
        Robot Framework keyword to extract email from a provided JWT token.
        Returns the email from the token claims.
        """
        try:
            # Decode the JWT token to get claimset
            claimset = _decode_jwt_token(token)

            # Extract email from claimset
            email = claimset.get("email")
            if not email:
                raise Exception("No email found in JWT token claimset")

            logger.info(f"JWT token email: {email}")
            return email

        except Exception as e:
            logger.error(f"Failed to extract email from JWT token: {e}")
            raise Exception(f"Failed to extract email from JWT token: {e}")
