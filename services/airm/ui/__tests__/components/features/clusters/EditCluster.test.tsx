// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import { editCluster } from '@/services/app/clusters';

import { generateClustersMock } from '../../../../__mocks__/utils/cluster-mock';

import { EditCluster } from '@/components/features/clusters';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('@/hooks/useSystemToast', () => {
  const useSystemToast = () => {
    const toast = vi.fn() as any;
    toast.success = toastSuccessMock;
    toast.error = toastErrorMock;
    return { toast };
  };
  return { default: useSystemToast };
});

vi.mock('@/services/app/clusters', () => ({
  editCluster: vi.fn(),
}));

const mockCluster = generateClustersMock(1)[0];
const mockOnOpenChange = vi.fn();

const renderEditCluster = (
  onOpenChange = mockOnOpenChange,
  isOpen = true,
  cluster = mockCluster,
) => {
  return act(() => {
    render(
      <EditCluster
        onOpenChange={onOpenChange}
        isOpen={isOpen}
        cluster={cluster}
      />,
      { wrapper },
    );
  });
};

describe('EditCluster', () => {
  beforeEach(() => {
    (editCluster as Mock).mockClear();
    mockOnOpenChange.mockClear();
  });

  it('renders EditCluster component', async () => {
    await renderEditCluster();
    const modelTitle = screen.getAllByText('form.edit.title');
    expect(modelTitle.length).toBeGreaterThan(0);
  });

  it('Invalid cluster base URL will show error', async () => {
    (editCluster as Mock).mockResolvedValueOnce({
      ...mockCluster,
    });
    await renderEditCluster();

    const baseUrlInput = screen.getByLabelText('form.edit.field.baseUrl.label');
    await fireEvent.change(baseUrlInput, { target: { value: 'invalid-url' } });

    await waitFor(() =>
      expect(
        screen.getByText('form.edit.field.baseUrl.error.invalid'),
      ).toBeInTheDocument(),
    );
  });

  it('Cluster base URL will be passed to API call', async () => {
    (editCluster as Mock).mockResolvedValueOnce({
      ...mockCluster,
    });
    await renderEditCluster();

    const baseUrlInput = screen.getByLabelText('form.edit.field.baseUrl.label');
    fireEvent.change(baseUrlInput, {
      target: { value: 'https://example.com' },
    });

    const saveButton = screen.getByText('form.edit.action.save');
    await fireEvent.click(saveButton);

    await waitFor(() => {
      expect(editCluster).toHaveBeenCalledWith(mockCluster.id, {
        base_url: 'https://example.com',
      });
    });
  });

  it('changes will not be saved if cluster is falsey', async () => {
    (editCluster as Mock).mockResolvedValueOnce({
      ...mockCluster,
    });
    await renderEditCluster(mockOnOpenChange, true, undefined);

    const baseUrlInput = screen.getByLabelText('form.edit.field.baseUrl.label');
    fireEvent.change(baseUrlInput, {
      target: { value: 'https://example.com' },
    });

    const saveButton = screen.getByText('form.edit.action.save');
    await fireEvent.click(saveButton);

    expect(editCluster).not.toHaveBeenCalledWith();
  });

  it('Cancel will call onOpenChange with false', async () => {
    await renderEditCluster();

    const cancelButton = screen.getByText('form.edit.action.cancel');
    await fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('show success toast', async () => {
    (editCluster as Mock).mockResolvedValueOnce({
      ...mockCluster,
    });
    await renderEditCluster();

    const baseUrlInput = screen.getByLabelText('form.edit.field.baseUrl.label');
    await fireEvent.change(baseUrlInput, {
      target: { value: 'https://example.com' },
    });

    const saveButton = screen.getByText('form.edit.action.save');
    await fireEvent.click(saveButton);

    await waitFor(() => {
      expect(editCluster).toHaveBeenCalledWith(mockCluster.id, {
        base_url: 'https://example.com',
      });
    });

    expect(toastSuccessMock).toHaveBeenCalledWith(
      'form.edit.notification.success',
    );
  });

  it('show error toast', async () => {
    const mockErrorPayload = { message: 'some error' };
    (editCluster as Mock).mockRejectedValueOnce(mockErrorPayload);
    await renderEditCluster();

    const baseUrlInput = screen.getByLabelText('form.edit.field.baseUrl.label');
    await fireEvent.change(baseUrlInput, {
      target: { value: 'https://example.com' },
    });

    const saveButton = screen.getByText('form.edit.action.save');
    await fireEvent.click(saveButton);

    await waitFor(() => {
      expect(editCluster).toHaveBeenCalledWith(mockCluster.id, {
        base_url: 'https://example.com',
      });
    });

    expect(toastErrorMock).toHaveBeenCalledWith(
      'form.edit.notification.error',
      mockErrorPayload,
    );
  });
});
