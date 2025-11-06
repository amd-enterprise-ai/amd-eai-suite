// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getCluster } from '@/services/server/clusters';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function GET(
  _: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: clusterId } = await params;
    const cluster = await getCluster(clusterId, accessToken as string);

    return NextResponse.json(cluster);
  } catch (error) {
    return handleError(error);
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id: clusterId } = await params;
    const { accessToken } = await authenticateRoute();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}`;
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
    const { id: clusterId } = await params;
    const { accessToken } = await authenticateRoute();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}`;
    const cluster = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(cluster);
  } catch (error) {
    return handleError(error);
  }
}
