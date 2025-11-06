// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// Test to verify the streaming bug fix
// This test demonstrates that the stream properly handles the closed controller state

import { getWorkloadLogsStream } from '@/services/app/workloads';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock fetch to simulate the streaming response
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('getWorkloadLogsStream bug fix', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not enqueue data to a closed stream', async () => {
    // Mock a response that sends data after [DONE]
    const mockResponse = new Response(
      new ReadableStream({
        start(controller) {
          // Simulate receiving data and then [DONE] and then more data
          // Each event should be separated by double newlines
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"timestamp":"2023-01-01T00:00:00Z","level":"info","message":"First log"}\n\n',
            ),
          );
          controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"timestamp":"2023-01-01T00:00:01Z","level":"info","message":"Should not be processed"}\n\n',
            ),
          );
          controller.close();
        },
      }),
      {
        headers: { 'Content-Type': 'text/event-stream' },
      },
    );

    mockFetch.mockResolvedValue(mockResponse);

    const stream = await getWorkloadLogsStream('test-workload-id');
    const reader = stream.getReader();

    const logs = [];

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        logs.push(value);
      }
    } catch (error) {
      // Should not throw an error about closed stream
      expect(error).toBeUndefined();
    }

    // Should only get the first log, not the one after [DONE]
    expect(logs).toHaveLength(1);
    expect(logs[0].message).toBe('First log');
  });

  it('should handle parsing errors gracefully without closing the stream', async () => {
    const mockResponse = new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"timestamp":"2023-01-01T00:00:00Z","level":"info","message":"Valid log"}\n\n',
            ),
          );
          controller.enqueue(
            new TextEncoder().encode('data: invalid json\n\n'),
          );
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"timestamp":"2023-01-01T00:00:01Z","level":"info","message":"Another valid log"}\n\n',
            ),
          );
          controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
          controller.close();
        },
      }),
      {
        headers: { 'Content-Type': 'text/event-stream' },
      },
    );

    mockFetch.mockResolvedValue(mockResponse);

    const stream = await getWorkloadLogsStream('test-workload-id');
    const reader = stream.getReader();

    const logs = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      logs.push(value);
    }

    // Should get both valid logs, skipping the invalid JSON
    expect(logs).toHaveLength(2);
    expect(logs[0].message).toBe('Valid log');
    expect(logs[1].message).toBe('Another valid log');
  });

  it('should handle stream read errors without throwing controller errors', async () => {
    // Mock a response that will cause a read error
    const mockResponse = new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"timestamp":"2023-01-01T00:00:00Z","level":"info","message":"Valid log"}\n\n',
            ),
          );
          // Simulate a stream error after some delay to allow processing
          setTimeout(() => {
            controller.error(new Error('Simulated stream error'));
          }, 10);
        },
      }),
      {
        headers: { 'Content-Type': 'text/event-stream' },
      },
    );

    mockFetch.mockResolvedValue(mockResponse);

    const stream = await getWorkloadLogsStream('test-workload-id');
    const reader = stream.getReader();

    const logs = [];

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        logs.push(value);
      }
    } catch (error) {
      // Should handle the error gracefully
      expect(error).toBeDefined();
    }

    // Should get the log before the error occurred
    expect(logs).toHaveLength(1);
    expect(logs[0].message).toBe('Valid log');
  });

  it('should handle reader cancellation without throwing locked stream errors', async () => {
    let controllerClosed = false;
    const mockResponse = new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"timestamp":"2023-01-01T00:00:00Z","level":"info","message":"Test log"}\n\n',
            ),
          );
          // Keep the stream open for cancellation test
          setTimeout(() => {
            // Check if controller is still open before enqueuing
            if (!controllerClosed && controller.desiredSize !== null) {
              try {
                controller.enqueue(
                  new TextEncoder().encode('data: [DONE]\n\n'),
                );
                controller.close();
                controllerClosed = true;
              } catch (error) {
                // Controller might already be closed, ignore the error
                controllerClosed = true;
              }
            }
          }, 100);
        },
        cancel() {
          controllerClosed = true;
        },
      }),
      {
        headers: { 'Content-Type': 'text/event-stream' },
      },
    );

    mockFetch.mockResolvedValue(mockResponse);

    const stream = await getWorkloadLogsStream('test-workload-id');
    const reader = stream.getReader();

    // Start reading but cancel before completion
    const readPromise = reader.read();

    // Cancel the reader (this should not throw)
    await expect(reader.cancel()).resolves.toBeUndefined();

    // The read should complete or be cancelled
    try {
      await readPromise;
    } catch (error) {
      // Cancellation might cause a read error, which is expected
      expect(error).toBeDefined();
    }
  });
});
