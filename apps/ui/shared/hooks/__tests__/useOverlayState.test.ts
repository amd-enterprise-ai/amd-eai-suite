// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, renderHook } from '@testing-library/react';

import { useOverlayState } from '@amdenterpriseai/hooks';

describe('useOverlayState', () => {
  it('starts closed by default', () => {
    const { result } = renderHook(() => useOverlayState());
    expect(result.current.isOpen).toBe(false);
  });

  it('opens via onOpen', () => {
    const { result } = renderHook(() => useOverlayState());
    act(() => {
      result.current.onOpen();
    });
    expect(result.current.isOpen).toBe(true);
  });

  it('closes via onClose', () => {
    const { result } = renderHook(() => useOverlayState());
    act(() => {
      result.current.onOpen();
    });
    act(() => {
      result.current.onClose();
    });
    expect(result.current.isOpen).toBe(false);
  });

  it('toggles via onOpenChange', () => {
    const { result } = renderHook(() => useOverlayState());
    act(() => {
      result.current.onOpenChange();
    });
    expect(result.current.isOpen).toBe(true);
    act(() => {
      result.current.onOpenChange();
    });
    expect(result.current.isOpen).toBe(false);
  });
});
