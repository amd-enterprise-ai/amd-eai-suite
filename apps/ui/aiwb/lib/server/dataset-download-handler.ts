// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { authenticateRoute, handleError } from '@amdenterpriseai/utils/server';

import { extractApiPath } from './route-utils';
import { validatePathSegments } from './proxy-handler';

export const maxDuration = 3600;

async function datasetDownloadHandler(req: NextRequest) {
  try {
    const apiPath = extractApiPath(req);
    const segments = apiPath.split('/').filter(Boolean);
    validatePathSegments(segments);

    const { accessToken } = await authenticateRoute();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/${apiPath}`;

    // Create abort controller for cleanup on client disconnect
    const abortController = new AbortController();

    // Listen for client disconnect to cancel upstream fetch
    req.signal.addEventListener(
      'abort',
      () => {
        abortController.abort();
      },
      { once: true },
    );

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      method: 'GET',
      signal: abortController.signal,
    });

    if (!response.ok) {
      // Proxy backend error response instead of throwing
      const headers = new Headers();
      response.headers.forEach((value, key) => {
        headers.set(key, value);
      });
      return new NextResponse(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    }

    // Forward Content-Type and Content-Disposition headers from backend
    const headers = new Headers();
    const contentType = response.headers.get('Content-Type');
    const contentDisposition = response.headers.get('Content-Disposition');

    if (contentType) {
      headers.set('Content-Type', contentType);
    }
    if (contentDisposition) {
      headers.set('Content-Disposition', contentDisposition);
    }

    // Prevents event loop blocking to allow health checks to continue during large downloads
    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  } catch (error) {
    return handleError(error);
  }
}

export function GET(req: NextRequest) {
  return datasetDownloadHandler(req);
}
