// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getClusters } from '@/services/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@amdenterpriseai/utils/server';

export async function GET() {
  try {
    const { accessToken } = await authenticateRoute();
    const clusters = await getClusters(accessToken as string);

    return NextResponse.json(clusters);
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters`;
    const json = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}
