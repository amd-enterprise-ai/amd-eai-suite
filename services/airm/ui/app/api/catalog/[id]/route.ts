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
    const { id: chartId } = await params;
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/charts/${chartId}`;
    const data = await proxyRequest(req, baseUrl, accessToken as string);

    return NextResponse.json(data);
  } catch (error) {
    return handleError(error);
  }
}
