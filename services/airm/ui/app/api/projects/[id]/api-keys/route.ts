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
import { ApiKeysResponse } from '@/types/api-keys';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse<ApiKeysResponse | APIError>> {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: projectId } = await params;

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/api-keys?project_id=${projectId}`;

    const res = await proxyRequest(req, url, accessToken as string);

    return NextResponse.json({ apiKeys: res });
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse<APIError>> {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: projectId } = await params;

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/api-keys?project_id=${projectId}`;
    const res = await proxyRequest(req, url, accessToken as string);

    return NextResponse.json(res);
  } catch (error) {
    return handleError(error);
  }
}
