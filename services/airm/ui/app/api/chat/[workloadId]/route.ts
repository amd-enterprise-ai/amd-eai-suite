// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';

import { authenticateRoute, handleError } from '@/utils/server/route';

import {
  INFERENCE_CHUNK_DELIMITER,
  InferenceChunk,
  StreamingChatResponse,
} from '@/types/chat';

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ workloadId: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { workloadId } = await params;

    const searchParams = req.nextUrl.searchParams;
    const projectId = (searchParams.get('projectId') as string) || '';

    const body = await req.json();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/managed-workloads/${workloadId}/chat?project_id=${projectId}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      method: 'POST',
      body: JSON.stringify(body),
    });

    const decoder = new TextDecoder();

    if (response.status !== 200) {
      const result = await response.json();
      throw new Error(
        `Chat endpoint returned error: ${JSON.stringify(result)}`,
      );
    }

    const reader = response.body?.getReader();

    if (!reader) {
      throw new Error('Response body is not readable');
    }

    return new Response(
      new ReadableStream({
        async pull(controller) {
          try {
            let readerChunk: ReadableStreamReadResult<Uint8Array>;
            let incompleteJson = '';

            while (!(readerChunk = await reader.read()).done) {
              const jsonChunk = decoder.decode(readerChunk.value);
              const jsons = jsonChunk
                .split(INFERENCE_CHUNK_DELIMITER)
                .filter((c) => c !== '');

              for (let json of jsons) {
                if (incompleteJson) {
                  json = incompleteJson + json;
                  incompleteJson = '';
                }

                let jsonObject: StreamingChatResponse;
                incompleteJson = '';
                try {
                  jsonObject = JSON.parse(json);
                } catch (_) {
                  incompleteJson += json;
                  continue;
                }
                const content = jsonObject.choices?.[0]?.delta?.content;
                const responseChunk: InferenceChunk = {};
                if (content) {
                  responseChunk.content = content;
                }
                if (jsonObject.context) {
                  responseChunk.context = jsonObject.context;
                }
                if (jsonObject.usage) {
                  responseChunk.context = {
                    ...responseChunk.context,
                    usage: jsonObject.usage,
                  };
                }
                controller.enqueue(
                  INFERENCE_CHUNK_DELIMITER + JSON.stringify(responseChunk),
                );
              }
            }
          } finally {
            reader.releaseLock();
            controller.close();
          }
        },
      }),
      { headers: { 'Content-Type': 'text/plain' } },
    );
  } catch (error) {
    return handleError(error);
  }
}
