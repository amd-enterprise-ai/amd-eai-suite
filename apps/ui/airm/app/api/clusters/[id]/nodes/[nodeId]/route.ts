// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getClusterNode } from '@/services/server';

import { authenticateRoute, handleError } from '@amdenterpriseai/utils/server';

export async function GET(
  _: NextRequest,
  { params }: { params: Promise<{ id: string; nodeId: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: clusterId, nodeId } = await params;
    const node = await getClusterNode(clusterId, nodeId, accessToken as string);

    return NextResponse.json(node);
  } catch (error) {
    return handleError(error);
  }
}
