// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import jsonwebtoken from 'jsonwebtoken';
import { NextRequest } from 'next/server';

import { POST } from '@/lib/server/aim-chat-handler';
import { clearAuthzCache } from '@/lib/server/authz-cache';
import { INFERENCE_CHUNK_DELIMITER } from '@/types/chat';

const mockAuthenticateRoute = vi.fn();

vi.mock('@amdenterpriseai/utils/server', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@amdenterpriseai/utils/server')>();
  return {
    ...actual,
    authenticateRoute: (...args: unknown[]) => mockAuthenticateRoute(...args),
  };
});

const MOCK_AIWB_URL = 'https://aiwb.example.com';
const MOCK_INTERNAL_URL = 'http://aim-internal.cluster.local';
const MOCK_ACCESS_TOKEN = 'mock-access-token';
const MOCK_USER_ID = 'alice-user-id';
const MOCK_DEPLOYMENT_ID = 'deployment-abc';
const MOCK_PROJECT = 'project-a';

function createChatRequest(
  project: string = MOCK_PROJECT,
  deploymentId: string = MOCK_DEPLOYMENT_ID,
): NextRequest {
  return new NextRequest(
    new URL(
      `/api/ui/projects/${project}/inference/${deploymentId}/chat`,
      'http://localhost:3000',
    ),
    {
      method: 'POST',
      body: JSON.stringify({ messages: [{ role: 'user', content: 'hi' }] }),
    },
  );
}

function streamingChatBody(content: string): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const payload = {
    choices: [{ delta: { content } }],
  };
  return new ReadableStream({
    start(controller) {
      controller.enqueue(
        encoder.encode(INFERENCE_CHUNK_DELIMITER + JSON.stringify(payload)),
      );
      controller.close();
    },
  });
}

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

beforeEach(() => {
  vi.stubEnv('AIRM_API_SERVICE_URL', MOCK_AIWB_URL);
  clearAuthzCache();
  mockAuthenticateRoute.mockResolvedValue({ accessToken: MOCK_ACCESS_TOKEN });
  vi.spyOn(jsonwebtoken, 'decode').mockReturnValue({ sub: MOCK_USER_ID });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

describe('aim-chat-handler', () => {
  it('resolves the internal URL and streams the chat response back', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input) => {
        const url = typeof input === 'string' ? input : (input as Request).url;
        if (url.startsWith(MOCK_AIWB_URL)) {
          return new Response(
            JSON.stringify({ endpoints: { internal: MOCK_INTERNAL_URL } }),
            { status: 200 },
          );
        }
        return new Response(streamingChatBody('hello'), { status: 200 });
      });
    const response = await POST(createChatRequest());
    expect(response.status).toBe(200);
    const text = await readStreamText(response);
    expect(text).toContain('hello');
    const aiwbCall = fetchSpy.mock.calls.find(([input]) =>
      String(
        typeof input === 'string' ? input : (input as Request).url,
      ).startsWith(MOCK_AIWB_URL),
    );
    expect(aiwbCall).toBeDefined();
    const aiwbInit = aiwbCall![1] as RequestInit;
    expect((aiwbInit.headers as Record<string, string>).Authorization).toBe(
      `Bearer ${MOCK_ACCESS_TOKEN}`,
    );
    const internalCall = fetchSpy.mock.calls.find(([input]) =>
      String(
        typeof input === 'string' ? input : (input as Request).url,
      ).startsWith(MOCK_INTERNAL_URL),
    );
    expect(internalCall).toBeDefined();
    const internalInit = internalCall![1] as RequestInit;
    expect(internalInit.method).toBe('POST');
    expect(
      (internalInit.headers as Record<string, string>).Authorization,
    ).toBeUndefined();
    expect(String(internalCall![0])).toBe(
      `${MOCK_INTERNAL_URL}/v1/chat/completions`,
    );
  });

  it('propagates 403 from the AIWB authorization check', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('forbidden', { status: 403 }),
    );
    const response = await POST(createChatRequest());
    expect(response.status).toBe(403);
  });

  it('returns 422 when endpoints.internal is missing', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ endpoints: {} }), { status: 200 }),
    );
    const response = await POST(createChatRequest());
    expect(response.status).toBe(422);
  });

  it('skips the AIWB fetch on a cache hit within TTL', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input) => {
        const url = typeof input === 'string' ? input : (input as Request).url;
        if (url.startsWith(MOCK_AIWB_URL)) {
          return new Response(
            JSON.stringify({ endpoints: { internal: MOCK_INTERNAL_URL } }),
            { status: 200 },
          );
        }
        return new Response(streamingChatBody('hi'), { status: 200 });
      });
    const first = await POST(createChatRequest());
    await readStreamText(first);
    const second = await POST(createChatRequest());
    await readStreamText(second);
    const aiwbCalls = fetchSpy.mock.calls.filter(([input]) =>
      String(
        typeof input === 'string' ? input : (input as Request).url,
      ).startsWith(MOCK_AIWB_URL),
    );
    const internalCalls = fetchSpy.mock.calls.filter(([input]) =>
      String(
        typeof input === 'string' ? input : (input as Request).url,
      ).startsWith(MOCK_INTERNAL_URL),
    );
    expect(aiwbCalls).toHaveLength(1);
    expect(internalCalls).toHaveLength(2);
  });

  it('routes chat to CHAT_INTERNAL_URL_OVERRIDE when set', async () => {
    const overrideUrl = 'http://localhost:9999';
    vi.stubEnv('CHAT_INTERNAL_URL_OVERRIDE', overrideUrl);
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input) => {
        const url = typeof input === 'string' ? input : (input as Request).url;
        if (url.startsWith(MOCK_AIWB_URL)) {
          return new Response(
            JSON.stringify({ endpoints: { internal: MOCK_INTERNAL_URL } }),
            { status: 200 },
          );
        }
        return new Response(streamingChatBody('via override'), {
          status: 200,
        });
      });
    const response = await POST(createChatRequest());
    expect(response.status).toBe(200);
    await readStreamText(response);
    const overrideCall = fetchSpy.mock.calls.find(([input]) =>
      String(
        typeof input === 'string' ? input : (input as Request).url,
      ).startsWith(overrideUrl),
    );
    expect(overrideCall).toBeDefined();
    expect(String(overrideCall![0])).toBe(`${overrideUrl}/v1/chat/completions`);
  });

  it('rejects protocol injection in project segment with 400', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const response = await POST(
      createChatRequest('foo:bar', MOCK_DEPLOYMENT_ID),
    );
    expect(response.status).toBe(400);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('rejects protocol injection in deploymentId segment with 400', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const response = await POST(createChatRequest(MOCK_PROJECT, 'foo:bar'));
    expect(response.status).toBe(400);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('rejects invalid characters in project segment with 400', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const response = await POST(
      createChatRequest('foo$bar', MOCK_DEPLOYMENT_ID),
    );
    expect(response.status).toBe(400);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('collapses concurrent first-time lookups into a single AIWB fetch', async () => {
    let aiwbCallCount = 0;
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input) => {
        const url = typeof input === 'string' ? input : (input as Request).url;
        if (url.startsWith(MOCK_AIWB_URL)) {
          aiwbCallCount += 1;
          await new Promise((resolve) => setTimeout(resolve, 50));
          return new Response(
            JSON.stringify({ endpoints: { internal: MOCK_INTERNAL_URL } }),
            { status: 200 },
          );
        }
        return new Response(streamingChatBody('hi'), { status: 200 });
      });
    const [resA, resB] = await Promise.all([
      POST(createChatRequest()),
      POST(createChatRequest()),
    ]);
    await readStreamText(resA);
    await readStreamText(resB);
    expect(aiwbCallCount).toBe(1);
    const internalCalls = fetchSpy.mock.calls.filter(([input]) =>
      String(
        typeof input === 'string' ? input : (input as Request).url,
      ).startsWith(MOCK_INTERNAL_URL),
    );
    expect(internalCalls).toHaveLength(2);
  });
});
