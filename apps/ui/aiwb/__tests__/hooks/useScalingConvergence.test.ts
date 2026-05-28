// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { useScalingConvergence } from '@/hooks/useScalingConvergence';
import type { AutoscalingFieldValues } from '@/lib/app/aims';
import type { AIMService } from '@/types/aims';

const savedSettings: AutoscalingFieldValues = {
  minReplicas: 2,
  maxReplicas: 5,
  metricQuery: 'vllm:num_requests_running',
  operationOverTime: 'avg',
  targetType: 'Value',
  targetValue: 10,
};

const makeAimService = (
  runtimeOverrides: Partial<{ minReplicas: number; maxReplicas: number }> = {},
): AIMService =>
  ({
    status: {
      runtime: {
        minReplicas: 1,
        maxReplicas: 3,
        ...runtimeOverrides,
      },
    },
  }) as unknown as AIMService;

describe('useScalingConvergence', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const defaultParams = () => ({
    aimService: undefined as AIMService | undefined,
    isAimServiceError: false,
    isPolling: false,
    onConverged: vi.fn(),
    onTimeout: vi.fn(),
  });

  it('returns startPolling and initial isPolling=false state', () => {
    const params = defaultParams();
    const { result } = renderHook(() => useScalingConvergence(params));
    expect(result.current.startPolling).toBeInstanceOf(Function);
  });

  it('does not call onConverged when not polling', () => {
    const params = defaultParams();
    params.aimService = makeAimService({
      minReplicas: savedSettings.minReplicas,
      maxReplicas: savedSettings.maxReplicas,
    });
    renderHook(() => useScalingConvergence(params));
    expect(params.onConverged).not.toHaveBeenCalled();
  });

  describe('Convergence detection', () => {
    it('calls onConverged when runtime matches saved replica values', () => {
      const params = defaultParams();
      params.isPolling = true;
      params.aimService = makeAimService();

      const { result, rerender } = renderHook(() =>
        useScalingConvergence(params),
      );

      act(() => {
        result.current.startPolling(savedSettings);
      });

      // Simulate runtime converging
      params.aimService = makeAimService({
        minReplicas: savedSettings.minReplicas,
        maxReplicas: savedSettings.maxReplicas,
      });
      rerender();

      expect(params.onConverged).toHaveBeenCalledTimes(1);
    });

    it('does not call onConverged when only minReplicas matches', () => {
      const params = defaultParams();
      params.isPolling = true;
      params.aimService = makeAimService();

      const { result, rerender } = renderHook(() =>
        useScalingConvergence(params),
      );

      act(() => {
        result.current.startPolling(savedSettings);
      });

      params.aimService = makeAimService({
        minReplicas: savedSettings.minReplicas,
        maxReplicas: 99,
      });
      rerender();

      expect(params.onConverged).not.toHaveBeenCalled();
    });

    it('does not call onConverged when only maxReplicas matches', () => {
      const params = defaultParams();
      params.isPolling = true;
      params.aimService = makeAimService();

      const { result, rerender } = renderHook(() =>
        useScalingConvergence(params),
      );

      act(() => {
        result.current.startPolling(savedSettings);
      });

      params.aimService = makeAimService({
        minReplicas: 99,
        maxReplicas: savedSettings.maxReplicas,
      });
      rerender();

      expect(params.onConverged).not.toHaveBeenCalled();
    });
  });

  describe('Error handling', () => {
    it('calls onConverged when a fetch error occurs during polling', () => {
      const params = defaultParams();
      params.isPolling = true;
      params.aimService = makeAimService();

      const { result, rerender } = renderHook(() =>
        useScalingConvergence(params),
      );

      act(() => {
        result.current.startPolling(savedSettings);
      });

      params.isAimServiceError = true;
      rerender();

      expect(params.onConverged).toHaveBeenCalledTimes(1);
    });
  });

  describe('Timeout', () => {
    it('calls onTimeout after the timeout period', () => {
      const params = defaultParams();
      params.isPolling = true;
      params.aimService = makeAimService();

      const { result } = renderHook(() => useScalingConvergence(params));

      act(() => {
        result.current.startPolling(savedSettings);
      });

      expect(params.onTimeout).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(60_000);
      });

      expect(params.onTimeout).toHaveBeenCalledTimes(1);
    });

    it('clears timeout when convergence is detected before timeout', () => {
      const params = defaultParams();
      params.isPolling = true;
      params.aimService = makeAimService();

      const { result, rerender } = renderHook(() =>
        useScalingConvergence(params),
      );

      act(() => {
        result.current.startPolling(savedSettings);
      });

      // Converge before timeout
      params.aimService = makeAimService({
        minReplicas: savedSettings.minReplicas,
        maxReplicas: savedSettings.maxReplicas,
      });
      rerender();

      expect(params.onConverged).toHaveBeenCalledTimes(1);

      // Advance past timeout -- onTimeout should NOT fire
      act(() => {
        vi.advanceTimersByTime(60_000);
      });

      expect(params.onTimeout).not.toHaveBeenCalled();
    });
  });

  describe('Rapid successive saves', () => {
    it('resets the timeout when startPolling is called again', () => {
      const params = defaultParams();
      params.isPolling = true;
      params.aimService = makeAimService();

      const { result } = renderHook(() => useScalingConvergence(params));

      act(() => {
        result.current.startPolling(savedSettings);
      });

      // Advance 50 seconds (not yet timed out)
      act(() => {
        vi.advanceTimersByTime(50_000);
      });
      expect(params.onTimeout).not.toHaveBeenCalled();

      // Save again — restarts the 60s timer
      act(() => {
        result.current.startPolling({
          ...savedSettings,
          maxReplicas: 10,
        });
      });

      // Advance another 50 seconds (100s total, but only 50s since second save)
      act(() => {
        vi.advanceTimersByTime(50_000);
      });
      expect(params.onTimeout).not.toHaveBeenCalled();

      // Advance the remaining 10 seconds to reach 60s after second save
      act(() => {
        vi.advanceTimersByTime(10_000);
      });
      expect(params.onTimeout).toHaveBeenCalledTimes(1);
    });
  });

  describe('Cleanup', () => {
    it('clears timeout on unmount', () => {
      const params = defaultParams();
      params.isPolling = true;
      params.aimService = makeAimService();

      const { result, unmount } = renderHook(() =>
        useScalingConvergence(params),
      );

      act(() => {
        result.current.startPolling(savedSettings);
      });

      unmount();

      // Advance past timeout — callback should not fire after unmount
      act(() => {
        vi.advanceTimersByTime(60_000);
      });

      expect(params.onTimeout).not.toHaveBeenCalled();
    });
  });
});
