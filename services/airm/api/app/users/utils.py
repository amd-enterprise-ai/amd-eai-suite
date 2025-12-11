# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from keycloak import KeycloakAdmin

from ..organizations.models import Organization
from ..organizations.service import enrich_organization_details
from ..projects.models import Project
from ..projects.schemas import ProjectResponse
from ..utilities.config import POST_REGISTRATION_REDIRECT_URL
from ..utilities.exceptions import (
    ConflictException,
    ExternalServiceError,
    PreconditionNotMetException,
    ValidationException,
)
from ..utilities.keycloak_admin import (
    create_user,
    send_verify_email,
    set_temporary_password,
)
from ..utilities.keycloak_admin import get_organization_by_id as get_organization_by_id_from_keycloak
from ..utilities.security import Roles
from .models import User as UserModel
from .schemas import InvitedUser, InvitedUserWithProjects, InviteUser, UserResponse, UserWithProjects


def merge_user_details(keycloak_user: dict, user: UserModel, platform_admins: set[str]) -> UserResponse:
    """
    Merge user data from Keycloak and database into a UserResponse response.

    Args:
        keycloak_user: User data from Keycloak containing firstName and lastName
        user: Database user model with local fields like email, timestamps, and keycloak_user_id
        platform_admins: Set of Keycloak user IDs that have platform administrator role

    Returns:
        UserResponse with combined data from both sources and computed role

    Note:
        Role is determined by checking if user's keycloak_user_id is in platform_admins set.
    """
    return UserResponse(
        id=user.id,
        first_name=keycloak_user["firstName"],
        last_name=keycloak_user["lastName"],
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at,
        created_by=user.created_by,
        updated_by=user.updated_by,
        role=__get_schema_role(user, platform_admins),
        last_active_at=user.last_active_at,
    )


def merge_invited_user_details(user: UserModel, platform_admins: set[str]) -> InvitedUser:
    """
    Create InvitedUser schema for users who haven't completed Keycloak profile setup.

    Args:
        user: Database user model with invitation and basic fields
        platform_admins: Set of Keycloak user IDs that have platform administrator role

    Returns:
        InvitedUser schema with database fields and computed role

    Note:
        Used for users who exist in database but haven't set firstName/lastName in Keycloak.
        Role determination follows same logic as active users.
    """
    return InvitedUser(
        id=user.id,
        email=user.email,
        invited_at=user.invited_at,
        invited_by=user.invited_by,
        created_at=user.created_at,
        updated_at=user.updated_at,
        created_by=user.created_by,
        updated_by=user.updated_by,
        role=__get_schema_role(user, platform_admins),
    )


def __get_schema_role(user: UserModel, platform_admins: set[str]) -> str:
    """
    Determine user role based on platform administrator status.

    Args:
        user: Database user model containing keycloak_user_id
        platform_admins: Set of Keycloak user IDs with platform administrator role

    Returns:
        Role string value (PLATFORM_ADMINISTRATOR or TEAM_MEMBER)
    """
    return Roles.PLATFORM_ADMINISTRATOR.value if user.keycloak_user_id in platform_admins else Roles.TEAM_MEMBER.value


def is_keycloak_user_active(keycloak_user: dict) -> bool:
    """
    Check if a Keycloak user has completed their profile setup.

    Args:
        keycloak_user: User data dictionary from Keycloak API

    Returns:
        True if user has both firstName and lastName set, indicating completed profile setup
    """
    return "firstName" in keycloak_user and "lastName" in keycloak_user


def is_keycloak_user_inactive(keycloak_user: dict) -> bool:
    """
    Check if a Keycloak user has not completed their profile setup.

    Args:
        keycloak_user: User data dictionary from Keycloak API

    Returns:
        True if user is missing firstName or lastName, indicating incomplete profile setup
    """
    return not is_keycloak_user_active(keycloak_user)


async def check_valid_email_domain(user_email: str, organization: Organization, kc_admin: KeycloakAdmin) -> None:
    """
    Check if a user email can be assigned to an organization.

    This method performs the following checks:
    1. Retrieves the organization in Keycloak using its keycloak_organization_id.
    2. Verifies that the user's email contains a valid domain for the organization.

    Args:
        user_email (str): The email address of the user.
        organization: The organization object containing the keycloak_organization_id.
        kc_admin: Injected KeycloakAdmin client.
    """
    kc_org = await get_organization_by_id_from_keycloak(kc_admin, organization.keycloak_organization_id)

    if not kc_org:
        raise ExternalServiceError("Organization not found in Keycloak.")

    # Extract the domain list from the organization's data
    domains = kc_org.get("domains", [])
    if domains:  # Check if domains list is not empty
        user_domain = user_email.split("@")[-1]
        valid_domains = [domain["name"] for domain in domains]

        # Check if the user's email domain matches any valid domains
        if user_domain not in valid_domains:
            raise ValidationException(
                f"User email domain '{user_domain}' is not in the organization's allowed domains: {valid_domains}"
            )


def merge_user_details_with_projects(
    keycloak_user: dict,
    user: UserModel,
    platform_admins: set[str],
    projects: list[Project] | None = None,
) -> UserWithProjects:
    """
    Merge user details with their associated projects into UserWithProjects schema.

    Args:
        keycloak_user: User data from Keycloak containing firstName and lastName
        user: Database user model with local fields
        platform_admins: Set of Keycloak user IDs that have platform administrator role
        projects: Optional list of Project models the user is a member of

    Returns:
        UserWithProjects schema combining user details and project list
    """
    user = merge_user_details(keycloak_user, user, platform_admins)
    return UserWithProjects(
        **user.model_dump(),
        projects=[ProjectResponse.model_validate(project) for project in projects] if projects else [],
    )


def merge_invited_user_details_with_projects(
    user: UserModel, platform_admins: set[str], projects: list[Project] | None = None
) -> InvitedUserWithProjects:
    """
    Merge invited user details with their associated projects into InvitedUserWithProjects schema.

    Args:
        user: Database user model for invited user
        platform_admins: Set of Keycloak user IDs that have platform administrator role
        projects: Optional list of Project models the user is a member of

    Returns:
        InvitedUserWithProjects schema combining invited user details and project list
    """
    invited_user = merge_invited_user_details(user, platform_admins)
    return InvitedUserWithProjects(
        **invited_user.model_dump(),
        projects=[ProjectResponse.model_validate(project) for project in projects] if projects else [],
    )


async def create_user_in_keycloak(kc_admin: KeycloakAdmin, user_in: InviteUser, organization: Organization) -> str:
    organization_details = await enrich_organization_details(kc_admin=kc_admin, organization=organization)

    if not organization_details.idp_linked and not organization_details.smtp_enabled:
        if not user_in.temporary_password:
            raise ConflictException("Temporary password is required for user creation")
        else:
            # Create user in Keycloak with temporary password
            user_data = {
                "username": user_in.email,
                "email": user_in.email,
                "emailVerified": True,  # set the email as already verified since there is no smtp setup
                "enabled": True,
                "requiredActions": ["UPDATE_PASSWORD", "UPDATE_PROFILE"],
            }
            keycloak_user_id = await create_user(kc_admin=kc_admin, user_data=user_data)
            await set_temporary_password(
                kc_admin=kc_admin, user_id=keycloak_user_id, temp_password=user_in.temporary_password
            )
            return keycloak_user_id
    elif organization_details.smtp_enabled:
        # Create user in Keycloak with email verification required
        user_data = {
            "username": user_in.email,
            "email": user_in.email,
            "emailVerified": False,
            "enabled": True,
            "requiredActions": ["VERIFY_EMAIL", "UPDATE_PASSWORD", "UPDATE_PROFILE"],
        }
        keycloak_user_id = await create_user(kc_admin=kc_admin, user_data=user_data)
        await send_verify_email(
            kc_admin=kc_admin, keycloak_user_id=keycloak_user_id, redirect_uri=POST_REGISTRATION_REDIRECT_URL
        )
        return keycloak_user_id
    else:
        raise PreconditionNotMetException("Organization is not configured for user creation")
