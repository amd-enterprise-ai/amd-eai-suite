// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextResponse } from 'next/server';

import { getClusterStats } from '@/services/server';

import { authenticateRoute, handleError } from '@amdenterpriseai/utils/server';

export async function GET() {
  try {
    const { accessToken } = await authenticateRoute();
    const clusters = await getClusterStats(accessToken as string);

    return NextResponse.json(clusters);
  } catch (error) {
    return handleError(error);
  }
}
