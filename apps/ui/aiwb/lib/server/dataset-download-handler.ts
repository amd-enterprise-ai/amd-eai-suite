// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { authenticateRoute, handleError } from '@amdenterpriseai/utils/server';

import { extractApiPath } from './route-utils';
import { validatePathSegments } from './proxy-handler';

async function datasetDownloadHandler(req: NextRequest) {
  try {
    const apiPath = extractApiPath(req);
    const segments = apiPath.split('/').filter(Boolean);
    validatePathSegments(segments);

    const { accessToken } = await authenticateRoute();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/${apiPath}`;

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      method: 'GET',
    });

    const data = await response.text();
    // segments: ['namespaces', namespace, 'datasets', datasetId, 'download']
    const datasetId = segments[3] || 'unknown';

    return new NextResponse(data, {
      status: 200,
      statusText: 'OK',
      headers: {
        'Content-Type': 'application/jsonl',
        'Content-Disposition': `attachment; filename=dataset-${datasetId}.jsonl`,
      },
    });
  } catch (error) {
    return handleError(error);
  }
}

export function GET(req: NextRequest) {
  return datasetDownloadHandler(req);
}
