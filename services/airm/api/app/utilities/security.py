# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OpenIdConnect
from keycloak import KeycloakAdmin, KeycloakOpenID
from loguru import logger

from ..organizations.repository import get_organization_by_keycloak_org_id
from ..projects.models import Project
from ..projects.repository import get_projects_by_names_in_organization
from ..users.models import User
from ..users.repository import create_user_in_organization, get_user_by_email, update_last_active_at
from ..utilities.database import get_session
from .enums import Roles
from .keycloak_admin import get_kc_admin
from .keycloak_admin import get_user as get_keycloak_user

KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "airm")
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
OPENID_CONFIGURATION_URL = os.getenv(
    "OPENID_CONFIGURATION_URL", f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
)
KEYCLOAK_PUBLIC_OPENID = KeycloakOpenID(server_url=KEYCLOAK_SERVER_URL, client_id=None, realm_name=KEYCLOAK_REALM)

DISABLE_JWT_VALIDATION = os.getenv("DISABLE_JWT_VALIDATION", "true") == "true"


class OpenIdAuthorization(OpenIdConnect):
    """
    Modified OpenIdConnect dependable class to return 401 with correct headers instead of 403 in case of missing auth.
    """

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


# Dependable that requires a JWT Bearer token to be set and provides docs for how to get
# the token with Keycloak. Will raise an exception if token not provided. Returns the
# token as a string in the form of "Bearer {token}"
BearerToken = OpenIdAuthorization(openIdConnectUrl=OPENID_CONFIGURATION_URL, auto_error=True)


def auth_token_claimset(authorization: str = Depends(BearerToken)):
    """
    Parses and verifies the JWT token from the Authorization header.

    This function extracts the JWT token from the Authorization header, verifies it, and returns the token's payload.
    If the Authorization header is missing, invalid, or if the token cannot be parsed, an HTTPException is raised.

    Args:
        authorization (Optional[str]): Authorization header that consist of schema + JWT token.

    Returns:
        dict: The payload of the verified JWT token.

    Raises:
        HTTPException: If the Authorization header is missing, the token scheme is invalid,
                       or if an error occurs during token parsing.
    """
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No Authorization header")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token scheme. Please include Bearer in Authorization header.",
            )
        return KEYCLOAK_PUBLIC_OPENID.decode_token(token, validate=not DISABLE_JWT_VALIDATION)
    except Exception as exc:
        logger.exception("Exception while reading token", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Validation of token failed: {exc}")


def is_user_in_role(claimset: dict, role: Roles) -> bool:
    """
    Check if the user has the specified role in the token.
    """
    return role.value in claimset.get("realm_access", {}).get("roles", [])


def ensure_platform_administrator(claimset: dict = Depends(auth_token_claimset)):
    """
    Dependable that checks if the token has the special admin role.
    """
    if not is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Missing required role: Platform Administrator"
        )


def ensure_super_administrator(claimset: dict = Depends(auth_token_claimset)):
    """
    Dependable that checks if the token has the super admin role.
    """
    if not is_user_in_role(claimset, Roles.SUPER_ADMINISTRATOR):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing required role: Super Administrator")


def __get_organization_id_from_claimset(claimset: dict) -> str | None:
    organization_claim = claimset.get("organization", {})

    # Handle dictionary format only: {'org_name': {'id': 'uuid'}}
    if isinstance(organization_claim, dict):
        for claim_organization in organization_claim.values():
            if isinstance(claim_organization, dict) and claim_organization.get("id") is not None:
                return claim_organization.get("id")

    return None


def __get_group_names_from_claimset(claimset: dict) -> list[str]:
    """
    Extract Keycloak group names from the JWT token claimset.

    Args:
        claimset: JWT token payload containing group information

    Returns:
        List of group names that the user is a member of
    """
    groups = claimset.get("groups", [])
    if isinstance(groups, list):
        return groups
    return []


async def get_user_organization(claimset: dict = Depends(auth_token_claimset), session=Depends(get_session)):
    """
    Dependable that retrieves the organization of the user from the database depending on the id in the token.
    This is the relevant part of the token:
    {
        "organization": {
            "org_name": {
                "id": "1b48c849-4ee8-49d4-b57b-19092a8f88c5"
            }
        }
    }
    """
    organization_id = __get_organization_id_from_claimset(claimset)
    if not organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization claim in token")
    organization = await get_organization_by_keycloak_org_id(session, organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return organization


def get_user_email(claimset: dict = Depends(auth_token_claimset)) -> str:
    """
    Dependable that retrieves the user email from the token.
    """
    email = claimset.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No user email in token")
    return email


async def get_user(email: str = Depends(get_user_email), session=Depends(get_session)) -> User:
    """
    Dependable that retrieves the user object from the database
    """
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found in the system")
    return user


async def create_logged_in_user_in_system(
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    claimset: dict = Depends(auth_token_claimset),
    session=Depends(get_session),
):
    """
    Dependable that checks if the logged in user exists in the database, and if not, creates it.
    This is to account for cases where users are federated from some IDP to keycloak directly
    """
    email = claimset.get("email")
    keycloak_user_id = claimset.get("sub")
    organization_id = __get_organization_id_from_claimset(claimset)
    if not organization_id or not email or not keycloak_user_id:
        return

    # User already exists, do nothing
    existing_user = await get_user_by_email(session, email)

    if existing_user:
        return

    try:
        organization = await get_organization_by_keycloak_org_id(session, organization_id)
        # Organization does not exist, do nothing
        if not organization:
            return
        keycloak_user = await get_keycloak_user(kc_admin=kc_admin, user_id=keycloak_user_id)
        # User has been deleted in keycloak but token is still valid, do nothing
        if not keycloak_user:
            return

        # Create a user entry in the database
        logger.info(f"User {email} does not exist in the database, creating it")
        await create_user_in_organization(session, organization.id, email, keycloak_user_id, "federated")
        await session.commit()
    except Exception as e:
        # If there is an exception, don't fail the request, if something downstream in this call is dependent on the
        # user existing, it will fail.
        # This also accounts for cases where there are two concurrent requests to create the same user
        # and one succeeds
        logger.warning(f"Failed to create user in database: {e}")


async def track_user_activity_from_token(
    claimset: dict = Depends(auth_token_claimset),
    session=Depends(get_session),
):
    email = claimset.get("email")
    auth_time = claimset.get("iat")
    if not email or auth_time is None:
        return

    existing_user = await get_user_by_email(session, email)
    if not existing_user:
        return

    auth_timestamp = datetime.fromtimestamp(auth_time, tz=UTC)
    if not existing_user.last_active_at or existing_user.last_active_at < auth_timestamp:
        await update_last_active_at(session, existing_user, auth_timestamp)


async def get_projects_accessible_to_user(
    claimset: dict = Depends(auth_token_claimset),
    session=Depends(get_session),
) -> list[Project]:
    """
    Dependable that retrieves projects accessible to the user based on Keycloak group membership.

    This function extracts group names from the JWT token and queries for projects
    with matching names within the user's organization, effectively using Keycloak
    as the source of truth for project membership.

    Args:
        claimset: JWT token payload containing group information
        session: Database session for querying projects

    Returns:
        List of Project objects the user has access to through group membership
    """
    # Get user's organization from token
    organization_id_str = __get_organization_id_from_claimset(claimset)
    if not organization_id_str:
        return []

    # Get organization from database to get the UUID
    organization = await get_organization_by_keycloak_org_id(session, organization_id_str)
    if not organization:
        return []

    # Get group names from token
    group_names = __get_group_names_from_claimset(claimset)
    if not group_names:
        return []

    # Get projects that match the group names within the user's organization
    projects = await get_projects_by_names_in_organization(session, group_names, organization.id)
    return projects


async def validate_and_get_project_from_query(
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    project_id: UUID = Query(..., description="The ID of the project for the request"),
) -> Project:
    """
    Validate that the user has access to the specified project and return it.

    Uses Keycloak group membership as the source of truth for project access.
    """
    # Check if the requested project is in the user's accessible projects
    for project in accessible_projects:
        if project.id == project_id:
            return project

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a member of the project")
