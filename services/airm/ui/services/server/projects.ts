// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';
import { proxyRequest } from '@/utils/server/route';

import { ProjectWithMembers, ProjectsResponse } from '@/types/projects';

export const getProjects = async (
  accessToken: string,
): Promise<ProjectsResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects`;
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
    throw new Error(
      `Failed to get projects: ${await getErrorMessage(response)}`,
    );
  }
};

export const getProject = async (
  projectId: string,
  accessToken: string,
): Promise<ProjectWithMembers> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}`;
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
    throw new Error(
      `Failed to get project: ${await getErrorMessage(response)}`,
    );
  }
};

export const addUserToProject = async (
  userId: string,
  projectId: string,
  accessToken: string,
): Promise<Response> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}/users`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ user_ids: [userId] }),
  });

  if (response.ok) {
    return response;
  } else {
    throw new Error(
      `Failed to add user to project: ${await getErrorMessage(response)}`,
    );
  }
};

export const deleteUserFromProject = async (
  userId: string,
  projectId: string,
  request: NextRequest,
  accessToken: string,
): Promise<NextResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}/users/${userId}`;
  await proxyRequest(request, url, accessToken as string);
  return new NextResponse(null, { status: 204 });
};
