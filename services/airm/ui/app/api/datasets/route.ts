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

export const maxDuration = 3600; // 1 hour for large file uploads

export async function GET(req: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/datasets`;
    const json = await proxyRequest(req, baseUrl, accessToken as string);

    return NextResponse.json(convertSnakeToCamel(json));
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(req: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();
    const projectId = req.nextUrl.searchParams.get('project_id') || '';
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/datasets/upload?project_id=${projectId}`;

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        // Forward the content-type header with boundary from the original request
        'Content-Type': req.headers.get('content-type') || '',
      },
      method: 'POST',
      // Use duplex mode to enable request body streaming
      // @ts-expect-error - duplex  is not yet in TypeScript types but is required for streaming
      duplex: 'half',
      body: req.body,
    });

    return NextResponse.json(await response.json());
  } catch (error) {
    return handleError(error);
  }
}
