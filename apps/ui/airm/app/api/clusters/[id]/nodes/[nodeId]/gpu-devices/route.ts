// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@amdenterpriseai/utils/server';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; nodeId: string }> },
) {
  try {
    const { id: clusterId, nodeId } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}/nodes/${nodeId}/gpu-devices`;

    const { accessToken } = await authenticateRoute();
    const res = await proxyRequest(req, url, accessToken as string);
    return NextResponse.json(res);
  } catch (error) {
    return handleError(error);
  }
}
