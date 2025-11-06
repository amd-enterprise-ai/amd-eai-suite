// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, renderHook } from '@testing-library/react';

import { useDebouncedCallback } from '../../hooks/useDebouncedCallback';

describe('useDebouncedCallback', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runAllTimers();
    vi.useRealTimers();
  });

  it('debounces multiple rapid calls and uses the latest arguments', () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(fn, 100));

    act(() => {
      result.current('first');
      vi.advanceTimersByTime(50);
      result.current('second');
      vi.advanceTimersByTime(99);
    });

    expect(fn).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });

    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenLastCalledWith('second');
  });

  it('returns a stable function when delay is unchanged but changes when delay differs', () => {
    const fn = vi.fn();
    const { result, rerender } = renderHook(
      ({ delay }) => useDebouncedCallback(fn, delay),
      { initialProps: { delay: 100 } },
    );

    const firstIdentity = result.current;
    rerender({ delay: 100 });
    expect(result.current).toBe(firstIdentity); // unchanged delay -> stable identity
    rerender({ delay: 200 });
    expect(result.current).not.toBe(firstIdentity); // changed delay -> new identity
  });

  it('delay of 0 defers execution to next macrotask', () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(fn, 0));

    act(() => {
      result.current('x');
      // Even with delay 0, should not run synchronously
      expect(fn).not.toHaveBeenCalled();
      vi.runAllTimers();
    });

    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('x');
  });

  it('cancels previous scheduled call when invoked again before delay', () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(fn, 200));

    act(() => {
      result.current('one');
      vi.advanceTimersByTime(150);
      result.current('two');
      vi.advanceTimersByTime(199);
    });

    expect(fn).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });

    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenLastCalledWith('two');
  });
});
