// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Workload } from './workloads';
import { AIMService } from './aims';

export interface TextContent {
  type: 'text';
  text: string;
}

export interface ImageUrlContent {
  type: 'image_url';
  // eslint-disable-next-line @typescript-eslint/naming-convention
  image_url: {
    url: string;
  };
}

export type ContentItem = TextContent | ImageUrlContent;

export interface Message {
  role: Role;
  content: string | ContentItem[];
}

export type Role = 'assistant' | 'user' | 'system' | 'function';

// Type definition for the chat request body
// This type must be compatible with both our API and OpenAI's API
// OpenAI-compatible endpoints follow snake_case convention
// eslint-disable-next-line @typescript-eslint/naming-convention
export interface ChatBody {
  model?: string;
  messages: Message[];
  stream: boolean;
  // eslint-disable-next-line @typescript-eslint/naming-convention
  stream_options: Record<string, any>;
  temperature: number;
  // eslint-disable-next-line @typescript-eslint/naming-convention
  frequency_penalty?: number;
  // eslint-disable-next-line @typescript-eslint/naming-convention
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
  // eslint-disable-next-line @typescript-eslint/naming-convention
  prompt_tokens: number;
  // eslint-disable-next-line @typescript-eslint/naming-convention
  total_tokens: number;
  // eslint-disable-next-line @typescript-eslint/naming-convention
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

export type ChattableResponse = {
  aimServices: AIMService[];
  workloads: Workload[];
};

export enum ChatWorkloadType {
  AIMService = 'aimservice',
  Workload = 'workload',
}
