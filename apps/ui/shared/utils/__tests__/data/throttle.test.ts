// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { throttle } from '@amdenterpriseai/utils/data';

describe('throttle', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('should call the function immediately on first invocation', () => {
    const mockFn = vi.fn();
    const throttled = throttle(mockFn, 1000);

    throttled('arg1', 'arg2');

    expect(mockFn).toHaveBeenCalledTimes(1);
    expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2');
  });

  it('should throttle subsequent calls within the limit', () => {
    const mockFn = vi.fn();
    const throttled = throttle(mockFn, 1000);

    throttled('call1');
    throttled('call2');
    throttled('call3');

    expect(mockFn).toHaveBeenCalledTimes(1);
    expect(mockFn).toHaveBeenCalledWith('call1');
  });

  it('should execute the last call after the throttle period', () => {
    const mockFn = vi.fn();
    const throttled = throttle(mockFn, 1000);

    throttled('call1');
    throttled('call2');
    throttled('call3');

    expect(mockFn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(1000);

    expect(mockFn).toHaveBeenCalledTimes(2);
    expect(mockFn).toHaveBeenLastCalledWith('call3');
  });

  it('should handle multiple throttle periods correctly', () => {
    const mockFn = vi.fn();
    const throttled = throttle(mockFn, 1000);

    throttled('call1');
    expect(mockFn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(500);
    throttled('call2');

    vi.advanceTimersByTime(500);
    expect(mockFn).toHaveBeenCalledTimes(2);

    vi.advanceTimersByTime(500);
    throttled('call3');

    vi.advanceTimersByTime(500);
    expect(mockFn).toHaveBeenCalledTimes(3);
  });

  it('should preserve function context and return type', () => {
    const mockFn = vi.fn((x: number, y: number) => x + y);
    const throttled = throttle(mockFn, 1000);

    throttled(2, 3);
    expect(mockFn).toHaveBeenCalledWith(2, 3);
  });

  it('should handle rapid successive calls', () => {
    const mockFn = vi.fn();
    const throttled = throttle(mockFn, 1000);

    // First call executes immediately
    throttled('call1');
    expect(mockFn).toHaveBeenCalledTimes(1);

    // Multiple rapid calls
    for (let i = 2; i <= 10; i++) {
      throttled(`call${i}`);
    }

    // Only the first call should have executed
    expect(mockFn).toHaveBeenCalledTimes(1);

    // After throttle period, the last call should execute
    vi.advanceTimersByTime(1000);
    expect(mockFn).toHaveBeenCalledTimes(2);
    expect(mockFn).toHaveBeenLastCalledWith('call10');
  });

  it('should cancel pending calls when a new call is made', () => {
    const mockFn = vi.fn();
    const throttled = throttle(mockFn, 1000);

    throttled('call1');
    expect(mockFn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(500);
    throttled('call2');

    vi.advanceTimersByTime(250);
    throttled('call3');

    // call2's timeout was cancelled by call3
    // call3 should execute after its delay (250ms remaining from 1000ms total)
    vi.advanceTimersByTime(250);
    expect(mockFn).toHaveBeenCalledTimes(2);
    expect(mockFn).toHaveBeenLastCalledWith('call3');
  });

  it('should work with different throttle limits', () => {
    const mockFn = vi.fn();
    const throttled = throttle(mockFn, 500);

    throttled('call1');
    expect(mockFn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(250);
    throttled('call2');

    vi.advanceTimersByTime(250);
    expect(mockFn).toHaveBeenCalledTimes(2);
  });
});
