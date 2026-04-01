// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { GET } from '@/app/api/clusters/[id]/nodes/[nodeId]/metrics/gpu-utilization/clock-speed/route';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@amdenterpriseai/utils/server';

vi.mock('@amdenterpriseai/utils/server', () => ({
  authenticateRoute: vi.fn(),
  handleError: vi.fn(),
  proxyRequest: vi.fn(),
}));

const mockAuthenticateRoute = vi.mocked(authenticateRoute);
const mockHandleError = vi.mocked(handleError);
const mockProxyRequest = vi.mocked(proxyRequest);

const CLUSTER_ID = 'cluster-abc';
const NODE_ID = 'node-xyz';
const START = '2024-01-01T00:00:00.000Z';
const END = '2024-01-01T01:00:00.000Z';

const makeRequest = (queryString = `start=${START}&end=${END}`) =>
  new NextRequest(
    `http://localhost:3000/api/clusters/${CLUSTER_ID}/nodes/${NODE_ID}/metrics/gpu-utilization/clock-speed?${queryString}`,
  );

const makeParams = () => Promise.resolve({ id: CLUSTER_ID, nodeId: NODE_ID });

describe('GET /api/clusters/[id]/nodes/[nodeId]/metrics/gpu-utilization/clock-speed', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthenticateRoute.mockResolvedValue({
      accessToken: 'mock-token',
    } as any);
  });

  it('proxies to the backend clock-speed endpoint and returns data', async () => {
    const mockData = {
      gpu_devices: [
        {
          gpu_uuid: 'uuid-1',
          gpu_id: '0',
          hostname: NODE_ID,
          metric: {
            series_label: 'clock_speed_mhz',
            values: [{ timestamp: START, value: 1800 }],
          },
        },
      ],
      range: { start: START, end: END },
    };
    mockProxyRequest.mockResolvedValue(mockData);

    const response = await GET(makeRequest(), { params: makeParams() });
    const data = await response.json();

    expect(mockAuthenticateRoute).toHaveBeenCalled();
    expect(mockProxyRequest).toHaveBeenCalledWith(
      expect.any(NextRequest),
      expect.stringContaining(
        `/v1/clusters/${CLUSTER_ID}/nodes/${NODE_ID}/metrics/gpu-utilization/clock-speed`,
      ),
      'mock-token',
    );
    expect(mockProxyRequest).toHaveBeenCalledWith(
      expect.any(NextRequest),
      expect.stringContaining(`start=${encodeURIComponent(START)}`),
      'mock-token',
    );
    expect(data).toEqual(mockData);
  });

  it('includes optional intervals query parameter in the upstream URL', async () => {
    mockProxyRequest.mockResolvedValue({});

    await GET(makeRequest(`start=${START}&end=${END}&intervals=60`), {
      params: makeParams(),
    });

    expect(mockProxyRequest).toHaveBeenCalledWith(
      expect.any(NextRequest),
      expect.stringContaining('intervals=60'),
      'mock-token',
    );
  });

  it('returns 400 when start query parameter is missing', async () => {
    const response = await GET(makeRequest(`end=${END}`), {
      params: makeParams(),
    });

    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toMatch(/start/i);
    expect(mockProxyRequest).not.toHaveBeenCalled();
  });

  it('returns 400 when end query parameter is missing', async () => {
    const response = await GET(makeRequest(`start=${START}`), {
      params: makeParams(),
    });

    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toMatch(/end/i);
    expect(mockProxyRequest).not.toHaveBeenCalled();
  });

  it('delegates to handleError when an exception is thrown', async () => {
    const error = new Error('upstream failure');
    mockProxyRequest.mockRejectedValue(error);
    mockHandleError.mockReturnValue(
      new Response(JSON.stringify({ error: 'upstream failure' }), {
        status: 502,
      }) as any,
    );

    const response = await GET(makeRequest(), { params: makeParams() });

    expect(mockHandleError).toHaveBeenCalledWith(error);
    expect(response.status).toBe(502);
  });
});
