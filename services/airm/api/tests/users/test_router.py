# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app import app  # type: ignore
from app.organizations.schemas import OrganizationResponse
from app.users.models import User as UserModel
from app.users.schemas import (
    InvitedUserWithProjects,
    InviteUser,
    UserResponse,
    UserRoleEnum,
    UserRolesUpdate,
)
from app.utilities.database import get_session
from app.utilities.exceptions import ConflictException
from app.utilities.security import Roles, ensure_platform_administrator, get_user_email, get_user_organization


@pytest.mark.asyncio
@patch(
    "app.users.router.get_users_for_organization",
    return_value=[
        UserResponse(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
            role=Roles.TEAM_MEMBER.value,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            created_by="test@example.com",
            updated_by="test@example.com",
        )
    ],
)
async def test_get_users_success(_):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/users")

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == {
        "users": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "role": "Team Member",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
                "last_active_at": None,
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_users_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    with TestClient(app) as client:
        response = client.get("/v1/users")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_users_not_in_organization():
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    with TestClient(app) as client:
        response = client.get("/v1/users")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_users_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/users")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_user_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    with TestClient(app) as client:
        response = client.get("/v1/users/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_user_not_in_organization():
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    with TestClient(app) as client:
        response = client.get("/v1/users/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_user_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/users/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.users.router.get_user_in_organization",
    return_value=None,
)
async def test_get_user_not_found(_):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/users/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}


@pytest.mark.asyncio
@patch("app.users.router.delete_user_service", return_value=None)
@patch(
    "app.users.router.get_user_in_organization",
    return_value=UserModel(
        id="487590ed-165c-44d5-b686-1aff81cca298",
        email="user1@test.com",
        organization_id="123",
        keycloak_user_id="444",
    ),
)
async def test_delete_user_success(_, __):
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.delete("/v1/users/b7c13f41-258d-44b1-a694-5dd4ccda660c")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@patch("app.users.router.delete_user_service", return_value=None)
@patch("app.users.router.get_user_in_organization", return_value=None)
async def test_delete_user_not_found(_, __):
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.delete("/v1/users/b7c13f41-258d-44b1-a694-5dd4ccda660c")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}

    app.dependency_overrides = {}


def test_user_role_request_validation():
    try:
        valid_request = UserRolesUpdate(roles=[UserRoleEnum.PLATFORM_ADMIN])
        assert valid_request.roles == [UserRoleEnum.PLATFORM_ADMIN]
    except ValidationError:
        pytest.fail("ValidationError raised unexpectedly with valid roles")

    with pytest.raises(ValidationError) as exc_info:
        UserRolesUpdate(roles=["invalid_role"])

    assert exc_info.value.errors()[0]["loc"] == ("roles", 0)
    assert exc_info.value.errors()[0]["msg"] == "Input should be 'Platform Administrator'"
    assert exc_info.value.errors()[0]["type"] == "enum"


@pytest.mark.asyncio
@patch("app.users.router.assign_roles_to_user", return_value=None)
@patch("app.users.router.get_user_in_organization")
async def test_add_role_to_user_success(_, mock_add_roles_to_user):
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    valid_payload = {"roles": [UserRoleEnum.PLATFORM_ADMIN]}

    with TestClient(app) as client:
        response = client.put("/v1/users/b7c13f41-258d-44b1-a694-5dd4ccda660c/roles", json=valid_payload)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_add_roles_to_user.assert_called_once()


@pytest.mark.asyncio
@patch("app.users.router.get_user_in_organization")
@patch("app.users.router.assign_roles_to_user", return_value=None)
async def test_remove_role_from_user(_, __):
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    invalid_payload = {"roles": []}

    with TestClient(app) as client:
        response = client.put("/v1/users/b7c13f41-258d-44b1-a694-5dd4ccda660c/roles", json=invalid_payload)

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@patch(
    "app.users.router.create_user_in_organization",
    return_value=UserModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        email="test1@example.com",
        keycloak_user_id="kc_user_id",
    ),
)
async def test_create_user_success(_):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/users", json=user_create.dict())

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_create_user_no_user():
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.side_effect = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/users", json=user_create.dict())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_user_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/users", json=user_create.dict())

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_user_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/users", json=user_create.dict())

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.users.router.create_user_in_organization")
async def test_create_user_duplicate_email(create_user_in_organization):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    create_user_in_organization.side_effect = ConflictException("A user with email 'test1@example.com' already exists")

    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/users", json=user_create.dict())

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "A user with email 'test1@example.com' already exists"}


@pytest.mark.asyncio
async def test_create_user_invalid_input():
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.post(
            "/v1/users",
            json={
                "first_name": "name" + "*" * 64,
                "last_name": "last name",
                "email": "test@example1.com",
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    with TestClient(app) as client:
        response = client.post(
            "/v1/users",
            json={
                "first_name": "first Name",
                "last_name": "name" + "*" * 1204,
                "email": "test@example1.com",
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    with TestClient(app) as client:
        response = client.post(
            "/v1/users",
            json={
                "first_name": "first Name",
                "last_name": "last Name",
                "email": "tes222com",
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_update_user_success():
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    valid_payload = {
        "first_name": "NewFirstName",
        "last_name": "NewLastName",
    }
    user = UserModel(
        id="b7c13f41-258d-44b1-a694-5dd4ccda660c",
        email="user1@test.com",
        organization_id="123",
        keycloak_user_id="03890db1-9627-4663-ae0b-6a74ef1ff638",
    )
    with (
        patch("app.users.router.get_user_in_organization", return_value=user),
        patch("app.users.router.edit_user_details", return_value=None) as mock_edit_user_details,
    ):
        with TestClient(app) as client:
            response = client.put("/v1/users/b7c13f41-258d-44b1-a694-5dd4ccda660c", json=valid_payload)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify the service was called with correct parameters
    mock_edit_user_details.assert_called_once()
    call_args = mock_edit_user_details.call_args

    # Verify user object and update data were passed correctly
    assert call_args[0][1] == user  # Second argument should be the user object
    user_update = call_args[0][2]  # Third argument should be the UserUpdate object
    assert user_update.first_name == "NewFirstName"
    assert user_update.last_name == "NewLastName"


@pytest.mark.asyncio
@patch(
    "app.users.router.get_invited_users_for_organization",
    return_value=[
        InvitedUserWithProjects(
            email="john.doe@example.com",
            id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
            invited_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
            invited_by="user@user.com",
            role=Roles.TEAM_MEMBER.value,
            projects=[],
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            created_by="test@example.com",
            updated_by="test@example.com",
        )
    ],
)
async def test_get_invited_users_success(_):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/invited_users")

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == {
        "invited_users": [
            {
                "email": "john.doe@example.com",
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "role": "Team Member",
                "projects": [],
                "invited_at": "2025-01-01T00:00:00Z",
                "invited_by": "user@user.com",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_invited_users_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    with TestClient(app) as client:
        response = client.get("/v1/invited_users")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_invited_users_not_in_organization():
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    with TestClient(app) as client:
        response = client.get("/v1/invited_users")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_invited_users_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/invited_users")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.users.router.resend_invitation", return_value=None)
@patch("app.users.router.get_user_in_organization")
async def test_resend_invitation_success(mock_get_user_in_organization, mock_resend_invitation):
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    mock_get_user_in_organization.return_value = UserModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        email="user1@test.com",
        organization_id="123",
        keycloak_user_id="444",
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    with TestClient(app) as client:
        response = client.post("/v1/invited_users/0aa18e92-002c-45b7-a06e-dcdb0277974c/resend_invitation")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_resend_invitation.assert_called_once()
    mock_get_user_in_organization.assert_called_once()


@pytest.mark.asyncio
@patch("app.users.router.get_user_in_organization")
async def test_resend_invitation_user_not_found(mock_get_user_in_organization):
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.return_value = OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        domains=["test.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    # Set up the mock to return None directly
    mock_get_user_in_organization.return_value = None

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_session] = lambda: AsyncMock(spec=AsyncSession)
    app.dependency_overrides[ensure_platform_administrator] = lambda: AsyncMock(spec_set=[])
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    with TestClient(app) as client:
        response = client.post("/v1/invited_users/0aa18e92-002c-45b7-a06e-dcdb0277974c/resend_invitation")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_get_user_in_organization.assert_called_once()


@pytest.mark.asyncio
async def test_resend_invitation_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    with TestClient(app) as client:
        response = client.post("/v1/invited_users/0aa18e92-002c-45b7-a06e-dcdb0277974c/resend_invitation")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_resend_invitation_not_in_organization():
    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    with TestClient(app) as client:
        response = client.post("/v1/invited_users/0aa18e92-002c-45b7-a06e-dcdb0277974c/resend_invitation")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_resend_invitation_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user_organization = MagicMock(spec=OrganizationResponse)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.post("/v1/invited_users/0aa18e92-002c-45b7-a06e-dcdb0277974c/resend_invitation")

    assert response.status_code == status.HTTP_404_NOT_FOUND
