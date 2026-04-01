// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';

import { authenticateRoute, handleError } from '@amdenterpriseai/utils/server';

import {
  INFERENCE_CHUNK_DELIMITER,
  InferenceChunk,
  StreamingChatResponse,
} from '@amdenterpriseai/types';

import { extractApiPath } from './route-utils';

/**
 * Generic streaming chat proxy handler.
 * Forwards chat requests to the backend and streams transformed responses back.
 *
 * Works for both:
 * - /api/namespaces/{namespace}/aims/services/{id}/chat
 * - /api/namespaces/{namespace}/workloads/{workload_id}/chat
 */
async function streamingChatHandler(req: NextRequest) {
  try {
    const apiPath = extractApiPath(req);
    const { accessToken } = await authenticateRoute();

    const body = await req.json();
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/${apiPath}`;

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

export function POST(req: NextRequest) {
  return streamingChatHandler(req);
}
