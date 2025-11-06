// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/aims/${params.id}`;
    const json = await proxyRequest(req, baseUrl, accessToken as string);

    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/aims/${params.id}`;
    const json = await proxyRequest(req, baseUrl, accessToken as string);

    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}
