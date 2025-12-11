// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: userId } = await params;

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/invited-users/${userId}/resend-invitation`;
    await proxyRequest(req, url, accessToken as string);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return handleError(error);
  }
}
