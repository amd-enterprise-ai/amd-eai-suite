// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export interface Message {
  role: Role;
  content: string;
}

export type Role = 'assistant' | 'user' | 'system' | 'function';

// Type definition for the chat request body
// This type must be compatible with both our API and OpenAI's API
export interface ChatBody {
  model: string;
  messages: Message[];
  stream: boolean;
  stream_options: Record<string, any>;
  temperature: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

export interface DebugInfo {
  messages: Message[];
  usage?: TokenUsage;
}

export interface ChatContext {
  messages: Message[];
  model: string;
  usage?: TokenUsage;
}

export interface ChatMessageWithDebug extends Message {
  debugInfo?: DebugInfo;
}

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface ChatConversation {
  messages: ChatMessageWithDebug[];
  streaming: boolean; // Is the conversation still streaming
}

export interface TokenUsage {
  prompt_tokens: number;
  total_tokens: number;
  completion_tokens: number;
}

export interface InferenceChunk {
  context?: { [key: string]: any };
  content?: string;
}

export interface StreamingChatResponse {
  choices?: Array<{
    delta?: {
      content?: string;
    };
  }>;
  context?: any;
  usage?: TokenUsage;
}

export const INFERENCE_CHUNK_DELIMITER = 'data: ';
