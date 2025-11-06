// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: projectId } = await params;

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}/workloads/metrics`;
    const res = await proxyRequest(req, url, accessToken as string);
    return new NextResponse(JSON.stringify(res), { status: 200 });
  } catch (error) {
    return handleError(error);
  }
}
