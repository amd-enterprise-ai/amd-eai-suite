// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { MutableRefObject } from 'react';

import useSystemToast from '@/hooks/useSystemToast';

import { getErrorMessage } from '@/utils/app/api-helpers';

import {
  ChatBody,
  INFERENCE_CHUNK_DELIMITER,
  InferenceChunk,
} from '@/types/chat';

export const streamChatResponse = async (
  workloadId: string,
  chatBody: ChatBody,
  projectId: string,
  stopConversationRef: MutableRefObject<boolean>,
) => {
  const { toast } = useSystemToast();

  const chatController = new AbortController();
  const data = await sendChatRequest(
    workloadId,
    chatBody,
    projectId,
    chatController,
  );

  if (!data) {
    toast.error('No response received');
    throw new Error('No response received from chat request');
  }
  const decoder = new TextDecoder();

  let resolveContextPromise: (arg: any) => void;
  const chatContextPromise = new Promise<any>((resolve, _reject) => {
    resolveContextPromise = resolve;
  });

  let context = {};
  const responseStream = new ReadableStream({
    async start(controller) {
      let done = false;
      const reader = data.getReader();
      let currentChunk = '';
      while (!done) {
        if (stopConversationRef.current === true) {
          chatController.abort();
          done = true;
          break;
        }
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const decoded = decoder.decode(value);
          const chunks = decoded
            .split(INFERENCE_CHUNK_DELIMITER)
            .filter((c) => c !== '');
          for (const chunk of chunks) {
            let chunkValue: InferenceChunk;
            currentChunk += chunk;
            try {
              chunkValue = JSON.parse(currentChunk) as InferenceChunk;
            } catch (error) {
              continue;
            }
            currentChunk = '';

            if (chunkValue.content) {
              controller.enqueue(chunkValue.content);
            }
            if (chunkValue.context) {
              context = { ...context, ...chunkValue.context };
            }
          }
        }
      }
      controller.close();
      resolveContextPromise(Object.keys(context).length ? context : undefined);
    },
  });

  return {
    responseStream,
    context: chatContextPromise,
  };
};

export const sendChatRequest = async (
  workloadId: string,
  chatBody: ChatBody,
  projectId: string,
  chatController: AbortController,
) => {
  const body = JSON.stringify(chatBody);

  const response = await fetch(
    `/api/chat/${workloadId}?projectId=${projectId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: chatController.signal,
      body,
    },
  );

  if (!response.ok) {
    throw new Error(
      `Failed to send chat request: ${await getErrorMessage(response)}`,
    );
  }
  return response.body;
};
