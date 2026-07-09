// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { INFERENCE_CHUNK_DELIMITER } from '@/types/chat';
import { InferenceChunk, StreamingChatResponse } from '@/types/chat';

/**
 * Wraps an upstream chat completion stream and re-emits each chunk in the
 * `InferenceChunk` shape expected by the AIWB UI chat client. Used by the
 * direct AIM chat handler (`aim-chat-handler.ts`).
 */
export function transformChatStream(
  upstreamBody: ReadableStream<Uint8Array>,
): Response {
  const reader = upstreamBody.getReader();
  const decoder = new TextDecoder();
  return new Response(
    new ReadableStream({
      async pull(controller) {
        try {
          let readerChunk: ReadableStreamReadResult<Uint8Array>;
          let incompleteJson = '';
          while (!(readerChunk = await reader.read()).done) {
            const jsonChunk = decoder.decode(readerChunk.value, {
              stream: true,
            });
            incompleteJson = processChunk(
              jsonChunk,
              incompleteJson,
              controller,
            );
          }
          // Flush any trailing bytes held by the streaming decoder.
          const tail = decoder.decode();
          if (tail) {
            processChunk(tail, incompleteJson, controller);
          }
        } finally {
          reader.releaseLock();
          controller.close();
        }
      },
    }),
    { headers: { 'Content-Type': 'text/plain' } },
  );
}

function processChunk(
  jsonChunk: string,
  incompleteJson: string,
  controller: ReadableStreamDefaultController,
): string {
  const jsons = jsonChunk
    .split(INFERENCE_CHUNK_DELIMITER)
    .filter((c) => c !== '');
  let pending = incompleteJson;
  for (let json of jsons) {
    if (pending) {
      json = pending + json;
      pending = '';
    }
    let jsonObject: StreamingChatResponse;
    try {
      jsonObject = JSON.parse(json);
    } catch (_) {
      pending = json;
      continue;
    }
    controller.enqueue(
      INFERENCE_CHUNK_DELIMITER +
        JSON.stringify(buildResponseChunk(jsonObject)),
    );
  }
  return pending;
}

function buildResponseChunk(jsonObject: StreamingChatResponse): InferenceChunk {
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
  return responseChunk;
}
