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
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/workloads/${id}/metrics`;
    const { workloadId, ...rest } = await proxyRequest(
      req,
      url,
      accessToken as string,
    );

    return NextResponse.json({ id: workloadId, ...rest });
  } catch (error) {
    return handleError(error);
  }
}
