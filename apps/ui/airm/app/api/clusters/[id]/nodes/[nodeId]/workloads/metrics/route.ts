// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@amdenterpriseai/utils/server';

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; nodeId: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: clusterId, nodeId } = await params;

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}/nodes/${nodeId}/workloads/metrics`;
    const json = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}
