// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextResponse } from 'next/server';

import { getWorkloadsStats } from '@/services/server/workloads';

import { authenticateRoute, handleError } from '@/utils/server/route';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const { accessToken } = await authenticateRoute();
    const stats = await getWorkloadsStats(accessToken as string);

    return NextResponse.json(stats);
  } catch (error) {
    return handleError(error);
  }
}
