// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { authenticateRoute, handleError } from '@/utils/server/route';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id } = await params;
    const projectId = request.nextUrl.searchParams.get('project_id') || '';
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/datasets/${id}/download?project_id=${projectId}`;

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      method: 'GET',
    });

    const data = await response.text();

    const headers = new Headers({
      'Content-Type': 'application/jsonl',
      'Content-Disposition': `attachment; filename=dataset-${id}.jsonl`,
    });

    return new NextResponse(data, {
      status: 200,
      statusText: 'OK',
      headers,
    });
  } catch (error) {
    return handleError(error);
  }
}
