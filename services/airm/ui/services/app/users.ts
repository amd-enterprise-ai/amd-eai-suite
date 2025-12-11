// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import { UserRole } from '@/types/enums/user-roles';
import {
  InviteUserRequest,
  UpdateUserRequest,
  UserWithProjects,
} from '@/types/users';

export const fetchUsers = async () => {
  const response = await fetch('/api/users');
  if (!response.ok) {
    throw new Error(`Failed to get users: ${await getErrorMessage(response)}`);
  }
  const json = await response.json();
  return json;
};

export const fetchUser = async (userId: string): Promise<UserWithProjects> => {
  const response = await fetch(`/api/users/${userId}`);
  if (!response.ok) {
    throw new Error(`Failed to get user: ${await getErrorMessage(response)}`);
  }
  const json = await response.json();
  return json;
};

export const fetchInvitedUsers = async () => {
  const response = await fetch('/api/invited-users');
  if (!response.ok) {
    throw new Error(
      `Failed to get invited users: ${await getErrorMessage(response)}`,
    );
  }
  const json = await response.json();
  return json;
};

export const inviteUser = async (inviteUserData: InviteUserRequest) => {
  const response = await fetch('/api/users', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(inviteUserData),
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to invite users: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteUser = async (userId: string) => {
  const response = await fetch(`/api/users/${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to delete user: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
};

export const resendInvitation = async (userId: string) => {
  const response = await fetch(
    `/api/invited-users/${userId}/resend-invitation`,
    {
      method: 'POST',
    },
  );
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to resend invitation to user: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
};

export const assignRoleToUser = async (data: {
  userId: string;
  role: UserRole;
}) => {
  const response = await fetch(`/api/users/${data.userId}/roles`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      roles: data.role === UserRole.TEAM_MEMBER ? [] : [data.role],
    }),
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to assign role to to user: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response;
};

export const updateUser = async (data: UpdateUserRequest) => {
  const response = await fetch(`/api/users/${data.id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      first_name: data.firstName,
      last_name: data.lastName,
    }),
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to assign role to to user: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
};
