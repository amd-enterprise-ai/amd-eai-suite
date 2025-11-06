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

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; apiKeyId: string }> },
): Promise<NextResponse<APIError>> {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: projectId, apiKeyId } = await params;

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/api-keys/${apiKeyId}/bind-group?project_id=${projectId}`;
    const res = await proxyRequest(req, url, accessToken as string);

    return NextResponse.json(res);
  } catch (error) {
    return handleError(error);
  }
}
