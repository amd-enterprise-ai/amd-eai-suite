// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { transformChatStream } from '@/lib/server/chat-stream-transform';
import { INFERENCE_CHUNK_DELIMITER } from '@/types/chat';

async function readStreamText(response: Response): Promise<string> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let text = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    text += typeof value === 'string' ? value : decoder.decode(value);
  }
  return text;
}

function bytesOf(text: string): Uint8Array {
  return new TextEncoder().encode(text);
}

describe('transformChatStream', () => {
  it('emits transformed content for a single complete chunk', async () => {
    const upstream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          bytesOf(
            INFERENCE_CHUNK_DELIMITER +
              JSON.stringify({ choices: [{ delta: { content: 'hello' } }] }),
          ),
        );
        controller.close();
      },
    });
    const text = await readStreamText(transformChatStream(upstream));
    expect(text).toContain('hello');
  });

  it('decodes multi-byte UTF-8 characters split across reader chunks', async () => {
    // 🚀 (rocket) is a 4-byte UTF-8 sequence: F0 9F 9A 80.
    const payload =
      INFERENCE_CHUNK_DELIMITER +
      JSON.stringify({ choices: [{ delta: { content: 'go 🚀 fly' } }] });
    const fullBytes = bytesOf(payload);
    // Find the rocket emoji's first byte (0xF0) and split mid-emoji (e.g. after 2 of 4 bytes).
    const rocketStart = fullBytes.indexOf(0xf0);
    expect(rocketStart).toBeGreaterThan(-1);
    const splitAt = rocketStart + 2;
    const part1 = fullBytes.slice(0, splitAt);
    const part2 = fullBytes.slice(splitAt);
    const upstream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(part1);
        controller.enqueue(part2);
        controller.close();
      },
    });
    const text = await readStreamText(transformChatStream(upstream));
    expect(text).toContain('🚀');
    expect(text).toContain('go ');
    expect(text).toContain(' fly');
  });

  it('handles JSON fragments split across chunks', async () => {
    const payload =
      INFERENCE_CHUNK_DELIMITER +
      JSON.stringify({ choices: [{ delta: { content: 'split-json' } }] });
    const bytes = bytesOf(payload);
    const half = Math.floor(bytes.length / 2);
    const upstream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(bytes.slice(0, half));
        controller.enqueue(bytes.slice(half));
        controller.close();
      },
    });
    const text = await readStreamText(transformChatStream(upstream));
    expect(text).toContain('split-json');
  });
});
