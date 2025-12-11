# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from keycloak import KeycloakAdmin
from sqlalchemy.ext.asyncio import AsyncSession

from ..organizations.models import Organization
from ..projects.models import Project
from ..projects.repository import (
    get_projects_by_names_in_organization,
    get_projects_in_organization,
)
from ..users.repository import get_user_by_email
from ..utilities.config import POST_REGISTRATION_REDIRECT_URL
from ..utilities.exceptions import ConflictException, ExternalServiceError, NotFoundException
from ..utilities.keycloak_admin import assign_roles_to_user as assign_roles_to_user_keycloak
from ..utilities.keycloak_admin import assign_user_to_organization as assign_user_to_organization_in_keycloak
from ..utilities.keycloak_admin import (
    assign_users_to_group,
    get_all_available_realm_roles,
    get_assigned_roles_to_user,
    get_user,
    get_user_groups,
    get_user_realm_roles,
    get_users_in_role,
    send_verify_email,
    unassign_roles_to_user,
    update_user_details,
)
from ..utilities.keycloak_admin import delete_user as delete_user_from_keycloak
from ..utilities.keycloak_admin import get_user_by_username as get_user_by_username_from_keycloak
from ..utilities.keycloak_admin import get_users_in_organization as get_users_in_organization_from_keycloak
from ..utilities.models import set_updated_fields
from ..utilities.security import Roles
from .models import User as UserModel
from .repository import create_user_in_organization as create_user_in_organization_in_db
from .repository import delete_user as delete_user_from_db
from .repository import get_users_in_organization
from .schemas import (
    InvitedUserWithProjects,
    InviteUser,
    UserDetailsUpdate,
    UserResponse,
    UserRolesUpdate,
    UserWithProjects,
)
from .utils import (
    check_valid_email_domain,
    create_user_in_keycloak,
    is_keycloak_user_active,
    is_keycloak_user_inactive,
    merge_invited_user_details_with_projects,
    merge_user_details,
    merge_user_details_with_projects,
)


async def delete_user(kc_admin: KeycloakAdmin, session: AsyncSession, user: UserModel) -> None:
    await delete_user_from_keycloak(kc_admin=kc_admin, user_id=user.keycloak_user_id)
    await delete_user_from_db(session, user.id)


async def assign_roles_to_user(
    kc_admin: KeycloakAdmin,
    user: UserModel,
    user_role_request: UserRolesUpdate,
    updater: str,
) -> None:
    roles_assigned_to_user, all_realm_roles = await asyncio.gather(
        get_assigned_roles_to_user(kc_admin=kc_admin, user_id=user.keycloak_user_id),
        get_all_available_realm_roles(kc_admin=kc_admin, user_id=user.keycloak_user_id),
    )

    user_platform_admin_role = next(
        (
            role
            for role in roles_assigned_to_user["realmMappings"]
            if role["name"] == Roles.PLATFORM_ADMINISTRATOR.value
        ),
        None,
    )
    platform_admin_role = next(
        (role for role in all_realm_roles if role["name"] == Roles.PLATFORM_ADMINISTRATOR.value),
        None,
    )

    if Roles.PLATFORM_ADMINISTRATOR.value in user_role_request.roles and not user_platform_admin_role:
        if platform_admin_role:
            await assign_roles_to_user_keycloak(
                kc_admin=kc_admin, user_id=user.keycloak_user_id, roles=[platform_admin_role]
            )

    elif user_platform_admin_role and not user_role_request.roles:
        await unassign_roles_to_user(kc_admin=kc_admin, user_id=user.keycloak_user_id, roles=[user_platform_admin_role])

    set_updated_fields(user, updater)


async def edit_user_details(
    kc_admin: KeycloakAdmin, user: UserModel, user_details: UserDetailsUpdate, updater: str
) -> None:
    new_user_details = {
        "firstName": user_details.first_name,
        "lastName": user_details.last_name,
    }
    await update_user_details(kc_admin=kc_admin, user_id=user.keycloak_user_id, user_details=new_user_details)
    set_updated_fields(user, updater)


async def resend_invitation(kc_admin: KeycloakAdmin, user: UserModel, logged_in_user: str) -> None:
    keycloak_user = await get_user(kc_admin=kc_admin, user_id=user.keycloak_user_id)

    if keycloak_user:
        if is_keycloak_user_inactive(keycloak_user):
            await send_verify_email(
                kc_admin=kc_admin, keycloak_user_id=user.keycloak_user_id, redirect_uri=POST_REGISTRATION_REDIRECT_URL
            )
            user.invited_by = logged_in_user
            user.invited_at = datetime.now(UTC)
        else:
            raise ConflictException("User is already active.")
    else:
        raise ExternalServiceError("User lookup failed.")


async def create_user_in_organization(
    kc_admin: KeycloakAdmin, session: AsyncSession, organization: Organization, user_in: InviteUser, creator: str
) -> UserModel:
    projects = await get_projects_in_organization(session, organization.id)

    if user_in.project_ids:
        project_ids_in_org = {str(project.id) for project in projects}
        invalid_projects = [pid for pid in user_in.project_ids if str(pid) not in project_ids_in_org]

        if invalid_projects:
            raise NotFoundException(
                f"Projects not found in organization: {', '.join(str(p) for p in invalid_projects)}"
            )

    existing_user = await get_user_by_email(session, user_in.email)
    if existing_user:
        if existing_user.organization_id == organization.id:
            raise ConflictException("User is already a member of this organization.")
        raise ConflictException("User is already part of another organization.")

    await check_valid_email_domain(user_in.email, organization, kc_admin)
    keycloak_user = await get_user_by_username_from_keycloak(kc_admin=kc_admin, username=user_in.email)
    keycloak_user_id = keycloak_user["id"] if keycloak_user else None

    if not keycloak_user_id:
        keycloak_user_id = await create_user_in_keycloak(kc_admin=kc_admin, user_in=user_in, organization=organization)

    await assign_user_to_organization_in_keycloak(
        kc_admin=kc_admin, user_id=keycloak_user_id, organization_id=organization.keycloak_organization_id
    )

    new_user = await create_user_in_organization_in_db(
        session, organization.id, user_in.email, keycloak_user_id, creator
    )

    new_user.invited_by = creator
    new_user.invited_at = datetime.now(UTC)

    if user_in.roles:
        await assign_roles_to_user(
            kc_admin,
            new_user,
            UserRolesUpdate(roles=user_in.roles),
            creator,
        )
    if user_in.project_ids:
        keycloak_group_ids = [project.keycloak_group_id for project in projects if project.id in user_in.project_ids]
        for group_id in keycloak_group_ids:
            await assign_users_to_group(
                kc_admin=kc_admin,
                user_ids=[keycloak_user_id],
                group_id=group_id,
            )

    return new_user


async def get_users_for_organization(
    kc_admin: KeycloakAdmin, session: AsyncSession, organization: Organization
) -> list[UserResponse]:
    platform_admin_users, keycloak_users, db_users = await asyncio.gather(
        get_users_in_role(kc_admin=kc_admin, role=Roles.PLATFORM_ADMINISTRATOR.value),
        get_users_in_organization_from_keycloak(
            kc_admin=kc_admin, organization_id=organization.keycloak_organization_id
        ),
        get_users_in_organization(session, organization.id),
    )

    keycloak_users_by_id = {user["id"]: user for user in keycloak_users}
    platform_admins = {pa["id"] for pa in platform_admin_users}

    return [
        merge_user_details(
            keycloak_user=keycloak_user,
            user=user,
            platform_admins=platform_admins,
        )
        for user in db_users
        if (keycloak_user := keycloak_users_by_id.get(user.keycloak_user_id)) and is_keycloak_user_active(keycloak_user)
    ]


async def get_invited_users_for_organization(
    kc_admin: KeycloakAdmin, session: AsyncSession, organization: Organization
) -> list[InvitedUserWithProjects]:
    platform_admin_users, keycloak_users, db_users = await asyncio.gather(
        get_users_in_role(kc_admin=kc_admin, role=Roles.PLATFORM_ADMINISTRATOR.value),
        get_users_in_organization_from_keycloak(
            kc_admin=kc_admin, organization_id=organization.keycloak_organization_id
        ),
        get_users_in_organization(session, organization.id),
    )

    keycloak_users_by_id = {user["id"]: user for user in keycloak_users}
    platform_admins = {pa["id"] for pa in platform_admin_users}

    return [
        merge_invited_user_details_with_projects(
            user=user,
            platform_admins=platform_admins,
            projects=await get_projects_for_user_groups(
                kc_admin=kc_admin,
                session=session,
                organization_id=organization.id,
                keycloak_user_id=user.keycloak_user_id,
            ),
        )
        for user in db_users
        if (keycloak_user := keycloak_users_by_id.get(user.keycloak_user_id))
        and is_keycloak_user_inactive(keycloak_user)
    ]


async def get_user_details(
    kc_admin: KeycloakAdmin, session: AsyncSession, organization: Organization, user: UserModel
) -> UserWithProjects:
    keycloak_user = await get_user(kc_admin=kc_admin, user_id=user.keycloak_user_id)
    user_roles = await get_user_realm_roles(kc_admin=kc_admin, user_id=user.keycloak_user_id)

    if not keycloak_user:
        raise ExternalServiceError("User not found in Keycloak service")

    user_projects = await get_projects_for_user_groups(kc_admin, session, organization.id, user.keycloak_user_id)

    return merge_user_details_with_projects(
        keycloak_user,
        user,
        (
            {user.keycloak_user_id}
            if any(role["name"] == Roles.PLATFORM_ADMINISTRATOR.value for role in user_roles)
            else set()
        ),
        user_projects,
    )


async def get_projects_for_user_groups(
    kc_admin: KeycloakAdmin, session: AsyncSession, organization_id: UUID, keycloak_user_id: str
) -> list[Project]:
    user_groups = await get_user_groups(kc_admin=kc_admin, user_id=keycloak_user_id)
    group_names = [name for group in user_groups if (name := group.get("name"))]
    user_projects = await get_projects_by_names_in_organization(session, group_names, organization_id)
    return user_projects
