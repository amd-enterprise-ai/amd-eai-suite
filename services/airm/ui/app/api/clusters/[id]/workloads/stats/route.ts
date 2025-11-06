// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getClusterWorkloadsStats } from '@/services/server/workloads';

import { authenticateRoute, handleError } from '@/utils/server/route';

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: clusterId } = await params;
    const stats = await getClusterWorkloadsStats(
      clusterId,
      accessToken as string,
    );

    return NextResponse.json(stats);
  } catch (error) {
    return handleError(error);
  }
}
