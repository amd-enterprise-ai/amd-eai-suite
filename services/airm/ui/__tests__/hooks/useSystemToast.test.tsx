// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { renderHook } from '@testing-library/react-hooks';
import { toast } from 'react-toastify';

import useSystemToast from '../../hooks/useSystemToast';

import { APIRequestError } from '@/utils/app/errors';

vi.mock('react-toastify', () => {
  const _toast = vi.fn() as any;
  _toast.error = vi.fn();
  _toast.info = vi.fn();
  _toast.warning = vi.fn();
  _toast.success = vi.fn();

  return {
    toast: _toast,
  };
});

describe('useSystemToast', () => {
  it('should call toast with correct content and options', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Test Toast';
    const toastOptions = { autoClose: 3000 };

    result.current.toast(toastContent, toastOptions);

    expect(toast).toHaveBeenCalledWith(toastContent, toastOptions);
  });

  it('should call toast.error with correct content and styles', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Error Toast';

    result.current.toast.error(toastContent);

    expect(toast.error).toHaveBeenCalledWith(
      toastContent,
      expect.objectContaining({
        icon: expect.anything(),
        style: expect.objectContaining({
          background: 'var(--toastify-background-error)',
          color: 'var(--toastify-text-error)',
        }),
      }),
    );
  });

  it('should call toast.error with string as param', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Error Toast';

    result.current.toast.error(toastContent);

    expect(toast.error).toHaveBeenCalledWith(toastContent, expect.anything());
  });

  it('should call toast.error with error instance message as param if status is in 400 class', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Generic error Toast';

    const apiError = new APIRequestError('Error message from API', 400);

    result.current.toast.error(toastContent, apiError);

    expect(toast.error).toHaveBeenCalledWith(
      apiError.message,
      expect.anything(),
    );
  });

  it('should call toast.error with toast message as param if status is not 400 class', () => {
    const { result } = renderHook(() => useSystemToast());
    const apiError = new APIRequestError('Error message from API', 500);
    const toastContent = 'Generic error Toast';

    result.current.toast.error(toastContent, apiError);

    expect(toast.error).toHaveBeenCalledWith(toastContent, expect.anything());
  });

  it('should call toast.info with correct content and styles', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Info Toast';

    result.current.toast.info(toastContent);

    expect(toast.info).toHaveBeenCalledWith(
      toastContent,
      expect.objectContaining({
        icon: expect.anything(),
      }),
    );
  });

  it('should call toast.warning with correct content and styles', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Warning Toast';

    result.current.toast.warning(toastContent);

    expect(toast.warning).toHaveBeenCalledWith(
      toastContent,
      expect.objectContaining({
        icon: expect.anything(),
        style: expect.objectContaining({
          background: 'var(--toastify-background-warning)',
          color: 'var(--toastify-text-warning)',
        }),
      }),
    );
  });

  it('should call toast.success with correct content and styles', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Success Toast';

    result.current.toast.success(toastContent);

    expect(toast.success).toHaveBeenCalledWith(
      toastContent,
      expect.objectContaining({
        icon: expect.anything(),
      }),
    );
  });
});
