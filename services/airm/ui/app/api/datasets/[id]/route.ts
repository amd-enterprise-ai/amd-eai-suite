// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { convertSnakeToCamel } from '@/utils/app/api-helpers';
import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id } = await params;
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/datasets/${id}`;
    const json = await proxyRequest(req, baseUrl, accessToken as string);

    return NextResponse.json(convertSnakeToCamel(json));
  } catch (error) {
    return handleError(error);
  }
}
