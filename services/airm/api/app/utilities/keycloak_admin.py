# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

from fastapi import Request
from keycloak import KeycloakAdmin, KeycloakPutError
from loguru import logger
from starlette.datastructures import State

from ..organizations.schemas import OrganizationCreate
from .exceptions import ExternalServiceError

KEYCLOAK_SERVER_URL = os.environ.get(
    "KEYCLOAK_ADMIN_SERVER_URL",
)
KEYCLOAK_ADMIN_CLIENT_ID = os.environ.get("KEYCLOAK_ADMIN_CLIENT_ID")
KEYCLOAK_ADMIN_CLIENT_SECRET = os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "airm")


async def init_keycloak_admin_client() -> KeycloakAdmin:
    """Initialize Keycloak client. This will be called at application startup."""
    client = KeycloakAdmin(
        client_id=KEYCLOAK_ADMIN_CLIENT_ID,
        client_secret_key=KEYCLOAK_ADMIN_CLIENT_SECRET,
        server_url=KEYCLOAK_SERVER_URL,
        realm_name=KEYCLOAK_REALM,
    )
    # Asynchronously get server info to ensure the client is operational
    server_info = await client.a_get_server_info()
    logger.info(
        "Connected to keycloak server with version: {0}",
        server_info["systemInfo"]["version"],
    )
    return client


def get_kc_admin(request: Request) -> KeycloakAdmin:
    """
    FastAPI dependency to get the initialized KeycloakAdmin client from app.state.

    Args:
        request: FastAPI Request object containing app state

    Returns:
        KeycloakAdmin client instance for performing administrative operations

    Raises:
        RuntimeError: If Keycloak admin client is not properly initialized in app state

    Note:
        Should be used as a dependency in FastAPI route handlers that need Keycloak access.
    """
    return get_kc_admin_client_from_state(request.app.state)


def get_kc_admin_client_from_state(app_state: State) -> KeycloakAdmin:
    if not hasattr(app_state, "keycloak_admin_client") or app_state.keycloak_admin_client is None:
        # This should ideally not happen if lifespan event is set up correctly
        logger.error("Keycloak admin client not initialized in app.state.")
        raise RuntimeError("Keycloak admin client not available.")
    return app_state.keycloak_admin_client


async def get_organizations(kc_admin: KeycloakAdmin) -> list:
    """
    Retrieve all organizations from Keycloak.

    Args:
        kc_admin: KeycloakAdmin client instance

    Returns:
        List of organization dictionaries from Keycloak API

    Note:
        Uses max=-1 to disable pagination and retrieve all organizations.
    """
    return await kc_admin.a_get_organizations(query={"max": -1})


async def get_organization_by_id(kc_admin: KeycloakAdmin, organization_id) -> dict:
    """
    Retrieve a specific organization by ID from Keycloak.

    Args:
        kc_admin: KeycloakAdmin client instance
        organization_id: UUID string of the organization

    Returns:
        Organization dictionary from Keycloak API
    """
    return await kc_admin.a_get_organization(organization_id)


async def get_users_in_organization(kc_admin: KeycloakAdmin, organization_id) -> list:
    """
    Get all members of a specific organization from Keycloak.

    Args:
        kc_admin: KeycloakAdmin client instance
        organization_id: UUID string of the organization

    Returns:
        List of user dictionaries who are members of the organization

    Note:
        Uses max=-1 to disable pagination and retrieve all members.
    """
    return await kc_admin.a_get_organization_members(organization_id, query={"max": -1})


async def get_users_in_role(kc_admin: KeycloakAdmin, role: str) -> list:
    """
    Get all users assigned to a specific realm role from Keycloak.

    Args:
        kc_admin: KeycloakAdmin client instance
        role: Name of the realm role (e.g., "platform-administrator")

    Returns:
        List of user dictionaries assigned to the specified role

    Note:
        Uses max=-1 to disable pagination and retrieve all users with the role.
    """
    return await kc_admin.a_get_realm_role_members(role_name=role, query={"max": -1})


async def get_user(kc_admin: KeycloakAdmin, user_id: str) -> dict:
    """
    Retrieve a specific user by ID from Keycloak.

    Args:
        kc_admin: KeycloakAdmin client instance
        user_id: UUID string of the user

    Returns:
        User dictionary from Keycloak API
    """
    return await kc_admin.a_get_user(user_id)


async def get_user_realm_roles(kc_admin: KeycloakAdmin, user_id: str) -> list:
    """
    Get all realm roles assigned to a specific user.

    Args:
        kc_admin: KeycloakAdmin client instance
        user_id: UUID string of the user

    Returns:
        List of role dictionaries assigned to the user
    """
    return await kc_admin.a_get_realm_roles_of_user(user_id)


async def create_organization_in_keycloak(kc_admin: KeycloakAdmin, organization: OrganizationCreate) -> str:
    """
    Create a new organization in Keycloak.

    Args:
        kc_admin: KeycloakAdmin client instance
        organization: OrganizationCreate schema with name and domains

    Returns:
        UUID string of the created organization

    Note:
        Organization is created as enabled with the specified domain restrictions.
    """
    payload = {
        "name": organization.name,
        "enabled": True,
        "domains": [{"name": domain} for domain in organization.domains],
    }
    organization_id = await kc_admin.a_create_organization(payload)
    return organization_id


async def create_group(
    kc_admin: KeycloakAdmin, group_name: str, path: str | None = None, parent_id: str | None = None
) -> str:
    """Create a new group in Keycloak"""
    payload = {
        "name": group_name,
        "path": f"/{group_name}" if path is None else path,
    }
    group_id = await kc_admin.a_create_group(payload, parent=parent_id)
    return group_id


async def delete_group(kc_admin: KeycloakAdmin, group_id: str) -> None:
    """Delete a group from Keycloak"""
    await kc_admin.a_delete_group(group_id)


async def delete_user(kc_admin: KeycloakAdmin, user_id):
    """Delete a user from Keycloak"""
    return await kc_admin.a_delete_user(user_id)


async def get_assigned_roles_to_user(kc_admin: KeycloakAdmin, user_id):
    """Get all roles belonging to a user in Keycloak"""
    return await kc_admin.a_get_all_roles_of_user(user_id)


async def assign_roles_to_user(kc_admin: KeycloakAdmin, user_id, roles):
    """Add a role to a user in Keycloak"""
    return await kc_admin.a_assign_realm_roles(user_id, roles)


async def create_user(kc_admin: KeycloakAdmin, email: str, exist_ok=False) -> str:
    """Create User in Keycloak"""
    user_data = {
        "username": email,
        "email": email,
        "emailVerified": False,
        "enabled": True,
        "requiredActions": ["VERIFY_EMAIL", "UPDATE_PASSWORD", "UPDATE_PROFILE"],
    }

    user_id = await kc_admin.a_create_user(user_data, exist_ok)
    return user_id


async def get_user_by_username(kc_admin: KeycloakAdmin, username: str) -> dict | None:
    lower_user_name = username.lower()
    users = await kc_admin.a_get_users(
        query={"username": lower_user_name, "max": 1, "exact": True},
    )
    return users[0] if len(users) == 1 else None


async def send_verify_email(kc_admin: KeycloakAdmin, keycloak_user_id: str, redirect_uri):
    """Send verification email to the user"""
    await kc_admin.a_send_verify_email(
        user_id=keycloak_user_id, client_id=KEYCLOAK_ADMIN_CLIENT_ID, redirect_uri=redirect_uri
    )


async def assign_user_to_organization(kc_admin: KeycloakAdmin, user_id: str, organization_id: str):
    """Assign user to an organization in Keycloak"""
    await kc_admin.a_organization_user_add(user_id, organization_id)


async def assign_users_to_group(kc_admin: KeycloakAdmin, user_ids: list[str], group_id: str):
    """Assign users to a group in Keycloak"""
    failed_users = []
    for user_id in user_ids:
        try:
            await kc_admin.a_group_user_add(user_id, group_id)
        except KeycloakPutError as e:
            logger.warning(f"Failed to add user {user_id} to group {group_id}: {e}")
            failed_users.append(user_id)
    if failed_users:
        raise ExternalServiceError(
            message=f"Failed to add {len(failed_users)} user(s) to group {group_id}",
            detail={"failed_users": failed_users},
        )


async def unassign_users_from_group(kc_admin: KeycloakAdmin, user_ids: list[str], group_id: str):
    """Unassign users from a group in Keycloak"""
    failed_users = []
    for user_id in user_ids:
        try:
            await kc_admin.a_group_user_remove(user_id, group_id)
        except KeycloakPutError as e:
            logger.warning(f"Failed to remove user {user_id} from group {group_id}: {e}")
            failed_users.append(user_id)
    if failed_users:
        raise ExternalServiceError(
            message=f"Failed to remove {len(failed_users)} user(s) from group {group_id}",
            detail={"failed_users": failed_users},
        )


async def unassign_roles_to_user(kc_admin: KeycloakAdmin, user_id, roles):
    """Unassign a role to a user in Keycloak"""
    return await kc_admin.a_delete_realm_roles_of_user(user_id, roles)


async def update_user_details(kc_admin: KeycloakAdmin, user_id, user_details):
    """Add a role to a user in Keycloak"""
    return await kc_admin.a_update_user(user_id, user_details)


async def get_all_available_realm_roles(kc_admin: KeycloakAdmin, user_id):
    """Get all roles available to the user from Keycloak"""
    return await kc_admin.a_get_available_realm_roles_of_user(user_id)


async def get_idps_for_organization(kc_admin: KeycloakAdmin, organization_id: str):
    """Get all identity providers linked to an organization in Keycloak"""
    return await kc_admin.a_get_organization_idps(organization_id)


async def get_idps(kc_admin: KeycloakAdmin) -> list[dict]:
    return await kc_admin.a_get_idps()


async def get_realm(kc_admin: KeycloakAdmin) -> dict:
    """Get realm details from Keycloak"""
    return await kc_admin.a_get_realm(KEYCLOAK_REALM)


async def get_user_groups(kc_admin: KeycloakAdmin, user_id: str) -> list[dict]:
    """
    Get all groups that a user belongs to in Keycloak.

    Args:
        kc_admin: KeycloakAdmin client instance
        user_id: UUID string of the user

    Returns:
        List of group dictionaries that the user is a member of

    Note:
        This returns the full group objects including group ID, name, and path.
    """
    return await kc_admin.a_get_user_groups(user_id, query={"max": -1})


async def get_group_members(kc_admin: KeycloakAdmin, group_id: str) -> list[dict]:
    """
    Get all members of a specific group from Keycloak.

    Args:
        kc_admin: KeycloakAdmin client instance
        group_id: UUID string of the group

    Returns:
        List of user dictionaries who are members of the group
    """
    return await kc_admin.a_get_group_members(group_id, query={"max": -1})
