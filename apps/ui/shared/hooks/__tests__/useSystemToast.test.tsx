// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { renderHook } from '@testing-library/react';
import { toast } from 'react-toastify';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { APIRequestError } from '@amdenterpriseai/utils/app';

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
      expect.objectContaining({
        props: expect.objectContaining({
          content: toastContent,
          copyText: toastContent,
        }),
      }),
      expect.objectContaining({
        icon: expect.anything(),
        style: expect.objectContaining({
          background: 'var(--toastify-background-error)',
          color: 'var(--toastify-text-error)',
        }),
      }),
    );
  });

  it('should make a string error message copyable', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Error Toast';

    result.current.toast.error(toastContent);

    expect(toast.error).toHaveBeenCalledWith(
      expect.objectContaining({
        props: expect.objectContaining({ copyText: toastContent }),
      }),
      expect.anything(),
    );
  });

  it('should not provide copy text for non-string content', () => {
    const { result } = renderHook(() => useSystemToast());

    result.current.toast.error(<span>Rich error</span>);

    expect(toast.error).toHaveBeenCalledWith(
      expect.objectContaining({
        props: expect.objectContaining({ copyText: undefined }),
      }),
      expect.anything(),
    );
  });

  it('should call toast.error with error message when APIRequestError is provided', () => {
    const { result } = renderHook(() => useSystemToast());
    const toastContent = 'Generic error Toast';

    const apiError = new APIRequestError(
      'Failed to get resource: Error message from API',
      400,
    );

    result.current.toast.error(toastContent, apiError);

    expect(toast.error).toHaveBeenCalledWith(
      expect.objectContaining({
        props: expect.objectContaining({
          content: 'Failed to get resource: Error message from API',
          copyText: 'Failed to get resource: Error message from API',
        }),
      }),
      expect.anything(),
    );
  });

  it('should call toast.error with error message for any status code', () => {
    const { result } = renderHook(() => useSystemToast());
    const apiError = new APIRequestError(
      'Failed to process request: Server error',
      500,
    );
    const toastContent = 'Generic error Toast';

    result.current.toast.error(toastContent, apiError);

    expect(toast.error).toHaveBeenCalledWith(
      expect.objectContaining({
        props: expect.objectContaining({
          content: 'Failed to process request: Server error',
        }),
      }),
      expect.anything(),
    );
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
