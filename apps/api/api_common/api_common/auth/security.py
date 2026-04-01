# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Shared Keycloak JWT authentication.

Common JWT utilities used by both AIRM and AIWB.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OpenIdConnect
from jwcrypto.jwt import JWTExpired
from keycloak import KeycloakOpenID
from loguru import logger

from .config import DISABLE_JWT_VALIDATION, KEYCLOAK_INTERNAL_URL, KEYCLOAK_REALM, OPENID_CONFIGURATION_URL

KEYCLOAK_OPENID = KeycloakOpenID(server_url=KEYCLOAK_INTERNAL_URL, client_id=None, realm_name=KEYCLOAK_REALM)


class OpenIdAuthorization(OpenIdConnect):
    """Return 401 with correct headers instead of 403 when auth is missing."""

    async def __call__(self, request: Request) -> str | None:
        authorization = request.headers.get("Authorization")
        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return authorization


BearerToken = OpenIdAuthorization(openIdConnectUrl=OPENID_CONFIGURATION_URL, auto_error=True)


def auth_token_claimset(authorization: str = Depends(BearerToken)) -> dict:
    """Parse and verify JWT token from Authorization header."""
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No Authorization header")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token scheme. Please include Bearer in Authorization header.",
            )
        decoded = KEYCLOAK_OPENID.decode_token(token, validate=not DISABLE_JWT_VALIDATION)
        logger.debug(f"Decoded token claims: email={decoded.get('email')}, groups={decoded.get('groups')}")
        return decoded
    except HTTPException:
        raise
    except JWTExpired:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception as exc:
        logger.exception("Exception while reading token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Validation of token failed: {exc}")


def get_user_email(claimset: dict = Depends(auth_token_claimset)) -> str:
    """Extract user email from JWT token."""
    email = claimset.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No user email in token")
    return email


def get_user_groups(claimset: dict = Depends(auth_token_claimset)) -> list[str]:
    """Extract group names from JWT token."""
    groups = claimset.get("groups", [])
    return groups if isinstance(groups, list) else []
