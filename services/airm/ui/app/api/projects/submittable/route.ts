// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function GET(request: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/submittable`;
    const json = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}
