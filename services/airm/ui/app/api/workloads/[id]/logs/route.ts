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
    const { id } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/workloads/${id}/logs`;
    const { accessToken } = await authenticateRoute();
    const res = await proxyRequest(req, url, accessToken as string);

    return NextResponse.json(res);
  } catch (error) {
    return handleError(error);
  }
}
