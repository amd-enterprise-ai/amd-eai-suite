// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { RetrievalContext } from './retrieval';

export interface Message {
  role: Role;
  content: string;
}

export type Role = 'assistant' | 'user' | 'system' | 'function';

// Type definition for the chat request body
// This type must be compatible with both our API and OpenAI's API
export interface ChatBody {
  model: string;
  collection?: RetrievalContext;
  messages: Message[];
  stream: boolean;
  stream_options: Record<string, any>;
  temperature: number;
  prompt_template?: string;
  debug?: boolean;
  frequency_penalty?: number;
  presence_penalty?: number;
}

export interface DebugInfo {
  messages: Message[];
  sources: Source[];
  usage?: TokenUsage;
}

export interface ChatContext {
  messages: Message[];
  model: string;
  rag_sources: Source[];
  usage?: TokenUsage;
}

export interface Source {
  url: string;
  sourceId: string;
  text: string;
  score?: number;
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

export const INFERENCE_CHUNK_DELIMITER = 'data: ';
