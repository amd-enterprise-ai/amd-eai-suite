# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, status
from keycloak import KeycloakAdmin
from sqlalchemy.ext.asyncio import AsyncSession

from ..organizations.models import Organization
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException
from ..utilities.keycloak_admin import get_kc_admin
from ..utilities.security import ensure_platform_administrator, get_user_organization
from ..utilities.security import get_user_email as get_logged_in_user
from .repository import get_user_in_organization
from .schemas import (
    InvitedUsers,
    InviteUser,
    UserDetailsUpdate,
    UserRolesUpdate,
    Users,
    UserWithProjects,
)
from .service import (
    assign_roles_to_user,
    create_user_in_organization,
    edit_user_details,
    get_invited_users_for_organization,
    get_user_details,
    get_users_for_organization,
    resend_invitation,
)
from .service import delete_user as delete_user_service

router = APIRouter(tags=["Users"])


@router.get(
    "/users",
    operation_id="get_users",
    summary="List organization users",
    description="""
        List all active users in the organization.
        Requires platform administrator role. Returns user details
        including roles for user management workflows.
    """,
    status_code=status.HTTP_200_OK,
    response_model=Users,
)
async def get_users(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
) -> Users:
    users = await get_users_for_organization(kc_admin, session, organization)
    return Users(
        data=users,
    )


@router.get(
    "/invited-users",
    operation_id="get_invited_users",
    summary="List pending user invitations",
    description="""
        List users with pending invitations who haven't yet joined the organization.
        Requires platform administrator role. Essential for tracking invitation
        status and managing onboarding workflows.
    """,
    status_code=status.HTTP_200_OK,
    response_model=InvitedUsers,
)
async def get_invited_users(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
) -> InvitedUsers:
    invited_users = await get_invited_users_for_organization(kc_admin, session, organization)
    return InvitedUsers(data=invited_users)


@router.post(
    "/users",
    operation_id="create_user",
    summary="Invite user to organization",
    description="""
        Send invitation to new user for organization access. Requires platform
        administrator role. Creates user account in Keycloak and sends email
        invitation. Foundation for user onboarding and access management.
    """,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_logged_in_user),
    session: AsyncSession = Depends(get_session),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    user_in: InviteUser = Body(description="The user to be created in the user's organization"),
) -> None:
    await create_user_in_organization(kc_admin, session, organization, user_in, user)


@router.get(
    "/users/{user_id}",
    operation_id="get_user",
    summary="Get user details",
    description="""
        Retrieve detailed information about a specific user including project
        memberships and roles. Requires platform administrator role and organization
        membership. Used for user profile management and access auditing.
    """,
    status_code=status.HTTP_200_OK,
    response_model=UserWithProjects,
)
async def get_user(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    user_id: UUID = Path(description="The ID of the user to be retrieved"),
) -> UserWithProjects:
    user = await get_user_in_organization(session, organization.id, user_id)

    if not user:
        raise NotFoundException("User not found")

    return await get_user_details(kc_admin, session, organization, user)


@router.delete(
    "/users/{user_id}",
    operation_id="delete_user",
    summary="Remove user from organization",
    description="""
        Permanently remove user from organization and all associated projects.
        Requires platform administrator role. Removes Keycloak account and
        project memberships. Irreversible operation for offboarding workflows.
    """,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    user_id: UUID = Path(description="The ID of the user to be deleted"),
) -> None:
    user = await get_user_in_organization(session, organization.id, user_id)
    if not user:
        raise NotFoundException("User not found")
    await delete_user_service(kc_admin, session, user)


@router.put(
    "/users/{user_id}/roles",
    operation_id="add_user_role",
    summary="Assign user roles",
    description="""
        Grant platform roles to user (Platform Administrator, etc.). Requires
        platform administrator role and organization membership. Controls access
        to administrative functions and resource management capabilities.
    """,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_user_role(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    logged_in_user: str = Depends(get_logged_in_user),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    user_id: UUID = Path(description="The ID of the user to add the role to"),
    user_role_request: UserRolesUpdate = Body(...),
) -> None:
    user = await get_user_in_organization(session, organization.id, user_id)
    if not user:
        raise NotFoundException("User not found")
    return await assign_roles_to_user(kc_admin, user, user_role_request, logged_in_user)


@router.put(
    "/users/{user_id}",
    operation_id="update_user",
    summary="Update user profile",
    description="""
        Modify user profile information including name and contact details.
        Requires platform administrator role. Updates both local database
        and Keycloak identity provider for consistent user information.
    """,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_user(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    logged_in_user: str = Depends(get_logged_in_user),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    user_id: UUID = Path(description="The ID of the user to update"),
    user_details: UserDetailsUpdate = Body(...),
) -> None:
    user = await get_user_in_organization(session, organization.id, user_id)
    if not user:
        raise NotFoundException("User not found")
    await edit_user_details(kc_admin, user, user_details, logged_in_user)


@router.post(
    "/invited-users/{user_id}/resend-invitation",
    operation_id="resend_invitations",
    summary="Resend user invitation",
    description="""
        Resend invitation email to user with pending invitation status.
        Requires platform administrator role. Useful when original invitation
        emails are missed or expired during onboarding process.
    """,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def resend_invitations(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    logged_in_user: str = Depends(get_logged_in_user),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    user_id: UUID = Path(description="The ID of the user to resend invitation to"),
) -> None:
    user = await get_user_in_organization(session, organization.id, user_id)
    if not user:
        raise NotFoundException("User not found")
    await resend_invitation(kc_admin, user, logged_in_user)
