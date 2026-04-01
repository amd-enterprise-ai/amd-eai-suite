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
    const { searchParams } = new URL(req.url);
    const start = searchParams.get('start');
    const end = searchParams.get('end');

    if (!start || !end) {
      return NextResponse.json(
        { error: 'Missing required query parameters: start and end' },
        { status: 400 },
      );
    }

    const query = searchParams.toString();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}/nodes/${nodeId}/metrics/temperature/memory${query ? `?${query}` : ''}`;

    const { accessToken } = await authenticateRoute();
    const res = await proxyRequest(req, url, accessToken as string);
    return NextResponse.json(res);
  } catch (error) {
    return handleError(error);
  }
}
