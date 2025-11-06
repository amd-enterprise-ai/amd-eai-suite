// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';
import { proxyRequest } from '@/utils/server/route';

import { InvitedUsersResponse, User, UsersResponse } from '@/types/users';

export const getUsers = async (accessToken: string): Promise<UsersResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/users`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (response.ok) {
    const json = await response.json();
    return convertSnakeToCamel(json);
  } else {
    throw new Error(`Failed to get users: ${await getErrorMessage(response)}`);
  }
};

export const getUser = async (
  userId: string,
  accessToken: string,
): Promise<User | null> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/users/${userId}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (response.ok) {
    const json = await response.json();
    return convertSnakeToCamel(json);
  } else {
    throw new Error(`Failed to get user: ${await getErrorMessage(response)}`);
  }
};

export const inviteUser = async (
  request: NextRequest,
  accessToken: string,
): Promise<User | NextResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/users`;
  const json = await proxyRequest(request, url, accessToken as string);
  return NextResponse.json(json) as unknown as User;
};

export const deleteUser = async (
  userId: string,
  request: NextRequest,
  accessToken: string,
): Promise<NextResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/users/${userId}`;
  await proxyRequest(request, url, accessToken as string);
  return new NextResponse(null, { status: 204 });
};

export const getInvitedUsers = async (
  accessToken: string,
): Promise<InvitedUsersResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/invited_users`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (response.ok) {
    const json = await response.json();
    return convertSnakeToCamel(json);
  } else {
    throw new Error(`Failed to get users: ${await getErrorMessage(response)}`);
  }
};
