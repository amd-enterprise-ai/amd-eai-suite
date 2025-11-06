// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getClusterNodes } from '@/services/server/clusters';

import { authenticateRoute, handleError } from '@/utils/server/route';

export async function GET(
  _: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: clusterId } = await params;
    const cluster = await getClusterNodes(clusterId, accessToken as string);

    return NextResponse.json(cluster);
  } catch (error) {
    return handleError(error);
  }
}
