// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { DebugInfo, Message, ChatMessageWithDebug } from '@/types/chat';

import type { InferenceSettings } from '@/types/models';

export const mockInferenceSettings: InferenceSettings = {
  systemPrompt: 'Test system prompt',
  temperature: 0.5,
  frequencyPenalty: 0.2,
  presencePenalty: 0.1,
};

export const mockInferenceSettingsExtreme: InferenceSettings = {
  systemPrompt: '',
  temperature: 1.0,
  frequencyPenalty: -2.0,
  presencePenalty: 2.0,
};

export const mockUserMessage: Message = {
  role: 'user',
  content: 'Hello, this is a user message',
};

export const mockAssistantMessage: Message = {
  role: 'assistant',
  content: 'Hello! This is an assistant response with **markdown**.',
};

export const mockSystemMessage: Message = {
  role: 'system',
  content: 'This is a system message',
};

export const mockDebugInfo: DebugInfo = {
  messages: [mockUserMessage, mockAssistantMessage],
};

export const mockAssistantMessageWithDebugInfo: ChatMessageWithDebug = {
  role: 'assistant',
  content: 'This is a message with debug information',
  debugInfo: mockDebugInfo,
};

export const mockEditableMessage: Message = {
  role: 'user',
  content: 'This is an editable message',
};

export const mockLongMessage: Message = {
  role: 'assistant',
  content:
    'This is a very long message that might need to be truncated or handled specially in the UI. '.repeat(
      10,
    ),
};

export const mockEmptyMessage: Message = {
  role: 'user',
  content: '',
};

export const mockMarkdownMessage: Message = {
  role: 'assistant',
  content: '# Heading\n\nThis is **bold** text and `code`.',
};

export const mockUserMarkdownMessage: Message = {
  role: 'user',
  content:
    '# This should not be rendered as heading\n\n**This should not be bold**',
};
