// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getProject } from '@/services/server/projects';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: projectId } = await params;
    const project = await getProject(projectId, accessToken as string);

    return NextResponse.json(project);
  } catch (error) {
    return handleError(error);
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();

    const { id: projectId } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}`;
    await proxyRequest(request, url, accessToken as string);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return handleError(error);
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();

    const { id: projectId } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}`;
    const response = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(response);
  } catch (error) {
    return handleError(error);
  }
}
