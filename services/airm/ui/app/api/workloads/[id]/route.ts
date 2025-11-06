// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getWorkload } from '@/services/server/workloads';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export const dynamic = 'force-dynamic';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const searchParams = req.nextUrl.searchParams;
    const { id } = await params;

    const workloads = await getWorkload({
      accessToken: accessToken as string,
      workloadId: id,
      withResources: searchParams.get('withResources') === 'true',
    });

    return NextResponse.json(workloads);
  } catch (error) {
    return handleError(error);
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/workloads/${id}`;
    const response = await proxyRequest(req, url, accessToken as string);

    return NextResponse.json(response);
  } catch (error) {
    return handleError(error);
  }
}
