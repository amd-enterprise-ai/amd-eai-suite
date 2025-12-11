// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; storageId: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();

    const { id: projectId, storageId } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}/storages/${storageId}/assign`;
    const response = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(response);
  } catch (error) {
    return handleError(error);
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; storageId: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();

    const { id: projectId, storageId } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}/storages/${storageId}`;
    await proxyRequest(request, url, accessToken as string);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return handleError(error);
  }
}
