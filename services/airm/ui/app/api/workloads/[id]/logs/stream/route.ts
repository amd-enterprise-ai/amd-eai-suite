// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { authenticateRoute } from '@/utils/server/route';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { accessToken } = await authenticateRoute();

  const searchParams = req.nextUrl.searchParams;
  const paramString = searchParams.toString();
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/workloads/${id}/logs/stream${paramString ? `?${paramString}` : ''}`;

  // ✅ Create abort controller for cleanup
  const abortController = new AbortController();

  // Listen for client disconnect
  req.signal.addEventListener('abort', () => {
    console.log('[BACKEND] Client disconnected, aborting upstream');
    abortController.abort();
  });

  // Fetch upstream
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
}
