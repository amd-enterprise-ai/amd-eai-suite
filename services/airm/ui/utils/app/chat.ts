// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ChatContext, DebugInfo } from '@/types/chat';

export const printContextToConsole = async (
  debugMode: boolean,
  context: ChatContext | undefined,
) => {
  if (debugMode && !!context?.messages?.length) {
    const userMessage = context.messages
      .slice()
      .reverse()
      .find((m) => m.role === 'user');
    console.log(!!userMessage ? userMessage.content : 'No user message');
  }
};

export const extractDebugInfoFromContext = (
  context: ChatContext | undefined,
): DebugInfo | undefined => {
  if (!context) {
    console.error('No context available');
    return undefined;
  }
  return {
    messages: context.messages,
    sources: context.rag_sources,
    usage: context.usage,
  } as DebugInfo;
};
