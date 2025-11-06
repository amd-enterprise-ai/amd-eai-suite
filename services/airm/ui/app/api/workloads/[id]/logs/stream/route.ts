// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { authenticateRoute, handleError } from '@/utils/server/route';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const { accessToken } = await authenticateRoute();

    // Build the URL with query parameters
    const searchParams = req.nextUrl.searchParams;
    const paramString = searchParams.toString();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/workloads/${id}/logs/stream${paramString ? `?${paramString}` : ''}`;

    // Create a streaming response
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
        Accept: 'text/event-stream',
      },
      method: 'GET',
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch workload logs stream' },
        { status: response.status },
      );
    }

    if (!response.body) {
      return NextResponse.json(
        { error: 'No response body received' },
        { status: 500 },
      );
    }

    // Create a readable stream that transforms the upstream response
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
    let decoder: TextDecoder | null = null;

    const stream = new ReadableStream({
      start() {
        // Initialize reader and decoder
        reader = response.body!.getReader();
        decoder = new TextDecoder();
      },

      async pull(controller) {
        try {
          if (!reader || !decoder) {
            controller.error(new Error('Stream not properly initialized'));
            return;
          }

          const { done, value } = await reader.read();
          console.log(
            `[BACKEND] Read from upstream - done: ${done}, value length: ${value?.length || 0}`,
          );

          if (done) {
            console.log('[BACKEND] Upstream stream completed (done=true)');
            controller.close();
            return;
          }

          // Forward the chunk as-is for Server-Sent Events
          const chunk = decoder.decode(value, { stream: true });
          console.log(`[BACKEND] Decoded chunk:`, chunk);
          controller.enqueue(new TextEncoder().encode(chunk));
        } catch (error) {
          console.error('Stream pull error:', error);
          // Check if controller is still usable before erroring
          try {
            controller.error(error);
          } catch (controllerError) {
            console.error('Failed to error controller:', controllerError);
          }
        }
      },

      cancel() {
        // Clean up when stream is cancelled
        if (reader) {
          try {
            reader.cancel();
          } catch (error) {
            console.debug(
              'Reader cancel error (expected if already closed):',
              error,
            );
          } finally {
            reader = null;
          }
        }
        decoder = null;
      },
    });

    // Return the stream as Server-Sent Events
    return new Response(stream, {
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
