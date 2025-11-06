// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

import { APIError } from '@/types/apis';

export async function GET(req: NextRequest): Promise<NextResponse<APIError>> {
  try {
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/secrets`;

    const { accessToken } = await authenticateRoute();

    const res = await proxyRequest(req, url, accessToken as string);

    return NextResponse.json(res);
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/secrets`;
    const json = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}
