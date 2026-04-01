// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useRef } from 'react';

export const useDebouncedCallback = <T extends (...args: any[]) => void>(
  callback: T,
  delay: number,
) => {
  const callbackRef = useRef(callback);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const argsRef = useRef<Parameters<T> | null>(null);

  // Always keep latest callback
  callbackRef.current = callback;

  const debounced = useCallback(
    (...args: Parameters<T>) => {
      // Store latest args
      argsRef.current = args;

      // Clear any existing timeout
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }

      // Schedule new timeout (even if delay === 0 to ensure async)
      timerRef.current = setTimeout(() => {
        const latestArgs = argsRef.current;
        if (latestArgs) {
          callbackRef.current(...latestArgs);
        }
      }, delay);
    },
    [delay],
  );

  // Cleanup on unmount or delay change
  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
    };
  }, [delay]);

  return debounced;
};
