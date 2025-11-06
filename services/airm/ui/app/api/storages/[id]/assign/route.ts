// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();

    const { id: storageId } = await params;
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/storages/${storageId}/assign`;
    const response = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(response);
  } catch (error) {
    return handleError(error);
  }
}
