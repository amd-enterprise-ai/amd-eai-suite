// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { authenticateRoute, handleError } from '@amdenterpriseai/utils/server';

import { validatePathSegments } from './proxy-handler';
import { extractApiPath } from './route-utils';

/**
 * Generic streaming logs proxy handler.
 * Forwards log streaming requests to the backend and passes through the SSE response.
 *
 * Works for:
 * - /api/namespaces/{namespace}/workloads/{workload_id}/logs/stream
 */
async function streamingLogsHandler(req: NextRequest) {
  try {
    const apiPath = extractApiPath(req);
    const segments = apiPath.split('/').filter(Boolean);
    validatePathSegments(segments);

    const { accessToken } = await authenticateRoute();

    const searchParams = req.nextUrl.searchParams;
    const paramString = searchParams.toString();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/${apiPath}${paramString ? `?${paramString}` : ''}`;

    // Create abort controller for cleanup
    const abortController = new AbortController();

    // Listen for client disconnect
    req.signal.addEventListener('abort', () => {
      abortController.abort();
    });

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: 'text/event-stream',
      },
      signal: abortController.signal,
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch logs' },
        { status: response.status },
      );
    }

    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  } catch (error) {
    return handleError(error);
  }
}

export function GET(req: NextRequest) {
  return streamingLogsHandler(req);
}
