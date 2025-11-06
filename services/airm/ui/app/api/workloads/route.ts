// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getWorkloads } from '@/services/server/workloads';

import { authenticateRoute, handleError } from '@/utils/server/route';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();
    const searchParams = req.nextUrl.searchParams;
    const type = (searchParams.get('type') as string) || '';
    const withResources = searchParams.get('withResources') === 'true';
    const status = (searchParams.get('status') as string) || '';
    const projectId = (searchParams.get('projectId') as string) || '';

    const workloads = await getWorkloads({
      type,
      status,
      withResources,
      accessToken: accessToken as string,
      projectId,
    });

    return NextResponse.json(workloads);
  } catch (error) {
    return handleError(error);
  }
}
