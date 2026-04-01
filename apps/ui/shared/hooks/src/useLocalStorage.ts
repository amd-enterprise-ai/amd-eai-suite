// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useState } from 'react';

import { getStorageItem, setStorageItem } from '@amdenterpriseai/utils/app';

/**
 * Hook that syncs state with localStorage.
 * On the client, initial state is read from localStorage so the value is correct
 * on first paint after navigation. On the server
 * or when no stored value exists, uses initialValue.
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [state, setState] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue;
    const stored = getStorageItem(key) as T | null | undefined;
    return stored !== null && stored !== undefined ? stored : initialValue;
  });

  useEffect(() => {
    const stored = getStorageItem(key) as T | null | undefined;
    if (stored !== null && stored !== undefined) setState(stored);
  }, [key]);

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setState((prev) => {
        const next =
          typeof value === 'function' ? (value as (prev: T) => T)(prev) : value;
        setStorageItem(key, next);
        return next;
      });
    },
    [key],
  );

  return [state, setValue];
}
