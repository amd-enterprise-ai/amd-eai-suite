// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@amdenterpriseai/utils/server';

import { APIError } from '@amdenterpriseai/types';
import { TimeSeriesResponse } from '@amdenterpriseai/types';

export async function GET(
  req: NextRequest,
): Promise<NextResponse<TimeSeriesResponse | APIError>> {
  try {
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/metrics/utilization`;

    const { accessToken } = await authenticateRoute();

    const res = await proxyRequest(req, url, accessToken as string);

    return NextResponse.json(res);
  } catch (error) {
    return handleError(error);
  }
}
