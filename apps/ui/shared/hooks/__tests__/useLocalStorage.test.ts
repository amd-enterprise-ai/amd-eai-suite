// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { useLocalStorage } from '@amdenterpriseai/hooks';

const mockGetStorageItem = vi.fn();
const mockSetStorageItem = vi.fn();

vi.mock('@amdenterpriseai/utils/app', () => ({
  getStorageItem: (key: string) => mockGetStorageItem(key),
  setStorageItem: (key: string, value: unknown) =>
    mockSetStorageItem(key, value),
}));

describe('useLocalStorage', () => {
  const key = 'test-key';

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetStorageItem.mockReturnValue(null);
  });

  it('returns initialValue when no value is stored', () => {
    const initialValue = { foo: 'bar' };
    mockGetStorageItem.mockReturnValue(null);

    const { result } = renderHook(() => useLocalStorage(key, initialValue));

    expect(result.current[0]).toBe(initialValue);
  });

  it('after mount, hydrates from localStorage when stored value exists', async () => {
    const stored = { foo: 'stored' };
    mockGetStorageItem.mockReturnValue(stored);

    const { result } = renderHook(() =>
      useLocalStorage(key, { foo: 'initial' }),
    );

    await waitFor(() => {
      expect(mockGetStorageItem).toHaveBeenCalledWith(key);
      expect(result.current[0]).toEqual(stored);
    });
  });

  it('setter updates state and calls setStorageItem', () => {
    const { result } = renderHook(() => useLocalStorage(key, 'initial'));

    act(() => {
      result.current[1]('updated');
    });

    expect(result.current[0]).toBe('updated');
    expect(mockSetStorageItem).toHaveBeenCalledWith(key, 'updated');
  });

  it('setter supports functional update', () => {
    const { result } = renderHook(() => useLocalStorage(key, 10));

    act(() => {
      result.current[1]((prev) => prev + 5);
    });

    expect(result.current[0]).toBe(15);
    expect(mockSetStorageItem).toHaveBeenCalledWith(key, 15);
  });
});
