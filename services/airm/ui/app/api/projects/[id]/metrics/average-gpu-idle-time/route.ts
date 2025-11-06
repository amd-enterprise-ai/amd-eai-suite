// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

import { APIError } from '@/types/apis';
import { MetricScalarResponse } from '@/types/metrics';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse<MetricScalarResponse | APIError>> {
  try {
    const { searchParams } = new URL(req.url);
    const start = searchParams.get('start');
    const end = searchParams.get('end');
    const { id: projectId } = await params;

    if (!start || !end) {
      return NextResponse.json(
        { error: 'Missing required query parameters: start and end' },
        { status: 400 },
      );
    }
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}/metrics/average_gpu_idle_time`;

    const { accessToken } = await authenticateRoute();

    const res = await proxyRequest(req, url, accessToken as string);

    return NextResponse.json(res);
  } catch (error) {
    return handleError(error);
  }
}
